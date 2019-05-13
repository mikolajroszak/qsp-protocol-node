####################################################################################################
#                                                                                                  #
# (c) 2018, 2019 Quantstamp, Inc. This content and its use are governed by the license terms at    #
# <https://s3.amazonaws.com/qsp-protocol-license/V2_LICENSE.txt>                                   #
#                                                                                                  #
####################################################################################################


def get_first(rows, key=None):
    if rows is None or len(rows) == 0:
        return {}

    row = rows[0]
    if key is None:
        return row

    return row[key]
