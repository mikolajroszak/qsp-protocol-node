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

variable "ETH_PASSPHRASE" {}
variable "ETH_AUTH_TOKEN" {}

module "main" {
  source = "../../modules/main"
  region = "us-east-1"
  environment = "qsp-protocol-prod"
  stage = "prod"
  key_name = "qsp-protocol-prod"
  node_instance_type_audit = "m4.large"
  volume_size = 8

  ETH_PASSPHRASE = "${var.ETH_PASSPHRASE}"
  ETH_AUTH_TOKEN = "${var.ETH_AUTH_TOKEN}"
}
