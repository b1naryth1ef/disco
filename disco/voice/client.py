from __future__ import print_function

import gevent
import socket
import struct
import time

try:
    import nacl.secret
except ImportError:
    print('WARNING: nacl is not installed, voice support is disabled')

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


class VoiceException(Exception):
    def __init__(self, msg, client):
        self.voice_client = client
        super(VoiceException, self).__init__(msg)


class UDPVoiceClient(LoggingClass):
    def __init__(self, vc):
        super(UDPVoiceClient, self).__init__()
        self.vc = vc

        # The underlying UDP socket
        self.conn = None

        # Connection information
        self.ip = None
        self.port = None

        self.run_task = None
        self.connected = False

    def send_frame(self, frame, sequence=None, timestamp=None):
        # Convert the frame to a bytearray
        frame = bytearray(frame)

        # First, pack the header (TODO: reuse bytearray?)
        header = bytearray(24)
        header[0] = 0x80
        header[1] = 0x78
        struct.pack_into('>H', header, 2, sequence or self.vc.sequence)
        struct.pack_into('>I', header, 4, timestamp or self.vc.timestamp)
        struct.pack_into('>i', header, 8, self.vc.ssrc)

        # Now encrypt the payload with the nonce as a header
        raw = self.vc.secret_box.encrypt(bytes(frame), bytes(header)).ciphertext

        # Send the header (sans nonce padding) plus the payload
        self.send(header[:12] + raw)

        # Increment our sequence counter
        self.vc.sequence += 1
        if self.vc.sequence >= 65535:
            self.vc.sequence = 0

    def run(self):
        while True:
            self.conn.recvfrom(4096)

    def send(self, data):
        self.conn.sendto(data, (self.ip, self.port))

    def disconnect(self):
        self.run_task.kill()

    def connect(self, host, port, timeout=10, addrinfo=None):
        self.ip = socket.gethostbyname(host)
        self.port = port

        self.conn = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        if addrinfo:
            ip, port = addrinfo
        else:
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

        if not channel.is_voice:
            raise ValueError('Cannot spawn a VoiceClient for a non-voice channel')

        self.channel = channel
        self.client = self.channel.client
        self.encoder = encoder or JSONEncoder

        # Bind to some WS packets
        self.packets = Emitter(gevent.spawn)
        self.packets.on(VoiceOPCode.READY, self.on_voice_ready)
        self.packets.on(VoiceOPCode.SESSION_DESCRIPTION, self.on_voice_sdp)

        # State + state change emitter
        self.state = VoiceState.DISCONNECTED
        self.state_emitter = Emitter(gevent.spawn)

        # Connection metadata
        self.token = None
        self.endpoint = None
        self.ssrc = None
        self.port = None
        self.secret_box = None
        self.udp = None

        # Voice data state
        self.sequence = 0
        self.timestamp = 0

        self.update_listener = None

        # Websocket connection
        self.ws = None
        self.heartbeat_task = None

    def __repr__(self):
        return u'<VoiceClient {}>'.format(self.channel)

    def set_state(self, state):
        self.log.debug('[%s] state %s -> %s', self, self.state, state)
        prev_state = self.state
        self.state = state
        self.state_emitter.emit(state, prev_state)

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
        self.log.debug('[%s] sending OP %s (data = %s)', self, op, data)
        self.ws.send(self.encoder.encode({
            'op': op.value,
            'd': data,
        }), self.encoder.OPCODE)

    def on_voice_ready(self, data):
        self.log.info('[%s] Recived Voice READY payload, attempting to negotiate voice connection w/ remote', self)
        self.set_state(VoiceState.CONNECTING)
        self.ssrc = data['ssrc']
        self.port = data['port']

        self.heartbeat_task = gevent.spawn(self.heartbeat, data['heartbeat_interval'])

        self.log.debug('[%s] Attempting IP discovery over UDP to %s:%s', self, self.endpoint, self.port)
        self.udp = UDPVoiceClient(self)
        ip, port = self.udp.connect(self.endpoint, self.port)

        if not ip:
            self.log.error('Failed to discover our IP, perhaps a NAT or firewall is fucking us')
            self.disconnect()
            return

        self.log.debug('[%s] IP discovery completed (ip = %s, port = %s), sending SELECT_PROTOCOL', self, ip, port)
        self.send(VoiceOPCode.SELECT_PROTOCOL, {
            'protocol': 'udp',
            'data': {
                'port': port,
                'address': ip,
                'mode': 'xsalsa20_poly1305'
            }
        })

    def on_voice_sdp(self, sdp):
        self.log.info('[%s] Recieved session description, connection completed', self)
        # Create a secret box for encryption/decryption
        self.secret_box = nacl.secret.SecretBox(bytes(bytearray(sdp['secret_key'])))

        # Toggle speaking state so clients learn of our SSRC
        self.set_speaking(True)
        self.set_speaking(False)
        gevent.sleep(0.25)

        self.set_state(VoiceState.CONNECTED)

    def on_voice_server_update(self, data):
        if self.channel.guild_id != data.guild_id or not data.token:
            return

        if self.token and self.token != data.token:
            return

        self.log.info('[%s] Recieved VOICE_SERVER_UPDATE (state = %s)', self, self.state)

        self.token = data.token
        self.set_state(VoiceState.AUTHENTICATING)

        self.endpoint = data.endpoint.split(':', 1)[0]
        self.ws = Websocket('wss://' + self.endpoint)
        self.ws.emitter.on('on_open', self.on_open)
        self.ws.emitter.on('on_error', self.on_error)
        self.ws.emitter.on('on_close', self.on_close)
        self.ws.emitter.on('on_message', self.on_message)
        self.ws.run_forever()

    def on_message(self, msg):
        try:
            data = self.encoder.decode(msg)
            self.packets.emit(VoiceOPCode[data['op']], data['d'])
        except:
            self.log.exception('Failed to parse voice gateway message: ')

    def on_error(self, err):
        # TODO: raise an exception here
        self.log.error('[%s] Voice websocket error: %s', self, err)

    def on_open(self):
        self.send(VoiceOPCode.IDENTIFY, {
            'server_id': self.channel.guild_id,
            'user_id': self.client.state.me.id,
            'session_id': self.client.gw.session_id,
            'token': self.token
        })

    def on_close(self, code, error):
        self.log.warning('[%s] Voice websocket disconnected (%s, %s)', self, code, error)

        if self.state == VoiceState.CONNECTED:
            self.log.info('Attempting voice reconnection')
            self.connect()

    def connect(self, timeout=5, mute=False, deaf=False):
        self.log.debug('[%s] Attempting connection', self)
        self.set_state(VoiceState.AWAITING_ENDPOINT)

        self.update_listener = self.client.events.on('VoiceServerUpdate', self.on_voice_server_update)

        self.client.gw.send(OPCode.VOICE_STATE_UPDATE, {
            'self_mute': mute,
            'self_deaf': deaf,
            'guild_id': int(self.channel.guild_id),
            'channel_id': int(self.channel.id),
        })

        if not self.state_emitter.once(VoiceState.CONNECTED, timeout=timeout):
            raise VoiceException('Failed to connect to voice', self)

    def disconnect(self):
        self.log.debug('[%s] disconnect called', self)
        self.set_state(VoiceState.DISCONNECTED)

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

    def send_frame(self, *args, **kwargs):
        self.udp.send_frame(*args, **kwargs)
