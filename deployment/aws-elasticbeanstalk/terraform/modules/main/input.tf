####################################################################################################
#                                                                                                  #
# (c) 2018 Quantstamp, Inc. All rights reserved.  This content shall not be used, copied,          #
# modified, redistributed, or otherwise disseminated except to the extent expressly authorized by  #
# Quantstamp for credentialed users. This content and its use are governed by the Quantstamp       #
# Demonstration License Terms at <https://s3.amazonaws.com/qsp-protocol-license/LICENSE.txt>.      #
#                                                                                                  #
####################################################################################################

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

variable "ETH_AUTH_TOKEN" {
  description = "The authorization token for accessing the provider endpoint"
}

variable "volume_size" {
  description = "Volume size (GB) for each node"
  default = 50
}
