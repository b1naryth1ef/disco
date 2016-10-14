import six

from disco.api.http import Routes, HTTPClient
from disco.util.logging import LoggingClass

from disco.types.user import User
from disco.types.message import Message
from disco.types.guild import Guild, GuildMember, Role
from disco.types.channel import Channel
from disco.types.invite import Invite
from disco.types.webhook import Webhook


def optional(**kwargs):
    """
    Takes a set of keyword arguments, creating a dictionary with only the non-
    null values.

    :returns: dict
    """
    return {k: v for k, v in six.iteritems(kwargs) if v is not None}


class APIClient(LoggingClass):
    """
    An abstraction over the :class:`disco.api.http.HTTPClient` that composes requests, and fits
    the models with the returned data.
    """
    def __init__(self, client):
        super(APIClient, self).__init__()

        self.client = client
        self.http = HTTPClient(self.client.config.token)

    def gateway(self, version, encoding):
        data = self.http(Routes.GATEWAY_GET).json()
        return data['url'] + '?v={}&encoding={}'.format(version, encoding)

    def channels_get(self, channel):
        r = self.http(Routes.CHANNELS_GET, dict(channel=channel))
        return Channel.create(self.client, r.json())

    def channels_modify(self, channel, **kwargs):
        r = self.http(Routes.CHANNELS_MODIFY, dict(channel=channel), json=kwargs)
        return Channel.create(self.client, r.json())

    def channels_delete(self, channel):
        r = self.http(Routes.CHANNELS_DELETE, dict(channel=channel))
        return Channel.create(self.client, r.json())

    def channels_messages_list(self, channel, around=None, before=None, after=None, limit=50):
        r = self.http(Routes.CHANNELS_MESSAGES_LIST, dict(channel=channel), params=optional(
            around=around,
            before=before,
            after=after,
            limit=limit
        ))

        return Message.create_map(self.client, r.json())

    def channels_messages_get(self, channel, message):
        r = self.http(Routes.CHANNELS_MESSAGES_GET, dict(channel=channel, message=message))
        return Message.create(self.client, r.json())

    def channels_messages_create(self, channel, content, nonce=None, tts=False):
        r = self.http(Routes.CHANNELS_MESSAGES_CREATE, dict(channel=channel), json={
            'content': content,
            'nonce': nonce,
            'tts': tts,
        })

        return Message.create(self.client, r.json())

    def channels_messages_modify(self, channel, message, content):
        r = self.http(Routes.CHANNELS_MESSAGES_MODIFY,
                dict(channel=channel, message=message),
                json={'content': content})
        return Message.create(self.client, r.json())

    def channels_messages_delete(self, channel, message):
        self.http(Routes.CHANNELS_MESSAGES_DELETE, dict(channel=channel, message=message))

    def channels_messages_delete_bulk(self, channel, messages):
        self.http(Routes.CHANNELS_MESSAGES_DELETE_BULK, dict(channel=channel), json={'messages': messages})

    def channels_permissions_modify(self, channel, permission, allow, deny, typ):
        self.http(Routes.CHANNELS_PERMISSIONS_MODIFY, dict(channel=channel, permission=permission), json={
            'allow': allow,
            'deny': deny,
            'type': typ,
        })

    def channels_permissions_delete(self, channel, permission):
        self.http(Routes.CHANNELS_PERMISSIONS_DELETE, dict(channel=channel, permission=permission))

    def channels_invites_list(self, channel):
        r = self.http(Routes.CHANNELS_INVITES_LIST, dict(channel=channel))
        return Invite.create_map(self.client, r.json())

    def channels_invites_create(self, channel, max_age=86400, max_uses=0, temporary=False, unique=False):
        r = self.http(Routes.CHANNELS_INVITES_CREATE, dict(channel=channel), json={
            'max_age': max_age,
            'max_uses': max_uses,
            'temporary': temporary,
            'unique': unique
        })
        return Invite.create(self.client, r.json())

    def channels_pins_list(self, channel):
        r = self.http(Routes.CHANNELS_PINS_LIST, dict(channel=channel))
        return Message.create_map(self.client, r.json())

    def channels_pins_create(self, channel, message):
        self.http(Routes.CHANNELS_PINS_CREATE, dict(channel=channel, message=message))

    def channels_pins_delete(self, channel, message):
        self.http(Routes.CHANNELS_PINS_DELETE, dict(channel=channel, message=message))

    def channels_webhooks_create(self, channel, name=None, avatar=None):
        r = self.http(Routes.CHANNELS_WEBHOOKS_CREATE, dict(channel=channel), json=optional(
            name=name,
            avatar=avatar,
        ))
        return Webhook.create(self.client, r.json())

    def channels_webhooks_list(self, channel):
        r = self.http(Routes.CHANNELS_WEBHOOKS_LIST, dict(channel=channel))
        return Webhook.create_map(self.client, r.json())

    def guilds_get(self, guild):
        r = self.http(Routes.GUILDS_GET, dict(guild=guild))
        return Guild.create(self.client, r.json())

    def guilds_modify(self, guild, **kwargs):
        r = self.http(Routes.GUILDS_MODIFY, dict(guild=guild), json=kwargs)
        return Guild.create(self.client, r.json())

    def guilds_delete(self, guild):
        r = self.http(Routes.GUILDS_DELETE, dict(guild=guild))
        return Guild.create(self.client, r.json())

    def guilds_channels_list(self, guild):
        r = self.http(Routes.GUILDS_CHANNELS_LIST, dict(guild=guild))
        return Channel.create_map(self.client, r.json(), guild_id=guild)

    def guilds_channels_create(self, guild, **kwargs):
        r = self.http(Routes.GUILDS_CHANNELS_CREATE, dict(guild=guild), json=kwargs)
        return Channel.create(self.client, r.json(), guild_id=guild)

    def guilds_channels_modify(self, guild, channel, position):
        self.http(Routes.GUILDS_CHANNELS_MODIFY, dict(guild=guild), json={
            'id': channel,
            'position': position,
        })

    def guilds_members_list(self, guild):
        r = self.http(Routes.GUILDS_MEMBERS_LIST, dict(guild=guild))
        return GuildMember.create_map(self.client, r.json(), guild_id=guild)

    def guilds_members_get(self, guild, member):
        r = self.http(Routes.GUILDS_MEMBERS_GET, dict(guild=guild, member=member))
        return GuildMember.create(self.client, r.json(), guild_id=guild)

    def guilds_members_modify(self, guild, member, **kwargs):
        self.http(Routes.GUILDS_MEMBERS_MODIFY, dict(guild=guild, member=member), json=kwargs)

    def guilds_members_kick(self, guild, member):
        self.http(Routes.GUILDS_MEMBERS_KICK, dict(guild=guild, member=member))

    def guilds_bans_list(self, guild):
        r = self.http(Routes.GUILDS_BANS_LIST, dict(guild=guild))
        return User.create_map(self.client, r.json())

    def guilds_bans_create(self, guild, user, delete_message_days):
        self.http(Routes.GUILDS_BANS_CREATE, dict(guild=guild, user=user), params={
            'delete-message-days': delete_message_days,
        })

    def guilds_bans_delete(self, guild, user):
        self.http(Routes.GUILDS_BANS_DELETE, dict(guild=guild, user=user))

    def guilds_roles_list(self, guild):
        r = self.http(Routes.GUILDS_ROLES_LIST, dict(guild=guild))
        return Role.create_map(self.client, r.json(), guild_id=guild)

    def guilds_roles_create(self, guild):
        r = self.http(Routes.GUILDS_ROLES_CREATE, dict(guild=guild))
        return Role.create(self.client, r.json(), guild_id=guild)

    def guilds_roles_modify_batch(self, guild, roles):
        r = self.http(Routes.GUILDS_ROLES_MODIFY_BATCH, dict(guild=guild), json=roles)
        return Role.create_map(self.client, r.json(), guild_id=guild)

    def guilds_roles_modify(self, guild, role, **kwargs):
        r = self.http(Routes.GUILDS_ROLES_MODIFY, dict(guild=guild, role=role), json=kwargs)
        return Role.create(self.client, r.json(), guild_id=guild)

    def guilds_roles_delete(self, guild, role):
        self.http(Routes.GUILDS_ROLES_DELETE, dict(guild=guild, role=role))

    def guilds_webhooks_list(self, guild):
        r = self.http(Routes.GUILDS_WEBHOOKS_LIST, dict(guild=guild))
        return Webhook.create_map(self.client, r.json())

    def invites_get(self, invite):
        r = self.http(Routes.INVITES_GET, dict(invite=invite))
        return Invite.create(self.client, r.json())

    def invites_delete(self, invite):
        r = self.http(Routes.INVITES_DELETE, dict(invite=invite))
        return Invite.create(self.client, r.json())

    def webhooks_get(self, webhook):
        r = self.http(Routes.WEBHOOKS_GET, dict(webhook=webhook))
        return Webhook.create(self.client, r.json())

    def webhooks_modify(self, webhook, name=None, avatar=None):
        r = self.http(Routes.WEBHOOKS_MODIFY, dict(webhook=webhook), json=optional(
            name=name,
            avatar=avatar,
        ))
        return Webhook.create(self.client, r.json())

    def webhooks_delete(self, webhook):
        self.http(Routes.WEBHOOKS_DELETE, dict(webhook=webhook))

    def webhooks_token_get(self, webhook, token):
        r = self.http(Routes.WEBHOOKS_TOKEN_GET, dict(webhook=webhook, token=token))
        return Webhook.create(self.client, r.json())

    def webhooks_token_modify(self, webhook, token, name=None, avatar=None):
        r = self.http(Routes.WEBHOOKS_TOKEN_MODIFY, dict(webhook=webhook, token=token), json=optional(
            name=name,
            avatar=avatar,
        ))
        return Webhook.create(self.client, r.json())

    def webhooks_token_delete(self, webhook, token):
        self.http(Routes.WEBHOOKS_TOKEN_DLEETE, dict(webhook=webhook, token=token))

    def webhooks_token_execute(self, webhook, token, data, wait=False):
        obj = self.http(
            Routes.WEBHOOKS_TOKEN_EXECUTE,
            dict(webhook=webhook, token=token),
            json=optional(**data), params={'wait': int(wait)})

        if wait:
            return Message.create(self.client, obj.json())
