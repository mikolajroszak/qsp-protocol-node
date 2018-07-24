import unittest

from streaming import CloudWatchProvider


class TestCloudWatchProvider(unittest.TestCase):
    def test_init(self):
        """
        Tests that the constructor properly initializes the parameters and that a handler can be
        returned without raising any errors.
        """
        log_group = "group"
        log_stream = "stream-{id}"
        interval = "15"
        account = "0x12345"
        provider = CloudWatchProvider(account, log_group, log_stream, interval)
        self.assertEqual("stream-" + account, provider._CloudWatchProvider__stream_name,
                         "Stream name was not set properly")
        self.assertEqual(log_group, provider._CloudWatchProvider__log_group,
                         "Log group was not set properly")
        self.assertEqual(interval, provider._CloudWatchProvider__send_interval,
                         "Send interval was not set properly")
        self.assertIsNotNone(provider.get_handler(), "None handler was returned")
