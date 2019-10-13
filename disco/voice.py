import os
import json

import gevent
from gevent.os import make_nonblocking, nb_read

from disco.gateway.packets import OPCode
from disco.types.channel import Channel
from disco.util.emitter import Emitter
from telecom import TelecomConnection, AvConvPlayable

try:
    import youtube_dl
    ytdl = youtube_dl.YoutubeDL()
except ImportError:
    ytdl = None


class YoutubeDLPlayable(AvConvPlayable):
    def __init__(self, url):
        url = next(self.from_url(url), None)
        if not url:
            raise Exception('No result found for URL {}'.format(url))
        super(YoutubeDLPlayable, self).__init__(url)

    @classmethod
    def from_url(cls, url):
        assert ytdl is not None, 'YoutubeDL isn\'t installed'

        results = ytdl.extract_info(url, download=False)
        if 'entries' not in results:
            results = [results]
        else:
            results = results['entries']

        for result in results:
            audio_formats = [fmt for fmt in result['formats'] if fmt['vcodec'] == 'none' and fmt['acodec'] == 'opus']
            if not audio_formats:
                raise Exception("Couldn't find valid audio format for {}".format(url))

            best_audio_format = sorted(audio_formats, key=lambda i: i['abr'], reverse=True)[0]
            yield AvConvPlayable(best_audio_format['url'])


class VoiceConnection(object):
    def __init__(self, client, guild_id, enable_events=False):
        self.client = client
        self.guild_id = guild_id
        self.channel_id = None
        self.enable_events = enable_events
        self._conn = None
        self._voice_server_update_listener = self.client.events.on(
            'VoiceServerUpdate',
            self._on_voice_server_update,
        )
        self._event_reader_greenlet = None

        self.events = None
        if self.enable_events:
            self.events = Emitter()

        self._mute = False
        self._deaf = False

    def __del__(self):
        if self._event_reader_greenlet:
            self._event_reader_greenlet.kill()

    @property
    def mute(self):
        return self._mute

    @property
    def deaf(self):
        return self._deaf

    @mute.setter
    def mute(self, value):
        if value is self._mute:
            return

        self._mute = value
        self._send_voice_state_update()

    @deaf.setter
    def deaf(self, value):
        if value is self._deaf:
            return

        self._deaf = value
        self._send_voice_state_update()

    @classmethod
    def from_channel(self, channel, **kwargs):
        assert channel.is_voice, 'Cannot connect to a non voice channel'
        conn = VoiceConnection(channel.client, channel.guild_id, **kwargs)
        conn.connect(channel.id)
        return conn

    def set_channel(self, channel_or_id):
        if channel_or_id and isinstance(channel_or_id, Channel):
            channel_or_id = channel_or_id.id

        self.channel_id = channel_or_id
        self._send_voice_state_update()

    def connect(self, channel_id):
        assert self._conn is None, 'Already connected'

        self.set_channel(channel_id)

        self._conn = TelecomConnection(
            self.client.state.me.id,
            self.guild_id,
            self.client.gw.session_id,
        )

        if self.enable_events:
            r, w = os.pipe()

            self._event_reader_greenlet = gevent.spawn(self._event_reader, r)
            self._conn.set_event_pipe(w)

    def disconnect(self):
        assert self._conn is not None, 'Not connected'

        # Send disconnection
        self.set_channel(None)

        # If we have an event reader, kill it
        if self._event_reader_greenlet:
            self._event_reader_greenlet.kill()
            self._event_reader_greenlet = None

        # Delete our connection so it will get GC'd
        del self._conn
        self._conn = None

    def play(self, playable):
        self._conn.play(playable)

    def play_file(self, url):
        self._conn.play(AvConvPlayable(url))

    def _on_voice_server_update(self, event):
        if not self._conn or event.guild_id != self.guild_id:
            return

        self._conn.update_server_info(event.endpoint, event.token)

    def _send_voice_state_update(self):
        self.client.gw.send(OPCode.VOICE_STATE_UPDATE, {
            'self_mute': self._mute,
            'self_deaf': self._deaf,
            'self_video': False,
            'guild_id': self.guild_id,
            'channel_id': self.channel_id,
        })

    def _event_reader(self, fd):
        if not make_nonblocking(fd):
            raise Exception('failed to make event pipe non-blocking')

        buff = ""
        while True:
            buff += nb_read(fd, 2048).decode('utf-8')

            parts = buff.split('\n')
            for message in parts[:-1]:
                event = json.loads(message)
                self.events.emit(event['e'], event['d'])

            if len(parts) > 1:
                buff = parts[-1]
            else:
                buff = ""
