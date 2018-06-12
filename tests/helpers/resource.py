"""
Provides functions related to testing resources.
"""
import os


def resource_uri(name):
    """
    Returns the filesystem URI of a given resource.
    """
    return "file://{0}/../resources/{1}".format(os.path.dirname(__file__), name)


def main_resource_uri(path):
    """
    Returns the filesystem URI of a given resource in the main codebase (not in the test section).
    """
    return "file://{0}/../../qsp_protocol_node/{1}".format(os.path.dirname(__file__), path)
