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
from audit.threads import PollRequestsThread
from audit.report_processing import ReportEncoder
from helpers.qsp_test import QSPTest
from helpers.resource import (
    fetch_config,
    remove,
    resource_uri,
)
from utils.io import fetch_file, load_json

from timeout_decorator import timeout
from threading import Thread
from unittest import mock
from unittest.mock import MagicMock


class TestPoliceFunctions(QSPTest):

    def test_call_to_is_police_officer_no_exception(self):
        """
        Tests whether calling the smart contract to assess whether a node is a police works.
        """
        config = fetch_config(inject_contract=True)
        QSPAuditNode.is_police_officer(config)


class TestPoliceLogic(QSPTest):

    @classmethod
    def setUpClass(cls):
        QSPTest.setUpClass()
        config = fetch_config(inject_contract=True)
        remove(config.evt_db_path)

    def setUp(self):
        self.__config = fetch_config(inject_contract=True)
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

        # Adds a police event to the database to trigger the flow of a police
        # check. Since no other thread should be writing to the DB at this
        # point, the write can be performed without a lock.
        poll_requests_instance = PollRequestsThread(self.__config)
        poll_requests_instance._PollRequestsThread__add_evt_to_db(
            request_id=request_id,
            requestor=self.__audit_node.config.audit_contract_address,
            price=100,
            uri=resource_uri("reports/DAOBug.json"),
            block_nbr=100,
            is_audit=False
        )

        with mock.patch('audit.audit.SubmitReportThread', return_value=submit_report_instance), \
             mock.patch('audit.audit.PollRequestsThread', return_value=poll_requests_instance):
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
            poll_requests_instance = PollRequestsThread(self.__config)
            poll_requests_instance._PollRequestsThread__add_evt_to_db(
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
        if self.__audit_node.exec:
            self.__audit_node.stop()

        remove(self.__config.evt_db_path)
