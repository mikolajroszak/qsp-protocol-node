provider "aws" {
  region = "us-east-1"
}

terraform {
  required_version = "= 0.11.1"
  backend "s3" {
    bucket = "quantstamp-terraform-state"
    key    = "prod/qsp-protocol/main.tfstate"
    region = "us-east-1"
  }
}

variable "ETH_PASSPHRASE" {}

module "main" {
  source = "../../modules/main"
  region = "us-east-1"
  environment = "qsp-protocol-prod"
  stage = "prod"
  key_name = "qsp-protocol-prod"
  node_instance_type_audit = "m4.large"

  ETH_PASSPHRASE = "${var.ETH_PASSPHRASE}"
}
