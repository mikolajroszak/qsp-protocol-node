class FilterThreads:

    __filter_threads = []

    @staticmethod
    def register(filter_thread):
        FilterThreads.__filter_threads.append(filter_thread)

    @staticmethod
    def any_filter_thread_present():
        return len(FilterThreads.__filter_threads) > 0

    @staticmethod
    def is_alive(filter_thread):
    # it's a wicked way of detecting whether a web3.py filter is still working
    # but unfortunately I wasn't able to find any other one
        return hasattr(filter_thread, '_args') and hasattr(filter_thread, '_kwargs')

    @staticmethod
    def list():
        return FilterThreads.__filter_threads