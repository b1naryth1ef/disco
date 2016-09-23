import websocket
import gevent
import json
import zlib
import six
import ssl

from disco.gateway.packets import OPCode, HeartbeatPacket, ResumePacket, IdentifyPacket
from disco.gateway.events import GatewayEvent
from disco.util.logging import LoggingClass

GATEWAY_VERSION = 6
TEN_MEGABYTES = 10490000


# Hack to get websocket close information
def websocket_get_close_args_override(data):
    if data and len(data) >= 2:
        code = 256 * six.byte2int(data[0:1]) + six.byte2int(data[1:2])
        reason = data[2:].decode('utf-8')
        return [code, reason]
    return [None, None]


class GatewayClient(LoggingClass):
    MAX_RECONNECTS = 5

    def __init__(self, client):
        super(GatewayClient, self).__init__()
        self.client = client

        self.client.events.on('Ready', self.on_ready)

        # Websocket connection
        self.ws = None

        # State
        self.seq = 0
        self.session_id = None
        self.reconnects = 0
        self.shutting_down = False

        # Cached gateway URL
        self._cached_gateway_url = None

        # Heartbeat
        self._heartbeat_task = None

    def send(self, packet):
        self.ws.send(json.dumps({
            'op': int(packet.OP),
            'd': packet.to_dict(),
        }))

    def heartbeat_task(self, interval):
        while True:
            self.send(HeartbeatPacket(data=self.seq))
            gevent.sleep(interval / 1000)

    def handle_dispatch(self, packet):
        obj = GatewayEvent.from_dispatch(self.client, packet)
        self.log.debug('Dispatching %s', obj.__class__.__name__)
        self.client.events.emit(obj.__class__.__name__, obj)

    def handle_heartbeat(self, packet):
        self.send(HeartbeatPacket(data=self.seq))

    def handle_reconnect(self, packet):
        self.log.warning('Received RECONNECT request, forcing a fresh reconnect')
        self.session_id = None
        self.ws.close()

    def handle_invalid_session(self, packet):
        self.log.warning('Recieved INVALID_SESSIOIN, forcing a fresh reconnect')
        self.sesion_id = None
        self.ws.close()

    def handle_hello(self, packet):
        self.log.info('Recieved HELLO, starting heartbeater...')
        self._heartbeat_task = gevent.spawn(self.heartbeat_task, packet['d']['heartbeat_interval'])

    def handle_heartbeat_ack(self, packet):
        pass

    def on_ready(self, ready):
        self.log.info('Recieved READY')
        self.session_id = ready.session_id
        self.reconnects = 0

    def connect_and_run(self):
        if not self._cached_gateway_url:
            self._cached_gateway_url = self.client.api.gateway(version=GATEWAY_VERSION, encoding='json')

        self.log.info('Opening websocket connection to URL `%s`', self._cached_gateway_url)
        self.ws = websocket.WebSocketApp(
            self._cached_gateway_url,
            on_message=self.log_on_error('Error in on_message:', self.on_message),
            on_error=self.log_on_error('Error in on_error:', self.on_error),
            on_open=self.log_on_error('Error in on_open:', self.on_open),
            on_close=self.log_on_error('Error in on_close:', self.on_close),
        )
        self.ws._get_close_args = websocket_get_close_args_override
        self.ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})

    def on_message(self, ws, msg):
        # Detect zlib and decompress
        if msg[0] != '{':
            msg = zlib.decompress(msg, 15, TEN_MEGABYTES)

        try:
            data = json.loads(msg)
        except:
            self.log.exception('Failed to load dispatch:')
            return

        # Update sequence
        if data['s'] and data['s'] > self.seq:
            self.seq = data['s']

        if data['op'] == OPCode.DISPATCH:
            self.handle_dispatch(data)
        elif data['op'] == OPCode.HEARTBEAT:
            self.handle_heartbeat(data)
        elif data['op'] == OPCode.RECONNECT:
            self.handle_reconnect(data)
        elif data['op'] == OPCode.INVALID_SESSION:
            self.handle_invalid_session(data)
        elif data['op'] == OPCode.HELLO:
            self.handle_hello(data)
        elif data['op'] == OPCode.HEARTBEAT_ACK:
            self.handle_heartbeat_ack(data)
        else:
            raise Exception('Unknown packet: {}'.format(data['op']))

    def on_error(self, ws, error):
        if isinstance(error, KeyboardInterrupt):
            self.shutting_down = True
        raise Exception('WS recieved error: %s', error)

    def on_open(self, ws):
        if self.seq and self.session_id:
            self.log.info('WS Opened: attempting resume w/ SID: %s SEQ: %s', self.session_id, self.seq)
            self.send(ResumePacket(seq=self.seq, session_id=self.session_id, token=self.client.token))
        else:
            self.log.info('WS Opened: sending identify payload')
            self.send(IdentifyPacket(
                token=self.client.token,
                compress=True,
                large_threshold=250,
                shard=[self.client.sharding['number'], self.client.sharding['total']]))

    def on_close(self, ws, code, reason):
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
        self.connect_and_run()
