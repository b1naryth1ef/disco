from unittest import TestCase

from tests.utils import APIClient


class TestReason(TestCase):
    def test_set_unicode_reason(self):
        api = APIClient()
        api.guilds_channels_modify(1, 2, 3, reason=u'yo \U0001F4BF test')

        _, kwargs = api.http.calls[0]
        self.assertEqual(kwargs['headers']['X-Audit-Log-Reason'], 'yo%20%F0%9F%92%BF%20test')

    def test_null_reason(self):
        api = APIClient()
        api.guilds_channels_modify(1, 2, 3, reason=None)

        _, kwargs = api.http.calls[0]
        self.assertFalse('X-Audit-Log-Reason' in kwargs['headers'])
