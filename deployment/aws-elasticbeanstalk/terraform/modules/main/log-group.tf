resource "aws_cloudwatch_log_group" "main" {
  name = "qsp-protocol-nodes-${var.stage}"

  tags {
    Environment = "${var.stage}"
  }
}
