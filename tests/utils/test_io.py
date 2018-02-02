from tempfile import mkstemp
from random import random

import json
import os
import unittest

from utils.io import load_json

class TestFile(unittest.TestCase):
    
    def test_load_json_for_inexistent_file(self):
        target = str(random())
        
        with self.assertRaises(Exception):
            load_json(target)

    def test_load_json_for_existent_file(self):
        json_obj={
            'key1': 123,
            'key2': 456, 
        }

        fd, tmp = mkstemp(text = True)

        with os.fdopen(fd, "w") as json_file:
            json.dump(json_obj, json_file)

        json_file.close()

        found = load_json(tmp)
        expected= json_obj

        self.assertEqual(found, expected)

    if __name__ == "__main__":
        unittest.main()
        
