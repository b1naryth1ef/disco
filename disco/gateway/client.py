import websocket
import gevent
import json

from disco.gateway.packets import (
    Packet, DispatchPacket, HeartbeatPacket, ReconnectPacket, InvalidSessionPacket, HelloPacket, HeartbeatAckPacket,
    ResumePacket, IdentifyPacket)
from disco.util.logging import LoggingClass

GATEWAY_VERSION = 6


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

        # Websocket connection
        self.ws = None

        # State
        self.seq = 0
        self.session_id = None

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

    def handle_hello(self, packet):
        self.log.info('Recieved HELLO, starting heartbeater...')
        self._heartbeat_task = gevent.spawn(self.heartbeat_task, packet.heartbeat_interval)

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
        # TODO: ZLIB

        try:
            packet = Packet.load_json(json.loads(msg))
            if packet.seq and packet.seq > self.seq:
                self.seq = packet.seq
        except:
            self.log.exception('Failed to load dispatch:')
            return

        if isinstance(packet, DispatchPacket):
            self.handle_dispatch(packet)
        elif isinstance(packet, HeartbeatPacket):
            self.handle_heartbeat(packet)
        elif isinstance(packet, ReconnectPacket):
            self.handle_reconnect(packet)
        elif isinstance(packet, InvalidSessionPacket):
            self.handle_invalid_session(packet)
        elif isinstance(packet, HelloPacket):
            self.handle_hello(packet)
        elif isinstance(packet, HeartbeatAckPacket):
            self.handle_heartbeat_ack(packet)
        else:
            raise Exception('Unknown packet: {}'.format(packet))

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
