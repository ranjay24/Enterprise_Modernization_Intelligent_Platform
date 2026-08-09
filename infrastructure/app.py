#!/usr/bin/env python3
"""CDK app — EXPERIMENTAL / LEGACY. Kept for reference only.

The canonical deployment path is AWS SAM (`infrastructure/template.yaml` +
`layers/dependencies/`), matching the live staging environment. Do NOT use
this stack for new deployments: it lacks the SQS worker, DLQ, SNS and
EventBridge resources, and its ALB is HTTP-only. See docs/14_DEPLOYMENT.md.
"""
import os
import aws_cdk as cdk
from cdk_stacks.backend_stack import EMIPBackendStack

app = cdk.App()

print("WARNING: infrastructure/app.py (CDK) is EXPERIMENTAL/LEGACY — use SAM (template.yaml) instead.")

env = cdk.Environment(
    account=os.getenv("CDK_DEFAULT_ACCOUNT", os.getenv("AWS_ACCOUNT_ID")),
    region=os.getenv("CDK_DEFAULT_REGION", os.getenv("AWS_REGION", "us-east-1")),
)

EMIPBackendStack(app, "EMIP-Backend", env=env)

app.synth()
