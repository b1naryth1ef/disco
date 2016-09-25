import gevent

from holster.enum import Enum
from holster.emitter import Emitter

from disco.util.websocket import Websocket
from disco.util.logging import LoggingClass
from disco.util.json import loads, dumps
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


class VoiceClient(LoggingClass):
    def __init__(self, channel):
        assert(channel.is_voice)
        self.channel = channel
        self.client = self.channel.client

        self.packets = Emitter(gevent.spawn)
        self.packets.on(VoiceOPCode.READY, self.on_voice_ready)
        self.packets.on(VoiceOPCode.SESSION_DESCRIPTION, self.on_voice_sdp)

        # State
        self.state = VoiceState.DISCONNECTED
        self.connected = gevent.event.Event()
        self.token = None
        self.endpoint = None

        self.update_listener = None

        # Websocket connection
        self.ws = None

    def send(self, op, data):
        self.ws.send(dumps({
            'op': op.value,
            'd': data,
        }))

    def on_voice_ready(self, data):
        print data

    def on_voice_sdp(self, data):
        print data

    def on_voice_server_update(self, data):
        if self.channel.guild_id != data.guild_id or not data.token:
            return

        if self.token and self.token != data.token:
            return

        self.token = data.token
        self.state = VoiceState.AUTHENTICATING

        self.endpoint = 'wss://{}'.format(data.endpoint.split(':', 1)[0])
        self.ws = Websocket(
            self.endpoint,
            on_message=self.on_message,
            on_error=self.on_error,
            on_open=self.on_open,
            on_close=self.on_close,
        )
        self.ws.run_forever()

    def on_message(self, ws, msg):
        try:
            data = loads(msg)
        except:
            self.log.exception('Failed to parse voice gateway message: ')

        self.packets.emit(VoiceOPCode[data['op']], data)

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

    def on_close(self, ws):
        # TODO
        self.log.warning('Voice websocket disconnected')

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
