####################################################################################################
#                                                                                                  #
# (c) 2018 Quantstamp, Inc. All rights reserved.  This content shall not be used, copied,          #
# modified, redistributed, or otherwise disseminated except to the extent expressly authorized by  #
# Quantstamp for credentialed users. This content and its use are governed by the Quantstamp       #
# Demonstration License Terms at <https://s3.amazonaws.com/qsp-protocol-license/LICENSE.txt>.      #
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
