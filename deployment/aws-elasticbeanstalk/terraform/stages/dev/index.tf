provider "aws" {
  region = "us-east-1"
}

terraform {
  required_version = "= 0.11.1"
  backend "s3" {
    bucket = "quantstamp-terraform-state"
    key    = "dev/qsp-protocol/main.tfstate"
    region = "us-east-1"
  }
}

variable "ETH_PASSPHRASE" {}
variable "WS_SECRET" {}

module "main" {
  source = "../../modules/main"
  region = "us-east-1"
  environment = "qsp-protocol-dev"
  stage = "dev"
  key_name = "qsp-protocol-dev"
  node_instance_type_audit = "m4.large"

  # the remaining variables are in terraform.tfvars
  ETH_PASSPHRASE = "${var.ETH_PASSPHRASE}"
  WS_SECRET = "${var.WS_SECRET}"
}
