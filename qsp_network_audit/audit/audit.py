"""
Provides the QSP Audit node implementation.
"""
from queue import Queue
from datetime import datetime
from tempfile import mkstemp
from time import sleep
import os
import json
import logging

from utils.io import fetch_file, digest
from utils.args import replace_args


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

                # Accepts all requests whose reward is at least as
                # high as given by min_reward
                if price >= self.__config.min_price:
                    logging.debug("Accepted processing audit request: {0}".format(
                        str(audit_request)
                    ))
                    try:
                        requestor = audit_request['args']['requestor']
                        contract_uri = audit_request['args']['uri']

                        report = json.dumps(
                            self.audit(requestor, contract_uri))

                        logging.debug(
                            "Generated report is {0}. Submitting".format(str(report)))
                        tx = self.__submitReport(
                            requestor, contract_uri, report)
                        logging.debug(
                            "Report is sucessfully submitted: Hash is {0}".format(str(tx)))

                    except Exception:
                        logging.exception(
                            "Unexpected error when performing audit")
                        pass

                else:
                    logging.debug(
                        "Declining processing audit request: {0}. Not enough incentive".format(
                            str(audit_request)
                        )
                    )

    def stop(self):
        """
        Signals to the executing QSP audit node that is should stop the execution of the node.
        """
        self.__exec = False

    def audit(self, requestor, uri):
        """
        Audits a target contract.
        """
        logging.info("Executing audit on contract at {0}".format(uri))

        target_contract = fetch_file(uri)

        report = self.__config.analyzer.check(
            target_contract,
            self.__config.analyzer_output,
        )

        return {
            'auditor': self.__config.account,
            'requestor': str(requestor),
            'contract_uri': str(uri),
            #'contract_sha256': str(digest(target_contract)),
            #'report': json.dumps(report),
            'report': 'test',
            #'timestamp': str(datetime.utcnow()),
        }

    def __submitReport(self, requestor, contract_uri, report):
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
            requestor,
            contract_uri,
            report,
        )
