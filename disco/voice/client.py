from __future__ import print_function

import gevent
import time

from collections import namedtuple

from holster.enum import Enum
from holster.emitter import Emitter

from disco.gateway.encoding.json import JSONEncoder
from disco.util.websocket import Websocket
from disco.util.logging import LoggingClass
from disco.gateway.packets import OPCode
from disco.types.base import cached_property
from disco.voice.packets import VoiceOPCode
from disco.voice.udp import AudioCodecs, RTPPayloadTypes, UDPVoiceClient

SpeakingFlags = Enum(
    NONE=0,
    VOICE=1 << 0,
    SOUNDSHARE=1 << 1,
    PRIORITY=1 << 2,
)

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

VoiceSpeaking = namedtuple('VoiceSpeaking', [
    'client',
    'user_id',
    'speaking',
    'soundshare',
    'priority',
])


class VoiceException(Exception):
    def __init__(self, msg, client):
        self.voice_client = client
        super(VoiceException, self).__init__(msg)


class VoiceClient(LoggingClass):
    VOICE_GATEWAY_VERSION = 4

    SUPPORTED_MODES = {
        'xsalsa20_poly1305_lite',
        'xsalsa20_poly1305_suffix',
        'xsalsa20_poly1305',
    }

    def __init__(self, client, server_id, is_dm=False, encoder=None, max_reconnects=5):
        super(VoiceClient, self).__init__()

        self.client = client
        self.server_id = server_id
        self.channel_id = None
        self.is_dm = is_dm
        self.encoder = encoder or JSONEncoder
        self.max_reconnects = max_reconnects
        self.video_enabled = False

        # Set the VoiceClient in the state's voice clients
        self.client.state.voice_clients[self.server_id] = self

        # Bind to some WS packets
        self.packets = Emitter()
        self.packets.on(VoiceOPCode.HELLO, self.on_voice_hello)
        self.packets.on(VoiceOPCode.READY, self.on_voice_ready)
        self.packets.on(VoiceOPCode.RESUMED, self.on_voice_resumed)
        self.packets.on(VoiceOPCode.SESSION_DESCRIPTION, self.on_voice_sdp)
        self.packets.on(VoiceOPCode.SPEAKING, self.on_voice_speaking)
        self.packets.on(VoiceOPCode.CLIENT_CONNECT, self.on_voice_client_connect)
        self.packets.on(VoiceOPCode.CLIENT_DISCONNECT, self.on_voice_client_disconnect)
        self.packets.on(VoiceOPCode.CODECS, self.on_voice_codecs)

        # State + state change emitter
        self.state = VoiceState.DISCONNECTED
        self.state_emitter = Emitter()

        # Connection metadata
        self.token = None
        self.endpoint = None
        self.ssrc = None
        self.ip = None
        self.port = None
        self.mode = None
        self.udp = None
        self.audio_codec = None
        self.video_codec = None
        self.transport_id = None

        # Websocket connection
        self.ws = None

        self._session_id = self.client.gw.session_id
        self._reconnects = 0
        self._heartbeat_task = None
        self._identified = False

        # SSRCs
        self.audio_ssrcs = {}

    def __repr__(self):
        return u'<VoiceClient {}>'.format(self.server_id)

    @cached_property
    def guild(self):
        return self.client.state.guilds.get(self.server_id) if not self.is_dm else None

    @cached_property
    def channel(self):
        return self.client.state.channels.get(self.channel_id)

    @property
    def user_id(self):
        return self.client.state.me.id

    @property
    def ssrc_audio(self):
        return self.ssrc

    @property
    def ssrc_video(self):
        return self.ssrc + 1

    @property
    def ssrc_rtx(self):
        return self.ssrc + 2

    @property
    def ssrc_rtcp(self):
        return self.ssrc + 3

    def set_state(self, state):
        self.log.debug('[%s] state %s -> %s', self, self.state, state)
        prev_state = self.state
        self.state = state
        self.state_emitter.emit(state, prev_state)

    def set_endpoint(self, endpoint):
        endpoint = endpoint.split(':', 1)[0]
        if self.endpoint == endpoint:
            return

        self.log.info(
            '[%s] Set endpoint from VOICE_SERVER_UPDATE (state = %s / endpoint = %s)', self, self.state, endpoint)

        self.endpoint = endpoint

        if self.ws and self.ws.sock and self.ws.sock.connected:
            self.ws.close()
            self.ws = None

        self._identified = False

    def set_token(self, token):
        if self.token == token:
            return
        self.token = token
        if not self._identified:
            self._connect_and_run()

    def _connect_and_run(self):
        self.ws = Websocket('wss://' + self.endpoint + '/?v={}'.format(self.VOICE_GATEWAY_VERSION))
        self.ws.emitter.on('on_open', self.on_open)
        self.ws.emitter.on('on_error', self.on_error)
        self.ws.emitter.on('on_close', self.on_close)
        self.ws.emitter.on('on_message', self.on_message)
        self.ws.run_forever()

    def _heartbeat(self, interval):
        while True:
            self.send(VoiceOPCode.HEARTBEAT, time.time())
            gevent.sleep(interval / 1000)

    def set_speaking(self, voice=False, soundshare=False, priority=False, delay=0):
        value = SpeakingFlags.NONE.value
        if voice:
            value |= SpeakingFlags.VOICE.value
        if soundshare:
            value |= SpeakingFlags.SOUNDSHARE.value
        if priority:
            value |= SpeakingFlags.PRIORITY.value

        self.send(VoiceOPCode.SPEAKING, {
            'speaking': value,
            'delay': delay,
            'ssrc': self.ssrc,
        })

    def set_voice_state(self, channel_id, mute=False, deaf=False, video=False):
        self.client.gw.send(OPCode.VOICE_STATE_UPDATE, {
            'self_mute': bool(mute),
            'self_deaf': bool(deaf),
            'self_video': bool(video),
            'guild_id': None if self.is_dm else self.server_id,
            'channel_id': channel_id,
        })

    def send(self, op, data):
        if self.ws and self.ws.sock and self.ws.sock.connected:
            self.log.debug('[%s] sending OP %s (data = %s)', self, op, data)
            self.ws.send(self.encoder.encode({
                'op': op.value,
                'd': data,
            }), self.encoder.OPCODE)
        else:
            self.log.debug('[%s] dropping because ws is closed OP %s (data = %s)', self, op, data)

    def on_voice_client_connect(self, data):
        user_id = int(data['user_id'])

        self.audio_ssrcs[data['audio_ssrc']] = user_id
        # ignore data['voice_ssrc'] for now

    def on_voice_client_disconnect(self, data):
        user_id = int(data['user_id'])

        for ssrc in self.audio_ssrcs.keys():
            if self.audio_ssrcs[ssrc] == user_id:
                del self.audio_ssrcs[ssrc]
                break

    def on_voice_codecs(self, data):
        self.audio_codec = data['audio_codec']
        self.video_codec = data['video_codec']
        self.transport_id = data['media_session_id']

        # Set the UDP's RTP Audio Header's Payload Type
        self.udp.set_audio_codec(data['audio_codec'])

    def on_voice_hello(self, data):
        self.log.info('[%s] Received Voice HELLO payload, starting heartbeater', self)
        self._heartbeat_task = gevent.spawn(self._heartbeat, data['heartbeat_interval'])
        self.set_state(VoiceState.AUTHENTICATED)

    def on_voice_ready(self, data):
        self.log.info('[%s] Received Voice READY payload, attempting to negotiate voice connection w/ remote', self)
        self.set_state(VoiceState.CONNECTING)
        self.ssrc = data['ssrc']
        self.ip = data['ip']
        self.port = data['port']
        self._identified = True

        for mode in self.SUPPORTED_MODES:
            if mode in data['modes']:
                self.mode = mode
                self.log.debug('[%s] Selected mode %s', self, mode)
                break
        else:
            raise Exception('Failed to find a supported voice mode')

        self.log.debug('[%s] Attempting IP discovery over UDP to %s:%s', self, self.ip, self.port)
        self.udp = UDPVoiceClient(self)
        ip, port = self.udp.connect(self.ip, self.port)

        if not ip:
            self.log.error('Failed to discover our IP, perhaps a NAT or firewall is fucking us')
            self.disconnect()
            return

        codecs = []

        # Sending discord our available codecs and rtp payload type for it
        for idx, codec in enumerate(AudioCodecs):
            codecs.append({
                'name': codec,
                'type': 'audio',
                'priority': (idx + 1) * 1000,
                'payload_type': RTPPayloadTypes.get(codec).value,
            })

        self.log.debug('[%s] IP discovery completed (ip = %s, port = %s), sending SELECT_PROTOCOL', self, ip, port)
        self.send(VoiceOPCode.SELECT_PROTOCOL, {
            'protocol': 'udp',
            'data': {
                'port': port,
                'address': ip,
                'mode': self.mode,
            },
            'codecs': codecs,
        })
        self.send(VoiceOPCode.CLIENT_CONNECT, {
            'audio_ssrc': self.ssrc,
            'video_ssrc': 0,
            'rtx_ssrc': 0,
        })

    def on_voice_resumed(self, data):
        self.log.info('[%s] Received resumed', self)
        self.set_state(VoiceState.CONNECTED)

    def on_voice_sdp(self, sdp):
        self.log.info('[%s] Received session description, connection completed', self)

        self.mode = sdp['mode']
        self.audio_codec = sdp['audio_codec']
        self.video_codec = sdp['video_codec']
        self.transport_id = sdp['media_session_id']

        # Set the UDP's RTP Audio Header's Payload Type
        self.udp.set_audio_codec(sdp['audio_codec'])

        # Create a secret box for encryption/decryption
        self.udp.setup_encryption(bytes(bytearray(sdp['secret_key'])))

        self.set_state(VoiceState.CONNECTED)

    def on_voice_speaking(self, data):
        user_id = int(data['user_id'])

        self.audio_ssrcs[data['ssrc']] = user_id

        # Maybe rename speaking to voice in future
        payload = VoiceSpeaking(
            client=self,
            user_id=user_id,
            speaking=bool(data['speaking'] & SpeakingFlags.VOICE.value),
            soundshare=bool(data['speaking'] & SpeakingFlags.SOUNDSHARE.value),
            priority=bool(data['speaking'] & SpeakingFlags.PRIORITY.value),
        )

        self.client.gw.events.emit('VoiceSpeaking', payload)

    def on_message(self, msg):
        try:
            data = self.encoder.decode(msg)
            self.packets.emit(VoiceOPCode[data['op']], data['d'])
        except Exception:
            self.log.exception('Failed to parse voice gateway message: ')

    def on_error(self, err):
        self.log.error('[%s] Voice websocket error: %s', self, err)

    def on_open(self):
        if self._identified:
            self.send(VoiceOPCode.RESUME, {
                'server_id': self.server_id,
                'session_id': self._session_id,
                'token': self.token,
            })
        else:
            self.send(VoiceOPCode.IDENTIFY, {
                'server_id': self.server_id,
                'user_id': self.user_id,
                'session_id': self._session_id,
                'token': self.token,
                'video': self.video_enabled,
            })

    def on_close(self, code, reason):
        self.log.warning('[%s] Voice websocket closed: [%s] %s (%s)', self, code, reason, self._reconnects)

        if self._heartbeat_task:
            self._heartbeat_task.kill()
            self._heartbeat_task = None

        self.ws = None

        # If we killed the connection, don't try resuming
        if self.state == VoiceState.DISCONNECTED:
            return

        self.log.info('[%s] Attempting Websocket Resumption', self)

        self.set_state(VoiceState.RECONNECTING)

        # Check if code is not None, was not from us
        if code is not None:
            self._reconnects += 1

            if self.max_reconnects and self._reconnects > self.max_reconnects:
                raise VoiceException(
                    'Failed to reconnect after {} attempts, giving up'.format(self.max_reconnects), self)

            # Don't resume for these error codes:
            if 4000 <= code <= 4016:
                self._identified = False

                if self.udp and self.udp.connected:
                    self.udp.disconnect()

            wait_time = 5
        else:
            wait_time = 1

        self.log.info(
            '[%s] Will attempt to %s after %s seconds', self, 'resume' if self._identified else 'reconnect', wait_time)
        gevent.sleep(wait_time)

        self._connect_and_run()

    def connect(self, channel_id, timeout=10, **kwargs):
        if self.is_dm:
            channel_id = self.server_id

        if not channel_id:
            raise VoiceException('[%s] cannot connect to an empty channel id', self)

        if self.channel_id == channel_id:
            if self.state == VoiceState.CONNECTED:
                self.log.debug('[%s] Already connected to %s, returning', self, self.channel)
                return self
        else:
            if self.state == VoiceState.CONNECTED:
                self.log.debug('[%s] Moving to channel %s', self, channel_id)
            else:
                self.log.debug('[%s] Attempting connection to channel id %s', self, channel_id)
                self.set_state(VoiceState.AWAITING_ENDPOINT)

        self.set_voice_state(channel_id, **kwargs)

        if not self.state_emitter.once(VoiceState.CONNECTED, timeout=timeout):
            self.disconnect()
            raise VoiceException('Failed to connect to voice', self)
        else:
            return self

    def disconnect(self):
        if self.state == VoiceState.DISCONNECTED:
            return

        self.log.debug('[%s] disconnect called', self)
        self.set_state(VoiceState.DISCONNECTED)

        del self.client.state.voice_clients[self.server_id]

        if self._heartbeat_task:
            self._heartbeat_task.kill()
            self._heartbeat_task = None

        if self.ws and self.ws.sock and self.ws.sock.connected:
            self.ws.close()
            self.ws = None

        if self.udp and self.udp.connected:
            self.udp.disconnect()

        if self.channel_id:
            self.set_voice_state(None)

        self.client.gw.events.emit('VoiceDisconnect', self)

    def send_frame(self, *args, **kwargs):
        self.udp.send_frame(*args, **kwargs)

    def increment_timestamp(self, *args, **kwargs):
        self.udp.increment_timestamp(*args, **kwargs)
