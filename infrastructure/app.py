#!/usr/bin/env python3
import os
import aws_cdk as cdk
from cdk_stacks.backend_stack import EMIPBackendStack

app = cdk.App()

env = cdk.Environment(
    account=os.getenv("CDK_DEFAULT_ACCOUNT", os.getenv("AWS_ACCOUNT_ID")),
    region=os.getenv("CDK_DEFAULT_REGION", os.getenv("AWS_REGION", "us-east-1")),
)

EMIPBackendStack(app, "EMIP-Backend", env=env)

app.synth()
