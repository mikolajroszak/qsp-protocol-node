"""
Provides functions related to testing resources.
"""
import os


def resource_uri(path, is_main=False):
    """
    Returns the filesystem URI of a given resource.
    """
    if is_main:
        return "file://{0}/../../qsp_protocol_node/{1}".format(os.path.dirname(__file__), path)
    else:
        return "file://{0}/../resources/{1}".format(os.path.dirname(__file__), path)
