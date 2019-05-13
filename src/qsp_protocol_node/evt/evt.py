####################################################################################################
#                                                                                                  #
# (c) 2018, 2019 Quantstamp, Inc. This content and its use are governed by the license terms at    #
# <https://s3.amazonaws.com/qsp-protocol-license/V2_LICENSE.txt>                                   #
#                                                                                                  #
####################################################################################################

__AUDIT = 'AU'
__POLICE_CHECK = 'PC'


def is_audit(evt):
    return evt['fk_type'] == __AUDIT


def is_police_check(evt):
    return evt['fk_type'] == __POLICE_CHECK


def set_evt_as_audit(evt):
    evt['fk_type'] = __AUDIT
    return evt


def set_evt_as_police_check(evt):
    evt['fk_type'] = __POLICE_CHECK
    return evt
