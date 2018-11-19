# Deployment using AWS Elastic Beanstalk

Deploying the audit node using AWS Elastic Beanstalk multi-container Docker.

## Steps

`<stage-name>` represent the name of a stage, e.g., `dev`, `prod`, etc.

1. Setup AWS credentials
    1. Request for credentials from the Protocol team (`#dev-protocol` on Slack)
    2. Do `aws configure --profile <stage-name>`
2. In AWS console, for each stage, create a new key pair: `qsp-protocol-<stage-name>`
3. In AWS console, create a new Elastic Beanstalk app: `qsp-protocol-node` (done only once)
4. Install [Terraform](https://www.terraform.io/). Tested with the following version:
  ```
  terraform version
  Terraform v0.11.1
  + provider.aws v1.17.0
  ```
5. Go to `terraform/stages`, then `cd` to the `<stage-name>`
6. Run `terraform plan` and review the changes
7. Run `terraform apply` and confirm the changes

    *Note*: you will be prompted to provide values for certain sensitive variables,
    such as, `QSP_ETH_PASSPHRASE` and `QSP_ETH_AUTH_TOKEN` for every `plan` or `apply` command.
    An alternative is to create a file `terraform.tfvars` in the current stage folder
    and specify the values here (**DO NOT** commit this to the source control):

    ```
    QSP_ETH_PASSPHRASE=<password>
    QSP_ETH_AUTH_TOKEN=<authentication token>
    ```

    If values aren't yet known, you may also choose to provide arbitrary values and change them later, after the environment is setup.

8. SSH to the EC2 instance and upload a keystore file for the Ethereum account to `/var/geth-keystore` (note: it should match the mount location for the `geth-keystore` volume in `app/Dockerrun.aws.json`)

9. Deploy the app.

    The application bundle is described by the `app/Dockerrun.aws.json` file. It's created separately as a part of the build pipeline. Refer to the `app` subfolder, AWS Code Pipeline jobs (`qsp-protocol-node-<stage-name>`), and the corresponding GitHub hooks for details.
