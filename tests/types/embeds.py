from unittest import TestCase

from datetime import datetime
from disco.types.message import MessageEmbed


class TestEmbeds(TestCase):
    def test_empty_embed(self):
        embed = MessageEmbed()
        self.assertDictEqual(
            embed.to_dict(),
            {
                'image': {},
                'author': {},
                'video': {},
                'thumbnail': {},
                'footer': {},
                'fields': [],
                'type': 'rich',
            })

    def test_embed(self):
        embed = MessageEmbed(
            title='Test Title',
            description='Test Description',
            url='https://test.url/'
        )
        obj = embed.to_dict()
        self.assertEqual(obj['title'], 'Test Title')
        self.assertEqual(obj['description'], 'Test Description')
        self.assertEqual(obj['url'], 'https://test.url/')

