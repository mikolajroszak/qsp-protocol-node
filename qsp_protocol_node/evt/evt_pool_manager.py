import os

from pathlib import Path
from utils.db import Sqlite3Worker
from utils.db import get_first


class EventPoolManager:
    @staticmethod
    def __encode(dictionary):
        if dictionary is None:
            return None

        new_dictionary = {}
        for key in dictionary.keys():
            if key == "price" or key == "block_nbr":
                new_dictionary[key] = str(dictionary[key])
            else:
                new_dictionary[key] = dictionary[key]

        return new_dictionary

    @staticmethod
    def __decode(dictionary):
        if dictionary is None:
            return None

        new_dictionary = {}
        for key in dictionary.keys():
            if key == "price" or key == "block_nbr":
                new_dictionary[key] = int(dictionary[key])
            else:
                new_dictionary[key] = dictionary[key]

        return new_dictionary

    @staticmethod
    def __query_path(query):
        return "{0}/{1}.sql".format(
            os.path.dirname(os.path.abspath(__file__)),
            query,
        )

    @staticmethod
    def __exec_sql(worker, query, values=()):
        query_file = EventPoolManager.__query_path(query)
        return worker.execute_script(query_file, values)

    def __init__(self, db_path, logger):
        # Gets a connection with the SQL3Lite server
        # Must be explicitly closed by calling `close` on the same
        # EventPool object. The connection is created with autocommit
        # mode on

        db_existed = False
        db_created = False
        error = False

        self.__sqlworker = None
        db_file = None
        try:
            db_file = Path(db_path)
            if db_file.is_file():
                db_existed = True

            self.__sqlworker = Sqlite3Worker(logger, file_name=db_path, max_queue_size=10000)
            db_created = True

            if not db_existed:
                EventPoolManager.__exec_sql(self.__sqlworker, 'createdb')

        except Exception:
            error = True
            raise

        finally:
            if error:
                if self.__sqlworker is not None:
                    self.__sqlworker.close()

                if not db_existed and db_created and db_file is not None:
                    db_file.unlink()

    @property
    def sql3lite_worker(self):
        return self.__sqlworker

    def get_latest_block_number(self):
        row = get_first(EventPoolManager.__exec_sql(self.__sqlworker, 'get_latest_block_number'))
        return EventPoolManager.__decode(row).get('block_nbr')

    def is_request_processed(self, request_id):
        row = self.get_event_by_request_id(request_id)
        return not (row is None or row == {})

    def get_next_block_number(self):
        current = self.get_latest_block_number()
        if current < 0 or current is None:
            return 0
        return current + 1

    def get_latest_request_id(self):
        row = get_first(EventPoolManager.__exec_sql(self.__sqlworker, 'get_latest_request_id'))
        return EventPoolManager.__decode(row).get('request_id')

    def add_evt_to_be_processed(self, evt):
        encoded_evt = EventPoolManager.__encode(evt)
        EventPoolManager.__exec_sql(
            self.__sqlworker,
            'add_evt_to_be_processed',
            values=(
                encoded_evt['request_id'],
                encoded_evt['requestor'],
                encoded_evt['contract_uri'],
                encoded_evt['evt_name'],
                encoded_evt['block_nbr'],
                encoded_evt['status_info'],
                encoded_evt['price'],
            )
        )

    def __process_evt_with_status(self, query_name, fct, values=(), fct_kwargs=None):
        for evt in EventPoolManager.__exec_sql(self.__sqlworker, query_name, values):
            decoded_evt = EventPoolManager.__decode(evt)
            if fct_kwargs is None:
                fct(decoded_evt, {})
            else:
                fct(decoded_evt, **fct_kwargs)

    def get_event_by_request_id(self, request_id):
        rows = EventPoolManager.__exec_sql(self.__sqlworker, 'get_event_by_request_id',
                                           (request_id,))
        row = get_first(rows)
        return EventPoolManager.__decode(row)

    def process_incoming_events(self, process_fct):
        self.__process_evt_with_status(
            'get_events_to_be_processed',
            process_fct,
        )

    def process_events_to_be_submitted(self, process_fct):
        self.__process_evt_with_status(
            'get_events_to_be_submitted',
            process_fct,
        )

    def process_submission_events(self, monitor_fct, current_block):
        kw_args = {'current_block': current_block}
        self.__process_evt_with_status(
            'get_events_to_be_monitored',
            monitor_fct,
            fct_kwargs=kw_args,
        )

    def set_evt_to_assigned(self, evt):
        encoded_evt = EventPoolManager.__encode(evt)
        EventPoolManager.__exec_sql(
            self.__sqlworker,
            'set_evt_to_assigned',
            (encoded_evt['evt_name'], encoded_evt['status_info'], encoded_evt['request_id'],),
        )

    def set_evt_to_be_submitted(self, evt):
        encoded_evt = EventPoolManager.__encode(evt)
        EventPoolManager.__exec_sql(
            self.__sqlworker,
            'set_evt_to_be_submitted',
            (encoded_evt['status_info'],
             encoded_evt['tx_hash'],
             encoded_evt['report_uri'],
             encoded_evt['report_hash'],
             encoded_evt['audit_state'],
             encoded_evt['request_id'],
             ),
        )

    def set_evt_to_submitted(self, evt):
        encoded_evt = EventPoolManager.__encode(evt)
        EventPoolManager.__exec_sql(
            self.__sqlworker,
            'set_evt_to_submitted',
            (encoded_evt['tx_hash'],
             encoded_evt['status_info'],
             encoded_evt['report_uri'],
             encoded_evt['report_hash'],
             encoded_evt['audit_state'],
             encoded_evt['request_id'],
             ),
        )

    def set_evt_to_done(self, evt):
        encoded_evt = EventPoolManager.__encode(evt)
        EventPoolManager.__exec_sql(
            self.__sqlworker,
            'set_evt_to_done',
            (encoded_evt['status_info'], encoded_evt['request_id'],),
        )

    def set_evt_to_error(self, evt):
        encoded_evt = EventPoolManager.__encode(evt)
        EventPoolManager.__exec_sql(
            self.__sqlworker,
            'set_evt_to_error',
            (encoded_evt['status_info'], encoded_evt['request_id'],),
        )

    def close(self):
        self.__sqlworker.close()
