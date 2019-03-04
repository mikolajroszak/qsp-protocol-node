####################################################################################################
#                                                                                                  #
# (c) 2018 Quantstamp, Inc. All rights reserved.  This content shall not be used, copied,          #
# modified, redistributed, or otherwise disseminated except to the extent expressly authorized by  #
# Quantstamp for credentialed users. This content and its use are governed by the Quantstamp       #
# Demonstration License Terms at <https://s3.amazonaws.com/qsp-protocol-license/LICENSE.txt>.      #
#                                                                                                  #
####################################################################################################

import boto3

from .base_upload_provider import BaseUploadProvider
from utils.dictionary.path import get
from utils.io import digest


class S3Provider(BaseUploadProvider):
    def __init__(self, account, config):
        super().__init__(config)

        print("===> S3 provider config is {0}".format(config))

        self.__client = boto3.client('s3')
        
        # Makes sure required parameters are in place
        _ = get(config, '/args/report_bucket_name', accept_none=False)
        _ = get(config, '/args/contract_bucket_name', accept_none=False)

        self.__account = account
        self.__config = config

    @property
    def report_bucket_name(self):
        return self.config['report_bucket_name']

    @property
    def contract_bucket_name(self):
        return self.config['contract_bucket_name']

    @property
    def config(self):
        return self.__config

    @property
    def is_enabled(self):
        return self.config['is_enabled']

    def upload_report(self, report_as_string, audit_report_hash=None):
        if not self.is_enabled:
            raise Exception(f"Cannot upload report: {self.component_name} is not enabled")

        report_hash = audit_report_hash
        if audit_report_hash is None:
            report_hash = digest(report_as_string)
        try:
            report_file_name = "{0}/{1}.json".format(self.__account, report_hash)
            response = self.__client.put_object(
                Body=str(report_as_string),
                Bucket=self.report_bucket_name,
                Key=report_file_name,
                ContentType="application/json"
            )
            return {
                'success': True,
                'url': "https://s3.amazonaws.com/{0}/{1}".format(
                    self.report_bucket_name,
                    report_file_name
                ),
                'provider_response': response
            }
        except Exception as exception:
            return {
                'success': False,
                'url': None,
                'provider_exception': exception
            }

    def upload_contract(self, request_id, contract_body, file_name):
        """
        Uploads a contract being audited into S3 for the purposes of future inspection.
        """
        if not self.is_enabled:
            raise Exception(f"Cannot upload contract: {self.component_name} is not enabled")

        try:
            contract_filname = "{0}/{1}/{2}".format(self.__account, request_id, file_name)
            response = self.__client.put_object(
                Body=str(contract_body),
                Bucket=self.contract_bucket_name,
                Key=contract_filname,
                ContentType="text/html"
            )
            return {
                'success': True,
                'url': "https://s3.amazonaws.com/{0}/{1}".format(
                    self.contract_bucket_name,
                    contract_filname
                ),
                'provider_response': response
            }
        except Exception as exception:
            return {
                'success': False,
                'url': None,
                'provider_exception': exception
            }
