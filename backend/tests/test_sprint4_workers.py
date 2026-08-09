"""Sprint 4 tests — Workers, SQS, EventBridge, checkpoint, notifications, events."""

import json
from unittest.mock import MagicMock, patch

import pytest

# ─── SQS Repository ───

class TestSQSRepository:
    def test_init(self):
        from app.aws.sqs import SQSRepository
        with patch("app.aws.sqs.get_settings") as mock_settings, \
             patch("app.aws.sqs.AWSClients") as mock_clients:
            mock_settings.return_value = MagicMock()
            repo = SQSRepository()
            assert repo is not None

    @patch("app.aws.sqs.AWSClients")
    @patch("app.aws.sqs.get_settings")
    def test_enqueue_analysis(self, mock_settings, MockClients):
        from app.aws.sqs import SQSRepository
        mock_settings.return_value = MagicMock(sqs_analysis_queue="q")
        mock_client = MagicMock()
        mock_client.sqs.get_queue_url.return_value = {"QueueUrl": "https://sqs.example.com/q"}
        mock_client.sqs.send_message.return_value = {"MessageId": "msg-123"}
        MockClients.return_value = mock_client
        repo = SQSRepository()
        msg_id = repo.enqueue_analysis("job-001", {"job_id": "job-001"})
        assert msg_id == "msg-123"

    @patch("app.aws.sqs.AWSClients")
    @patch("app.aws.sqs.get_settings")
    def test_get_queue_attributes(self, mock_settings, MockClients):
        from app.aws.sqs import SQSRepository
        mock_settings.return_value = MagicMock(sqs_analysis_queue="q", sqs_analysis_dlq="dlq")
        mock_client = MagicMock()
        mock_client.sqs.get_queue_url.return_value = {"QueueUrl": "https://sqs.example.com/q"}
        mock_client.sqs.get_queue_attributes.return_value = {
            "Attributes": {"ApproximateNumberOfMessages": "5"}
        }
        MockClients.return_value = mock_client
        repo = SQSRepository()
        attrs = repo.get_queue_attributes()
        assert attrs["ApproximateNumberOfMessages"] == "5"


# ─── EventBridge Repository ───

class TestEventBridgeRepository:
    def test_init(self):
        from app.aws.eventbridge import EventBridgeRepository
        with patch("app.aws.eventbridge.get_settings") as mock_settings, \
             patch("app.aws.eventbridge.AWSClients") as mock_clients:
            mock_settings.return_value = MagicMock(eventbridge_bus_name="emip-events")
            mock_clients.return_value = MagicMock()
            repo = EventBridgeRepository()
            assert repo is not None

    @patch("app.aws.eventbridge.AWSClients")
    @patch("app.aws.eventbridge.get_settings")
    def test_publish_event(self, mock_settings, MockClients):
        from app.aws.eventbridge import EventBridgeRepository
        mock_settings.return_value = MagicMock(eventbridge_bus_name="emip-events")
        mock_client = MagicMock()
        mock_client.events.put_events.return_value = {
            "FailedEntryCount": 0,
            "Entries": [{"EventId": "evt-123"}],
        }
        MockClients.return_value = mock_client
        repo = EventBridgeRepository()
        event_id = repo.publish_event(
            source="emip.pipeline",
            detail_type="Analysis Started",
            detail={"job_id": "job-001"},
        )
        assert event_id == "evt-123"

    @patch("app.aws.eventbridge.AWSClients")
    @patch("app.aws.eventbridge.get_settings")
    def test_publish_event_failure(self, mock_settings, MockClients):
        from app.aws.eventbridge import EventBridgeRepository
        mock_settings.return_value = MagicMock(eventbridge_bus_name="emip-events")
        mock_client = MagicMock()
        mock_client.events.put_events.return_value = {"FailedEntryCount": 1, "Entries": []}
        MockClients.return_value = mock_client
        repo = EventBridgeRepository()
        event_id = repo.publish_event(source="src", detail_type="dt", detail={})
        assert event_id is None


# ─── Checkpoint Manager ───

class TestCheckpointManager:
    def test_save_and_load(self):
        from app.pipeline.state import PipelineState
        from app.services.checkpoint import CheckpointManager
        with patch("app.services.checkpoint.S3Repository") as MockS3, \
             patch("app.services.checkpoint.JobRepository") as MockJobs:
            mock_s3 = MagicMock()
            MockS3.return_value = mock_s3
            MockJobs.return_value = MagicMock()

            mgr = CheckpointManager()
            ps = PipelineState(job_id="job-001")
            ps.mark_started("stage_a")
            ps.mark_completed("stage_a")

            mgr.save("job-001", ps)
            mock_s3.put_object.assert_called_once()

            # Now make load return the saved data
            saved_data = ps.to_dict()
            mock_s3.get_object.return_value = {
                "Body": MagicMock(read=lambda: json.dumps(saved_data).encode())
            }
            loaded = mgr.load("job-001")
            assert loaded is not None
            assert loaded.job_id == "job-001"
            assert "stage_a" in loaded.stages

    def test_has_checkpoint(self):
        from app.services.checkpoint import CheckpointManager
        with patch("app.services.checkpoint.S3Repository") as MockS3, \
             patch("app.services.checkpoint.JobRepository"):
            mock_s3 = MagicMock()
            mock_s3.get_object.side_effect = Exception("not found")
            MockS3.return_value = mock_s3
            mgr = CheckpointManager()
            assert mgr.has_checkpoint("job-001") is False

    def test_no_checkpoint_load(self):
        from app.services.checkpoint import CheckpointManager
        with patch("app.services.checkpoint.S3Repository") as MockS3, \
             patch("app.services.checkpoint.JobRepository"):
            mock_s3 = MagicMock()
            mock_s3.get_object.side_effect = Exception("not found")
            MockS3.return_value = mock_s3
            mgr = CheckpointManager()
            assert mgr.load("nonexistent") is None

    def test_get_resume_stage(self):
        from app.pipeline.state import PipelineState
        from app.services.checkpoint import CheckpointManager
        with patch("app.services.checkpoint.S3Repository") as MockS3, \
             patch("app.services.checkpoint.JobRepository"):
            mock_s3 = MagicMock()
            MockS3.return_value = mock_s3
            mgr = CheckpointManager()
            ps = PipelineState(job_id="job-001")
            ps.mark_started("s1")
            ps.mark_completed("s1")
            ps.current_stage = "s2"
            mock_s3.get_object.return_value = {
                "Body": MagicMock(read=lambda: json.dumps(ps.to_dict()).encode())
            }
            resume = mgr.get_resume_stage("job-001")
            assert resume == "s2"

    def test_clear_checkpoint(self):
        from app.services.checkpoint import CheckpointManager
        with patch("app.services.checkpoint.S3Repository") as MockS3, \
             patch("app.services.checkpoint.JobRepository"):
            mock_s3 = MagicMock()
            MockS3.return_value = mock_s3
            mgr = CheckpointManager()
            mgr.clear_checkpoint("job-001")
            mock_s3.client.delete_object.assert_called_once()


