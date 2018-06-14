def get_first(rows, key=None):
    if rows is None or len(rows) == 0:
        return {}

    row = rows[0]
    if key is None:
        return row

    return row[key]
