####################################################################################################
#                                                                                                  #
# (c) 2018 Quantstamp, Inc. All rights reserved.  This content shall not be used, copied,          #
# modified, redistributed, or otherwise disseminated except to the extent expressly authorized by  #
# Quantstamp for credentialed users. This content and its use are governed by the Quantstamp       #
# Demonstration License Terms at <https://s3.amazonaws.com/qsp-protocol-license/LICENSE.txt>.      #
#                                                                                                  #
####################################################################################################

resource "aws_iam_instance_profile" "audit" {
  name  = "${var.environment}-${var.stage}-audit-beanstalk-ec2-profile"
  role = "${aws_iam_role.main.name}"
}

resource "aws_elastic_beanstalk_environment" "audit" {
  name                  = "qsp-protocol-node-${var.stage}"
  application           = "qsp-protocol-node"
  solution_stack_name   = "${var.beanstalk_stack}"
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
    name = "QSP_ENV"
    value = "${var.stage}"
  }
  
  setting {
    namespace = "aws:elasticbeanstalk:application:environment"
    name = "QSP_CONFIG"
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
    name = "QSP_ETH_PASSPHRASE"
    value = "${var.QSP_ETH_PASSPHRASE}"
  }

  setting {
    namespace = "aws:elasticbeanstalk:application:environment"
    name = "QSP_ETH_AUTH_TOKEN"
    value = "${var.QSP_ETH_AUTH_TOKEN}"
  }
  
  setting {
    namespace = "aws:elasticbeanstalk:application:environment"
    name      = "QSP_NODE_TYPE"
    value     = "audit"
  }
  
  tags {
    Name = "${var.environment}-${var.stage}-node-beanstalk-app"
  }
}
