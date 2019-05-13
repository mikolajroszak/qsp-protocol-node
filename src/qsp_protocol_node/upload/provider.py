####################################################################################################
#                                                                                                  #
# (c) 2019 Quantstamp, Inc. This content and its use are governed by the license terms at          #
# <https://s3.amazonaws.com/qsp-protocol-license/V2_LICENSE.txt>                                   #
#                                                                                                  #
####################################################################################################


class UploadProvider:
    def upload_report(self, report_as_string, audit_report_hash=None):
        raise Exception("Unimplemented method")

    def upload_contract(self, request_id, contract_body, file_name):
        raise Exception("Unimplemented method")
