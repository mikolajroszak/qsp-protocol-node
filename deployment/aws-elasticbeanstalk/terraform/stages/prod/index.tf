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
    key    = "prod/qsp-protocol/main.tfstate"
    region = "us-east-1"
    profile = "prod"
  }
}

variable "QSP_ETH_PASSPHRASE" {}
variable "QSP_ETH_AUTH_TOKEN" {}

module "main" {
  source = "../../modules/main"
  region = "us-east-1"
  environment = "qsp-protocol-prod"
  stage = "prod"
  key_name = "qsp-protocol-prod"
  node_instance_type_audit = "m4.large"
  volume_size = 8

  QSP_ETH_PASSPHRASE = "${var.QSP_ETH_PASSPHRASE}"
 QSP_ETH_AUTH_TOKEN = "${var.QSP_ETH_AUTH_TOKEN}"
}
