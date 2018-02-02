#!/bin/bash
set -f # do not expand
env_name=""
commit=$(git rev-parse HEAD)
branch=$(git branch -r --contains "$commit")
if [[ $branch == *"origin/prod"* ]]
then
  env_name="prod"
  echo "Deploying into PRODUCTION..."
elif [[ $branch == *"origin/develop"* ]]
then
  env_name="dev"
  echo "Deploying into DEV..."
else
  echo "The branch is not eligible for deployment. Skipping deploy..."
  exit 0
fi

if [[ "$1" != "-s" ]]
then
  read -p "Are you sure? [y or n]: " -n 1 -r
  echo # (optional) move to a new line

  if ! [[ $REPLY =~ ^[Yy]$ ]]
  then
    exit 0
  fi
fi

image_tag=$commit
echo Pulling the image if already exists...

if docker pull $AWS_ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com/$IMAGE_REPO_NAME:$image_tag
then
    echo The image for this commit already exists, no need to rebuild
else
    echo The image for this commit does not yet exist, building it...
    docker build -t $IMAGE_REPO_NAME:$image_tag .
    docker tag $IMAGE_REPO_NAME:$image_tag $AWS_ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com/$IMAGE_REPO_NAME:$image_tag
    echo Pushing the Docker image...
    docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com/$IMAGE_REPO_NAME:$image_tag
fi

echo Tagging the image with $env_name...
docker tag $AWS_ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com/$IMAGE_REPO_NAME:$image_tag $AWS_ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com/$IMAGE_REPO_NAME:$env_name
echo Pushing the Docker image...
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com/$IMAGE_REPO_NAME:$env_name
echo Script ran successfully!
