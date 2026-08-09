"""P3.4 — settings fail fast with actionable AWS-config guidance.

Guards that the non-existent resource defaults (`emip-artifacts`, `emip-jobs`,
`emip-analysis-queue`, …) are gone, that any leftover bare placeholder is
surfaced as an actionable problem, and that local startup refuses to run with
an incomplete AWS config instead of failing later with NoSuchBucket.
"""

import pytest

from app.core.settings import Settings
from app.core import startup as startup_mod

AWS_VARS = [
    "S3_BUCKET",
    "DYNAMODB_JOBS_TABLE",
    "DYNAMODB_ANALYSIS_TABLE",
    "SQS_ANALYSIS_QUEUE",
    "SQS_ANALYSIS_DLQ",
    "SNS_NOTIFICATION_TOPIC",
    "EVENTBRIDGE_BUS_NAME",
    "AWS_LAMBDA_FUNCTION_NAME",
]


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch):
    for var in AWS_VARS:
        monkeypatch.delenv(var, raising=False)


class TestAwsConfigProblems:
    def test_unconfigured_settings_flag_s3_bucket(self):
        s = Settings(_env_file=None, s3_bucket="emip-artifacts")
        problems = s.aws_config_problems
        assert any("S3_BUCKET" in p for p in problems)

    def test_fixed_defaults_use_real_dev_resources(self):
        s = Settings(_env_file=None, s3_bucket="emip-artifacts-dev-123456789012")
        assert s.aws_config_problems == []
        assert s.dynamodb_jobs_table == "emip-jobs-dev"
        assert s.dynamodb_analysis_table == "emip-analysis-dev"
        assert s.sqs_analysis_queue == "emip-analysis-queue-dev"
        assert s.sqs_analysis_dlq == "emip-analysis-dlq-dev"
        assert s.sns_notification_topic == "emip-notifications-dev"
        assert s.eventbridge_bus_name == "emip-events-dev"

    def test_bare_legacy_values_still_flagged(self):
        s = Settings(
            _env_file=None,
            s3_bucket="emip-artifacts",
            dynamodb_jobs_table="emip-jobs",
        )
        problems = s.aws_config_problems
        assert len(problems) == 2
        assert any("DYNAMODB_JOBS_TABLE" in p for p in problems)

    def test_empty_values_flagged(self):
        s = Settings(_env_file=None, s3_bucket="", dynamodb_jobs_table="")
        problems = s.aws_config_problems
        assert any("S3_BUCKET" in p for p in problems)
        assert any("DYNAMODB_JOBS_TABLE" in p for p in problems)

    def test_message_mentions_real_suffix(self):
        s = Settings(_env_file=None, s3_bucket="emip-artifacts")
        msg = s.aws_config_problems[0]
        assert "-dev" in msg and "-staging" in msg


class TestStartupFailFast:
    def test_startup_raises_with_actionable_message(self, monkeypatch):
        bad = Settings(_env_file=None, s3_bucket="emip-artifacts")
        monkeypatch.setattr(startup_mod, "get_settings", lambda: bad)
        with pytest.raises(RuntimeError) as exc_info:
            startup_mod.on_startup()
        msg = str(exc_info.value)
        assert "S3_BUCKET" in msg
        assert ".env.example" in msg

    def test_startup_ok_when_configured(self, monkeypatch):
        good = Settings(_env_file=None, s3_bucket="emip-artifacts-dev-123456789012")
        monkeypatch.setattr(startup_mod, "get_settings", lambda: good)
        startup_mod.on_startup()  # must not raise

    def test_startup_skips_validation_in_lambda(self, monkeypatch):
        monkeypatch.setenv("AWS_LAMBDA_FUNCTION_NAME", "emip-backend-staging")
        bad = Settings(_env_file=None, s3_bucket="emip-artifacts")
        monkeypatch.setattr(startup_mod, "get_settings", lambda: bad)
        startup_mod.on_startup()  # must not raise
