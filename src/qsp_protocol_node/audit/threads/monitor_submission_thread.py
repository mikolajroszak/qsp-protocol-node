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

from .qsp_thread import TimeIntervalPollingThread
from utils.eth import mk_read_only_call


class MonitorSubmissionThread(TimeIntervalPollingThread):

    MAX_SUBMISSION_ATTEMPTS = 3

    def __process_submissions(self):
        """
        Checks all events in state SB for timeout and sets the ones that timed out to state ER.
        """
        # Checks for a potential timeouts
        timeout_limit_blocks = mk_read_only_call(
            self.config, self.config.audit_contract.functions.getAuditTimeoutInBlocks()
        )

        self.config.event_pool_manager.process_submission_events(
            self.__monitor_submission_timeout,
            timeout_limit_blocks,
        )

    def __monitor_submission_timeout(self, evt, timeout_limit_blocks):
        """
        Sets the event to state ER if the timeout window passed.
        """
        try:
            submission_attempts = evt['submission_attempts']

            is_finished = mk_read_only_call(
                self.config, self.config.audit_contract.functions.isAuditFinished(evt['request_id'])
            )

            current_block = self.config.web3_client.eth.blockNumber
            if is_finished and evt != {}:

                submission_block = evt['submission_block_nbr']
                if (current_block - submission_block) < self.config.n_blocks_confirmation:
                    # Not yet confirmed. Wait...
                    self.logger.debug(
                        "Waiting on report submission for {0}".format(evt['request_id']),
                        requestId=evt['request_id']
                    )
                    return

                # (Else) Submission is finished and final. Move its status to done.
                evt['status_info'] = 'Report successfully submitted'
                self.config.event_pool_manager.set_evt_status_to_done(evt)
                self.logger.debug(
                    "Report successfully submitted for event: {0}".format(
                        str(evt)
                    ),
                    requestId=evt['request_id']
                )
            else:
                assigned_block = evt['assigned_block_nbr']

                # Checks if current timepoint still falls within the
                # audit window. If so, retry provided the number of
                # maximum attempts is not excedded.
                if current_block < (assigned_block + timeout_limit_blocks):
                    # Retries exceeds the number of allowed attempts. Then, mark the
                    # event as error.
                    if (submission_attempts + 1) > MonitorSubmissionThread.MAX_SUBMISSION_ATTEMPTS:
                        error_msg = "Submitting audit {0} timed-out after {1} attempts. "
                        error_msg += "The event was created in block {2}. The timeout limit is {3} blocks. "
                        error_msg += "The current block is {4}."
                        error_msg = error_msg.format(
                            evt['request_id'],
                            submission_attempts,
                            evt['assigned_block_nbr'],
                            timeout_limit_blocks,
                            current_block
                        )
                        self.logger.debug(error_msg, requestId=evt['request_id'])
                        evt['status_info'] = "Reached maximum number of submission attempts ({0})".format(
                            MonitorSubmissionThread.MAX_SUBMISSION_ATTEMPTS
                        )
                        self.config.event_pool_manager.set_evt_status_to_error(evt)
                    else:
                        # A retry is still possible. Make it happen.
                        evt['status_info'] = "Attempting to resubmit report {0} (retry = {1})".format(
                            evt['request_id'],
                            (submission_attempts + 1)
                        )
                        self.logger.debug(evt['status_info'], requestId=evt['request_id'])

                        # Resets the transaction hash from the previous
                        # submission attempt
                        evt['tx_hash'] = None
                        self.config.event_pool_manager.set_evt_status_to_be_submitted(evt)
                else:
                    evt['status_info'] = "Submission of audit report outside completion window ({0} blocks)".format(
                        timeout_limit_blocks
                    )
                    self.logger.debug(evt['status_info'], requestId=evt['request_id'])
                    self.config.event_pool_manager.set_evt_status_to_error(evt)

        except KeyError as error:
            evt['status_info'] = "KeyError when monitoring submission and timeout: {0}".format(str(error))
            self.logger.exception(evt['status_info'], requestId=evt.get('request_id', -1))

            # Non-recoverable exception. If a field is missing, it is a bug
            # elsewhere!!! The field will not magically be given a value out
            # of nowhere...
            self.config.event_pool_manager.set_evt_status_to_error(evt)

        except Exception as error:
            # TODO How to inform the network of a submission timeout?
            error_msg = "Unexpected error when monitoring submission and timeout: {0}. "
            error_msg += "Audit event is {1}"
            error_msg = error_msg.format(error, evt)
            self.logger.exception(error_msg, requestId=evt['request_id'])
            evt['status_info'] = error_msg

            # Potentially recoverable if number of resubmission is not exceeded.
            if (submission_attempts + 1) > MonitorSubmissionThread.MAX_SUBMISSION_ATTEMPTS:
                self.config.event_pool_manager.set_evt_status_to_error(evt)
            else:
                self.config.event_pool_manager.set_evt_status_to_be_submitted(evt)

    def __init__(self, config):
        """
        Builds a the thread object from the given input parameters.
        """
        TimeIntervalPollingThread.__init__(
            self,
            config=config,
            target_function=self.__process_submissions,
            thread_name="monitor thread"
        )
