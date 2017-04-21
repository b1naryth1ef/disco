from unittest import TestCase

from disco.client import ClientConfig, Client
from disco.bot.bot import Bot


class TestBot(TestCase):
    def setUp(self):
        self.client = Client(ClientConfig(
            {'config': 'TEST_TOKEN'}
        ))
        self.bot = Bot(self.client)

    def test_command_abbreviation(self):
        groups = ['config', 'copy', 'copez', 'copypasta']
        result = self.bot.compute_group_abbrev(groups)
        self.assertDictEqual(result, {
            'config': 'con',
            'copypasta': 'copy',
            'copez': 'cope',
        })

    def test_command_abbreivation_conflicting(self):
        groups = ['cat', 'cap', 'caz', 'cas']
        result = self.bot.compute_group_abbrev(groups)
        self.assertDictEqual(result, {})
