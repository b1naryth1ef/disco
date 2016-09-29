import inflection

from collections import defaultdict, deque, namedtuple
from weakref import WeakValueDictionary

from disco.gateway.packets import OPCode

StackMessage = namedtuple('StackMessage', ['id', 'channel_id', 'author_id'])


class StateConfig(object):
    # Whether to keep a buffer of messages
    track_messages = True

    # The number maximum number of messages to store
    track_messages_size = 100


class State(object):
    EVENTS = [
        'Ready', 'GuildCreate', 'GuildUpdate', 'GuildDelete', 'GuildMemberAdd', 'GuildMemberRemove',
        'GuildMemberUpdate', 'GuildMemberChunk', 'GuildRoleCreate', 'GuildRoleUpdate', 'GuildRoleDelete',
        'ChannelCreate', 'ChannelUpdate', 'ChannelDelete', 'VoiceStateUpdate'
    ]

    def __init__(self, client, config=None):
        self.client = client
        self.config = config or StateConfig()
        self.listeners = []

        self.me = None

        self.dms = {}
        self.guilds = {}
        self.channels = WeakValueDictionary()
        self.users = WeakValueDictionary()
        self.voice_states = WeakValueDictionary()

        self.messages = defaultdict(lambda: deque(maxlen=self.config.track_messages_size))
        if self.config.track_messages:
            self.EVENTS += ['MessageCreate', 'MessageDelete']

        self.bind()

    def unbind(self):
        map(lambda k: k.unbind(), self.listeners)
        self.listeners = []

    def bind(self):
        for event in self.EVENTS:
            func = 'on_' + inflection.underscore(event)
            self.listeners.append(self.client.events.on(event, getattr(self, func)))

    def on_ready(self, event):
        self.me = event.user

    def on_message_create(self, event):
        self.messages[event.message.channel_id].append(
            StackMessage(event.message.id, event.message.channel_id, event.message.author.id))

    def on_message_update(self, event):
        message, cid = event.message, event.message.channel_id
        if cid not in self.messages:
            return

        sm = next((i for i in self.messages[cid] if i.id == message.id), None)
        if not sm:
            return

        sm.id = message.id
        sm.channel_id = cid
        sm.author_id = message.author.id

    def on_message_delete(self, event):
        if event.channel_id not in self.messages:
            return

        sm = next((i for i in self.messages[event.channel_id] if i.id == event.id), None)
        if not sm:
            return

        self.messages[event.channel_id].remove(sm)

    def on_guild_create(self, event):
        self.guilds[event.guild.id] = event.guild
        self.channels.update(event.guild.channels)

        for member in event.guild.members.values():
            self.users[member.user.id] = member.user

        # Request full member list
        self.client.gw.send(OPCode.REQUEST_GUILD_MEMBERS, {
            'guild_id': event.guild.id,
            'query': '',
            'limit': 0,
        })

    def on_guild_update(self, event):
        self.guilds[event.guild.id].update(event.guild)

    def on_guild_delete(self, event):
        if event.guild_id in self.guilds:
            # Just delete the guild, channel references will fall
            del self.guilds[event.guild_id]

    def on_channel_create(self, event):
        if event.channel.is_guild and event.channel.guild_id in self.guilds:
            self.guilds[event.channel.guild_id].channels[event.channel.id] = event.channel
            self.channels[event.channel.id] = event.channel
        elif event.channel.is_dm:
            self.dms[event.channel.id] = event.channel
            self.channels[event.channel.id] = event.channel

    def on_channel_update(self, event):
        if event.channel.id in self.channels:
            self.channels[event.channel.id].update(event.channel)

    def on_channel_delete(self, event):
        if event.channel.is_guild and event.channel.guild_id in self.guilds:
            del self.guilds[event.channel.id]
        elif event.channel.is_dm:
            del self.pms[event.channel.id]

    def on_voice_state_update(self, event):
        # Happy path: we have the voice state and want to update/delete it
        guild = self.guilds.get(event.state.guild_id)

        if event.state.session_id in guild.voice_states:
            if event.state.channel_id:
                guild.voice_states[event.state.session_id].update(event.state)
            else:
                del guild.voice_states[event.state.session_id]
        elif event.state.channel_id:
            guild.voice_states[event.state.session_id] = event.state

    def on_guild_member_add(self, event):
        if event.member.user.id not in self.users:
            self.users[event.member.user.id] = event.member.user
        else:
            event.member.user = self.users[event.member.user.id]

        if event.member.guild_id not in self.guilds:
            return

        event.member.guild = self.guilds[event.member.guild_id]
        self.guilds[event.member.guild_id].members[event.member.id] = event.member

    def on_guild_member_update(self, event):
        if event.guild_id not in self.guilds:
            return

        self.guilds[event.guild_id].members[event.user.id].roles = event.roles
        self.guilds[event.guild_id].members[event.user.id].user.update(event.user)

    def on_guild_member_remove(self, event):
        if event.guild_id not in self.guilds:
            return

        if event.user.id not in self.guilds[event.guild_id].members:
            return

        del self.guilds[event.guild_id].members[event.user.id]

    def on_guild_member_chunk(self, event):
        if event.guild_id not in self.guilds:
            return

        guild = self.guilds[event.guild_id]
        for member in event.members:
            member.guild = guild
            member.guild_id = guild.id
            guild.members[member.id] = member

    def on_guild_role_create(self, event):
        if event.guild_id not in self.guilds:
            return

        self.guilds[event.guild_id].roles[event.role.id] = event.role

    def on_guild_role_update(self, event):
        if event.guild_id not in self.guilds:
            return

        self.guilds[event.guild_id].roles[event.role.id].update(event.role)

    def on_guild_role_delete(self, event):
        if event.guild_id not in self.guilds:
            return

        del self.guilds[event.guild_id].roles[event.role.id]
