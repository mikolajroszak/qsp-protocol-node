"""
Provides the QSP Audit node implementation.
"""
from queue import Queue
from datetime import datetime
from tempfile import mkstemp
from time import sleep
import os
import json

from utils.io import fetch_file, digest
from utils.args import replace_args

class QSPAuditNode:

    def __init__(self, 
                auditor_address,
                internal_contract,
                analyzer, 
                min_price,  
                polling,
                analyzer_output):
        """
        Builds a QSPAuditNode object from the given input parameters.
        """
        self.__auditor_address = auditor_address
        self.__internal_contract = internal_contract
        self.__filter = internal_contract.on("LogAuditRequested")
        self.__analyzer = analyzer
        self.__min_price = min_price
        self.__polling = polling
        self.__exec = False
        self.__analyzer_output = analyzer_output

    def run(self):
        """
        Runs the QSP Audit node in a busy waiting fashion.
        """
        self.__exec = True
        while self.__exec:
            requests = self.__filter.get()

            if requests == []:
                sleep(self.__polling)
                continue

            print("===> GOT REQUESTS: " + str(requests))

            # Process all incoming requests
            for audit_request in requests:

                print("===> RECEIVED AUDIT REQUEST")
                price = audit_request['args']['price']

                print("===> PRICE IS " + str(price))

                # Accepts all requests whose reward is at least as
                # high as given by min_reward
                if price >= self.__min_price:
                    try:
                        requestor = audit_request['args']['requestor']
                        contract_uri = audit_request['args']['uri']

                        report = json.dumps(self.audit(requestor, contract_uri))

                        print("===> GENERATED REPORT IS " + str(report))

                        self.__submitReport(requestor, contract_uri, report)

                    except Exception as e:
                        import traceback
                        traceback.print_exc()

                        pass
                        # TODO 
                        # log expcetion but allow node to proceed with
                        # audits. When that happens, nothing
                        # should be recorded on the blockchain


                else:
                    print("===> REJECTING AUDIT")


    def stop(self):
        """
        Signals to the executing QSP audit node that is should stop the execution of the node.
        """
        self.__exec = False
    
    def audit(self, requestor, uri):
        """
        Audits a target contract.
        """

        print("===> INSIDE AUDIT")

        target_contract = fetch_file(uri)

        print("===> FETCHED URL")

        print("===> INSIDE AUDIT")
        print("===>   requestor is " + str(requestor))
        print("===>   uri is " + str(uri))
        print("===>   output_file template is " + str(self.__analyzer_output))
        print("===>   target file is  " + str(target_contract))

        report = self.__analyzer.check(
            target_contract, 
            self.__analyzer_output,
        )

        print("===> ABOUT TO PRODUCE REPORT")
        print("===> PRODUCING AUGMENTED RESULT")

        return {
            'auditor': self.__auditor_address,
            'requestor': str(requestor),
            'contract_uri': str(uri),
            'contract_sha256': str(digest(target_contract)),
            'report': json.dumps(report),
            'timestamp': str(datetime.utcnow()),
        }

    def __submitReport(self, requestor, contract_uri, report):
        """
        Submits the audit report to the entire QSP network.
        """

        print("===> REQUESTOR is " + requestor)
        print("===> URI is " + contract_uri)

        self.__internal_contract.transact(
            {'from': self.__auditor_address}).submitReport(
                requestor,
                contract_uri,
                report,
        )

        
