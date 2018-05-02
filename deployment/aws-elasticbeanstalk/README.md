# aws-elasticbeanstalk

Deploying the audit node using AWS Elastic Beanstalk multi-container Docker.

## Setup

1. Acquire AWS admin credentials
2. In AWS console, create a new key pair: `qsp-protocol-dev` and `qsp-protocol-prod`.
3. In AWS console, create a new Elastic Beanstalk app: `qsp-protocol-node` 
4. Install [Terraform](https://www.terraform.io/).
5. Go to `terraform`, then `stages/dev` or `stages/prod`
6. Create a file called `terraform.tfvars` for storing secret values (but DO NOT commit these to the source control)

`ETH_PASSWORD=...` - a passphrase for an account on the main (Ropsten) network
`WS_SECRET=...` - a secret for `eth-stats` dashboard

7. Run `terraform plan` and review the changes
8. Run `terraform apply` and confirm the changes
