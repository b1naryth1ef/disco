import websocket
import gevent
import json
import zlib

from holster.emitter import Emitter
# from holster.util import SimpleObject

from disco.gateway.packets import OPCode, HeartbeatPacket, ResumePacket, IdentifyPacket
from disco.gateway.events import GatewayEvent, Ready
from disco.util.logging import LoggingClass

GATEWAY_VERSION = 6
TEN_MEGABYTES = 10490000


def log_error(log, msg, w):
    def _f(*args, **kwargs):
        try:
            return w(*args, **kwargs)
        except:
            log.exception(msg)
            raise
    return _f


class GatewayClient(LoggingClass):
    def __init__(self, client):
        super(GatewayClient, self).__init__()
        self.client = client
        self.emitter = Emitter(gevent.spawn)

        self.emitter.on(Ready, self.on_ready)

        # Websocket connection
        self.ws = None

        # State
        self.seq = 0
        self.session_id = None
        self.reconnects = 0

        # Cached gateway URL
        self._cached_gateway_url = None

        # Heartbeat
        self._heartbeat_task = None

        self._fatal_error_promise = gevent.event.AsyncResult()

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
        cls, obj = GatewayEvent.from_dispatch(packet)
        self.log.info('Dispatching %s', cls)
        self.emitter.emit(cls, obj)

    def handle_heartbeat(self, packet):
        pass

    def handle_reconnect(self, packet):
        pass

    def handle_invalid_session(self, packet):
        pass

    def handle_hello(self, packet):
        self.log.info('Recieved HELLO, starting heartbeater...')
        self._heartbeat_task = gevent.spawn(self.heartbeat_task, packet['d']['heartbeat_interval'])

    def handle_heartbeat_ack(self, packet):
        pass

    def on_ready(self, ready):
        self.log.info('Recieved READY')
        self.session_id = ready.session_id
        self.reconnects = 0

    def connect(self):
        if not self._cached_gateway_url:
            self._cached_gateway_url = self.client.api.gateway(version=GATEWAY_VERSION, encoding='json')

        self.log.info('Opening websocket connection to URL `%s`', self._cached_gateway_url)
        self.ws = websocket.WebSocketApp(
            self._cached_gateway_url,
            on_message=log_error(self.log, 'Error in on_message:', self.on_message),
            on_error=log_error(self.log, 'Error in on_error:', self.on_error),
            on_open=log_error(self.log, 'Error in on_open:', self.on_open),
            on_close=log_error(self.log, 'Error in on_close:', self.on_close),
        )

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
        print 'error', error

    def on_open(self, ws):
        print 'on open'
        if self.seq and self.session_id:
            self.send(ResumePacket(seq=self.seq, session_id=self.session_id, token=self.client.token))
        else:
            self.send(IdentifyPacket(
                token=self.client.token,
                compress=True,
                large_threshold=250,
                shard=[self.client.sharding['number'], self.client.sharding['total']]))

    def on_close(self, ws):
        print 'close'

    def run(self):
        self.connect()

        # Spawn a thread to run the connection loop forever
        gevent.spawn(self.ws.run_forever)

        # Wait for a fatal error
        self._fatal_error_promise.get()
