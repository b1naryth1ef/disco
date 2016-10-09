from datetime import datetime

DISCORD_EPOCH = 1420070400000


def to_datetime(snowflake):
    """
    Converts a snowflake to a UTC datetime.
    """
    return datetime.utcfromtimestamp(to_unix(snowflake))


def to_unix(snowflake):
    return to_unix_ms(snowflake) / 1000


def to_unix_ms(snowflake):
    return ((int(snowflake) >> 22) + DISCORD_EPOCH)
