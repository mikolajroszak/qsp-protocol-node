import sys
import os
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(levelname)s[%(threadName)s] %(message)s',
)

sys.path.append(os.path.dirname(__file__) + '/../qsp_network_audit')
sys.path.append(os.path.dirname(__file__))
