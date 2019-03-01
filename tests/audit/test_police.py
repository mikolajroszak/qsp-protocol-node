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
from audit.threads import SubmitReportThread
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

    def test_call_to_get_next_police_assignment(self):
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

    def __test_police_poll_event(self, is_police, is_new_assignment, is_already_processed,
                                 should_add_evt):
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
        uncompressed_report = load_json(fetch_file(resource_uri("reports/DAOBug.json")))
        request_id = uncompressed_report['request_id']

        encoder = ReportEncoder()
        compressed_report = encoder.compress_report(uncompressed_report, request_id)

        # Creates a mocked method for retrieving the audit result from the blockchain.
        submit_report_instance = SubmitReportThread(self.__config)
        submit_report_instance._SubmitReportThread__get_report_in_blockchain = MagicMock()
        submit_report_instance._SubmitReportThread__get_report_in_blockchain.return_value = \
            compressed_report

        with mock.patch('audit.audit.SubmitReportThread', return_value=submit_report_instance):
            # Sets the node as a police officer.
            self.__audit_node.is_police_officer = MagicMock()
            self.__audit_node.is_police_officer.return_value = True

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
            sql = "select * from audit_evt where request_id = {0} and fk_status == 'SB' and fk_type='PC'"
            while not result_found:
                rows = sql3lite_worker.execute(sql.format(request_id))
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

        # Sets the audit result to be retrieved from the blockchain (should cause
        # an exception within the audit node)
        submit_report_instance = SubmitReportThread(self.__config)
        submit_report_instance._SubmitReportThread__get_report_in_blockchain = MagicMock()
        submit_report_instance._SubmitReportThread__get_report_in_blockchain.return_value = None

        with mock.patch('audit.audit.SubmitReportThread', return_value=submit_report_instance):

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
            sql = "select * from audit_evt where request_id = {0} and fk_status == 'ER'"
            while not result_found:
                rows = sql3lite_worker.execute(sql.format(request_id))
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
