provider "aws" {
  region = "us-east-1"
  profile = "staging"
}

terraform {
  required_version = ">= 0.11.1"
  backend "s3" {
    bucket = "qsp-protocol-staging-terraform-state"
    key    = "staging/qsp-protocol/main.tfstate"
    region = "us-east-1"
    profile = "staging"
  }
}

variable "ETH_PASSPHRASE" {}
variable "ETH_AUTH_TOKEN" {}

module "main" {
  source = "../../modules/main"
  region = "us-east-1"
  environment = "qsp-protocol-staging"
  stage = "staging"
  key_name = "qsp-protocol-staging"
  node_instance_type_audit = "m4.large"
  volume_size = 8

  ETH_PASSPHRASE = "${var.ETH_PASSPHRASE}"
  ETH_AUTH_TOKEN = "${var.ETH_AUTH_TOKEN}"
}
