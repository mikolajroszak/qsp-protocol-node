import sqlite3
import os


class EventPoolManager:

    def __row_to_dict(self, row):
        return dict(zip(row.keys(), row)) 

    def __exec_sql_script(self, cursor, query, query_params=(), multiple_stmts=False):
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

    def __init__(self, db_path):
        # Gets a connection with the SQL3Lite server
        # Must be explicitly closed by calling `close` on the same
        # EventPool object. The connection is created with autocommit
        # mode on

        cursor = None
        try:
            self.__connection = sqlite3.connect(db_path, check_same_thread=False, isolation_level=None)
            self.__connection.row_factory = sqlite3.Row

            cursor = self.__connection.cursor()

            self.__exec_sql_script(cursor, 'createdb', multiple_stmts=True)
            self.__connection.commit()
        
        except Exception:
            # Exception occurred. Close first the cursor, followed
            # by the connection.
            if cursor is not None:
                cursor.close()
                cursor = None

            if self.__connection is not None:
                self.__connection.close()

            raise
        
        finally:
            # Cursor should be closed only if still opened.
            if cursor is not None:
                cursor.close()


    def get_latest_block_number(self):
        cursor = self.__connection.cursor()
        self.__exec_sql_script(cursor, 'get_latest_block_number')
        row = cursor.fetchone()
        cursor.close()
        return row['block_nbr']

    def get_next_block_number(self):
        return self.get_latest_block_number() + 1

    def add_evt_to_be_processed(self, evt):
        cursor = None
        try:
            cursor = self.__connection.cursor()
            self.__exec_sql_script(
                cursor,
                'add_evt_to_be_processed',
                query_params=(
                    evt['request_id'], 
                    evt['requestor'], 
                    evt['contract_uri'], 
                    evt['evt_name'], 
                    evt['block_nbr'],
                    evt['status_info'],
                )
            )
            self.__connection.commit()

        except sqlite3.Error:
            self.__connection.rollback()
            raise

        finally:
            if cursor is not None:
                cursor.close()

    def __process_evt_with_status(self, query_name, fct, query_params=(), fct_kwargs={}):
        cursor = None
        try:
            cursor = self.__connection.cursor()
            self.__exec_sql_script(cursor, query_name, query_params)
            for evt in cursor:
                fct(self.__row_to_dict(evt), **fct_kwargs)
            self.__connection.commit()

        except sqlite3.Error:
            self.__connection.rollback()
            raise

        finally:
            if cursor is not None:
                cursor.close()

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

    def set_evt_to_be_submitted(self, evt):
        cursor = None
        try:
            cursor = self.__connection.cursor()
            self.__exec_sql_script(
                cursor,
                'set_evt_to_be_submitted',
                (evt['status_info'], evt['report'], evt['id'],)
            )
            self.__connection.commit()

        except sqlite3.Error:
            self.__connection.rollback()
            raise

        finally:
            if cursor is not None:
                cursor.close()

    def set_evt_to_submitted(self, evt):
        cursor = None
        try:
            cursor = self.__connection.cursor()
            self.__exec_sql_script(
                cursor,
                'set_evt_to_submitted',
                (evt['tx_hash'], evt['status_info'], evt['report'], evt['id'],)
            )
            self.__connection.commit()

        except sqlite3.Error as error:
            self.__connection.rollback()
            raise error

        finally:
            if cursor is not None:
                cursor.close()

    def set_evt_to_done(self, evt):
        cursor = None
        try:
            cursor = self.__connection.cursor()
            self.__exec_sql_script(
                cursor,
                'set_evt_to_done',
                (evt['id'],)
            )
            self.__connection.commit()

        except sqlite3.Error:
            self.__connection.rollback()
            raise

        finally:
            if cursor is not None:
                cursor.close()

    def set_evt_to_error(self, evt):
        cursor = None
        try:
            cursor = self.__connection.cursor()
            self.__exec_sql_script(
                cursor,
                'set_evt_to_error',
                (evt['status_info'], evt['id'],)
            )
            self.__connection.commit()

        except sqlite3.Error as error:
            self.__connection.rollback()
            raise error 

        finally:
            if cursor is not None:
                cursor.close()

    def close(self):
        self.__connection.close()
