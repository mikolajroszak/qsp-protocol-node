from dpath.util import get

def get(dictionary, path, default=None, accept_none=True):
    """
    Extracts a configuration entry from a given dictionary.
    """
    try:
        value = dpath.util.get(dictionary, path)
    except KeyError as key_error:
        if default is not None:
            return default

        if accept_none:
            return None

        raise key_error

    return value