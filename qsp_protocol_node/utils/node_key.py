import uuid
import logging

from pathlib import Path


class NodeKey:

    KEY_FILENAME = ".node.key"

    @staticmethod
    def __is_valid(key):
        try:
            uuid_obj = uuid.UUID(key)
        except Exception as err:
            logging.debug('Could not instantiate UUID object: "{0}"'.format(err))
            return False

        return str(uuid_obj) == key

    @staticmethod
    def __load():
        my_file = Path(NodeKey.KEY_FILENAME)
        if not my_file.is_file():
            logging.debug('Node key not loaded - file "{0}" not found'.format(NodeKey.KEY_FILENAME))
            return False

        with open(NodeKey.KEY_FILENAME, 'r') as key_file:
            node_key = key_file.read()
            if not NodeKey.__is_valid(node_key):
                logging.debug(
                    'Invalid node key in file "{0}": "{1}"'.format(NodeKey.KEY_FILENAME, node_key))
                return False

            logging.debug('Node key loaded successfully: "{0}"'.format(node_key))
            return node_key

    @staticmethod
    def __recreate():
        with open(NodeKey.KEY_FILENAME, 'w+') as key_file:
            node_key = str(uuid.uuid4())
            key_file.write(node_key)
            logging.debug('Node key re-created successfully: "{0}"'.format(node_key))

    @staticmethod
    def fetch():
        node_key = NodeKey.__load()
        if node_key:
            logging.debug('Node key found and loaded successfully: "{0}"'.format(node_key))
            return node_key

        NodeKey.__recreate()
        node_key = NodeKey.__load()
        if node_key:
            logging.debug('Node key re-created and loaded successfully: "{0}"'.format(node_key))
            return node_key
        else:
            raise Exception('Could not load key after re-creating')
