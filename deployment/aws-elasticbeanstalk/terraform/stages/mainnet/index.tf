####################################################################################################
#                                                                                                  #
# (c) 2018 Quantstamp, Inc. All rights reserved.  This content shall not be used, copied,          #
# modified, redistributed, or otherwise disseminated except to the extent expressly authorized by  #
# Quantstamp for credentialed users. This content and its use are governed by the Quantstamp       #
# Demonstration License Terms at <https://s3.amazonaws.com/qsp-protocol-license/LICENSE.txt>.      #
#                                                                                                  #
####################################################################################################

provider "aws" {
  region = "us-east-1"
  profile = "prod"
}

terraform {
  required_version = "= 0.11.1"
  backend "s3" {
    bucket = "qsp-protocol-prod-terraform-state"
    key    = "mainnet/qsp-protocol/main.tfstate"
    region = "us-east-1"
    profile = "prod"
  }
}

variable "QSP_ETH_PASSPHRASE" {}
variable "QSP_ETH_AUTH_TOKEN" {}

variable "QSP_ETH_POLICE_PASSPHRASE" {}
variable "QSP_ETH_POLICE_AUTH_TOKEN" {}
module "main" {
  source = "../../modules/main"
  region = "us-east-1"
  environment = "qsp-protocol"
  stage = "mainnet"
  key_name = "qsp-protocol-mainnet"
  node_instance_type_audit = "m4.large"
  node_instance_type_police = "r5.large"
  volume_size = 8
  beanstalk_stack = "64bit Amazon Linux 2018.03 v2.11.9 running Multi-container Docker 18.06.1-ce (Generic)"
  QSP_ETH_PASSPHRASE = "${var.QSP_ETH_PASSPHRASE}"
  QSP_ETH_AUTH_TOKEN = "${var.QSP_ETH_AUTH_TOKEN}"
  QSP_ETH_POLICE_PASSPHRASE = "${var.QSP_ETH_POLICE_PASSPHRASE}"
  QSP_ETH_POLICE_AUTH_TOKEN = "${var.QSP_ETH_POLICE_AUTH_TOKEN}"
}
