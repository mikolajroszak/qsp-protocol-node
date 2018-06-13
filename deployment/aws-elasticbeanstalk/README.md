# Deployment using AWS Elastic Beanstalk

Deploying the audit node using AWS Elastic Beanstalk multi-container Docker.

## Setup

1. Acquire AWS admin credentials (`#dev-protocol` on Slack)
2. In AWS console, create a new key pair: `qsp-protocol-dev` and `qsp-protocol-prod`.
3. In AWS console, create a new Elastic Beanstalk app: `qsp-protocol-node` 
4. Install [Terraform](https://www.terraform.io/). Tested with the following version:
  ```
  terraform version
  Terraform v0.11.1
  + provider.aws v1.17.0
  ```
5. Go to `terraform`, then `stages/dev` or `stages/prod`
6. Run `terraform plan` and review the changes
7. Run `terraform apply` and confirm the changes

*Note*: by default, you will be prompted to provide values for certain sensitive variables,
such as, `ETH_PASSPHRASE`. An alternative option is to create a file `terraform.tfvars`
(in `stages/dev` or `stages/prod`) and specify the values here (but DO NOT commit this to the source control):

```
ETH_PASSPHRASE=value1
```
