from utils.node_key import NodeKey
import psutil
import boto3

class CloudWatchMetricCollectionProvider:
    def __init__(self, config, namespace):
        self.__client = boto3.client('cloudwatch')
        self.__namespace = namespace
        self.__config = config
      
    def collect_and_send(self):
        dimensions = [
            {
                'Name': 'uniqueKey',
                'Value': NodeKey.fetch()
            },
            {
                'Name': 'account',
                'Value': self.__config.account
            },
            {
                'Name': 'ethNodeVersion',
                'Value': self.__config.web3_client.version.node
            }
        ]
        
        response = self.__client.put_metric_data(
            Namespace=self.__namespace,
            MetricData=[
                {
                    'MetricName': 'ethBlockNumber',
                    'Value': self.__config.web3_client.eth.blockNumber,
                    'Unit': 'None',
                    'Dimensions': dimensions,
                },
                {
                    'MetricName': 'hostCpu',
                    'Value': psutil.cpu_percent(),
                    'Unit': 'Percent',
                    'Dimensions': dimensions,
                },
                {
                    'MetricName': 'hostMemory',
                    'Value': psutil.virtual_memory().percent,
                    'Unit': 'Percent',
                    'Dimensions': dimensions,
                },
                {
                    'MetricName': 'hostDisk',
                    'Value': psutil.disk_usage('/').percent,
                    'Unit': 'Percent',
                    'Dimensions': dimensions,
                },
                {
                    'MetricName': 'minPrice',
                    'Value': self.__config.min_price,
                    'Unit': 'None',
                    'Dimensions': dimensions,
                },
            ]
          )
