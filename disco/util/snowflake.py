import six

from datetime import datetime

UNIX_EPOCH = datetime(1970, 1, 1)
DISCORD_EPOCH = 1420070400000


def to_datetime(snowflake):
    """
    Converts a snowflake to a UTC datetime.
    """
    return datetime.utcfromtimestamp(to_unix(snowflake))


def to_unix(snowflake):
    return to_unix_ms(snowflake) / 1000


def to_unix_ms(snowflake):
    return (int(snowflake) >> 22) + DISCORD_EPOCH


def from_datetime(date):
    return from_timestamp((date - UNIX_EPOCH).total_seconds())


def from_timestamp(ts):
    return long(ts * 1000.0 - DISCORD_EPOCH) << 22


def to_snowflake(i):
    if isinstance(i, six.integer_types):
        return i
    elif isinstance(i, str):
        return int(i)
    elif hasattr(i, 'id'):
        return i.id

    raise Exception('{} ({}) is not convertable to a snowflake'.format(type(i), i))


def calculate_shard(shard_count, guild_id):
    return (guild_id >> 22) % shard_count
