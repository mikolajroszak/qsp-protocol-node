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
variable "WS_SECRET" {}

module "main" {
  source = "../../modules/main"
  region = "us-east-1"
  environment = "qsp-protocol-prod"
  stage = "prod"
  key_name = "qsp-protocol-prod"
  node_instance_type_audit = "m4.large"

  WS_ENDPOINT = "qsp-stats.quantstamp.com"
  # the remaining variables are in terraform.tfvars
  ETH_PASSPHRASE = "${var.ETH_PASSPHRASE}"
  WS_SECRET = "${var.WS_SECRET}"
}
