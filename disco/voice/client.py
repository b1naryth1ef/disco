import gevent
import socket
import struct
import time

from holster.enum import Enum
from holster.emitter import Emitter

from disco.gateway.encoding.json import JSONEncoder
from disco.util.websocket import Websocket
from disco.util.logging import LoggingClass
from disco.voice.packets import VoiceOPCode
from disco.gateway.packets import OPCode

VoiceState = Enum(
    DISCONNECTED=0,
    AWAITING_ENDPOINT=1,
    AUTHENTICATING=2,
    CONNECTING=3,
    CONNECTED=4,
    VOICE_CONNECTING=5,
    VOICE_CONNECTED=6,
)

# TODO:
#   - player implementation
#   - encryption
#   - cleanup


class VoiceException(Exception):
    def __init__(self, msg, client):
        self.voice_client = client
        super(VoiceException, self).__init__(msg)


class UDPVoiceClient(LoggingClass):
    def __init__(self, vc):
        super(UDPVoiceClient, self).__init__()
        self.vc = vc
        self.conn = None
        self.ip = None
        self.port = None
        self.run_task = None
        self.connected = False

    def run(self):
        while True:
            self.conn.recvfrom(4096)

    def send(self, data):
        self.conn.sendto(data, (self.ip, self.port))

    def disconnect(self):
        self.run_task.kill()

    def connect(self, host, port, timeout=10):
        self.ip = socket.gethostbyname(host)
        self.port = port

        self.conn = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Send discovery packet
        packet = bytearray(70)
        struct.pack_into('>I', packet, 0, self.vc.ssrc)
        self.send(packet)

        # Wait for a response
        try:
            data, addr = gevent.spawn(lambda: self.conn.recvfrom(70)).get(timeout=timeout)
        except gevent.Timeout:
            return (None, None)

        # Read IP and port
        ip = str(data[4:]).split('\x00', 1)[0]
        port = struct.unpack('<H', data[-2:])[0]

        # Spawn read thread so we don't max buffers
        self.connected = True
        self.run_task = gevent.spawn(self.run)

        return (ip, port)


class VoiceClient(LoggingClass):
    def __init__(self, channel, encoder=None):
        super(VoiceClient, self).__init__()

        assert channel.is_voice, 'Cannot spawn a VoiceClient for a non-voice channel'
        self.channel = channel
        self.client = self.channel.client
        self.encoder = encoder or JSONEncoder

        self.packets = Emitter(gevent.spawn)
        self.packets.on(VoiceOPCode.READY, self.on_voice_ready)
        self.packets.on(VoiceOPCode.SESSION_DESCRIPTION, self.on_voice_sdp)

        # State
        self.state = VoiceState.DISCONNECTED
        self.connected = gevent.event.Event()
        self.token = None
        self.endpoint = None
        self.ssrc = None
        self.port = None

        self.update_listener = None

        # Websocket connection
        self.ws = None
        self.heartbeat_task = None

    def heartbeat(self, interval):
        while True:
            self.send(VoiceOPCode.HEARTBEAT, time.time() * 1000)
            gevent.sleep(interval / 1000)

    def set_speaking(self, value):
        self.send(VoiceOPCode.SPEAKING, {
            'speaking': value,
            'delay': 0,
        })

    def send(self, op, data):
        self.ws.send(self.encoder.encode({
            'op': op.value,
            'd': data,
        }), self.encoder.OPCODE)

    def on_voice_ready(self, data):
        self.state = VoiceState.CONNECTING
        self.ssrc = data['ssrc']
        self.port = data['port']

        self.heartbeat_task = gevent.spawn(self.heartbeat, data['heartbeat_interval'])

        self.udp = UDPVoiceClient(self)
        ip, port = self.udp.connect(self.endpoint, self.port)

        if not ip:
            self.disconnect()
            return

        self.send(VoiceOPCode.SELECT_PROTOCOL, {
            'protocol': 'udp',
            'data': {
                'port': port,
                'address': ip,
                'mode': 'plain'
            }
        })

    def on_voice_sdp(self, data):
        # Toggle speaking state so clients learn of our SSRC
        self.set_speaking(True)
        self.set_speaking(False)
        gevent.sleep(0.25)

        self.state = VoiceState.CONNECTED
        self.connected.set()

    def on_voice_server_update(self, data):
        if self.channel.guild_id != data.guild_id or not data.token:
            return

        if self.token and self.token != data.token:
            return

        self.token = data.token
        self.state = VoiceState.AUTHENTICATING

        self.endpoint = data.endpoint.split(':', 1)[0]
        self.ws = Websocket(
            'wss://' + self.endpoint,
            on_message=self.on_message,
            on_error=self.on_error,
            on_open=self.on_open,
            on_close=self.on_close,
        )
        self.ws.run_forever()

    def on_message(self, ws, msg):
        try:
            data = self.encoder.decode(msg)
        except:
            self.log.exception('Failed to parse voice gateway message: ')

        self.packets.emit(VoiceOPCode[data['op']], data['d'])

    def on_error(self, ws, err):
        # TODO
        self.log.warning('Voice websocket error: {}'.format(err))

    def on_open(self, ws):
        self.send(VoiceOPCode.IDENTIFY, {
            'server_id': self.channel.guild_id,
            'user_id': self.client.state.me.id,
            'session_id': self.client.gw.session_id,
            'token': self.token
        })

    def on_close(self, ws, code, error):
        # TODO
        self.log.warning('Voice websocket disconnected (%s, %s)', code, error)

    def connect(self, timeout=5, mute=False, deaf=False):
        self.state = VoiceState.AWAITING_ENDPOINT

        self.update_listener = self.client.events.on('VoiceServerUpdate', self.on_voice_server_update)

        self.client.gw.send(OPCode.VOICE_STATE_UPDATE, {
            'self_mute': mute,
            'self_deaf': deaf,
            'guild_id': int(self.channel.guild_id),
            'channel_id': int(self.channel.id),
        })

        if not self.connected.wait(timeout) or self.state != VoiceState.CONNECTED:
            raise VoiceException('Failed to connect to voice', self)

    def disconnect(self):
        self.state = VoiceState.DISCONNECTED

        if self.heartbeat_task:
            self.heartbeat_task.kill()
            self.heartbeat_task = None

        if self.ws and self.ws.sock.connected:
            self.ws.close()

        if self.udp and self.udp.connected:
            self.udp.disconnect()

        self.client.gw.send(OPCode.VOICE_STATE_UPDATE, {
            'self_mute': False,
            'self_deaf': False,
            'guild_id': int(self.channel.guild_id),
            'channel_id': None,
        })
