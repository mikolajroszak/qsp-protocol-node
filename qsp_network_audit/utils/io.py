"""
Provides utilitiy methods for performing I/O-related tasks.
"""
from urllib.parse import urlparse
from urllib import request
from json import load
import os
import re

def fetch_file(uri):
    """
    Fetches a target file into the filesystem.
    """
    if urlparse(uri).scheme not in ('file'):
        local_file, _ = request.urlretrieve(uri)
    else:
        local_file = uri


    return local_file

def resource_path(name):
    """
    Returns the filesystem path of a given resource.
    """
    return "/{0}/../../resources/{1}".format(os.path.dirname(__file__), name)

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

