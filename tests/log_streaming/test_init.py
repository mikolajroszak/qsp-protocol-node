####################################################################################################
#                                                                                                  #
# (c) 2018, 2019 Quantstamp, Inc. This content and its use are governed by the license terms at    #
# <https://s3.amazonaws.com/qsp-protocol-license/V2_LICENSE.txt>                                   #
#                                                                                                  #
####################################################################################################

import log_streaming

from config import ConfigFactory, config_value
from helpers.resource import resource_uri
from helpers.qsp_test import QSPTest
from helpers.qsp_test import setup_logging
from streaming import CloudWatchProvider
import pytest


def get_config():
    return log_streaming.__config


def get_account():
    return log_streaming.__account


def get_loggers():
    return log_streaming.__stream_loggers


@pytest.mark.ci
class TestLoggingInit(QSPTest):

    def test_initialize(self):
        config_file_uri = resource_uri("test_config.yaml")
        config = ConfigFactory.create_from_file(config_file_uri, "dev",
                                                validate_contract_settings=False)
        log_streaming.initialize("account", config_value(config, "/logging/streaming", {}),
                                 force=True)
        self.assertEqual(get_config(), {})
        self.assertEqual(get_account(), "account")
        self.assertEqual(get_loggers(), {})
        try:
            log_streaming.initialize("account", {})
            self.fail("An exception was expected")
        except Exception:
            # expected
            pass

    def test_create_logging_streaming_provider_ok(self):
        """
        Tests that the CloudWatch provider can be created and is properly returned.
        """
        log_streaming.initialize("account", {}, force=True)
        streaming_provider_name = "CloudWatchProvider"
        streaming_provider_args = {'log_group': 'grp', 'log_stream': 'stream',
                                   'send_interval_seconds': 10}

        result = log_streaming.create_streaming_provider(streaming_provider_name,
                                                         streaming_provider_args)
        self.assertTrue(isinstance(result, CloudWatchProvider),
                        "The created provider is not a CloudWatchProvider")

    def test_create_logging_streaming_provider_not_ok(self):
        """
        Tests that wrong streaming provider specification causes an exception being thrown.
        """
        log_streaming.initialize("account", {}, force=True)
        streaming_provider_name = "nonsense"
        streaming_provider_args = {'log_group': 'grp', 'log_stream': 'stream',
                                   'send_interval_seconds': 10}
        try:
            log_streaming.create_streaming_provider(streaming_provider_name,
                                                    streaming_provider_args)
            self.fail("Succeeded to create streaming provider without proper provider name.")
        except Exception:
            # expected
            pass

    def test_configure_logging_no_stream(self):
        # Since streaming is set to False, this will not invoke logger creating and will pass
        streaming_provider_name = "Nonsense"
        # The logger is not initialized proper
        streaming_provider_args = {'log_group': 'grp', 'log_stream': 'stream',
                                   'send_interval_seconds': 10}
        config = {'is_enabled': False, 'provider': streaming_provider_name,
                  'args': streaming_provider_args}
        log_streaming.initialize("test-account", config, force=True)
        self.assertEqual(get_loggers(), {})
        log_streaming.get_logger("test_get_logger")
        # No configuration should happen
        self.assertFalse("test_get_logger" in get_loggers())

    def test_configure_logging_stream_provider(self):
        streaming_provider_name = "CloudWatchProvider"
        # The logger is not initialized proper
        streaming_provider_args = {'log_group': 'grp', 'log_stream': 'stream',
                                   'send_interval_seconds': 10}
        config = {'is_enabled': True, 'provider': streaming_provider_name,
                  'args': streaming_provider_args}
        log_streaming.initialize("test-account", config, force=True)
        logger = log_streaming.get_logger("test_get_logger")
        self.assertTrue(logger is log_streaming.get_logger("test_get_logger"))
        self.assertTrue("test_get_logger" in get_loggers())
        # Reset logging after this call
        log_streaming.initialize("account", {'is_enabled': False}, force=True)

    @classmethod
    def tearDownClass(cls):
        # resets logging
        setup_logging()
        log_streaming.initialize("account", {'is_enabled': False}, force=True)
