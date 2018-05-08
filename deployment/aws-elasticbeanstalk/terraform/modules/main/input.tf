variable "region" {
  description = "The AWS region."
}

variable "environment" {
  description = "The name of our environment"
}

variable "stage" {
  description = "Stage (dev, prod, etc.)"
}

variable "key_name" {
  description = "The AWS key pair to use for SSH-ing the nodes"
}

variable "node_instance_type_audit" {
  description = "The web server instance type for QSP Audit"
}

variable "ETH_PASSPHRASE" {
  description = "The passphrase for the keystore file"
}

variable "WS_ENDPOINT" {
  description = "Netstats endpoint"
}

variable "WS_SECRET" {
  description = "Secret for Netstats endpoint"
}

variable "volume_size" {
  description = "Volume size (GB) for each node"
  default = 50
}
