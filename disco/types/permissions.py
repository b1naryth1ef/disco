import six


class Permissions(object):
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

    @classmethod
    def keys(cls):
        for k, v in six.iteritems(cls.__dict__):
            if k.isupper():
                yield k


class PermissionValue(object):
    __slots__ = ['value']

    def __init__(self, value=0):
        if isinstance(value, PermissionValue):
            value = value.value

        self.value = value

    def can(self, *perms):
        # Administrator permission overwrites all others
        if self.administrator:
            return True

        for perm in perms:
            if not (self.value & perm) == perm:
                return False
        return True

    def add(self, other):
        if isinstance(other, PermissionValue):
            self.value |= other.value
        elif isinstance(other, int):
            self.value |= other
        else:
            raise TypeError('Cannot PermissionValue.add from type {}'.format(type(other)))
        return self

    def sub(self, other):
        if isinstance(other, PermissionValue):
            self.value &= ~other.value
        elif isinstance(other, int):
            self.value &= ~other
        else:
            raise TypeError('Cannot PermissionValue.sub from type {}'.format(type(other)))
        return self

    def __iadd__(self, other):
        return self.add(other)

    def __isub__(self, other):
        return self.sub(other)

    def __getattribute__(self, name):
        try:
            perm_value = getattr(Permissions, name.upper())
            return (self.value & perm_value) == perm_value
        except AttributeError:
            return object.__getattribute__(self, name)

    def __setattr__(self, name, value):
        try:
            perm_value = getattr(Permissions, name.upper())
        except AttributeError:
            return super(PermissionValue, self).__setattr__(name, value)

        if value:
            self.value |= perm_value
        else:
            self.value &= ~perm_value

    def __int__(self):
        return self.value

    def to_dict(self):
        return {
            k: getattr(self, k) for k in list(Permissions.keys())
        }

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
