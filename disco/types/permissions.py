from disco.types.base import BitsetMap, BitsetValue


class Permissions(BitsetMap):
    CREATE_INSTANT_INVITE = 1 << 0
    KICK_MEMBERS = 1 << 1
    BAN_MEMBERS = 1 << 2
    ADMINISTRATOR = 1 << 3
    MANAGE_CHANNELS = 1 << 4
    MANAGE_GUILD = 1 << 5
    ADD_REACTIONS = 1 << 6
    VIEW_AUDIT_LOG = 1 << 7
    PRIORITY_SPEAKER = 1 << 8
    STREAM = 1 << 9
    VIEW_CHANNEL = 1 << 10
    SEND_MESSAGES = 1 << 11
    SEND_TSS_MESSAGES = 1 << 12
    MANAGE_MESSAGES = 1 << 13
    EMBED_LINKS = 1 << 14
    ATTACH_FILES = 1 << 15
    READ_MESSAGE_HISTORY = 1 << 16
    MENTION_EVERYONE = 1 << 17
    USE_EXTERNAL_EMOJIS = 1 << 18
    CONNECT = 1 << 20
    SPEAK = 1 << 21
    MUTE_MEMBERS = 1 << 22
    DEAFEN_MEMBERS = 1 << 23
    MOVE_MEMBERS = 1 << 24
    USE_VAD = 1 << 25
    CHANGE_NICKNAME = 1 << 26
    MANAGE_NICKNAMES = 1 << 27
    MANAGE_ROLES = 1 << 28
    MANAGE_WEBHOOKS = 1 << 29
    MANAGE_EMOJIS = 1 << 30


class PermissionValue(BitsetValue):
    map = Permissions

    def can(self, *perms):
        # Administrator permission overwrites all others
        if self.administrator:
            return True
        return self.check(*perms)

    @classmethod
    def text(cls):
        return cls(523264)

    @classmethod
    def voice(cls):
        return cls(66060288)


class Permissible(object):
    __slots__ = []

    def get_permissions(self):
        raise NotImplementedError

    def can(self, user, *args):
        perms = self.get_permissions(user)
        return perms.administrator or perms.can(*args)
