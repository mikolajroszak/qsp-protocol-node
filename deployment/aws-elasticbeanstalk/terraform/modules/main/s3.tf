resource "aws_s3_bucket" "reports" {
  bucket = "qsp-protocol-reports"
  acl    = "private"
}
