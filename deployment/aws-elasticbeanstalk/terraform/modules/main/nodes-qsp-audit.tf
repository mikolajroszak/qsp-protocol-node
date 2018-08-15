resource "aws_iam_instance_profile" "audit" {
  name  = "${var.environment}-audit-beanstalk-ec2-profile"
  role = "${aws_iam_role.main.name}"
}

resource "aws_elastic_beanstalk_environment" "audit" {
  name                  = "qsp-protocol-node-${var.stage}"
  application           = "qsp-protocol-node"
  solution_stack_name   = "64bit Amazon Linux 2018.03 v2.11.0 running Multi-container Docker 18.03.1-ce (Generic)"
  tier                  = "WebServer"

  # You can set the environment type, single or LoadBalanced
  setting {
    namespace = "aws:elasticbeanstalk:environment"
    name      = "EnvironmentType"
    value     = "LoadBalanced"
  }

  setting {
    namespace = "aws:autoscaling:launchconfiguration"
    name      = "InstanceType"
    value     = "${var.node_instance_type_audit}"
  }

  setting {
    namespace = "aws:autoscaling:launchconfiguration"
    name      = "SecurityGroups"
    value = "${aws_security_group.audit.name}"
  }

  setting {
    namespace = "aws:autoscaling:launchconfiguration"
    name      = "IamInstanceProfile"
    value     = "${aws_iam_instance_profile.audit.name}"
  }

  setting {
    namespace = "aws:autoscaling:launchconfiguration"
    name      = "EC2KeyName"
    value     = "${var.key_name}"
  }
  
  setting {
    namespace = "aws:autoscaling:launchconfiguration"
    name      = "RootVolumeSize"
    value     = "${var.volume_size}"
  }
  
  setting {
    namespace = "aws:elasticbeanstalk:application:environment"
    name = "ENV"
    value = "${var.stage}"
  }
  
  setting {
    namespace = "aws:elasticbeanstalk:application:environment"
    name = "CONFIG"
    value = "/app/node-config/config.yaml"
  }
  
  setting {
    namespace = "aws:elasticbeanstalk:application:environment"
    name = "AWS_DEFAULT_REGION"
    value = "us-east-1"
  }
  
  setting {
    namespace = "aws:elasticbeanstalk:application:environment"
    name = "LOG_GROUP_NAME"
    value = "/aws/elasticbeanstalk/qsp-protocol-${var.stage}/all.log"
  }
  
  setting {
    namespace = "aws:elasticbeanstalk:application:environment"
    name = "ETH_PASSPHRASE"
    value = "${var.ETH_PASSPHRASE}"
  }

  setting {
    namespace = "aws:elasticbeanstalk:application:environment"
    name = "ETH_AUTH_TOKEN"
    value = "${var.ETH_AUTH_TOKEN}"
  }
  
  tags {
    Name = "${var.environment}-node-beanstalk-app"
  }
}
