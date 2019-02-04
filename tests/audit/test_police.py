####################################################################################################
#                                                                                                  #
# (c) 2018 Quantstamp, Inc. All rights reserved.  This content shall not be used, copied,          #
# modified, redistributed, or otherwise disseminated except to the extent expressly authorized by  #
# Quantstamp for credentialed users. This content and its use are governed by the Quantstamp       #
# Demonstration License Terms at <https://s3.amazonaws.com/qsp-protocol-license/LICENSE.txt>.      #
#                                                                                                  #
####################################################################################################

import json

from audit import QSPAuditNode
from audit.report_processing import ReportEncoder
from helpers.qsp_test import QSPTest
from helpers.resource import fetch_config, remove, resource_uri
from utils.io import fetch_file, load_json

from timeout_decorator import timeout
from threading import Thread
from unittest import mock
from unittest.mock import MagicMock


class TestPoliceFunctions(QSPTest):

    @classmethod
    def setUpClass(cls):
        QSPTest.setUpClass()
        config = fetch_config()
        remove(config.evt_db_path)

    def setUp(self):
        self.__config = fetch_config()
        self.__audit_node = QSPAuditNode(self.__config)

    def test_call_to_is_police_officer(self):
        """
        Tests whether calling the smart contract to assess whether a node is a police works.
        """
        exception = None
        try:
            self.__audit_node.is_police_officer()
        except Exception as e:
            exception = e
        self.assertIsNone(exception)

    def test_call_to_get_report_in_blockchain(self):
        """
        Tests whether calling the smart contract to get a report in the blockchain works.
        """
        exception = None
        try:
            self.__audit_node._QSPAuditNode__get_report_in_blockchain(0)
        except Exception as e:
            exception = e
        self.assertIsNone(exception)

    def test_call_to_get_next_police_assigment(self):
        """
        Tests whether calling the smart contract to get the next police
        assigment works.
        """
        exception = None
        try:
            self.__audit_node._QSPAuditNode__get_next_police_assignment()
        except Exception as e:
            exception = e
        self.assertIsNone(exception)

    def test_call_to_submit_police_report(self):
        """
        Tests whether calling the smart contract to get the next police
        assigment works.
        """
        exception = None
        try:
            self.__audit_node._QSPAuditNode__submit_police_report(1, "", True)
        except Exception as e:
            exception = e
        self.assertIsNone(exception)

    def test_encoding_to_get_report_in_blockchain(self):
        compressed_report_bytes = b' \x03\x90\xb5U\xf2\xefS\'\xe1\x89`\x01\xd8tb\xe2\xe6\x9d\xa3\xda\xac\xe1\x8c\xb7\xb6\x0f"1$\x93\xa9\xc4\xf9\x05\x00\x0f\x0c\x00\x0f\r\x00\x0f\x05\x00\x13\x03\x00\x0f\x07\x00\x0f\x1a\x00\x0f\x15\x00\x06\x12\x00\x0e\x12\x00\n'
        expected_compressed_report_hex = '200390b555f2ef5327e1896001d87462e2e69da3daace18cb7b60f22312493a9c4f905000f0c000f0d000f05001303000f07000f1a000f15000612000e12000a'
        with mock.patch('audit.audit.mk_read_only_call', return_value=compressed_report_bytes):
            hex_compressed_report = self.__audit_node._QSPAuditNode__get_report_in_blockchain(
                request_id=1
            )
            self.assertEquals(hex_compressed_report, expected_compressed_report_hex)

    def test_is_report_deemed_correct_in_case_of_no_vulnerabilities(self):
        self.__test_auditor_report_correctness(
            auditor_compressed_report=self.__compressed_report("reports/Empty.json"),
            police_report=self.__load_report("reports/Empty.json"),
            deemed_correct=True
        )

    def test_is_report_demmed_correct_in_case_of_incorrect_encoding(self):
        self.__test_auditor_report_correctness(
            auditor_compressed_report=b'garbage',
            police_report=resource_uri("reports/DAOBug.json"),
            deemed_correct=False
        )

    def test_non_police_cannot_poll_check_events(self):
        self.__test_police_poll_event(
            is_police=False,
            is_new_assignment=False,
            is_already_processed=False,
            should_add_evt=False
        )

    def test_police_does_not_save_evt_upon_no_request(self):
        self.__test_police_poll_event(
            is_police=True,
            is_new_assignment=False,
            is_already_processed=False,
            should_add_evt=False
        )

    def test_police_does_not_save_evt_upon_repeated_request(self):
        self.__test_police_poll_event(
            is_police=True,
            is_new_assignment=True,
            is_already_processed=True,
            should_add_evt=False
        )

    def test_police_saves_evt_upon_new_request(self):
        self.__test_police_poll_event(
            is_police=True,
            is_new_assignment=True,
            is_already_processed=False,
            should_add_evt=True
        )

    def test_is_report_deemed_correct_for_empty_police_report(self):
        # Get the contract_hash from the DAOBug report
        full_report = self.__load_report("reports/DAOBug.json")
        contract_hash = full_report.get('contract_hash', "")

        # Update the police report with the correct hash
        police_report = self.__load_report("reports/Empty.json")
        police_report['contract_hash'] = contract_hash

        self.__test_auditor_report_correctness(
            auditor_compressed_report=self.__compressed_report("reports/DAOBug.json"),
            police_report=police_report,
            deemed_correct=True
        )

    def test_is_report_deemed_incorrect_for_different_contract_hashes(self):
        police_report = self.__load_report("reports/DAOBug.json")
        police_report['contract_hash'] = "1111111111111111111111111111111111111111111111111111111111111111"

        self.__test_auditor_report_correctness(
            auditor_compressed_report=self.__compressed_report("reports/DAOBug.json"),
            police_report=police_report,
            deemed_correct=False
        )

    def test_is_report_deemed_incorrect_for_disjoint_reports(self):
        self.__test_auditor_report_correctness(
            auditor_compressed_report=self.__compressed_report("reports/Empty.json"),
            police_report=self.__load_report("reports/DAOBug.json"),
            deemed_correct=False
        )

    def test_is_report_deemed_correct_for_equal_reports(self):
        self.__test_auditor_report_correctness(
            auditor_compressed_report=self.__compressed_report("reports/DAOBug.json"),
            police_report=self.__load_report("reports/DAOBug.json"),
            deemed_correct=True
        )

    def test_is_report_deemed_correct_for_report_under_threshold(self):
        self.__test_auditor_report_correctness(
            auditor_compressed_report=self.__compressed_report("reports/DAOBugIncomplete.json"),
            police_report=self.__load_report("reports/DAOBug.json"),
            deemed_correct=False
        )

    def tearDown(self):
        if self.__audit_node._QSPAuditNode__exec:
            self.__audit_node.stop()

        remove(self.__config.evt_db_path)

    def __load_report(self, report_file_path):
        return load_json(fetch_file(resource_uri(report_file_path)))

    def __compressed_report(self, report_file_path):
        full_report = self.__load_report(report_file_path)
        request_id = full_report['request_id']

        encoder = ReportEncoder()
        return encoder.compress_report(full_report, request_id)

    def __test_auditor_report_correctness(self, auditor_compressed_report, police_report, deemed_correct):
        self.__audit_node._QSPAuditNode__get_report_in_blockchain = MagicMock()
        self.__audit_node._QSPAuditNode__get_report_in_blockchain.return_value = \
            auditor_compressed_report

        is_deemed_correct = self.__audit_node._QSPAuditNode__is_report_deemed_correct(
            1,
            police_report
        )
        self.assertEquals(is_deemed_correct, deemed_correct)

    def __test_police_poll_event(self, is_police, is_new_assignment, is_already_processed, should_add_evt):
        # Configures the behaviour of is_police_officer
        self.__audit_node.is_police_officer = MagicMock()
        self.__audit_node.is_police_officer.return_value = is_police

        # Configures the behaviour of __get_next_police_assignment
        self.__audit_node._QSPAuditNode__get_next_police_assignment = MagicMock()
        self.__audit_node._QSPAuditNode__get_next_police_assignment.return_value = \
            [is_new_assignment, 1, 0, "some-url", 1, False]

        # Configures the behaviour of __is_request_processed
        self.__config.event_pool_manager.is_request_processed = MagicMock()
        self.__config.event_pool_manager.is_request_processed.return_value = \
            is_already_processed

        # Configures the behaviour of __add_evt_to_db
        self.__audit_node._QSPAuditNode__add_evt_to_db = MagicMock()

        # Polls for police requests
        self.__audit_node._QSPAuditNode__poll_police_request()

        if should_add_evt:
            self.__audit_node._QSPAuditNode__add_evt_to_db.assert_called()
        else:
            self.__audit_node._QSPAuditNode__add_evt_to_db.assert_not_called()


