"""
Provides functions related to testing resources.
"""
import os

def resource_uri(name):
    """
    Returns the filesystem path of a given resource.
    """
    return "file://{0}/../resources/{1}".format(os.path.dirname(__file__), name)