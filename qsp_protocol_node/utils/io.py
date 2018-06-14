"""
Provides utility methods for performing I/O-related tasks.
"""
import re
import codecs

from urllib.parse import urlparse
from urllib import request
from json import load
from hashlib import sha256

__regex_file_uri = re.compile("^file://")


def fetch_file(uri):
    """
    Fetches a target file into the filesystem.
    """
    if urlparse(uri).scheme not in 'file':
        local_file, _ = request.urlretrieve(uri)
    else:
        local_file = __regex_file_uri.sub("", uri, 1)

    return local_file


def load_json(json_file_path):
    """
    Loads a JSON file as a in-memory dictionary.
    """
    with open(json_file_path) as json_file:
        json_dict = load(json_file)

    return json_dict


def has_matching_line(file, regex):
    with open(file) as f:
        for line in f:
            if re.match(regex, line):
                return True

    return False


def digest(file, charset="utf-8"):
    with codecs.open(file, 'r', charset) as stream:
        in_memory_str = stream.read()

    return sha256(in_memory_str.encode(charset)).hexdigest()
