

class State(object):
    def __init__(self, client):
        self.client = client

        self.me = None

        self.channels = {}
        self.guilds = {}

        self.client.events.on('Ready', self.on_ready)

        # Guilds
        self.client.events.on('GuildCreate', self.on_guild_create)
        self.client.events.on('GuildUpdate', self.on_guild_update)
        self.client.events.on('GuildDelete', self.on_guild_delete)

        # Channels
        self.client.events.on('ChannelCreate', self.on_channel_create)
        self.client.events.on('ChannelUpdate', self.on_channel_update)
        self.client.events.on('ChannelDelete', self.on_channel_delete)

    def on_ready(self, event):
        self.me = event.user

    def on_guild_create(self, event):
        self.guilds[event.guild.id] = event.guild

        for channel in event.guild.channels:
            self.channels[channel.id] = channel

    def on_guild_update(self, event):
        # TODO
        pass

    def on_guild_delete(self, event):
        if event.guild_id in self.guilds:
            del self.guilds[event.guild_id]

        # CHANNELS?

    def on_channel_create(self, event):
        self.channels[event.channel.id] = event.channel

    def on_channel_update(self, event):
        # TODO
        pass

    def on_channel_delete(self, event):
        if event.channel.id in self.channels:
            del self.channels[event.channel.id]
