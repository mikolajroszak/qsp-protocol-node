####################################################################################################
#                                                                                                  #
# (c) 2018 Quantstamp, Inc. All rights reserved.  This content shall not be used, copied,          #
# modified, redistributed, or otherwise disseminated except to the extent expressly authorized by  #
# Quantstamp for credentialed users. This content and its use are governed by the Quantstamp       #
# Demonstration License Terms at <https://s3.amazonaws.com/qsp-protocol-license/LICENSE.txt>.      #
#                                                                                                  #
####################################################################################################

import boto3

from .provider import UploadProvider
from utils.dictionary.path import get
from utils.io import digest


class S3Provider(UploadProvider):
    def __init__(self, account, config):
        self.__client = boto3.client('s3')
        self.__bucket_name = get(config, 
            '/bucket_name', accept_none=False)
        self.__contract_bucket_name = get(config, 
            '/contract_bucket_name', accept_none=False)
        self.__account = account
        self.__config = config

    def config(self):
        return self.__config

    def upload_report(self, report_as_string, audit_report_hash=None):
        report_hash = audit_report_hash
        if audit_report_hash is None:
            report_hash = digest(report_as_string)
        try:
            report_file_name = "{0}/{1}.json".format(self.__account, report_hash)
            response = self.__client.put_object(
                Body=str(report_as_string),
                Bucket=self.__bucket_name,
                Key=report_file_name,
                ContentType="application/json"
            )
            return {
                'success': True,
                'url': "https://s3.amazonaws.com/{0}/{1}".format(
                    self.__bucket_name,
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
        if self.__contract_bucket_name is None:
            return {
                'success': False,
                'url': None,
                'provider_exception': Exception('The contact bucket name is not configured')
            }
        try:
            contract_filname = "{0}/{1}/{2}".format(self.__account, request_id, file_name)
            response = self.__client.put_object(
                Body=str(contract_body),
                Bucket=self.__contract_bucket_name,
                Key=contract_filname,
                ContentType="text/html"
            )
            return {
                'success': True,
                'url': "https://s3.amazonaws.com/{0}/{1}".format(
                    self.__contract_bucket_name,
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
