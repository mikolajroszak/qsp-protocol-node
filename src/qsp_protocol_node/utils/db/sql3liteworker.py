# Copyright (c) 2014 Palantir Technologies
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
# Author: Shawn Lee
# Changes by Leonardo Passos (Quantstamp Inc): support aspw layer, plus transaction control
# Changes by Martin Derka (Quantstamp Inc): Exception handling and rollbacks, support of custom
#     error handlers


"""Thread safe sqlite3 interface."""

__author__ = "Shawn Lee"
__email__ = "shawnl@palantir.com"
__license__ = "MIT"

import apsw
import queue as Queue
import threading
import time
import uuid

from log_streaming import get_logger


class Sqlite3Worker(threading.Thread):
    """Sqlite thread safe object.

    Example:
        from sqlite3worker import Sqlite3Worker
        sql_worker = Sqlite3Worker("/tmp/test.sqlite")
        sql_worker.execute(
            "CREATE TABLE tester (timestamp DATETIME, uuid TEXT)")
        sql_worker.execute(
            "INSERT into tester values (?, ?)", ("2010-01-01 13:00:00", "bow"))
        sql_worker.execute(
            "INSERT into tester values (?, ?)", ("2011-02-02 14:14:14", "dog"))
        sql_worker.execute("SELECT * from tester")
        sql_worker.close()

    Each call to execute runs within a transaction (except in the case of selects).

    Calls to execute_script, in turn, have certain limitations:
        - scripts may contain at most one select statement
        - non-select statements should not be mixed with select statements
        - scripts must not have comments

    As with execute, execute_script executes within a transaction.
    """

    def __init__(self, file_name, max_queue_size=100):
        """Automatically starts the thread.

        Args:
            file_name: The name of the file.
            max_queue_size: The max queries that will be queued.
        """
        self.logger = get_logger(self.__class__.__qualname__)
        threading.Thread.__init__(self)
        self.daemon = True
        self.sqlite3_conn = apsw.Connection(file_name)

        # Configures the connection always to return a dictionary
        # instead of a tuple
        def row_factory(cursor, row):
            return {k[0]: row[i] for i, k in enumerate(cursor.getdescription())}

        self.sqlite3_conn.setrowtrace(row_factory)
        self.sqlite3_cursor = self.sqlite3_conn.cursor()
        self.sql_queue = Queue.Queue(maxsize=max_queue_size)
        self.results = {}
        self.max_queue_size = max_queue_size
        self.exit_set = False
        # Token that is put into queue when close() is called.
        self.exit_token = str(uuid.uuid4())
        self.start()
        self.thread_running = True

    def run(self):
        """Thread loop.

        This is an infinite loop.  The iter method calls self.sql_queue.get()
        which blocks if there are not values in the queue.  As soon as values
        are placed into the queue the process will continue.

        If many executes happen at once it will churn through them all before
        calling commit() to speed things up by reducing the number of times
        commit is called.
        """
        execute_count = 0
        for token, query, values, error_handler in iter(self.sql_queue.get, None):
            if token != self.exit_token:
                self.run_query(token, query, values, error_handler)
                execute_count += 1

                if self.sql_queue.empty() or execute_count == self.max_queue_size:
                    execute_count = 0

            # Only exit if the queue is empty. Otherwise keep getting
            # through the queue until it's empty.
            if self.exit_set and self.sql_queue.empty():
                self.sqlite3_conn.close()
                self.thread_running = False
                return

    def run_query(self, token, query, values, error_handler):
        """Run a query.

        Args:
            token: A uuid object of the query you want returned.
            query: A sql query with ? placeholders for values.
            values: A tuple of values to replace "?" in query.
            error_handler: A function to handle error. None executes the default.
        """
        if query.lower().strip().startswith("select"):
            try:
                self.sqlite3_cursor.execute(query, values)
                self.results[token] = self.sqlite3_cursor.fetchall()
            except apsw.Error as err:
                # Put the error into the output queue since a response
                # is required.
                self.results[token] = ("Query returned error: %s: %s: %s" % (query, values, err))
                if error_handler is None:
                    self.logger.error("Query returned error: %s: %s: %s".format(query, values, err))
                else:
                    error_handler(self, query, values, err)
        else:
            try:
                self.sqlite3_cursor.execute("begin")
                self.sqlite3_cursor.execute(query, values)
                self.sqlite3_cursor.execute("commit")
            except apsw.Error as err:
                self.results[token] = err
                self.sqlite3_cursor.execute("rollback")
                if error_handler is None:
                    self.logger.error(
                        "Query returned error: %s: %s: %s",
                        query,
                        values,
                        err,
                    )
                else:
                    error_handler(self, query, values, err)

    def close(self):
        """Close down the thread and close the sqlite3 database file."""
        self.exit_set = True
        self.sql_queue.put((self.exit_token, "", "", None), timeout=5)
        # Sleep and check that the thread is done before returning.
        while self.thread_running:
            time.sleep(.01)  # Don't kill the CPU waiting.

    @property
    def queue_size(self):
        """Return the queue size."""
        return self.sql_queue.qsize()

    def query_results(self, token):
        """Get the query results for a specific token.

        Args:
            token: A uuid object of the query you want returned.

        Returns:
            Return the results of the query when it's executed by the thread.
        """
        delay = .001
        while True:
            if token in self.results:
                return_val = self.results[token]
                del self.results[token]
                return return_val
            # Double back on the delay to a max of 8 seconds.  This prevents
            # a long lived select statement from trashing the CPU with this
            # infinite loop as it's waiting for the query results.
            # self.logger.debug("Sleeping: %s %s", delay, token)
            time.sleep(delay)
            if delay < 8:
                delay += delay

    def execute(self, query, values=None, error_handler=None):
        """Execute a query.

        Args:
            query: The sql string using ? for placeholders of dynamic values.
            values: A tuple of values to be replaced into the ? of the query.
            error_handler: An optional custom handler to deal with a possible error.

        Returns:
            If it's a select query it will return the results of the query.
        """
        if self.exit_set:
            return "Exit Called"
        values = values or []
        # A token to track this query with.
        token = str(uuid.uuid4())
        # If it's a select we queue it up with a token to mark the results
        # into the output queue so we know what results are ours.
        if query.lower().strip().startswith("select"):
            self.sql_queue.put((token, query, values, error_handler), timeout=5)
            return self.query_results(token)
        else:
            self.sql_queue.put((token, query, values, error_handler), timeout=5)

        return None

    def execute_script(self, query_file, values=(), error_handler=None):
        with open(query_file) as query_stream:
            query = query_stream.read().strip()

        return self.execute(query, values, error_handler)
