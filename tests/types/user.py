from disco.types.user import User, DefaultAvatars


def test_user_avatar_url():
    u = User(id=12345, avatar='1234567890abcdefghijkl')
    assert u.avatar_url == 'https://cdn.discordapp.com/avatars/12345/1234567890abcdefghijkl.webp?size=1024'
    avatar_url = u.get_avatar_url(still_format='png')
    assert avatar_url == 'https://cdn.discordapp.com/avatars/12345/1234567890abcdefghijkl.png?size=1024'


def test_user_animated_avatar_url():
    u = User(id=12345, avatar='a_1234567890abcdefghijkl')
    assert u.avatar_url == 'https://cdn.discordapp.com/avatars/12345/a_1234567890abcdefghijkl.gif?size=1024'
    avatar_url = u.get_avatar_url(animated_format='webp')
    assert avatar_url == 'https://cdn.discordapp.com/avatars/12345/a_1234567890abcdefghijkl.webp?size=1024'


def test_user_default_avatar_url():
    u = User(id=12345, discriminator='1234')
    assert u.default_avatar == DefaultAvatars.RED
    assert u.avatar_url == 'https://cdn.discordapp.com/embed/avatars/4.png'
