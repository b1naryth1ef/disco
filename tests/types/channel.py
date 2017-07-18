from unittest import TestCase

from disco.types.channel import Channel, ChannelType


class TestChannel(TestCase):
    def test_deprecated_nsfw_channel(self):
        channel = Channel(
            name='nsfw-testing',
            type=ChannelType.GUILD_TEXT)
        self.assertTrue(channel.is_nsfw)

        channel = Channel(
            name='nsfw-testing',
            type=ChannelType.GUILD_VOICE)
        self.assertFalse(channel.is_nsfw)

        channel = Channel(
            name='nsfw_testing',
            type=ChannelType.GUILD_TEXT)
        self.assertFalse(channel.is_nsfw)

    def test_nsfw_channel(self):
        channel = Channel(name='test', nsfw=True, type=ChannelType.GUILD_TEXT)
        assert channel.is_nsfw
