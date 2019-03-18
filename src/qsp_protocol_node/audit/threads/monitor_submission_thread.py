####################################################################################################
#                                                                                                  #
# (c) 2018 Quantstamp, Inc. All rights reserved.  This content shall not be used, copied,          #
# modified, redistributed, or otherwise disseminated except to the extent expressly authorized by  #
# Quantstamp for credentialed users. This content and its use are governed by the Quantstamp       #
# Demonstration License Terms at <https://s3.amazonaws.com/qsp-protocol-license/LICENSE.txt>.      #
#                                                                                                  #
####################################################################################################

"""
Provides the thread for monitoring the submissions in the QSP Audit node implementation.
"""

from threading import Thread

from .qsp_thread import QSPThread
from utils.eth import mk_read_only_call


class MonitorSubmissionThread(QSPThread):

    def __init__(self, config):
        """
        Builds a the thread object from the given input parameters.
        """
        QSPThread.__init__(self, config)

    def start(self):
        """
        Monitors submissions of reports.
        """
        monitor_thread = Thread(target=self.__execute, name="monitor thread")
        monitor_thread.start()
        return monitor_thread

    def __execute(self):
        """
        Defines the function to be executed and how often.
        """
        self.run_with_interval(self.__process_submissions, self.config.evt_polling)

    def __process_submissions(self):
        """
        Checks all events in state SB for timeout and sets the ones that timed out to state ER.
        """
        # Checks for a potential timeouts
        block = self.config.web3_client.eth.blockNumber
        self.config.event_pool_manager.process_submission_events(
            self.__monitor_submission_timeout,
            block,
        )

    def __monitor_submission_timeout(self, evt, current_block):
        """
        Sets the event to state ER if the timeout window passed.
        """
        is_finished = mk_read_only_call(
            self.config, self.config.audit_contract.functions.isAuditFinished(evt['request_id'])
        )
        try:
            if is_finished and evt != {}:

                evt['status_info'] = 'Report successfully submitted'
                self.config.event_pool_manager.set_evt_status_to_done(evt)
                self.logger.debug(
                    "Report successfully submitted for event: {0}".format(
                        str(evt)
                    ),
                    requestId=evt['request_id']
                )
            else:
                timeout_limit = self.config.submission_timeout_limit_blocks
                if (current_block - evt['block_nbr']) > timeout_limit:
                    msg = "Submission timeout for audit {0}. Setting to error. The event was " \
                          "created in block {1}. The timeout limit is {2} blocks. The current " \
                          "block is {3}."
                    self.logger.debug(msg.format(str(evt['request_id']),
                                                 str(evt['block_nbr']),
                                                 str(timeout_limit),
                                                 str(current_block)),
                                      requestId=evt['request_id'])
                    evt['status_info'] = "Submission timeout"
                    self.config.event_pool_manager.set_evt_status_to_error(evt)
        except KeyError as error:
            self.logger.exception(
                "KeyError when monitoring submission and timeout: {0}".format(str(error)),
                requestId=evt.get('request_id', default=-1)
            )
        except Exception as error:
            # TODO How to inform the network of a submission timeout?
            self.logger.exception(
                "Unexpected error when monitoring submission and timeout: {0}. "
                "Audit event is {1}".format(str(error),
                                            str(evt)),
                requestId=evt['request_id'])
