from disco.types.channel import Channel, ChannelType


def test_deprecated_nsfw_channel():
    channel = Channel(
        name='nsfw-testing',
        type=ChannelType.GUILD_TEXT)
    assert channel.is_nsfw

    channel = Channel(
        name='nsfw-testing',
        type=ChannelType.GUILD_VOICE)
    assert not channel.is_nsfw

    channel = Channel(
        name='nsfw_testing',
        type=ChannelType.GUILD_TEXT)
    assert not channel.is_nsfw


def test_nsfw_channel():
    channel = Channel(name='test', nsfw=True, type=ChannelType.GUILD_TEXT)
    assert channel.is_nsfw
