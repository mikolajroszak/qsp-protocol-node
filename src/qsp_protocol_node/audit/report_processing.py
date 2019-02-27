####################################################################################################
#                                                                                                  #
# (c) 2018 Quantstamp, Inc. All rights reserved.  This content shall not be used, copied,          #
# modified, redistributed, or otherwise disseminated except to the extent expressly authorized by  #
# Quantstamp for credentialed users. This content and its use are governed by the Quantstamp       #
# Demonstration License Terms at <https://s3.amazonaws.com/qsp-protocol-license/LICENSE.txt>.      #
#                                                                                                  #
####################################################################################################

"""
Encodes and decodes audit reports for on-chain storage.
Reports are formatted internally as bitstrings but produces hexstrings.

ENCODING FORMAT:
    * Numbers are encoded in unsigned big-endian format.
    * The header is the audit node source version, audit state, and status, packed into 16 bits as follows:
        * 4 bits for the major version
        * 4 bits for the minor version
        * 6 bits for the patch version
        * 1 bit for the audit state (1 == success)
        * 1 bit for the audit status (1 == success)
    * Each vulnerability is encoded to include its type, start line, and end line as follows:
        * 8 bits for the type, ordered by analyzers/schema/vulnerability_types.json (0-based)
        * 1 bit to encode if the end line is different than the start line (1 if so)
        * 15 bits to encode the start line
        * if end line is different than start line:
            * 8 bits encode end_line - start_line (otherwise no bits are used)

There should be a universal decoder for any encoding version,
but not clear where this should be implemented.
This could be a top-level package/executable, similar to the analyzers.
"""

import argparse
import json
import math
import os

from stream_logger import get_logger

from collections import OrderedDict
from pprint import pprint


class ReportFormattingException(Exception):
    pass


