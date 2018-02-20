import sqlite3
import os


class EventPoolManager:

    def __exec_sql_script(self, cursor, query, query_params=None):
        query_path = "{0}/{1}}.sql".format(
            os.path.dirname(os.path.abspath(__file__)),
            query,
        )

        with open(query_path) as query_stream:
            query = query_stream.read()

        if query_params is None:
            cursor.executescript(query, query_params)

        cursor.execute(query, query_params)

    def __init__(self, db_path, max_submission_attempts):
        # Gets a connection with the SQL3Lite server
        # Must be explicitly closed by calling `close` on the same
        # EventPool object. The connection is created with autocommit
        # mode on
        self.connection = sqlite3.connect(db_path)
        self.max_submission_attempts = max_submission_attempts
        self.connection.isolation_level = None
        self.connection.row_factory = sqlite3.Row

        cursor = self.connection.cursor()
        cursor.execute("begin transaction")
        self.__exec_sql_script('createdb', cursor)
        cursor.execute("commit transaction")
        cursor.close()

    def get_latest_beep(self):
        cursor = self.connection.cursor()
        self.__exec_sql_script('get_latest_beep', cursor)
        row = cursor.fetchone()
        cursor.close()
        return row['current_beep']

    def get_next_beep(self):
        return self.get_latest_beep() + 1

    def get_latest_block_number(self):
        cursor = self.connection.cursor()
        self.__exec_sql_script('get_current_block_number', cursor)
        row = cursor.fetchone()
        cursor.close()
        return row['block_nbr']

    def get_next_block_number(self):
        return self.get_latest_block_number() + 1

    def add_evt_to_be_processed(self, evt):
        cursor = self.connection.cursor()
        cursor.execute("begin transaction")
        self.__exec_sql_script(
            cursor,
            'set_evt_to_be_processed',
            (evt['beep'], evt['evt_name'], evt['block_nbr'],)
        )
        cursor.execute("commit transaction")
        cursor.close()

    def __process_evt_with_new_status(self, query_name, query_params, fct):
        cursor = self.connection.cursor()
        self.__exec_sql_script(cursor, query_name, query_params)
        for evt in cursor:
            fct(evt)
        cursor.close()

    def process_incoming_events(self, beep, process_fct):
        self.__process_evt_with_new_status(
            'get_events_to_be_processed', (beep,), process_fct
        )

    def process_events_to_be_submitted(self, process_fct):
        self.__process_evt_with_new_status(
            'set_events_to_be_submitted',
            (self.max_submission_attempts,),
            process_fct
        )

    def set_evt_to_be_submitted(self, evt):
        cursor = self.connection.cursor()
        cursor.execute("begin transaction")
        self.__exec_sql_script(
            cursor,
            'set_evt_to_be_submitted',
            (evt['id'],)
        )
        cursor.execute("commit transaction")
        cursor.close()

    def set_evt_to_done(self, evt):
        cursor = self.connection.cursor()
        cursor.execute("begin transaction")
        self.__exec_sql_script(
            cursor,
            'set_evt_to_done',
            (evt['id'],)
        )
        cursor.execute("commit transaction")
        cursor.close()

    def close(self):
        self.connection.close()
