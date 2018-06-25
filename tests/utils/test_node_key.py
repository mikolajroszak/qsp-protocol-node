import os
import os.path
import unittest
import utils.node_key

from utils.node_key import NodeKey


class TestNodeKey(unittest.TestCase):
    """Tests manipulation with keys using name mangling and a separate test key file."""

    def setUp(self):
        """Replaces a node key file with a test file and internally remembers the original value"""
        self.__original_file = NodeKey.KEY_FILENAME
        self.__test_key_file = ".test-node-key"
        NodeKey.KEY_FILENAME = self.__test_key_file
        if os.path.isfile(self.__test_key_file):
            os.remove(self.__test_key_file)

    def tearDown(self):
        """Restores teh original value for other test suites"""
        NodeKey.KEY_FILENAME = self.__original_file
        if os.path.isfile(self.__test_key_file):
            os.remove(self.__test_key_file)

    def test_is_valid(self):
        """
        Tests that the class correctly validates keys.
        """
        self.assertFalse(NodeKey._NodeKey__is_valid("nonsense"),
                         "This key should not be recognized as valid")
        uuid = "f0c41472-e1da-421a-a210-880165de55f6"
        self.assertTrue(NodeKey._NodeKey__is_valid(uuid),
                        "This key should be recognized as valid")

    def test_load_nonexistent(self):
        """Tests that the load of non-existent key file returns False"""
        self.assertFalse(NodeKey._NodeKey__load(), "The key file does not exist yet")

    def test_load_wrong_content(self):
        """Tests that the load of key file with invalid key returns False"""
        with open(self.__test_key_file, 'w+') as key_file:
            node_key = str("something that is not a key")
            key_file.write(node_key)
        self.assertFalse(NodeKey._NodeKey__load(), "The key file does not contain a key")

    def test_load_proper_content(self):
        """Tests that the load of a key file with proper key returns the key"""
        uuid = "f0c41472-e1da-421a-a210-880165de55f6"
        with open(self.__test_key_file, 'w+') as key_file:
            key_file.write(uuid)
        loaded = NodeKey._NodeKey__load()
        self.assertEquals(uuid, loaded,
                          "The key contains a valid key but " + str(loaded) + "was loaded")

    def test_recreate(self):
        """
        Tests that the class correctly recreates keys.
        """
        NodeKey._NodeKey__recreate()
        self.assertTrue(isinstance(NodeKey._NodeKey__load(), str), "The loaded key is not a string")

    def test_fetch(self):
        """
        Tests that the class correctly creates and reloads keys using public fetch.
        """
        key = NodeKey.fetch()
        self.assertTrue(isinstance(key, str), "The loaded key is not a string")
        self.assertTrue(NodeKey._NodeKey__is_valid(key), "The loaded key is not valid")
        reloaded_key = NodeKey.fetch()
        self.assertEqual(key, reloaded_key, "The reloaded key does not match the original")

    if __name__ == "__main__":
        unittest.main()
