"""
Provides the QSP Audit node implementation.
"""
from queue import Queue
from datetime import datetime
from tempfile import mkstemp
from hashlib import sha256
from time import sleep
import os

from utils.io import fetch_file

class QSPAuditNode:

    def __init__(self, 
                auditor_address,
                internal_contract,
                analyzer, 
                min_reward = 0,  
                polling = 5):
        """
        Builds a QSPAuditNode object from the given input parameters.
        """
        self.__auditor_address = auditor_address
        self.__internal_contract = internal_contract
        self.__filter = internal_contract.on("LogAuditRequested")
        self.__analyzer = analyzer
        self.__min_reward = min_reward
        self.__polling = polling
        self.__exec = False

    def run(self):
        """
        Runs the QSP Audit node in a busy waiting fashion.
        """
        self.__exec = True
        while self.__exec:
            requests = self.__filter.get()
            if requests == []:
                sleep(self.__polling)
            else:
                # Process all incoming requests
                for audit_request in requests:

                    # Accepts all requests whose reward is at least as
                    # high as given by min_reward
                    if audit_request['price'] >= self.__min_reward:
                        try:
                            report = self.audit(audit_request['requestor'], audit_request['uri'])
                            self.__submitReport(report)
                        except Exception as e:
                            pass
                            # TODO 
                            # log expcetion but allow node to proceed with
                            # audits. When that happens, nothing
                            # should be recorded on the blockchain


    def stop(self):
        """
        Signals to the executing QSP audit node that is should stop the execution of the node.
        """
        self.__exec = False
    
    def audit(self, requestor, uri, output_file = None, remove_output_file = True):
        """
        Audits a target contract.
        """
        target_contract = fetch_file(uri)

        if output_file is None:
            _, output = mkstemp(text = True)

        report = self.__analyzer.check(
            target_contract, 
            output,
        )

        if remove_output_file:
            os.remove(output_file)

        return {
            'auditor': self.__auditor_address,
            'requestor': requestor,
            'contract_uri': uri,
            'contract_sha256': sha256(target_contract).hexdigest(),
            'report': report,
            'timestamp': str(datetime.utcnow()),
        }

    def __submitReport(self, report):
        """
        Submits the audit report to the entire QSP network.
        """

        self.__internal_contract.transact(
            {'from': self.__auditor_address}).submitReport(
                report['requestor'], 
                report['contract_uri'],
                str(report),
        )

        
