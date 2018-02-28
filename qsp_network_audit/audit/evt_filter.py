from utils.tx import mk_args
import utils.logging as logging_utils


logging = logging_utils.getLogging()

class AuditEventFilter:

    __EVT_AUDIT_REQUESTED = "LogAuditRequested"
    __EVT_AUDIT_REQUEST_ASSIGNED = "LogAuditRequestAssigned"

    def __get_next_audit_request(self):
        """
        Attempts to get a request from the audit request queue.
        """
        tx_args = mk_args(self.__config)
        self.__config.wallet_session_manager.unlock(self.__config.account_ttl)
        return self.__config.internal_contract.transact(tx_args).getNextAuditRequest()

    def __bid_for_audit_request(self, evt):
        """
        Bids for an audit upon an audit request event.
        """
        try:
            # Bids for audit requests whose reward is at least as
            # high as given by the configured min_price
            price = evt['args']['price']
            request_id = str(evt['args']['requestId'])

            if price >= self.__config.min_price:
                logging.debug("Accepted processing audit event: {0}. Bidding for it".format(
                    str(evt)
                ))
                self.__get_next_audit_request()

            else:
                logging.debug(
                    "Declining processing audit request: {0}. Not enough incentive".format(
                        str(evt)
                    ), 
                    requestId=request_id,
                )
        except Exception as error:
            logging.exception(
                "Error when bidding for request {0}: {1}".format(str(evt), str(error)), 
                requestId=request_id,
            )

    def __process_audit_request(self, evt):
        request_id = str(evt['args']['requestId'])
        try:
            target_auditor = evt['args']['auditor']

            # If an audit request is not targeted to the 
            # running audit node, just disconsider it
            if target_auditor != self.__config.account:
                pass

            # Otherwise, the audit request must be processed
            # throught its different stages. As such, save it
            # in the internal database, marking it as RECEIVED

            audit_evt = {
                'request_id': request_id,
                'requestor': str(evt['args']['requestor']),
                'contract_uri': str(evt['args']['uri']),
                'evt_name':  AuditEventFilter.__EVT_AUDIT_REQUEST_ASSIGNED,
                'block_nbr': evt['blockNumber'],
                'price': evt['args']['price'],
                'status_info': "Audit request received",
            }

            self.__config.event_pool_manager.add_evt_to_be_processed(
                audit_evt
            )
        except Exception as error:
            logging.exception(
                "Error when processing event {0}: {1}".format(str(evt), str(error)), 
                requestId=request_id,
            )


    def __init__(self, config):
        self.__config = config

        start_block = self.__config.event_pool_manager.get_next_block_number()

        self.__filter_audit_requests = self.__config.internal_contract.on(
            AuditEventFilter.__EVT_AUDIT_REQUESTED,
            {'fromBlock': start_block},
            self.__bid_for_audit_request,
        )

        self.__filter_audit_requests = self.__config.internal_contract.on(
            AuditEventFilter.__EVT_AUDIT_REQUEST_ASSIGNED,
            {'fromBlock': start_block},
            self.__process_audit_request,
        )