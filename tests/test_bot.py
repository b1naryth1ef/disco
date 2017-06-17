from unittest import TestCase

from disco.client import ClientConfig, Client
from disco.bot.bot import Bot
from disco.bot.command import Command


class Object(object):
    pass


class MockBot(Bot):
    @property
    def commands(self):
        return getattr(self, '_commands', [])


class TestBot(TestCase):
    def setUp(self):
        self.client = Client(ClientConfig(
            {'config': 'TEST_TOKEN'}
        ))
        self.bot = MockBot(self.client)

    def test_command_abbreviation(self):
        groups = ['config', 'copy', 'copez', 'copypasta']
        result = self.bot.compute_group_abbrev(groups)
        self.assertDictEqual(result, {
            'config': 'con',
            'copypasta': 'copy',
            'copez': 'cope',
        })

        self.assertDictEqual(self.bot.compute_group_abbrev(['test']), {
            'test': 't',
        })

    def test_command_abbreivation_conflicting(self):
        groups = ['cat', 'cap', 'caz', 'cas']
        result = self.bot.compute_group_abbrev(groups)
        self.assertDictEqual(result, {})

    def test_many_commands(self):
        self.bot._commands = [
            Command(None, None, 'test{}'.format(i), '<test:str>')
            for i in range(1000)
        ]

        self.bot.compute_command_matches_re()
        match = self.bot.command_matches_re.match('test5 123')
        self.assertNotEqual(match, None)

        match = self.bot._commands[0].compiled_regex.match('test0 123 456')
        self.assertEqual(match.group(1).strip(), 'test0')
        self.assertEqual(match.group(2).strip(), '123 456')

    def test_command_grouping_greadyness(self):
        plugin = Object()
        plugin.bot = self.bot

        self.bot._commands = [
            Command(plugin, None, 'a', group='test'),
            Command(plugin, None, 'b', group='test')
        ]

        self.bot.recompute()
        self.assertNotEqual(self.bot.command_matches_re.match('test a'), None)
        self.assertNotEqual(self.bot.command_matches_re.match('te a'), None)
        self.assertNotEqual(self.bot.command_matches_re.match('t b'), None)
        self.assertEqual(self.bot.command_matches_re.match('testing b'), None)
        self.assertEqual(self.bot.command_matches_re.match('testlmao a'), None)

    def test_group_and_command(self):
        plugin = Object()
        plugin.bot = self.bot

        self.bot._commands = [
            Command(plugin, None, 'test'),
            Command(plugin, None, 'a', group='test'),
            Command(plugin, None, 'b', group='test'),
        ]

        self.bot.recompute()

        msg = Object()

        msg.content = '!test a'
        commands = list(self.bot.get_commands_for_message(False, None, '!', msg))
        self.assertEqual(commands[0][0], self.bot._commands[1])
        self.assertEqual(commands[1][0], self.bot._commands[0])

        msg.content = '!test'
        commands = list(self.bot.get_commands_for_message(False, None, '!', msg))
        self.assertEqual(commands[0][0], self.bot._commands[0])
