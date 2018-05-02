resource "aws_iam_instance_profile" "audit" {
  name  = "${var.environment}-audit-beanstalk-ec2-profile"
  role = "${aws_iam_role.main.name}"
}

resource "aws_elastic_beanstalk_environment" "audit" {
  name                  = "qsp-protocol-node-${var.stage}"
  application           = "qsp-protocol-node"
  solution_stack_name   = "64bit Amazon Linux 2017.09 v2.8.4 running Multi-container Docker 17.09.1-ce (Generic)"
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
    value = "${aws_security_group.audit.id}"
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
    name = "NODE_NAME"
    value = "audit-${var.stage}"
  }
  
  setting {
    namespace = "aws:elasticbeanstalk:application:environment"
    name = "LOG_GROUP_NAME"
    value = "/aws/elasticbeanstalk/qsp-protocol-${stage}/all.log"
  }
  
  setting {
    namespace = "aws:elasticbeanstalk:application:environment"
    name = "ETH_PASSPHRASE"
    value = "${var.ETH_PASSPHRASE}"
  }
  
  setting {
    namespace = "aws:elasticbeanstalk:application:environment"
    name = "WS_SECRET"
    value = "${var.WS_SECRET}"
  }
}
