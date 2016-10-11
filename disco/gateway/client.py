import gevent
import zlib
import six
import ssl

from disco.gateway.packets import OPCode, RECV, SEND
from disco.gateway.events import GatewayEvent
from disco.gateway.encoding import ENCODERS
from disco.util.websocket import Websocket
from disco.util.logging import LoggingClass
from disco.util.limiter import SimpleLimiter

TEN_MEGABYTES = 10490000


class GatewayClient(LoggingClass):
    GATEWAY_VERSION = 6
    MAX_RECONNECTS = 5

    def __init__(self, client, encoder='json'):
        super(GatewayClient, self).__init__()
        self.client = client
        self.encoder = ENCODERS[encoder]

        self.events = client.events
        self.packets = client.packets

        # Its actually 60, 120 but lets give ourselves a buffer
        self.limiter = SimpleLimiter(60, 130)

        # Create emitter and bind to gateway payloads
        self.packets.on((RECV, OPCode.DISPATCH), self.handle_dispatch)
        self.packets.on((RECV, OPCode.HEARTBEAT), self.handle_heartbeat)
        self.packets.on((RECV, OPCode.RECONNECT), self.handle_reconnect)
        self.packets.on((RECV, OPCode.INVALID_SESSION), self.handle_invalid_session)
        self.packets.on((RECV, OPCode.HELLO), self.handle_hello)

        # Bind to ready payload
        self.events.on('Ready', self.on_ready)

        # Websocket connection
        self.ws = None
        self.ws_event = gevent.event.Event()

        # State
        self.seq = 0
        self.session_id = None
        self.reconnects = 0
        self.shutting_down = False

        # Cached gateway URL
        self._cached_gateway_url = None

        # Heartbeat
        self._heartbeat_task = None

    def send(self, op, data):
        self.limiter.check()
        return self._send(op, data)

    def _send(self, op, data):
        self.log.debug('SEND %s', op)
        self.packets.emit((SEND, op), data)
        self.ws.send(self.encoder.encode({
            'op': op.value,
            'd': data,
        }), self.encoder.OPCODE)

    def heartbeat_task(self, interval):
        while True:
            self._send(OPCode.HEARTBEAT, self.seq)
            gevent.sleep(interval / 1000)

    def handle_dispatch(self, packet):
        obj = GatewayEvent.from_dispatch(self.client, packet)
        self.log.debug('Dispatching %s', obj.__class__.__name__)
        self.client.events.emit(obj.__class__.__name__, obj)

    def handle_heartbeat(self, packet):
        self._send(OPCode.HEARTBEAT, self.seq)

    def handle_reconnect(self, packet):
        self.log.warning('Received RECONNECT request, forcing a fresh reconnect')
        self.session_id = None
        self.ws.close()

    def handle_invalid_session(self, packet):
        self.log.warning('Recieved INVALID_SESSION, forcing a fresh reconnect')
        self.session_id = None
        self.ws.close()

    def handle_hello(self, packet):
        self.log.info('Recieved HELLO, starting heartbeater...')
        self._heartbeat_task = gevent.spawn(self.heartbeat_task, packet['d']['heartbeat_interval'])

    def on_ready(self, ready):
        self.log.info('Recieved READY')
        self.session_id = ready.session_id
        self.reconnects = 0

    def connect_and_run(self):
        if not self._cached_gateway_url:
            self._cached_gateway_url = self.client.api.gateway(
                version=self.GATEWAY_VERSION,
                encoding=self.encoder.TYPE)

        self.log.info('Opening websocket connection to URL `%s`', self._cached_gateway_url)
        self.ws = Websocket(self._cached_gateway_url)
        self.ws.emitter.on('on_open', self.on_open)
        self.ws.emitter.on('on_error', self.on_error)
        self.ws.emitter.on('on_close', self.on_close)
        self.ws.emitter.on('on_message', self.on_message)

        self.ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})

    def on_message(self, msg):
        # Detect zlib and decompress
        is_erlpack = ((six.PY2 and ord(msg[0]) == 131) or (six.PY3 and msg[0] == 131))
        if msg[0] != '{' and not is_erlpack:
            msg = zlib.decompress(msg, 15, TEN_MEGABYTES).decode("utf-8")

        try:
            data = self.encoder.decode(msg)
        except:
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
        if self.seq and self.session_id:
            self.log.info('WS Opened: attempting resume w/ SID: %s SEQ: %s', self.session_id, self.seq)
            self.send(OPCode.RESUME, {
                'token': self.client.config.token,
                'session_id': self.session_id,
                'seq': self.seq
            })
        else:
            self.log.info('WS Opened: sending identify payload')
            self.send(OPCode.IDENTIFY, {
                'token': self.client.config.token,
                'compress': True,
                'large_threshold': 250,
                'shard': [
                    self.client.config.shard_id,
                    self.client.config.shard_count,
                ],
                'properties': {
                    '$os': 'linux',
                    '$browser': 'disco',
                    '$device': 'disco',
                    '$referrer': '',
                }
            })

    def on_close(self, code, reason):
        if self.shutting_down:
            self.log.info('WS Closed: shutting down')
            return

        self.reconnects += 1
        self.log.info('WS Closed: [%s] %s (%s)', code, reason, self.reconnects)

        if self.MAX_RECONNECTS and self.reconnects > self.MAX_RECONNECTS:
            raise Exception('Failed to reconect after {} attempts, giving up'.format(self.MAX_RECONNECTS))

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
