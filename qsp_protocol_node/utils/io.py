####################################################################################################
#                                                                                                  #
# (c) 2018 Quantstamp, Inc. All rights reserved.  This content shall not be used, copied,          #
# modified, redistributed, or otherwise disseminated except to the extent expressly authorized by  #
# Quantstamp for credentialed users. This content and its use are governed by the Quantstamp       #
# Demonstration License Terms at <https://s3.amazonaws.com/qsp-protocol-license/LICENSE.txt>.      #
#                                                                                                  #
####################################################################################################

"""
Provides utility methods for performing I/O-related tasks.
"""
import codecs
import os
import re
import yaml

from urllib.parse import urlparse
from urllib import request
from json import load
from hashlib import sha256


def fetch_file(uri):
    """
    Fetches a target file into the filesystem.
    """
    regex_file_uri = re.compile("^file://")
    if urlparse(uri).scheme not in 'file':
        local_file, _ = request.urlretrieve(uri)
    else:
        local_file = regex_file_uri.sub("", uri, 1)

    return local_file


def load_json(json_file_path):
    """
    Loads a JSON file as a in-memory dictionary.
    """
    json_dict = {}

    with open(json_file_path) as json_file:
        json_dict = load(json_file)

    return json_dict


def load_yaml(yaml_file_path):
    """
    Loads a YAML file as a in-memory dictionary
    """
    with open(yaml_file_path) as yaml_file:
        yaml_config = yaml.load(yaml_file)
    return yaml_config


def has_matching_line(file, regex):
    with open(file) as f:
        for line in f:
            if re.match(regex, line):
                return True
    return False


def digest(input, charset="utf-8"):
    return sha256(str(input).encode(charset)).hexdigest()


def digest_file(file, charset="utf-8"):
    return digest(read_file(file, charset), charset)


def read_file(file, charset="utf-8"):
    in_memory_str = None
    with codecs.open(file, 'r', charset) as stream:
        in_memory_str = stream.read()
    return in_memory_str


def dir_exists(dir, throw_exception=False):
    exists = True
    if not (os.path.exists(dir) and os.path.isdir(dir)):
        if throw_exception:
            raise Exception("Folder does not exist: {0}".format(dir))

        exists = False

    return exists


def file_exists(file, throw_exception=False):
    exists = True
    if (not os.path.exists(file)) or os.path.isdir(file):
        if throw_exception:
            raise Exception("File does not exist: {0}".format(file))

        exists = False

    return exists


def is_executable(file, throw_exception=False):
    return os.access(file, os.X_OK)
