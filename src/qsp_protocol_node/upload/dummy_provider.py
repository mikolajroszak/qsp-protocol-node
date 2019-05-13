from .provider import UploadProvider
####################################################################################################
#                                                                                                  #
# (c) 2018, 2019 Quantstamp, Inc. This content and its use are governed by the license terms at    #
# <https://s3.amazonaws.com/qsp-protocol-license/V2_LICENSE.txt>                                   #
#                                                                                                  #
####################################################################################################

from singleton_decorator import singleton
import tempfile


@singleton
class DummyProvider(UploadProvider):

    def __init__(self):
        self.__response = {
            'success': True,
            'url': "Not available. Full report was not uploaded",
            'provider_response': {},
        }

    def upload_report(self, report_as_string, audit_report_hash=None):
        tmp = tempfile.NamedTemporaryFile(delete=False)
        with open(tmp.name, 'w') as f:
            f.write(report_as_string)
        upload_response = self.__response.copy()
        upload_response['url'] = "file://" + tmp.name
        return upload_response

    def upload_contract(self, request_id, contract_body, file_name):
        return self.__response
