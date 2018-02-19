"""
Provides the QSP Audit node implementation.
"""
from queue import Queue
from datetime import datetime
from tempfile import mkstemp
from time import sleep
import os
import json
import utils.logging as logging_utils
logging = logging_utils.getLogging()

from utils.io import fetch_file, digest
from utils.args import replace_args

from hashlib import sha256

class QSPAuditNode:

    def __init__(self, config):
        """
        Builds a QSPAuditNode object from the given input parameters.
        """
        self.__config = config
        self.__filter = self.__config.internal_contract.on("LogAuditRequested")
        self.__exec = False

    def run(self):
        """
        Runs the QSP Audit node in a busy waiting fashion.
        """
        self.__exec = True
        while self.__exec:
            requests = self.__filter.get()

            if requests == []:
                sleep(self.__config.evt_polling)
                continue

            logging.debug("Found incomming audit requests: {0}".format(
                str(requests)
            ))

            # Process all incoming requests
            for audit_request in requests:
                price = audit_request['args']['price']
                request_id = str(audit_request['args']['requestId'])

                # Accepts all requests whose reward is at least as
                # high as given by min_reward
                if price >= self.__config.min_price:
                    logging.debug("Accepted processing audit request: {0}".format(
                        str(audit_request)
                    ), requestId=request_id)
                    try:
                        requestor = audit_request['args']['requestor']
                        contract_uri = audit_request['args']['uri']

                        report = self.audit(requestor, contract_uri, request_id)

                        if report is None:
                          logging.exception(
                              "Could not generate report", requestId=request_id)
                          pass
                        
                        report_json = json.dumps(report)
                        logging.debug(
                            "Generated report is {0}. Submitting".format(str(report_json)), requestId=request_id)
                        tx = self.__submitReport(
                            audit_request['args']['requestId'], requestor, contract_uri, report_json)
                        logging.debug(
                            "Report is sucessfully submitted: Hash is {0}".format(str(tx)), requestId=request_id)

                    except Exception:
                        logging.exception("Unexpected error when performing audit", requestId=request_id)
                        pass

                else:
                    logging.debug(
                        "Declining processing audit request: {0}. Not enough incentive".format(
                            str(audit_request)
                        ), requestId=request_id
                    )

    def stop(self):
        """
        Signals to the executing QSP audit node that is should stop the execution of the node.
        """
        self.__exec = False

    def audit(self, requestor, uri, request_id):
        """
        Audits a target contract.
        """
        logging.info("Executing audit on contract at {0}".format(uri), requestId=request_id)

        target_contract = fetch_file(uri)

        report = self.__config.analyzer.check(
            target_contract,
            self.__config.analyzer_output,
            request_id
        )
        
        report_as_string = str(json.dumps(report));
        
        upload_result = self.__config.report_uploader.upload(report_as_string);
        logging.info(
            "Report upload result: {0}".format(upload_result), requestId=request_id)
        
        if (upload_result['success'] is False):
          logging.exception(
              "Unexpected error when uploading report: {0}".format(json.dumps(upload_result)), requestId=request_id)
          return None

        return {
            'auditor': self.__config.account,
            'requestor': str(requestor),
            'contract_uri': str(uri),
            'contract_sha256': str(digest(target_contract)),
            'report_uri': upload_result['url'],
            'report_sha256': sha256(report_as_string.encode()).hexdigest(),
            'timestamp': str(datetime.utcnow()),
        }

    def __submitReport(self, request_id, requestor, contract_uri, report):
        """
        Submits the audit report to the entire QSP network.
        """
        gas = self.__config.default_gas

        if gas is None:
            args = {'from': self.__config.account}
        else:
            args = {'from': self.__config.account, 'gas': int(gas)}

        self.__config.wallet_session_manager.unlock(self.__config.account_ttl)
        return self.__config.internal_contract.transact(args).submitReport(
            request_id,
            requestor,
            contract_uri,
            report,
        )