class ReportEncoder:
    # bitstring indices and sizes
    __HEADER_SIZE = 16
    # 14 bits to encode the version
    __MAJOR_VERSION_SIZE = 4
    __MINOR_VERSION_SIZE = 4
    __PATCH_VERSION_SIZE = 6
    __CONTRACT_HASH_SIZE = 256
    __VULNERABILITY_TYPE_SIZE = 8
    __START_LINE_SIZE = 16
    __END_LINE_SIZE = 8

    __MAJOR_VERSION_START = 0
    __MINOR_VERSION_START = __MAJOR_VERSION_START + __MAJOR_VERSION_SIZE
    __PATCH_VERSION_START = __MINOR_VERSION_START + __MINOR_VERSION_SIZE
    __AUDIT_STATE_INDEX = __PATCH_VERSION_START + __PATCH_VERSION_SIZE
    __STATUS_INDEX = __AUDIT_STATE_INDEX + 1
    __CONTRACT_HASH_START = __STATUS_INDEX + 1
    __VULNERABILITIES_START = __CONTRACT_HASH_START + __CONTRACT_HASH_SIZE

    # Copied from audit.py for self-containment.
    # Must be in sync with
    # https://github.com/quantstamp/qsp-protocol-audit-contract
    __AUDIT_STATE_SUCCESS = 4
    __AUDIT_STATE_ERROR = 5
    __AUDIT_STATUS_ERROR = "error"
    __AUDIT_STATUS_SUCCESS = "success"

    __HEX_BITS = 4

    def __init__(self):
        self.__logger = get_logger(self.__class__.__qualname__)
        self.__vulnerability_types, self.__vulnerability_types_inverted = \
            ReportEncoder.__initialize_vulnerability_types()

    @staticmethod
    def __initialize_vulnerability_types():
        """
        Initializes the mapping of vulnerability types to bitstring IDs
        """
        vulnerability_types = {}
        vulnerability_types_inverted = {}
        script_path = os.path.realpath(__file__)
        json_fstr = "{0}/../../../plugins/analyzers/vulnerability_types.json"
        types_file = json_fstr.format(os.path.dirname(script_path))
        with open(types_file) as json_data:
            types_json = json.load(json_data)
            types_list = types_json["vulnerabilities"]
            vulnerability_count = 0
            for vulnerability_type in types_list:
                bitstring = ReportEncoder.__to_bitstring(vulnerability_count,
                                                         ReportEncoder.__VULNERABILITY_TYPE_SIZE)
                vulnerability_types[vulnerability_type] = bitstring
                vulnerability_types_inverted[bitstring] = vulnerability_type
                vulnerability_count += 1
        return vulnerability_types, vulnerability_types_inverted

    @staticmethod
    def __to_bitstring(number, bitstring_length=0, is_hex=False):
        """
        Converts a number to a bitstring of specified length.
        """
        if not is_hex:
            fstr = "{0:0" + str(bitstring_length) + "b}"
            if math.log2(number + 1) > bitstring_length:
                raise ReportFormattingException("The number {0} cannot fit in {1} bits."
                                                .format(number, bitstring_length))
            return fstr.format(number)

        else:
            fstr = "{0:0" + str(ReportEncoder.__HEX_BITS) + "b}"
            b_number = ""
            if bitstring_length != 0 and len(number) * ReportEncoder.__HEX_BITS != bitstring_length:
                raise ReportFormattingException("The number {0} cannot fit in {1} bits."
                                                .format(number, bitstring_length))
            # check that only hex characters are used
            try:
                int(number, 16)
            except ValueError:
                raise ReportFormattingException("The hex string {0} contained a non-hex character"
                                                .format(number))
            for i in number:
                b_number += fstr.format(int(i, 16))
            return b_number

    @staticmethod
    def __from_bitstring(bitstring):
        """
        Converts a bitstring back to a decimal representation
        """
        return int(bitstring, 2)

    @staticmethod
    def __to_hex(bitstring):
        """
        Converts a string of binary to hex.

        See: https://stackoverflow.com/questions/2072351/
                 python-conversion-from-binary-string-to-hexadecimal
        """
        if len(bitstring) % ReportEncoder.__HEX_BITS != 0:
            fstr = "The bitstring {0} of {1} bits must have a length divisible by 4."
            raise ReportFormattingException(fstr.format(bitstring, len(bitstring)))
        hexstring = '%0*X' % ((len(bitstring) + 3) // ReportEncoder.__HEX_BITS, int(bitstring, 2))
        return hexstring

    @staticmethod
    def __encode_header_bytes(version, audit_state, status):
        """
        Encodes the header bytes of the compressed report.
        """
        major_version, minor_version, patch_version = [int(i) for i in version.split(".")]
        b_major_version = ReportEncoder.__to_bitstring(major_version,
                                                       ReportEncoder.__MAJOR_VERSION_SIZE)
        b_minor_version = ReportEncoder.__to_bitstring(minor_version,
                                                       ReportEncoder.__MINOR_VERSION_SIZE)
        b_patch_version = ReportEncoder.__to_bitstring(patch_version,
                                                       ReportEncoder.__PATCH_VERSION_SIZE)

        # A single bit for audit_state (1: success, 0: error),
        # followed by a single bit for a status (1: success, 0: error).
        if audit_state == ReportEncoder._ReportEncoder__AUDIT_STATE_SUCCESS:
            b_audit_state = ReportEncoder.__to_bitstring(1, 1)
        elif audit_state == ReportEncoder._ReportEncoder__AUDIT_STATE_ERROR:
            b_audit_state = ReportEncoder.__to_bitstring(0, 1)
        else:
            raise ReportFormattingException("audit_state must be 4 or 5")

        if status == ReportEncoder.__AUDIT_STATUS_SUCCESS:
            b_status = ReportEncoder.__to_bitstring(1, 1)
        elif status == ReportEncoder.__AUDIT_STATUS_ERROR:
            b_status = ReportEncoder.__to_bitstring(0, 1)
        else:
            raise ReportFormattingException("status must be success or error")

        bitstring = b_major_version + \
            b_minor_version + \
            b_patch_version + \
            b_audit_state + \
            b_status

        return bitstring

    @staticmethod
    def __decode_header_bytes(b_header):
        """
        Decodes the header bytes of the compressed report.
        """
        major_version = ReportEncoder.__from_bitstring(
            b_header[:ReportEncoder.__MAJOR_VERSION_SIZE])
        minor_version = ReportEncoder.__from_bitstring(
            b_header[ReportEncoder.__MINOR_VERSION_START:
                     ReportEncoder.__MINOR_VERSION_START + ReportEncoder.__MINOR_VERSION_SIZE])
        patch_version = ReportEncoder.__from_bitstring(
            b_header[ReportEncoder.__PATCH_VERSION_START:
                     ReportEncoder.__PATCH_VERSION_START + ReportEncoder.__PATCH_VERSION_SIZE])
        version = ".".join([str(i) for i in [major_version, minor_version, patch_version]])

        # map back to original values for success/error
        audit_state = b_header[ReportEncoder.__AUDIT_STATE_INDEX]
        if audit_state == "1":
            audit_state = ReportEncoder._ReportEncoder__AUDIT_STATE_SUCCESS
        else:
            audit_state = ReportEncoder._ReportEncoder__AUDIT_STATE_ERROR

        status = b_header[ReportEncoder.__STATUS_INDEX]
        if status == "1":
            status = ReportEncoder.__AUDIT_STATUS_SUCCESS
        else:
            status = ReportEncoder.__AUDIT_STATUS_ERROR

        return version, audit_state, status

    @staticmethod
    def __produce_json(version, audit_state, status, contract_hash, vulnerabilities):
        """
        Produce a json report that adheres to the analyzers_integration schema.
        This check does not occur here to keep this module self-contained,
        but is enforced by police nodes during decoding.
        """

        # Upon decoding, we do not know which analyzer/file is associated with a given vulnerability
        __UNKNOWN_ANALYZER = {
            "name": "Unknown Analyzer"
        }
        __UNKNOWN_FILE = "Unknown File"

        # Convert vulnerabilities into a schema-compliant format
        vulnerability_group_instances = {}
        # Do not use a mapping for this in order to preserve ordering
        vulnerability_group_names = []
        for (name, start_line, end_line) in vulnerabilities:
            instances = vulnerability_group_instances.get(name, [])
            if not instances:
                vulnerability_group_names.append(name)
            ref_id = len(instances)  # zero-based
            instances.append(
                {
                    "ref_id": ref_id,
                    "start_line": start_line,
                    "end_line": end_line
                }
            )
            vulnerability_group_instances[name] = instances

        vulnerability_lists = []
        for name in vulnerability_group_names:
            vulnerability_lists.append(
                {
                    "type": name,
                    "file": __UNKNOWN_FILE,
                    "instances": vulnerability_group_instances[name]
                }
            )

        report = {
            "version": version,
            "audit_state": audit_state,
            "status": status,
            "contract_hash": contract_hash,
            "analyzers_reports": [
                {
                    "status": status,
                    "analyzer": __UNKNOWN_ANALYZER,
                    "potential_vulnerabilities": vulnerability_lists
                }
            ]
        }
        return report

    def __encode_vulnerabilities(self, analyzers_reports):
        """
        Encodes each vulnerability instance as a bitstring.
        """
        encoded_vulnerabilities = []
        for analyzer_report in analyzers_reports:
            vulnerabilities = analyzer_report.get("potential_vulnerabilities", [])
            for vulnerability in vulnerabilities:
                type_name = vulnerability.get("type", None)
                for instance in vulnerability["instances"]:
                    start_line = int(instance["start_line"])
                    end_line = int(instance.get("end_line", 0))

                    b_vulnerability_id = self.__vulnerability_types.get(type_name, None)
                    if not b_vulnerability_id:
                        raise ReportFormattingException(
                            "Type name not in list of types: {0}".format(str(type_name)))

                    # The first bit of start line is 0 if end_line == start_line, else 1
                    if end_line == 0 or start_line == end_line:
                        b_is_end_line = ReportEncoder.__to_bitstring(0, 1)
                        end_line_diff = 0
                    else:
                        b_is_end_line = ReportEncoder.__to_bitstring(1, 1)
                        end_line_diff = end_line - start_line

                    # the remaining bits encode the start line
                    b_start_line = ReportEncoder.__to_bitstring(
                        int(start_line),
                        ReportEncoder.__START_LINE_SIZE - 1)

                    current_vulnerability = b_vulnerability_id + b_is_end_line + b_start_line

                    # only include bits for end line if needed
                    if end_line_diff != 0:
                        current_vulnerability += ReportEncoder.__to_bitstring(
                            end_line_diff,
                            ReportEncoder.__END_LINE_SIZE)
                    encoded_vulnerabilities.append(current_vulnerability)

        # remove duplicate vulnerabilities
        encoded_vulnerabilities = list(OrderedDict.fromkeys(encoded_vulnerabilities))

        return "".join(encoded_vulnerabilities)

    def __decode_vulnerabilities(self, b_vulnerabilities):
        """
        Decodes the bits encoding the vulnerabilities.
        """
        vulnerabilities = []
        while b_vulnerabilities:
            # convert the type in bitstring format to the original string type
            vulnerability_type = self.__vulnerability_types_inverted[
                b_vulnerabilities[:ReportEncoder.__VULNERABILITY_TYPE_SIZE]
            ]
            start_line_bits = b_vulnerabilities[
                ReportEncoder.__VULNERABILITY_TYPE_SIZE:
                ReportEncoder.__VULNERABILITY_TYPE_SIZE + ReportEncoder.__START_LINE_SIZE]

            is_end_line = start_line_bits[0]
            start_line = ReportEncoder.__from_bitstring(
                start_line_bits[1: ReportEncoder.__START_LINE_SIZE])

            consumed_bits = ReportEncoder.__VULNERABILITY_TYPE_SIZE
            consumed_bits += ReportEncoder.__START_LINE_SIZE

            if is_end_line == "1":
                # the end line is different than the start line,
                # and it encodes the difference from the start line
                end_bit = consumed_bits + ReportEncoder.__END_LINE_SIZE
                end_line = start_line + ReportEncoder.__from_bitstring(
                    b_vulnerabilities[consumed_bits: end_bit]
                )
                b_vulnerabilities = b_vulnerabilities[end_bit:]
            else:
                end_line = start_line
                b_vulnerabilities = b_vulnerabilities[consumed_bits:]
            vulnerabilities.append((vulnerability_type, start_line, end_line))
        return vulnerabilities

    def compress_report(self, report, request_id):
        """
        Converts a JSON report to a compressed hex representation.

        For further details, see:
        https://quantstamp.atlassian.net/wiki/
            spaces/QUAN/pages/115212289/Compressed+Reports+for+On-Chain+Storage
        """
        try:
            self.__logger.info("Compressing report {0}".format(request_id))
            audit_state = report["audit_state"]
            status = report["status"]
            version = report["version"]
            b_header = ReportEncoder.__encode_header_bytes(version, audit_state, status)

            contract_hash = report["contract_hash"]
            # the contract hash is 64 hex characters == 256 bits
            b_contract_hash = ReportEncoder.__to_bitstring(contract_hash,
                                                           ReportEncoder.__CONTRACT_HASH_SIZE,
                                                           is_hex=True)

            # may not exist if there are compilation errors
            analyzers_reports = report.get("analyzers_reports", [])
            b_vulnerabilities = self.__encode_vulnerabilities(analyzers_reports)

            b_report = b_header + b_contract_hash + b_vulnerabilities
            return ReportEncoder.__to_hex(b_report)
        except ReportFormattingException as e:
            self.__logger.exception(
                "Error: report formatting error occurred during compression: {0}.".format(str(e)),
                requestId=request_id,
            )
            raise e
        except Exception as e:
            # defensive programming
            self.__logger.exception(
                "Error: report could not be compressed: {0}.".format(str(e)),
                requestId=request_id,
            )
            raise Exception("Report could not be compressed") from e

    def decode_report(self, report, request_id):
        """
        Decodes a compressed report in hex format.

        NOTE: if the compression format gets updated, the decoder should be maintained
              to support deprecated formats. This may be in a separate UI repository.
        """
        self.__logger.info("Decoding report {0}".format(request_id))

        b_report = ReportEncoder.__to_bitstring(report, is_hex=True)
        # the first sequence of bits is the header
        b_header = b_report[:ReportEncoder.__HEADER_SIZE]
        version, audit_state, status = ReportEncoder.__decode_header_bytes(b_header)

        b_contract_hash = b_report[ReportEncoder.__HEADER_SIZE:
                                   ReportEncoder.__HEADER_SIZE + ReportEncoder.__CONTRACT_HASH_SIZE
                          ]
        contract_hash = ReportEncoder.__to_hex(b_contract_hash)

        # the remaining bits encode the vulnerabilities
        b_vulnerabilities = b_report[ReportEncoder.__VULNERABILITIES_START:]
        vulnerabilities = self.__decode_vulnerabilities(b_vulnerabilities)

        # produce the final json report
        report = self.__produce_json(version, audit_state, status, contract_hash, vulnerabilities)

        return report


def main():
    """
    Takes as input a hexstring-encoded report and decodes it.
    """
    encoder = ReportEncoder()
    request_id = 0

    try:
        # Sets the program's arguments
        parser = argparse.ArgumentParser(description='QSP Audit Report Decoder')
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument(
            '-d', '--decode-report',
            type=str, default='',
            help='hex string of compressed report (no 0x)',
        )
        group.add_argument(
            '-e', '--encode-report',
            type=str, default='',
            help='json file to be encoded',
        )
        args = parser.parse_args()
        if args.decode_report:
            report = encoder.decode_report(args.decode_report, request_id)
            pprint(report)
        else:
            with open(args.encode_report) as stream:
                json_report = json.load(stream)
                hexstring = encoder.compress_report(json_report, request_id)
                print(hexstring)
    except Exception as error:
        raise error


if __name__ == "__main__":
    main()
