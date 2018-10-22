####################################################################################################
#                                                                                                  #
# (c) 2018 Quantstamp, Inc. All rights reserved.  This content shall not be used, copied,          #
# modified, redistributed, or otherwise disseminated except to the extent expressly authorized by  #
# Quantstamp for credentialed users. This content and its use are governed by the Quantstamp       #
# Demonstration License Terms at <https://s3.amazonaws.com/qsp-protocol-license/LICENSE.txt>.      #
#                                                                                                  #
####################################################################################################

import unittest
import psutil
import urllib
from unittest.mock import Mock, MagicMock
from utils.metrics import MetricCollector
from unittest.mock import patch
from web3 import (
    Web3,
    EthereumTesterProvider,
)

class TestFile(unittest.TestCase):
    def setUp(self):
        self.__fake_metrics_json = {
            'processIdentifier': 'test-host-123',
            'ethBlockNumber': 123456,
            'ethNodeVersion': '1.8.13',
            'ethProtocolVersion': 'Geth/v1.8.13-stable-225171a4/linux-amd64/go1.10',
            'contractVersion': '4.5.6',
            'nodeVersion': '1.2.3',
            'hostCpu': 16,
            'hostMemory': 18,
            'hostDisk': 20,
            'minPrice': 1000,
            'account': '0xe685187635499B823d97FFBf16CB0EE34a172c33'
        }

    def __setup_fake_metrics(self, disk_usage, virtual_memory, cpu_percent, getpid, gethostname):
        """
        Sets up mocks to return fake metrics
        """
        gethostname.return_value = 'test-host'
        getpid.return_value = '123'
        cpu_percent.return_value = 16

        self.__config_mock = MagicMock()
        self.__config_mock.node_version = '1.2.3'
        self.__config_mock.contract_version = '4.5.6'
        self.__config_mock.web3_client.eth.blockNumber = 123456
        self.__config_mock.web3_client.version.node = '1.8.13'
        self.__config_mock.web3_client.version.ethereum = 'Geth/v1.8.13-stable-225171a4/linux-amd64/go1.10'
        self.__config_mock.account = '0xe685187635499B823d97FFBf16CB0EE34a172c33'
        self.__config_mock.min_price_in_qsp = 1000
        self.__config_mock.metric_collection_is_enabled = True

        virtual_memory_percent = MagicMock()
        virtual_memory_percent.percent = 18
        virtual_memory.return_value = virtual_memory_percent

        disk_usage_percent = MagicMock()
        disk_usage_percent.percent = 20
        disk_usage.return_value = disk_usage_percent

    @patch('socket.gethostname')
    @patch('os.getpid')
    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    def test_send_and_collect_calls_send_when_endpoint_is_defined(self, disk_usage, virtual_memory, cpu_percent, getpid, gethostname):
        """
        send_and_collect() should call send_to_dashboard(...) with expected arguments when destination endpoint is defined.
        """
        self.__setup_fake_metrics(disk_usage, virtual_memory, cpu_percent, getpid, gethostname)
        self.__config_mock.metric_collection_destination_endpoint = 'some-value'
        metrics = MetricCollector(self.__config_mock)

        with patch.object(metrics, 'send_to_dashboard', return_value=None) as mock_method:
            metrics.collect_and_send()
            mock_method.assert_called_with(self.__fake_metrics_json)

    @patch('socket.gethostname')
    @patch('os.getpid')
    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    def test_send_and_collect_does_not_call_send_when_endpoint_is_not_defined(self, disk_usage, virtual_memory, cpu_percent, getpid, gethostname):
        """
        send_and_collect() should not call send_to_dashboard(...) when destination endpoint is not defined.
        """
        self.__setup_fake_metrics(disk_usage, virtual_memory, cpu_percent, getpid, gethostname)
        self.__config_mock.metric_collection_destination_endpoint = None
        metrics = MetricCollector(self.__config_mock)

        with patch.object(metrics, 'send_to_dashboard', return_value=None) as mock_method:
            metrics.collect_and_send()
            mock_method.assert_not_called()

    @patch('socket.gethostname')
    @patch('os.getpid')
    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    def test_send_and_collect_logs_exception_when_collect_and_send_throws(self, disk_usage, virtual_memory, cpu_percent, getpid, gethostname):
        """
        send_and_collect() should log an exception when send_to_dashboard(...) fails.
        """
        self.__setup_fake_metrics(disk_usage, virtual_memory, cpu_percent, getpid, gethostname)
        self.__config_mock.metric_collection_destination_endpoint = 'some-value'
        metrics = MetricCollector(self.__config_mock)

        with patch.object(metrics, 'send_to_dashboard', side_effect=Exception('Boom!')) as mock_method:
            metrics.collect_and_send()
            self.__config_mock.logger.error.assert_called_with('Could not collect metrics due to the error: "Boom!"')

    def test_send_to_dashboard_logs_success_when_no_exception(self):
        """
        send_to_dashboard() should log success when request succeeds.
        """

        self.__config_mock = MagicMock()
        self.__config_mock.metric_collection_destination_endpoint = 'http://localhost:1234'

        web3_client = Web3(EthereumTesterProvider())
        self.__config_mock.web3_client.eth.account.signHash = web3_client.eth.account.signHash
        self.__config_mock.web3_client.toHex = web3_client.toHex
        self.__config_mock.account_private_key = '0xc2fd94c5216e754d3eb8f4f34017120fef318c50780ce408b54db575b120229f'

        metrics = MetricCollector(self.__config_mock)

        response = MagicMock()
        response.__enter__().read.return_value = 'ok'

        with patch.object(urllib.request, 'urlopen', return_value=response) as mock_method:
            metrics.send_to_dashboard(self.__fake_metrics_json)
            self.__config_mock.logger.debug.assert_called_with(
                "Metrics sent successfully to 'http://localhost:1234'",
                metrics_json=self.__fake_metrics_json,
                headers={
                    'Content-type': 'application/json',
                    'User-agent': 'Mozilla/5.0',
                    'Authorization': 'Digest: 0xde0cf725751768ff5b7e1e4bd36ce22242d5559f87b626beb9cf1ff412f232cc0fcc2aba1d29d8fdd95ac575d96dfb1ad10b24ae1a771e658ee90f4b8150b6c71b'
                },
                response='ok')

    def test_send_to_dashboard_logs_error_when_http_error(self):
        """
        send_to_dashboard() should log an error when request fails with HTTPError.
        """

        self.__config_mock = MagicMock()
        self.__config_mock.metric_collection_destination_endpoint = 'http://localhost:1234'
        metrics = MetricCollector(self.__config_mock)

        response = MagicMock()
        response.__enter__().read.side_effect = urllib.request.HTTPError(401, 'authentication failure', MagicMock(), MagicMock(), MagicMock())

        with patch.object(urllib.request, 'urlopen', return_value=response) as mock_method:
            metrics.send_to_dashboard(self.__fake_metrics_json)
            self.__config_mock.logger.debug.assert_called_with('HTTPError occurred when sending metrics', code='authentication failure', endpoint='http://localhost:1234')

    def test_send_to_dashboard_logs_error_when_url_error(self):
        """
        send_to_dashboard() should log an error when request fails with HTTPError.
        """

        self.__config_mock = MagicMock()
        self.__config_mock.metric_collection_destination_endpoint = 'http://localhost:1234'
        metrics = MetricCollector(self.__config_mock)

        response = MagicMock()
        response.__enter__().read.side_effect = urllib.request.URLError(400, 'URL invalid')

        with patch.object(urllib.request, 'urlopen', return_value=response) as mock_method:
            metrics.send_to_dashboard(self.__fake_metrics_json)
            self.__config_mock.logger.debug.assert_called_with('URLError occurred when sending metrics', endpoint='http://localhost:1234', reason=400)

    def test_send_to_dashboard_logs_error_when_unhandled_error(self):
        """
        send_to_dashboard() should log an error when request fails with generic Exception.
        """

        self.__config_mock = MagicMock()
        self.__config_mock.metric_collection_destination_endpoint = 'http://localhost:1234'
        metrics = MetricCollector(self.__config_mock)

        response = MagicMock()
        response.__enter__().read.side_effect = Exception('Generic exception')

        with patch.object(urllib.request, 'urlopen', return_value=response) as mock_method:
            metrics.send_to_dashboard(self.__fake_metrics_json)
            self.__config_mock.logger.debug.assert_called_with('Unhandled exception occurred when sending metrics', endpoint='http://localhost:1234', message='Generic exception')
