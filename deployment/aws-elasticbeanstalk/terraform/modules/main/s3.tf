####################################################################################################
#                                                                                                  #
# (c) 2018 Quantstamp, Inc. All rights reserved.  This content shall not be used, copied,          #
# modified, redistributed, or otherwise disseminated except to the extent expressly authorized by  #
# Quantstamp for credentialed users. This content and its use are governed by the Quantstamp       #
# Demonstration License Terms at <https://s3.amazonaws.com/qsp-protocol-license/LICENSE.txt>.      #
#                                                                                                  #
####################################################################################################

resource "aws_s3_bucket" "reports_bucket" {
  bucket = "qsp-protocol-reports-${var.stage}"
  acl    = "private"
}

resource "aws_s3_bucket_policy" "reports_bucket_policy" {
  bucket = "${aws_s3_bucket.reports_bucket.id}"
  policy =<<POLICY
{
    "Version": "2012-10-17",
    "Id": "Policy1509863250411",
    "Statement": [
        {
            "Sid": "Stmt1509863248911",
            "Effect": "Allow",
            "Principal": {
                "AWS": "*"
            },
            "Action": "s3:GetObject",
            "Resource": "arn:aws:s3:::${aws_s3_bucket.reports_bucket.id}/*"
        }
    ]
}
POLICY
}
