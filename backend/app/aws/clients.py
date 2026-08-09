"""Centralized AWS client factory with lifecycle management."""


import boto3
from botocore.config import Config

from app.core.settings import Settings


class AWSClients:
    """Factory for AWS service clients. Lazy-initialized and cached."""

    def __init__(self, settings: Settings):
        self._settings = settings
        self._s3_client = None
        self._s3_resource = None
        self._dynamodb_resource = None
        self._bedrock_client = None
        self._sqs_client = None
        self._sns_client = None
        self._cloudwatch_client = None
        self._sts_client = None
        self._events_client = None
        self._pricing_client = None
        self._cognito_idp_client = None

    @property
    def sts(self):
        if self._sts_client is None:
            self._sts_client = boto3.client(
                "sts",
                region_name=self._settings.aws_region,
            )
        return self._sts_client

    @property
    def s3(self):
        if self._s3_client is None:
            self._s3_client = boto3.client(
                "s3",
                region_name=self._settings.aws_region,
                config=Config(retries={"max_attempts": 3, "mode": "adaptive"}),
            )
        return self._s3_client

    @property
    def s3_resource(self):
        if self._s3_resource is None:
            self._s3_resource = boto3.resource(
                "s3",
                region_name=self._settings.aws_region,
            )
        return self._s3_resource

    @property
    def dynamodb(self):
        if self._dynamodb_resource is None:
            self._dynamodb_resource = boto3.resource(
                "dynamodb",
                region_name=self._settings.aws_region,
                config=Config(retries={"max_attempts": 3, "mode": "adaptive"}),
            )
        return self._dynamodb_resource

    @property
    def bedrock(self):
        if self._bedrock_client is None:
            self._bedrock_client = boto3.client(
                "bedrock-runtime",
                region_name=self._settings.aws_region,
                config=Config(retries={"max_attempts": 3, "mode": "adaptive"}),
            )
        return self._bedrock_client

    @property
    def sqs(self):
        if self._sqs_client is None:
            self._sqs_client = boto3.client(
                "sqs",
                region_name=self._settings.aws_region,
            )
        return self._sqs_client

    @property
    def sns(self):
        if self._sns_client is None:
            self._sns_client = boto3.client(
                "sns",
                region_name=self._settings.aws_region,
            )
        return self._sns_client

    @property
    def cloudwatch(self):
        if self._cloudwatch_client is None:
            self._cloudwatch_client = boto3.client(
                "cloudwatch",
                region_name=self._settings.aws_region,
            )
        return self._cloudwatch_client

    @property
    def events(self):
        if self._events_client is None:
            self._events_client = boto3.client(
                "events",
                region_name=self._settings.aws_region,
            )
        return self._events_client

    @property
    def pricing(self):
        if self._pricing_client is None:
            self._pricing_client = boto3.client(
                "pricing",
                region_name=self._settings.aws_pricing_region,
                config=Config(retries={"max_attempts": 3, "mode": "adaptive"}),
            )
        return self._pricing_client

    @property
    def cognito_idp(self):
        if self._cognito_idp_client is None:
            self._cognito_idp_client = boto3.client(
                "cognito-idp",
                region_name=self._settings.aws_region,
            )
        return self._cognito_idp_client

    @property
    def s3_bucket_name(self) -> str:
        return self._settings.s3_bucket

    @property
    def jobs_table_name(self) -> str:
        return self._settings.dynamodb_jobs_table

    @property
    def analysis_table_name(self) -> str:
        return self._settings.dynamodb_analysis_table

    def close(self) -> None:
        """Clean up clients."""
        self._s3_client = None
        self._s3_resource = None
        self._dynamodb_resource = None
        self._bedrock_client = None
        self._sqs_client = None
        self._sns_client = None
        self._cloudwatch_client = None
        self._events_client = None
        self._pricing_client = None
        self._cognito_idp_client = None
