from holster.enum import Enum, EnumAttr

Permissions = Enum(
    CREATE_INSTANT_INVITE=1 << 0,
    KICK_MEMBERS=1 << 1,
    BAN_MEMBERS=1 << 2,
    ADMINISTRATOR=1 << 3,
    MANAGE_CHANNELS=1 << 4,
    MANAGE_GUILD=1 << 5,
    READ_MESSAGES=1 << 10,
    SEND_MESSAGES=1 << 11,
    SEND_TSS_MESSAGES=1 << 12,
    MANAGE_MESSAGES=1 << 13,
    EMBED_LINKS=1 << 14,
    ATTACH_FILES=1 << 15,
    READ_MESSAGE_HISTORY=1 << 16,
    MENTION_EVERYONE=1 << 17,
    USE_EXTERNAL_EMOJIS=1 << 18,
    CONNECT=1 << 20,
    SPEAK=1 << 21,
    MUTE_MEMBERS=1 << 22,
    DEAFEN_MEMBERS=1 << 23,
    MOVE_MEMBERS=1 << 24,
    USE_VAD=1 << 25,
    CHANGE_NICKNAME=1 << 26,
    MANAGE_NICKNAMES=1 << 27,
    MANAGE_ROLES=1 << 28,
    MANAGE_WEBHOOKS=1 << 29,
    MANAGE_EMOJIS=1 << 30,
)


class PermissionValue(object):
    __slots__ = ['value']

    def __init__(self, value=0):
        if isinstance(value, EnumAttr) or isinstance(value, PermissionValue):
            value = value.value

        self.value = value

    def can(self, *perms):
        for perm in perms:
            if isinstance(perm, EnumAttr):
                perm = perm.value
            if not (self.value & perm) == perm:
                return False
        return True

    def add(self, other):
        if isinstance(other, PermissionValue):
            self.value |= other.value
        elif isinstance(other, int):
            self.value |= other
        elif isinstance(other, EnumAttr):
            setattr(self, other.name, True)
        else:
            raise TypeError('Cannot PermissionValue.add from type {}'.format(type(other)))
        return self

    def sub(self, other):
        if isinstance(other, PermissionValue):
            self.value &= ~other.value
        elif isinstance(other, int):
            self.value &= other
        elif isinstance(other, EnumAttr):
            setattr(self, other.name, False)
        else:
            raise TypeError('Cannot PermissionValue.sub from type {}'.format(type(other)))
        return self

    def __iadd__(self, other):
        return self.add(other)

    def __isub__(self, other):
        return self.sub(other)

    def __getattribute__(self, name):
        if name in Permissions.attrs:
            return (self.value & Permissions[name].value) == Permissions[name].value
        else:
            return object.__getattribute__(self, name)

    def __setattr__(self, name, value):
        if name not in Permissions.attrs:
            return super(PermissionValue, self).__setattr__(name, value)

        if value:
            self.value |= Permissions[name].value
        else:
            self.value &= ~Permissions[name].value

    def to_dict(self):
        return {
            k: getattr(self, k) for k in Permissions.attrs
        }

    @classmethod
    def text(cls):
        return cls(523264)

    @classmethod
    def voice(cls):
        return cls(66060288)


class Permissible(object):
    __slots__ = []

    def can(self, user, *args):
        perms = self.get_permissions(user)
        return perms.administrator or perms.can(*args)
