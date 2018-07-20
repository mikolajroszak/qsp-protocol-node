import unittest

from upload import S3Provider


class TestS3Provider(unittest.TestCase):
    """
    Tests uploads to Amazon S3.
    """

    def test_init(self):
        """
        Tests that the constructor properly initializes the parameters.
        """
        bucket = "bucket-that-does-not-exist"
        contract_bucket = "contract-bucket-that-does-not-exist"
        provider = S3Provider(bucket, contract_bucket)
        self.assertEqual(bucket, provider._S3Provider__bucket_name,
                         "Bucket name was not initized properly")
        self.assertEqual(contract_bucket, provider._S3Provider__contract_bucket_name,
                         "Bucket name was not initized properly")
        self.assertIsNotNone(provider._S3Provider__client,
                             "The internal S3 client was not initalized properly")

    def test_successful_upload(self):
        """
        Tests uploads can be completed successfully and that the proper result is returned.
        """
        # This bucket exists in S3 so the upload should succeed if the credentials are set up
        bucket = "qsp-protocol-reports-dev"
        provider = S3Provider(bucket, bucket)
        result = provider.upload("some testing report")
        self.assertTrue(result["success"], "The result does not indicate a successful upload.")
        self.assertIsNotNone(result["url"], "The url for the report is not set.")
        self.assertIsNotNone(result["provider_response"], "The response for the upload is not set.")
        result = provider.upload_contract(0, "some testing contract", "Test.sol")
        self.assertTrue(result["success"], "The result does not indicate a successful upload.")
        self.assertIsNotNone(result["url"], "The url for the report is not set.")
        self.assertIsNotNone(result["provider_response"], "The response for the upload is not set.")

    def test_fail_upload(self):
        """
        Tests expected reactions to failed uploads.
        """
        bucket = "bucket-that-does-not-exist"
        provider = S3Provider(bucket, bucket)
        result = provider.upload("some testing report")
        self.assertFalse(result["success"], "The result does not indicate a successful upload.")
        self.assertIsNone(result["url"], "The url for the report is set.")
        self.assertIsNotNone(result["provider_exception"],
                             "The exception for the failed upload is not set.")
        result = provider.upload_contract(0, "some testing contract", "Test.sol")
        self.assertFalse(result["success"], "The result does not indicate a successful upload.")
        self.assertIsNone(result["url"], "The url for the report is set.")
        self.assertIsNotNone(result["provider_exception"],
                             "The exception for the failed upload is not set.")
        provider = S3Provider(bucket, None)
        result = provider.upload_contract(0, "some testing contract", "Test.sol")
        self.assertFalse(result["success"], "The result does not indicate a successful upload.")
        self.assertIsNone(result["url"], "The url for the report is set.")
        self.assertIsNotNone(result["provider_exception"],
                             "The exception for the failed upload is not set.")
