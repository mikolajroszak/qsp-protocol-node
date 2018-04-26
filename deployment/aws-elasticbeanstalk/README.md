# aws-elasticbeanstalk

Deploying the audit node using AWS Elastic Beanstalk multi-container Docker.

## Setup

1. Acquire AWS admin credentials
2. Install [Terraform](https://www.terraform.io/).
3. Go to `terraform`, then `stages/dev` or `stages/prod`
5. Create a file called `terraform.tfvars` for storing secret values (but not committing them to source control)

`ETH_PASSWORD` - a passphrase for an account on the main (Ropsten) network
`WS_SECRET` - a secret for `eth-stats` dashboard

5. Run `terraform plan` and review the changes
6. Run `terraform apply` and confirm the changes

## Details

1. Create a new key pair: `qsp-protocol-dev` and `qsp-protocol-prod`.
2. 
