####################################################################################################
#                                                                                                  #
# (c) 2018 Quantstamp, Inc. All rights reserved.  This content shall not be used, copied,          #
# modified, redistributed, or otherwise disseminated except to the extent expressly authorized by  #
# Quantstamp for credentialed users. This content and its use are governed by the Quantstamp       #
# Demonstration License Terms at <https://s3.amazonaws.com/qsp-protocol-license/LICENSE.txt>.      #
#                                                                                                  #
####################################################################################################


from audit import QSPAuditNode
from helpers.resource import fetch_config, remove
from helpers.qsp_test import QSPTest

from unittest.mock import patch


class TestStakingFunctions(QSPTest):

    @classmethod
    def setUpClass(cls):
        QSPTest.setUpClass()
        config = fetch_config()
        remove(config.evt_db_path)

    def setUp(self):
        self.__config = fetch_config()
        self.__audit_node = QSPAuditNode(self.__config)

    def test_call_to_has_enough_stake(self):
        """
        Tests whether calling the smart contract to assess staking works.
        """
        exception = None
        try:
            self.__audit_node._QSPAuditNode__has_enough_stake()
        except Exception as e:
            exception = e
        self.assertIsNone(exception)

    def test_qsp_return_in_get_min_stake_audit(self):
        """
        Tests whether the conversion in get_min_stake_audit works, return
        a result in QSP.
        """
        with patch('audit.audit.mk_read_only_call', return_value=(1000 * (10 ** 18))):
            self.assertEquals(self.__audit_node._QSPAuditNode__get_min_stake_qsp(), 1000)

    def test_call_to_get_min_stake_audit(self):
        """
        Tests whether calling the smart contract works.
        """
        exception = None
        try:
            self.__audit_node._QSPAuditNode__get_min_stake_qsp()
        except Exception as e:
            exception = e
        self.assertIsNone(exception)

    def tearDown(self):
        if self.__audit_node._QSPAuditNode__exec:
            self.__audit_node.stop()

        remove(self.__config.evt_db_path)
