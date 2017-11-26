# Docker in Production using AWS ECS Capacity Manager Lambda Function

This repository defines a Lamdba function called `ecsCapacity`, which is included with the Pluralsight course [Docker in Production using Amazon Web Services](https://app.pluralsight.com/library/courses/docker-production-using-amazon-web-services/table-of-contents).

This function calculates the current capacity of an ECS cluster in terms of the following resources:

- CPU
- Memory
- Network Ports

The function calculates two metrics and publishes the metrics to the AWS CloudWatch service:

- **ContainerCapacity (integer)** - the current spare capacity of the ECS cluster, expressed in terms of number of containers.  Typically you would *scale out* your ECS cluster when this value drops below (<) 1.
- **IdleHostCapacity (float)** - the current number of idle hosts in the ECS cluster, express in terms of number of hosts.  Typically you would *scale in* your ECS cluster when this value is greater than (>) 1.0.

## Branches

This repository contains two branches:

- [`master`](https://github.com/docker-production-aws/lambda-ecs-capacity/tree/master) - represents the initial starting state of the repository as viewed in the course.  Specifically this is an empty repository that you are instructed to create in the module **Auto Scaling ECS Applications**.

- [`final`](https://github.com/docker-production-aws/lambda-ecs-capacity/tree/final) - represents the final state of the repository after completing all configuration tasks as described in the course material.

> The `final` branch is provided as a convenience in the case you get stuck, or want to avoid manually typing out large configuration files.  In most cases however, you should attempt to configure this repository by following the course material.

To clone this repository and checkout a branch you can simply use the following commands:

```
$ git clone https://github.com/docker-production-aws/lambda-ecs-capacity.git
...
...
$ git checkout final
Switched to branch 'final'
$ git checkout master
Switched to branch 'master'
```

## Errata

No known issues.

## Further Reading

- [Amazon ECS Events](http://docs.aws.amazon.com/AmazonECS/latest/developerguide/ecs_cwe_events.html)

## Build Instructions

To complete the build process you need the following tools installed:

- Python 2.7
- PIP package manager
- [AWS CLI](https://aws.amazon.com/cli/)

Any dependencies need to defined in `src/requirements.txt`.  Note that you do not need to include `boto3`, as this is provided by AWS for Python Lambda functions.

To build the function and its dependencies:

`make build`

This will create the necessary dependencies in the `src` folder and create a ZIP package in the `build` folder.  This file is suitable for upload to the AWS Lambda service to create a Lambda function.

```
$ make build
=> Building ecsCapacity.zip...
...
...
updating: requirements.txt (stored 0%)
updating: setup.cfg (stored 0%)
updating: ecsCapacity.py (deflated 63%)
=> Built build/ecsCapacity.zip
```

### Function Naming

The default name for this function is `ecsCapacity` and the corresponding ZIP package that is generated is called `ecsCapacity.zip`.

If you want to change the function name, you can either update the `FUNCTION_NAME` setting in the `Makefile` or alternatively configure an environment variable of the same name to override the default function name.

## Publishing the Function

When you publish the function, you are simply copying the built ZIP package to an S3 bucket.  Before you can do this, you must ensure you have created the S3 bucket and your environment is configured correctly with appropriate AWS credentials and/or profiles.

To specify the S3 bucket that the function should be published to, you can either configure the `S3_BUCKET` setting in the `Makefile` or alternatively configure an environment variable of the same name to override the default S3 bucket name.

> [Versioning](http://docs.aws.amazon.com/AmazonS3/latest/dev/Versioning.html) should be enabled on the S3 bucket

To deploy the built ZIP package:

`make publish`

This will upload the built ZIP package to the configured S3 bucket.

> When a new or updated package is published, the S3 object version will be displayed.

### Publish Example

```
$ make publish
...
...
=> Built build/ecsCapacity.zip
=> Publishing ecsCapacity.zip to s3://123456789012-cfn-lambda...
=> Published to S3 URL: https://s3.amazonaws.com/123456789012-cfn-lambda/ecsCapacity.zip
=> S3 Object Version: gyujkgVKoH.NVeeuLYTi_7n_NUburwa4
```