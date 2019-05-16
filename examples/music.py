from disco.bot import Plugin
from disco.voice import VoiceConnection, YoutubeDLPlayable


class MusicPlugin(Plugin):
    def load(self, data):
        super(MusicPlugin, self).load(data)
        self._connections = {}

    @Plugin.command('join')
    def on_join(self, event):
        vs = event.guild.get_member(event.author).get_voice_state()
        if not vs:
            return event.msg.reply('you are not in a voice channel')

        if event.guild.id in self._connections:
            if self._connections[event.guild.id].channel_id == vs.channel_id:
                return event.msg.reply('already in that channel')
            else:
                self._connections[event.guild.id].set_channel(vs.channel)
                return

        self._connections[event.guild.id] = VoiceConnection.from_channel(vs.channel, enable_events=True)

    @Plugin.command('play', '<song:str>')
    def on_play(self, event, song):
        if event.guild.id not in self._connections:
            return event.msg.reply('not in voice here')

        playables = list(YoutubeDLPlayable.from_url(song))
        for playable in playables:
            self._connections[event.guild.id].play(playable)
