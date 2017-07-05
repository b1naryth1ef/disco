from unittest import TestCase

from disco.types.message import Sendable


class TestSendable(TestCase):
    def test_sendable_truncate(self):
        self.assertEqual(Sendable.truncate('*' * 2001), ('*' * 1997) + '...')
        self.assertEqual(Sendable.truncate('*' * 1999), '*' * 1999)
        self.assertEqual(Sendable.truncate(u'\U0001F947' * 20), u'\U0001F947' * 20)
        self.assertEqual(Sendable.truncate(u'\U0001F947' * 3000, tail=''), u'\U0001F947' * 2000)

    def test_sendable_fit(self):
        self.assertEqual(Sendable.fit('*' * 3000), '```{}```'.format('*' * 1994))
        self.assertEqual(Sendable.fit('test'), '```test```')
        self.assertEqual(Sendable.fit('test', '`', '`'), '`test`')
        self.assertEqual(Sendable.fit(u'\U0001F947'), u'```\U0001F947```')
