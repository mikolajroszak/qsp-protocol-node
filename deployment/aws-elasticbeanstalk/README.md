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

## CI and deployment pipeline

1. On every push to the repository, `buildspec-ci.yml` is activated. The build script runs `make test-ci` and reports the status back to AWS CodeBuild.

1. On every merge into `develop`, `buildspec.yml` is activated. It builds the image, pushes it to AWS Docker repository, creates a build artifact (a ZIP containing `Dockerrun.aws.json` and `.ebextensions` from `deployment/aws-elasticbeanstalk`) and deploys it to a dev environment on AWS using [AWS CodePipeline](https://console.aws.amazon.com/codepipeline/home?region=us-east-1#/view/qsp-protocol-node-dev).

1. To promote a dev environment to production (automation is coming as part of `QSP-488` - "Create staging (dev -> prod) pipeline for safe release to production"):
    1. In dev AWS account, go to [Application versions](https://us-east-1.console.aws.amazon.com/elasticbeanstalk/home?region=us-east-1#/application/versions?applicationName=qsp-protocol-node), download the desired artifact and unzip it
    2. Download the Docker image referenced in the unzipped folder's `Dockerrun.aws.json` and re-push it to the prod account id
    3. Edit `Dockerrun.aws.json` to use the prod AWS account id instead of the dev account id
    4. Zip the files located inside extracted folder. Note: do not zip the containing folder, only the files
    5. Run `zip -d Archive.zip __MACOSX/\*` to remove MacOS files from the archive
    6. In prod account's AWS console, upload the ZIP to the Beanstalk environment

1. To add a new deployment method, add another subfolder to `deployment`.
1. The [end-to-end test](https://console.aws.amazon.com/codepipeline/home?region=us-east-1#/view/qsp-protocol-end-to-end-test-dev) runs periodically against the Dev stack and posts any failures to the channel `#qsp-monitoring-dev`. To run the test outside of the regular schedule, go to the test link and do `Release change`.

1. [Audit node logs](https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#logStream:group=/aws/elasticbeanstalk/qsp-protocol-dev/all.log)

## SSH to instance and container

1. Go [EC2 Dashboard](https://console.aws.amazon.com/ec2/v2/home?region=us-east-1#Instances:sort=tag:Name)

1. Look for one of the instances named `qsp-protocol-node-{stage}`

1. Click `Connect` and provide the corresponding key

1. Type in the following commands:

    ```bash
    sudo su
    docker ps
    ```

    and locate the image `466368306539.dkr.ecr.us-east-1.amazonaws.com/qsp-protocol-node` and record its id, e.g., `e237a5cf55f2`.
    With that, run:

    ```bash
    docker exec -i -t e237a5cf55f2 bash
    ```