####################################################################################################
#                                                                                                  #
# (c) 2018 Quantstamp, Inc. All rights reserved.  This content shall not be used, copied,          #
# modified, redistributed, or otherwise disseminated except to the extent expressly authorized by  #
# Quantstamp for credentialed users. This content and its use are governed by the Quantstamp       #
# Demonstration License Terms at <https://s3.amazonaws.com/qsp-protocol-license/LICENSE.txt>.      #
#                                                                                                  #
####################################################################################################

resource "aws_iam_instance_profile" "police" {
  name  = "${var.environment}-${var.stage}-police-beanstalk-ec2-profile"
  role = "${aws_iam_role.main.name}"
}

resource "aws_elastic_beanstalk_environment" "police" {
  name                  = "qsp-protocol-police-node-${var.stage}"
  application           = "qsp-protocol-police-node"
  solution_stack_name   = "64bit Amazon Linux 2018.03 v2.11.4 running Multi-container Docker 18.06.1-ce (Generic)"
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
    value     = "${var.node_instance_type_police}"
  }

  setting {
    namespace = "aws:autoscaling:launchconfiguration"
    name      = "SecurityGroups"
    value = "${aws_security_group.police.name}"
  }

  setting {
    namespace = "aws:autoscaling:launchconfiguration"
    name      = "IamInstanceProfile"
    value     = "${aws_iam_instance_profile.police.name}"
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
    value = "${var.QSP_ETH_POLICE_PASSPHRASE}"
  }
  
  setting {
    namespace = "aws:elasticbeanstalk:application:environment"
    name      = "QSP_NODE_TYPE"
    value     = "police"
  }
  
  tags {
    Name = "${var.environment}-${var.stage}-node-beanstalk-app"
  }
}