class TestPoliceLogic(QSPTest):

    @classmethod
    def setUpClass(cls):
        QSPTest.setUpClass()
        config = fetch_config()
        remove(config.evt_db_path)

    def setUp(self):
        self.__config = fetch_config()
        self.__audit_node = QSPAuditNode(self.__config)

    @timeout(300, timeout_exception=StopIteration)
    def test_successful_police_audit(self):
        # Sets the node as a police officer.
        self.__audit_node.is_police_officer = MagicMock()
        self.__audit_node.is_police_officer.return_value = True

        uncompressed_report = load_json(fetch_file(resource_uri("reports/DAOBug.json")))
        request_id = uncompressed_report['request_id']

        encoder = ReportEncoder()
        compressed_report = encoder.compress_report(uncompressed_report, request_id)

        # Sets the audit result to be retrived from the blockchain.
        self.__audit_node._QSPAuditNode__get_report_in_blockchain = MagicMock()
        self.__audit_node._QSPAuditNode__get_report_in_blockchain.return_value = compressed_report

        # Sets the audit report value itself to be returned by the audit node.
        self.__audit_node.audit = MagicMock()
        self.__audit_node.audit.return_value = {
            'audit_state': uncompressed_report['audit_state'],
            'audit_uri': 'http://some-url.com',
            'audit_hash': 'some-hash',
            'full_report': json.dumps(uncompressed_report),
            'compressed_report': compressed_report
        }

        # Adds a police event to the database to trigger the flow of a police
        # check. Since no other thread should be writing to the DB at this
        # point, the write can be performed without a lock.
        self.__audit_node._QSPAuditNode__add_evt_to_db(
            request_id=request_id,
            requestor=self.__audit_node.config.audit_contract_address,
            price=100,
            uri=resource_uri("reports/DAOBug.json"),
            block_nbr=100,
            is_audit=False
        )

        self.__run_audit_node()

        sql3lite_worker = self.__audit_node.config.event_pool_manager.sql3lite_worker
        result_found = False

        # Waits till the record moves from assigned status to submitted.
        while not result_found:
            rows = sql3lite_worker.execute(
                "select * from audit_evt where request_id = {0} and fk_status == 'SB' and fk_type='PC'".format(
                    request_id
                )
            )
            if len(rows) == 0:
                continue

            self.assertTrue(len(rows), 1)
            result_found = True

    @timeout(300, timeout_exception=StopIteration)
    def test_police_fails_when_original_audit_is_not_found(self):
        # Sets the node as a police officer.
        self.__audit_node.is_police_officer = MagicMock()
        self.__audit_node.is_police_officer.return_value = True

        uncompressed_report = load_json(fetch_file(resource_uri("reports/DAOBug.json")))
        request_id = uncompressed_report['request_id']

        encoder = ReportEncoder()
        compressed_report = encoder.compress_report(uncompressed_report, request_id)

        # Sets the audit result to be retrived from the blockchain (should cause
        # an exception within the audit node)
        self.__audit_node._QSPAuditNode__get_report_in_blockchain = MagicMock()
        self.__audit_node._QSPAuditNode__get_report_in_blockchain.return_value = None

        # Sets the audit report value itself to be returned by the audit node.
        self.__audit_node.audit = MagicMock()
        self.__audit_node.audit.return_value = {
            'audit_state': uncompressed_report['audit_state'],
            'audit_uri': 'http://some-url.com',
            'audit_hash': 'some-hash',
            'full_report': json.dumps(uncompressed_report),
            'compressed_report': compressed_report
        }

        # Adds a police event to the database to trigger the flow of a police
        # check. Since no other thread should be writing to the DB at this
        # point, the write can be performed without a lock.
        self.__audit_node._QSPAuditNode__add_evt_to_db(
            request_id=request_id,
            requestor=self.__audit_node.config.audit_contract_address,
            price=100,
            uri=resource_uri("reports/DAOBug.json"),
            block_nbr=100,
            is_audit=False
        )

        self.__run_audit_node()

        sql3lite_worker = self.__audit_node.config.event_pool_manager.sql3lite_worker
        result_found = False

        # Waits till the record moves from assigned status to error.
        while not result_found:
            rows = sql3lite_worker.execute(
                "select * from audit_evt where request_id = {0} and fk_status == 'ER'".format(
                    request_id
                )
            )
            if len(rows) == 0:
                continue

            self.assertTrue(len(rows), 1)
            result_found = True

    def __run_audit_node(self):
        def exec():
            self.__audit_node.run()

        audit_node_thread = Thread(target=exec, name="Audit node")
        audit_node_thread.start()

    def tearDown(self):
        if self.__audit_node._QSPAuditNode__exec:
            self.__audit_node.stop()

        remove(self.__config.evt_db_path)
