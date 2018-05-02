resource "aws_s3_bucket" "reports_bucket" {
  bucket = "qsp-protocol-reports-${stage}"
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
