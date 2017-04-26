from disco.bot import Plugin
from disco.bot.command import CommandError
from disco.voice.player import Player
from disco.voice.playable import YoutubeDLInput, BufferedOpusEncoderPlayable
from disco.voice.client import VoiceException


class MusicPlugin(Plugin):
    def load(self, ctx):
        super(MusicPlugin, self).load(ctx)
        self.guilds = {}

    @Plugin.command('join')
    def on_join(self, event):
        if event.guild.id in self.guilds:
            return event.msg.reply("I'm already playing music here.")

        state = event.guild.get_member(event.author).get_voice_state()
        if not state:
            return event.msg.reply('You must be connected to voice to use that command.')

        try:
            client = state.channel.connect()
        except VoiceException as e:
            return event.msg.reply('Failed to connect to voice: `{}`'.format(e))

        self.guilds[event.guild.id] = Player(client)
        self.guilds[event.guild.id].complete.wait()
        del self.guilds[event.guild.id]

    def get_player(self, guild_id):
        if guild_id not in self.guilds:
            raise CommandError("I'm not currently playing music here.")
        return self.guilds.get(guild_id)

    @Plugin.command('leave')
    def on_leave(self, event):
        player = self.get_player(event.guild.id)
        player.disconnect()

    @Plugin.command('play', '<url:str>')
    def on_play(self, event, url):
        item = YoutubeDLInput(url).pipe(BufferedOpusEncoderPlayable)
        self.get_player(event.guild.id).queue.put(item)

    @Plugin.command('pause')
    def on_pause(self, event):
        self.get_player(event.guild.id).pause()

    @Plugin.command('resume')
    def on_resume(self, event):
        self.get_player(event.guild.id).resume()
