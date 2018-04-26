resource "aws_iam_role" "main" {
  name = "${var.environment}-main-beanstalk-ec2-role"

  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": "sts:AssumeRole",
      "Principal": {
        "Service": "ec2.amazonaws.com"
      },
      "Effect": "Allow",
      "Sid": ""
    }
  ]
}
EOF
}

resource "aws_iam_role_policy" "main" {
  name = "${var.environment}-beanstalk-ec2-role-policy"
  role = "${aws_iam_role.main.id}"

  policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
        "Sid": "BucketAccess",
        "Action": [
            "s3:Get*",
            "s3:List*",
            "s3:PutObject"
        ],
        "Effect": "Allow",
        "Resource": [
            "arn:aws:s3:::elasticbeanstalk-*",
            "arn:aws:s3:::elasticbeanstalk-*/*"
        ]
    },
    {
        "Sid": "XRayAccess",
        "Action": [
            "xray:PutTraceSegments",
            "xray:PutTelemetryRecords"
        ],
        "Effect": "Allow",
        "Resource": "*"
    },
    {
        "Sid": "CloudWatchLogsAccess",
        "Action": [
            "logs:PutLogEvents",
            "logs:CreateLogStream"
        ],
        "Effect": "Allow",
        "Resource": [
            "arn:aws:logs:*:*:log-group:/aws/elasticbeanstalk*"
        ]
    },
    {
      "Effect": "Allow",
      "Action": [
          "ecs:Poll",
          "ecs:StartTask",
          "ecs:StopTask",
          "ecs:DiscoverPollEndpoint",
          "ecs:StartTelemetrySession",
          "ecs:RegisterContainerInstance",
          "ecs:DeregisterContainerInstance",
          "ecs:DescribeContainerInstances",
          "ecs:Submit*",
          "ecs:DescribeTasks"
      ],
      "Resource": "*"
    },
    {
        "Effect": "Allow",
        "Action": [
            "ecr:GetAuthorizationToken",
            "ecr:BatchCheckLayerAvailability",
            "ecr:GetDownloadUrlForLayer",
            "ecr:GetRepositoryPolicy",
            "ecr:DescribeRepositories",
            "ecr:ListImages",
            "ecr:DescribeImages",
            "ecr:BatchGetImage"
        ],
        "Resource": "*"
    },
    {
        "Action": [
            "logs:CreateLogGroup",
            "logs:CreateLogStream",
            "logs:PutRetentionPolicy"
        ],
        "Effect": "Allow",
        "Resource": [
            "arn:aws:logs:*:*:log-group:/aws/elasticbeanstalk*"
        ]
    },
    {
        "Effect": "Allow",
        "Action": [
            "s3:ListBucketByTags",
            "s3:GetLifecycleConfiguration",
            "s3:GetBucketTagging",
            "s3:GetInventoryConfiguration",
            "s3:GetObjectVersionTagging",
            "s3:ListBucketVersions",
            "s3:GetBucketLogging",
            "s3:ListBucket",
            "s3:GetAccelerateConfiguration",
            "s3:GetBucketPolicy",
            "s3:GetObjectVersionTorrent",
            "s3:GetObjectAcl",
            "s3:GetBucketRequestPayment",
            "s3:GetObjectVersionAcl",
            "s3:GetObjectTagging",
            "s3:GetMetricsConfiguration",
            "s3:GetIpConfiguration",
            "s3:ListBucketMultipartUploads",
            "s3:GetBucketWebsite",
            "s3:GetBucketVersioning",
            "s3:GetBucketAcl",
            "s3:GetBucketNotification",
            "s3:GetReplicationConfiguration",
            "s3:ListMultipartUploadParts",
            "s3:GetObject",
            "s3:GetObjectTorrent",
            "s3:GetBucketCORS",
            "s3:GetAnalyticsConfiguration",
            "s3:GetObjectVersionForReplication",
            "s3:GetBucketLocation",
            "s3:GetObjectVersion"
        ],
        "Resource": [
            "arn:aws:s3:::qsp-protocol-contract-abi-${var.stage}/*",
            "arn:aws:s3:::qsp-protocol-contract-abi-${var.stage}",
            "arn:aws:s3:::qsp-protocol-reports-${var.stage}/*",
            "arn:aws:s3:::qsp-protocol-reports-${var.stage}"
        ]
    },
    {
        "Effect": "Allow",
        "Action": [
            "s3:ListAllMyBuckets",
            "s3:HeadBucket",
            "s3:ListObjects"
        ],
        "Resource": "*"
    }
  ]
}
EOF
}
