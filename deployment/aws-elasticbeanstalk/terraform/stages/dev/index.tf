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
variable "ETH_AUTH_TOKEN" {}

module "main" {
  source = "../../modules/main"
  region = "us-east-1"
  environment = "qsp-protocol-dev"
  stage = "dev"
  key_name = "qsp-protocol-dev"
  node_instance_type_audit = "m4.large"
  
  ETH_PASSPHRASE = "${var.ETH_PASSPHRASE}"
  ETH_AUTH_TOKEN = "${var.ETH_AUTH_TOKEN}"
}
