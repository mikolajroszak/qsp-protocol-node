import os
import unittest
import utils.node_key

from streaming import CloudWatchProvider
from utils.node_key import NodeKey


class TestCloudWatchProvider(unittest.TestCase):

    def setUp(self):
        """
        Replaces a node key file with a test file and internally remembers the original value
        """
        self.__original_file = NodeKey.KEY_FILENAME
        self.__test_key_file = ".test-node-key"
        NodeKey.KEY_FILENAME = self.__test_key_file
        if os.path.isfile(self.__test_key_file):
            os.remove(self.__test_key_file)

    def tearDown(self):
        """
        Restores teh original value for other test suites
        """
        NodeKey.KEY_FILENAME = self.__original_file
        if os.path.isfile(self.__test_key_file):
            os.remove(self.__test_key_file)

    def test_init(self):
        """
        Tests that the constructor properly initializes the parameters and that a handler can be
        returned without raising any errors.
        """
        log_group = "group"
        log_stream = "stream-{id}"
        interval = "15"
        provider = CloudWatchProvider(log_group, log_stream, interval)
        uuid = NodeKey.fetch()
        self.assertEqual("stream-" + uuid, provider._CloudWatchProvider__stream_name,
                         "Stream name was not set properly")
        self.assertEqual(log_group, provider._CloudWatchProvider__log_group,
                         "Log group was not set properly")
        self.assertEqual(interval, provider._CloudWatchProvider__send_interval,
                         "Send interval was not set properly")
        self.assertIsNotNone(provider.get_handler(), "None handler was returned")
