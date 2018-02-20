import sqlite3
import os


class EventPoolManager:

    def __exec_sql_script(self, cursor, query, query_params={}, multiple_stmts=False):
        if query_params and multiple_stmts:
            raise Exception(
                "query_params should not be used in queries with multiple statements")

        query_path = "{0}/{1}.sql".format(
            os.path.dirname(os.path.abspath(__file__)),
            query,
        )

        with open(query_path) as query_stream:
            query = query_stream.read()

        if multiple_stmts:
            cursor.executescript(query)
        else:
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

        cursor = None
        try:
            cursor = self.connection.cursor()
            self.__exec_sql_script(cursor, 'createdb', multiple_stmts=True)
            self.connection.commit()
        except sqlite3.Error:
            self.connection.rollback()
        finally:
            if cursor is not None:
                cursor.close()

    def get_latest_beep(self):
        cursor = self.connection.cursor()
        self.__exec_sql_script(cursor, 'get_latest_beep')
        row = cursor.fetchone()
        cursor.close()
        return row['beep']

    def get_next_beep(self):
        return self.get_latest_beep() + 1

    def get_latest_block_number(self):
        cursor = self.connection.cursor()
        self.__exec_sql_script(cursor, 'get_current_block_number')
        row = cursor.fetchone()
        cursor.close()
        return row['block_nbr']

    def get_next_block_number(self):
        return self.get_latest_block_number() + 1

    def add_evt_to_be_processed(self, evt):
        cursor = None
        try:
            cursor = self.connection.cursor()
            self.__exec_sql_script(
                cursor,
                'add_evt_to_be_processed',
                (evt['beep'], evt['evt_name'], evt['block_nbr'],)
            )
            self.connection.commit()
        except sqlite3.Error:
            self.connection.rollback()
        finally:
            if cursor is not None:
                cursor.close()

    def __process_evt_with_new_status(self, query_name, query_params, fct):
        cursor = None
        try:
            cursor = self.connection.cursor()
            self.__exec_sql_script(cursor, query_name, query_params)
            for evt in cursor:
                fct(evt)
            self.connection.commit()
        except sqlite3.Error:
            self.connection.rollback()
        finally:
            if cursor is not None:
                cursor.close()

    def process_incoming_events(self, beep, process_fct):
        self.__process_evt_with_new_status(
            'get_events_to_be_processed', (beep,), process_fct
        )

    def process_events_to_be_submitted(self, process_fct):
        self.__process_evt_with_new_status(
            'get_events_to_be_submitted',
            (self.max_submission_attempts,),
            process_fct
        )

    def set_evt_to_be_submitted(self, evt):
        cursor = None
        try:
            cursor = self.connection.cursor()
            self.__exec_sql_script(
                cursor,
                'set_evt_to_be_submitted',
                (evt['audit_report'], evt['id'],)
            )
            self.connection.commit()
        except sqlite3.Error:
            self.connection.rollback()
        finally:
            if cursor is not None:
                cursor.close()

    def record_submission(self, evt):
        cursor = None
        try:
            cursor = self.connection.cursor()
            self.__exec_sql_script(
                cursor,
                'set_submission',
                (evt['tx_hash'], evt['id'],)
            )
            self.connection.commit()
        except sqlite3.Error:
            self.connection.rollback()
        finally:
            if cursor is not None:
                cursor.close()

    def set_evt_to_done(self, evt):
        cursor = None
        try:
            cursor = self.connection.cursor()
            self.__exec_sql_script(
                cursor,
                'set_evt_to_done',
                (evt['id'],)
            )
            self.connection.commit()
        except sqlite3.Error:
            self.connection.rollback()
        finally:
            if cursor is not None:
                cursor.close()

    def set_evt_to_error(self, evt):
        cursor = None
        try:
            cursor = self.connection.cursor()
            self.__exec_sql_script(
                cursor,
                'set_evt_to_err',
                (evt['id'],)
            )
            self.connection.commit()
        except sqlite3.Error:
            self.connection.rollback()
        finally:
            if cursor is not None:
                cursor.close()

    def close(self):
        self.connection.close()
