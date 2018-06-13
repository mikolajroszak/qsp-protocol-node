import boto3
import uuid


class S3Provider:
    def __init__(self, bucket_name):
        self.__client = boto3.client('s3')
        self.__bucket_name = bucket_name

    def upload(self, report_as_string):
        try:
            report_file_name = "{0}.json".format(str(uuid.uuid4()))
            response = self.__client.put_object(
                Body=str(report_as_string),
                Bucket=self.__bucket_name,
                Key=report_file_name,
                ContentType="application/json"
            )
            return {
                'success': True,
                'url': "https://s3.amazonaws.com/{0}/{1}".format(
                    self.__bucket_name,
                    report_file_name
                ),
                'provider_response': response
            }
        except Exception as exception:
            return {
                'success': False,
                'url': None,
                'provider_exception': exception
            }
