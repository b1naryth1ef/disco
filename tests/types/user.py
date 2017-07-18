from unittest import TestCase

from disco.types.user import User, DefaultAvatars


class TestChannel(TestCase):
    def test_user_avatar(self):
        u = User(
            id=12345,
            username='test123',
            avatar='1234567890abcdefghijkl',
            discriminator='1234',
            bot=False)

        self.assertEqual(
            u.avatar_url, 'https://cdn.discordapp.com/avatars/12345/1234567890abcdefghijkl.webp?size=1024'
        )

    def test_user_default_avatar(self):
        u = User(id=123456, discriminator='1234')
        self.assertEqual(u.default_avatar, DefaultAvatars.RED)
        self.assertEqual(u.avatar_url, 'https://cdn.discordapp.com/embed/avatars/4.png')
