import os
from functools import lru_cache

import boto3


@lru_cache
def get_s3_client():
    return boto3.client(
        "s3",
        region_name=os.getenv("AWS_REGION", "us-east-1"),
    )


@lru_cache
def get_dynamodb_resource():
    return boto3.resource(
        "dynamodb",
        region_name=os.getenv("AWS_REGION", "us-east-1"),
    )


@lru_cache
def get_bedrock_client():
    return boto3.client(
        "bedrock-runtime",
        region_name=os.getenv("AWS_REGION", "us-east-1"),
    )


def get_s3_bucket() -> str:
    return os.getenv("S3_BUCKET", "emip-artifacts")


def get_dynamodb_table() -> str:
    return os.getenv("DYNAMODB_TABLE", "emip-jobs")
