resource "aws_iam_policy" "node_operator" {
  name = "qsp-protocol-node-operator-${var.stage}"
  policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
      {
          "Sid": "VisualEditor1",
          "Effect": "Allow",
          "Action": [
              "s3:PutObject",
              "s3:PutObjectAcl"
          ],
          "Resource": [
              "arn:aws:s3:::qsp-protocol-reports-${var.stage}/$${aws:username}/*"
          ]
        },
        {
          "Sid": "VisualEditor3",
          "Effect": "Allow",
          "Action": [
              "logs:CreateLogStream",
              "logs:PutLogEvents"
          ],
          "Resource": [
              "arn:aws:logs:*:*:*:qsp-protocol-nodes-${var.stage}:log-stream:node-$${aws:username}"
          ]
        }
    ]
}
EOF
}
