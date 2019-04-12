####################################################################################################
#                                                                                                  #
# (c) 2018 Quantstamp, Inc. All rights reserved.  This content shall not be used, copied,          #
# modified, redistributed, or otherwise disseminated except to the extent expressly authorized by  #
# Quantstamp for credentialed users. This content and its use are governed by the Quantstamp       #
# Demonstration License Terms at <https://s3.amazonaws.com/qsp-protocol-license/LICENSE.txt>.      #
#                                                                                                  #
####################################################################################################


class VulnerabilitiesSet:

    @classmethod
    def from_uncompressed_report(cls, report):
        if report is None or len(report) == 0:
            return set()

        vulnerabilities_set = set()
        for analyzer_report in report.get('analyzers_reports', {}):
            for vulnerability in analyzer_report.get('potential_vulnerabilities', []):
                vulnerability_type = vulnerability['type']
                for instance in vulnerability.get('instances', []):
                    line = instance['start_line']
                    vulnerabilities_set.add((vulnerability_type, line))
        return vulnerabilities_set
