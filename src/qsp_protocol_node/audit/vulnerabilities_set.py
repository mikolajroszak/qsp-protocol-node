####################################################################################################
#                                                                                                  #
# (c) 2018, 2019 Quantstamp, Inc. This content and its use are governed by the license terms at    #
# <https://s3.amazonaws.com/qsp-protocol-license/V2_LICENSE.txt>                                   #
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
