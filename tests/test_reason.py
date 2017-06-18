from unittest import TestCase
from utils import TestAPIClient


class TestReason(TestCase):
    def test_set_unicode_reason(self):
        api = TestAPIClient()
        api.guilds_channels_modify(1, 2, 3, reason=u'yo \U0001F4BF test')

        _, kwargs = api.http.calls[0]
        self.assertEquals(kwargs['headers']['X-Audit-Log-Reason'], 'yo%20%F0%9F%92%BF%20test')
