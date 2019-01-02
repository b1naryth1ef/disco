import gevent
import zlib
import six
import ssl

from websocket import ABNF

from disco.gateway.packets import OPCode, RECV, SEND
from disco.gateway.events import GatewayEvent
from disco.gateway.encoding import ENCODERS
from disco.util.websocket import Websocket
from disco.util.logging import LoggingClass
from disco.util.limiter import SimpleLimiter

TEN_MEGABYTES = 10490000
ZLIB_SUFFIX = b'\x00\x00\xff\xff'


class GatewayClient(LoggingClass):
    GATEWAY_VERSION = 6

    def __init__(self, client, max_reconnects=5, encoder='json', zlib_stream_enabled=True, ipc=None):
        super(GatewayClient, self).__init__()
        self.client = client
        self.max_reconnects = max_reconnects
        self.encoder = ENCODERS[encoder]
        self.zlib_stream_enabled = zlib_stream_enabled

        self.events = client.events
        self.packets = client.packets

        # IPC for shards
        if ipc:
            self.shards = ipc.get_shards()
            self.ipc = ipc

        # Its actually 60, 120 but lets give ourselves a buffer
        self.limiter = SimpleLimiter(60, 130)

        # Create emitter and bind to gateway payloads
        self.packets.on((RECV, OPCode.DISPATCH), self.handle_dispatch)
        self.packets.on((RECV, OPCode.HEARTBEAT), self.handle_heartbeat)
        self.packets.on((RECV, OPCode.HEARTBEAT_ACK), self.handle_heartbeat_acknowledge)
        self.packets.on((RECV, OPCode.RECONNECT), self.handle_reconnect)
        self.packets.on((RECV, OPCode.INVALID_SESSION), self.handle_invalid_session)
        self.packets.on((RECV, OPCode.HELLO), self.handle_hello)

        # Bind to ready payload
        self.events.on('Ready', self.on_ready)
        self.events.on('Resumed', self.on_resumed)

        # Websocket connection
        self.ws = None
        self.ws_event = gevent.event.Event()
        self._zlib = None
        self._buffer = None

        # State
        self.seq = 0
        self.session_id = None
        self.reconnects = 0
        self.shutting_down = False
        self.replaying = False
        self.replayed_events = 0

        # Cached gateway URL
        self._cached_gateway_url = None

        # Heartbeat
        self._heartbeat_task = None
        self._heartbeat_acknowledged = True

    def send(self, op, data):
        self.limiter.check()
        return self._send(op, data)

    def _send(self, op, data):
        self.log.debug('GatewayClient.send %s', op)
        self.packets.emit((SEND, op), data)
        self.ws.send(self.encoder.encode({
            'op': op.value,
            'd': data,
        }), self.encoder.OPCODE)

    def heartbeat_task(self, interval):
        while True:
            if not self._heartbeat_acknowledged:
                self.log.warning('Received HEARTBEAT without HEARTBEAT_ACK, forcing a fresh reconnect')
                self._heartbeat_acknowledged = True
                self.ws.close(status=4000)
                return

            self._send(OPCode.HEARTBEAT, self.seq)
            self._heartbeat_acknowledged = False
            gevent.sleep(interval / 1000)

    def handle_dispatch(self, packet):
        obj = GatewayEvent.from_dispatch(self.client, packet)
        self.log.debug('GatewayClient.handle_dispatch %s', obj.__class__.__name__)
        self.client.events.emit(obj.__class__.__name__, obj)
        if self.replaying:
            self.replayed_events += 1

    def handle_heartbeat(self, _):
        self._send(OPCode.HEARTBEAT, self.seq)

    def handle_heartbeat_acknowledge(self, _):
        self.log.debug('Received HEARTBEAT_ACK')
        self._heartbeat_acknowledged = True

    def handle_reconnect(self, _):
        self.log.warning('Received RECONNECT request, forcing a fresh reconnect')
        self.session_id = None
        self.ws.close()

    def handle_invalid_session(self, _):
        self.log.warning('Received INVALID_SESSION, forcing a fresh reconnect')
        self.session_id = None
        self.ws.close()

    def handle_hello(self, packet):
        self.log.info('Received HELLO, starting heartbeater...')
        self._heartbeat_task = gevent.spawn(self.heartbeat_task, packet['d']['heartbeat_interval'])

    def on_ready(self, ready):
        self.log.info('Received READY')
        self.session_id = ready.session_id
        self.reconnects = 0

    def on_resumed(self, _):
        self.log.info('RESUME completed, replayed %s events', self.replayed_events)
        self.reconnects = 0
        self.replaying = False

    def connect_and_run(self, gateway_url=None):
        if not gateway_url:
            if not self._cached_gateway_url:
                self._cached_gateway_url = self.client.api.gateway_get()['url']

            gateway_url = self._cached_gateway_url

        gateway_url += '?v={}&encoding={}'.format(self.GATEWAY_VERSION, self.encoder.TYPE)

        if self.zlib_stream_enabled:
            gateway_url += '&compress=zlib-stream'

        self.log.info('Opening websocket connection to URL `%s`', gateway_url)
        self.ws = Websocket(gateway_url)
        self.ws.emitter.on('on_open', self.on_open)
        self.ws.emitter.on('on_error', self.on_error)
        self.ws.emitter.on('on_close', self.on_close)
        self.ws.emitter.on('on_message', self.on_message)

        self.ws.run_forever(sslopt={'cert_reqs': ssl.CERT_NONE})

    def on_message(self, msg):
        if self.zlib_stream_enabled:
            if not self._buffer:
                self._buffer = bytearray()

            self._buffer.extend(msg)

            if len(msg) < 4:
                return

            if msg[-4:] != ZLIB_SUFFIX:
                return

            msg = self._zlib.decompress(self._buffer if six.PY3 else str(self._buffer))
            # If this encoder is text based, we want to decode the data as utf8
            if self.encoder.OPCODE == ABNF.OPCODE_TEXT:
                msg = msg.decode('utf-8')
            self._buffer = None
        else:
            # Detect zlib and decompress
            is_erlpack = ((six.PY2 and ord(msg[0]) == 131) or (six.PY3 and msg[0] == 131))
            if msg[0] != '{' and not is_erlpack:
                msg = zlib.decompress(msg, 15, TEN_MEGABYTES).decode('utf-8')

        try:
            data = self.encoder.decode(msg)
        except Exception:
            self.log.exception('Failed to parse gateway message: ')
            return

        # Update sequence
        if data['s'] and data['s'] > self.seq:
            self.seq = data['s']

        # Emit packet
        self.packets.emit((RECV, OPCode[data['op']]), data)

    def on_error(self, error):
        if isinstance(error, KeyboardInterrupt):
            self.shutting_down = True
            self.ws_event.set()
        raise Exception('WS recieved error: %s', error)

    def on_open(self):
        if self.zlib_stream_enabled:
            self._zlib = zlib.decompressobj()

        if self.seq and self.session_id:
            self.log.info('WS Opened: attempting resume w/ SID: %s SEQ: %s', self.session_id, self.seq)
            self.replaying = True
            self.send(OPCode.RESUME, {
                'token': self.client.config.token,
                'session_id': self.session_id,
                'seq': self.seq,
            })
        else:
            self.log.info('WS Opened: sending identify payload')
            self.send(OPCode.IDENTIFY, {
                'token': self.client.config.token,
                'compress': True,
                'large_threshold': 250,
                'shard': [
                    int(self.client.config.shard_id),
                    int(self.client.config.shard_count),
                ],
                'properties': {
                    '$os': 'linux',
                    '$browser': 'disco',
                    '$device': 'disco',
                    '$referrer': '',
                },
            })

    def on_close(self, code, reason):
        # Make sure we cleanup any old data
        self._buffer = None

        # Kill heartbeater, a reconnect/resume will trigger a HELLO which will
        #  respawn it
        if self._heartbeat_task:
            self._heartbeat_task.kill()

        # If we're quitting, just break out of here
        if self.shutting_down:
            self.log.info('WS Closed: shutting down')
            return

        self.replaying = False

        # Track reconnect attempts
        self.reconnects += 1
        self.log.info('WS Closed: [%s] %s (%s)', code, reason, self.reconnects)

        if self.max_reconnects and self.reconnects > self.max_reconnects:
            raise Exception('Failed to reconnect after {} attempts, giving up'.format(self.max_reconnects))

        # Don't resume for these error codes
        if code and 4000 <= code <= 4010:
            self.session_id = None

        wait_time = self.reconnects * 5
        self.log.info('Will attempt to %s after %s seconds', 'resume' if self.session_id else 'reconnect', wait_time)
        gevent.sleep(wait_time)

        # Reconnect
        self.connect_and_run()

    def run(self):
        gevent.spawn(self.connect_and_run)
        self.ws_event.wait()

    def request_guild_members(self, guild_id_or_ids, query=None, limit=0):
        """
        Request a batch of Guild members from Discord. Generally this function
        can be called when initially loading Guilds to fill the local member state.
        """
        self.send(OPCode.REQUEST_GUILD_MEMBERS, {
            # This is simply unfortunate naming on the part of Discord...
            'guild_id': guild_id_or_ids,
            'query': query or '',
            'limit': limit,
        })