# ─── Event Publishers ───

class TestEventPublishers:
    def test_import_all_functions(self):
        from app.services.events import (
            publish_pipeline_completed,
            publish_pipeline_failed,
            publish_pipeline_started,
            publish_report_generated,
            publish_stage_completed,
            publish_stage_failed,
        )
        assert callable(publish_pipeline_started)
        assert callable(publish_stage_completed)
        assert callable(publish_stage_failed)
        assert callable(publish_pipeline_completed)
        assert callable(publish_pipeline_failed)
        assert callable(publish_report_generated)

    @patch("app.services.events._get_publisher")
    def test_publish_pipeline_started(self, mock_get_pub):
        from app.services.events import publish_pipeline_started
        mock_pub = MagicMock()
        mock_pub.publish_pipeline_event.return_value = "evt-1"
        mock_get_pub.return_value = mock_pub
        result = publish_pipeline_started("job-001", total_stages=10)
        assert result == "evt-1"
        mock_pub.publish_pipeline_event.assert_called_once_with(
            "pipeline.started", "job-001", {"schema_version": "1.0.0", "correlation_id": "job-001", "started_stages": 10}
        )


# ─── Notifications ───

class TestNotifications:
    def test_import(self):
        from app.services.notifications import (
            notify_analysis_completed,
            notify_analysis_failed,
        )
        assert callable(notify_analysis_completed)
        assert callable(notify_analysis_failed)


# ─── Worker Handler ───

class TestWorkerHandler:
    def test_import(self):
        from worker_handler import handler
        assert callable(handler)

    def test_handler_empty_records(self):
        from worker_handler import handler
        result = handler({"Records": []}, MagicMock())
        assert result["statusCode"] == 200
        assert result["body"]["processed"] == 0

    @patch("app.services.workers.analysis_worker.handle_analysis_job")
    def test_handler_analysis_event(self, mock_handle):
        from worker_handler import handler
        mock_handle.return_value = {"status": "completed"}
        event = {
            "Records": [{
                "body": json.dumps({"job_id": "job-001", "action": "start_analysis"}),
                "messageId": "msg-001",
            }]
        }
        result = handler(event, MagicMock())
        assert result["statusCode"] == 200
        assert result["body"]["processed"] == 1
        mock_handle.assert_called_once_with("job-001", resume_from=None)

    @patch("app.services.workers.report_worker.handle_report_job")
    def test_handler_report_event(self, mock_handle):
        from worker_handler import handler
        mock_handle.return_value = {"status": "completed"}
        event = {
            "Records": [{
                "body": json.dumps({"job_id": "job-002", "action": "generate_report", "report_type": "full"}),
                "messageId": "msg-002",
            }]
        }
        result = handler(event, MagicMock())
        assert result["statusCode"] == 200
        mock_handle.assert_called_once_with("job-002", report_type="full")

    def test_handler_missing_job_id_redrives_to_dlq(self):
        from worker_handler import handler
        event = {
            "Records": [{
                "body": json.dumps({"action": "start_analysis"}),
                "messageId": "msg-003",
            }]
        }
        with pytest.raises(RuntimeError):
            handler(event, MagicMock())

    def test_handler_unknown_action_redrives_to_dlq(self):
        from worker_handler import handler
        event = {
            "Records": [{
                "body": json.dumps({"job_id": "job-001", "action": "unknown"}),
                "messageId": "msg-004",
            }]
        }
        with pytest.raises(RuntimeError):
            handler(event, MagicMock())

    @patch("app.services.workers.analysis_worker.handle_analysis_job")
    def test_handler_failure_raises_for_sqs_retry(self, mock_handle):
        from worker_handler import handler
        mock_handle.side_effect = Exception("boom")
        event = {
            "Records": [{
                "body": json.dumps({"job_id": "job-005", "action": "start_analysis"}),
                "messageId": "msg-005",
            }]
        }
        # Returning 200 would make SQS delete the message; raising keeps it for
        # retries so maxReceiveCount: 3 redrives it to the DLQ.
        with pytest.raises(RuntimeError):
            handler(event, MagicMock())
