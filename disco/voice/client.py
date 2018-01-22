from __future__ import print_function

import gevent
import time

from holster.enum import Enum
from holster.emitter import Emitter

from disco.gateway.encoding.json import JSONEncoder
from disco.util.websocket import Websocket
from disco.util.logging import LoggingClass
from disco.gateway.packets import OPCode
from disco.voice.packets import VoiceOPCode
from disco.voice.udp import UDPVoiceClient

VoiceState = Enum(
    DISCONNECTED=0,
    RECONNECTING=1,
    AWAITING_ENDPOINT=2,
    AUTHENTICATING=3,
    AUTHENTICATED=4,
    CONNECTING=5,
    CONNECTED=6,
    VOICE_CONNECTING=7,
    VOICE_CONNECTED=8,
)


class VoiceException(Exception):
    def __init__(self, msg, client):
        self.voice_client = client
        super(VoiceException, self).__init__(msg)


class VoiceClient(LoggingClass):
    VOICE_GATEWAY_VERSION = 3

    SUPPORTED_MODES = {
        'xsalsa20_poly1305_suffix',
        'xsalsa20_poly1305',
    }

    def __init__(self, channel, encoder=None, max_reconnects=5):
        super(VoiceClient, self).__init__()

        if not channel.is_voice:
            raise ValueError('Cannot spawn a VoiceClient for a non-voice channel')

        self.channel = channel
        self.client = self.channel.client
        self.encoder = encoder or JSONEncoder
        self.max_reconnects = max_reconnects

        # Bind to some WS packets
        self.packets = Emitter()
        self.packets.on(VoiceOPCode.HELLO, self.on_voice_hello)
        self.packets.on(VoiceOPCode.READY, self.on_voice_ready)
        self.packets.on(VoiceOPCode.RESUMED, self.on_voice_resumed)
        self.packets.on(VoiceOPCode.SESSION_DESCRIPTION, self.on_voice_sdp)

        # State + state change emitter
        self.state = VoiceState.DISCONNECTED
        self.state_emitter = Emitter()

        # Connection metadata
        self.token = None
        self.endpoint = None
        self.ssrc = None
        self.port = None
        self.mode = None
        self.udp = None

        # Websocket connection
        self.ws = None

        self._session_id = None
        self._reconnects = 0
        self._update_listener = None
        self._heartbeat_task = None

    def __repr__(self):
        return u'<VoiceClient {}>'.format(self.channel)

    def set_state(self, state):
        self.log.debug('[%s] state %s -> %s', self, self.state, state)
        prev_state = self.state
        self.state = state
        self.state_emitter.emit(state, prev_state)

    def _connect_and_run(self):
        self.ws = Websocket('wss://' + self.endpoint + '/v={}'.format(self.VOICE_GATEWAY_VERSION))
        self.ws.emitter.on('on_open', self.on_open)
        self.ws.emitter.on('on_error', self.on_error)
        self.ws.emitter.on('on_close', self.on_close)
        self.ws.emitter.on('on_message', self.on_message)
        self.ws.run_forever()

    def _heartbeat(self, interval):
        while True:
            self.send(VoiceOPCode.HEARTBEAT, time.time())
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

    def on_voice_hello(self, data):
        self.log.info('[%s] Recieved Voice HELLO payload, starting heartbeater', self)
        self._heartbeat_task = gevent.spawn(self._heartbeat, data['heartbeat_interval'] * 0.75)
        self.set_state(VoiceState.AUTHENTICATED)

    def on_voice_ready(self, data):
        self.log.info('[%s] Recived Voice READY payload, attempting to negotiate voice connection w/ remote', self)
        self.set_state(VoiceState.CONNECTING)
        self.ssrc = data['ssrc']
        self.port = data['port']

        for mode in self.SUPPORTED_MODES:
            if mode in data['modes']:
                self.mode = mode
                self.log.debug('[%s] Selected mode %s', self, mode)
                break
        else:
            raise Exception('Failed to find a supported voice mode')

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
                'mode': self.mode,
            },
        })

    def on_voice_resumed(self, data):
        self.log.info('[%s] Recieved resumed', self)
        self.set_state(VoiceState.CONNECTED)

    def on_voice_sdp(self, sdp):
        self.log.info('[%s] Recieved session description, connection completed', self)

        # Create a secret box for encryption/decryption
        self.udp.setup_encryption(bytes(bytearray(sdp['secret_key'])))

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

        self.log.info('[%s] Recieved VOICE_SERVER_UPDATE (state = %s / endpoint = %s)', self, self.state, data.endpoint)

        self.token = data.token
        self.set_state(VoiceState.AUTHENTICATING)

        self.endpoint = data.endpoint.split(':', 1)[0]

        self._connect_and_run()

    def on_message(self, msg):
        try:
            data = self.encoder.decode(msg)
            self.packets.emit(VoiceOPCode[data['op']], data['d'])
        except Exception:
            self.log.exception('Failed to parse voice gateway message: ')

    def on_error(self, err):
        self.log.error('[%s] Voice websocket error: %s', self, err)

    def on_open(self):
        if self._session_id:
            return self.send(VoiceOPCode.RESUME, {
                'server_id': self.channel.guild_id,
                'user_id': self.client.state.me.id,
                'session_id': self._session_id,
                'token': self.token,
            })

        self._session_id = self.client.gw.session_id

        self.send(VoiceOPCode.IDENTIFY, {
            'server_id': self.channel.guild_id,
            'user_id': self.client.state.me.id,
            'session_id': self._session_id,
            'token': self.token,
        })

    def on_close(self, code, reason):
        self.log.warning('[%s] Voice websocket closed: [%s] %s (%s)', self, code, reason, self._reconnects)

        if self._heartbeat_task:
            self._heartbeat_task.kill()

        # If we're not in a connected state, don't try to resume/reconnect
        if self.state != VoiceState.CONNECTED:
            return

        self.log.info('[%s] Attempting Websocket Resumption', self)
        self._reconnects += 1

        if self.max_reconnects and self._reconnects > self.max_reconnects:
            raise VoiceException('Failed to reconnect after {} attempts, giving up'.format(self.max_reconnects))

        self.set_state(VoiceState.RECONNECTING)

        # Don't resume for these error codes:
        if code and 4000 <= code <= 4016:
            self._session_id = None

            if self.udp and self.udp.connected:
                self.udp.disconnect()

        wait_time = (self._reconnects - 1) * 5
        self.log.info(
            '[%s] Will attempt to %s after %s seconds', self, 'resume' if self._session_id else 'reconnect', wait_time)
        gevent.sleep(wait_time)

        self._connect_and_run()

    def connect(self, timeout=5, mute=False, deaf=False):
        self.log.debug('[%s] Attempting connection', self)
        self.set_state(VoiceState.AWAITING_ENDPOINT)

        self._update_listener = self.client.events.on('VoiceServerUpdate', self.on_voice_server_update)

        self.client.gw.send(OPCode.VOICE_STATE_UPDATE, {
            'self_mute': mute,
            'self_deaf': deaf,
            'guild_id': int(self.channel.guild_id),
            'channel_id': int(self.channel.id),
        })

        if not self.state_emitter.once(VoiceState.CONNECTED, timeout=timeout):
            self.disconnect()
            raise VoiceException('Failed to connect to voice', self)

    def disconnect(self):
        self.log.debug('[%s] disconnect called', self)
        self.set_state(VoiceState.DISCONNECTED)

        if self._heartbeat_task:
            self._heartbeat_task.kill()
            self._heartbeat_task = None

        if self.ws and self.ws.sock and self.ws.sock.connected:
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

    def increment_timestamp(self, *args, **kwargs):
        self.udp.increment_timestamp(*args, **kwargs)
