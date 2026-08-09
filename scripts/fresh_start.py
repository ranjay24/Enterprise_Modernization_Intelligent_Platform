"""Fresh start script — deletes all jobs and data from DynamoDB and S3.

Usage:
    python scripts/fresh_start.py
    python scripts/fresh_start.py --force   # bypass the prod/staging guard

This will:
1. Delete all job records from DynamoDB
2. Delete all job data from S3 (artifacts, analysis results, uploads)
3. Clear local checkpoint files

Refuses to run when ENVIRONMENT is prod or staging unless --force is given.
"""

import sys
import os
import shutil
import argparse

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.core.settings import get_settings
from app.aws.clients import AWSClients


def main():
    settings = get_settings()
    clients = AWSClients(settings=settings)

    print("=" * 60)
    print("  EMIP Fresh Start — Deleting All Data")
    print("=" * 60)

    # 1. Delete all DynamoDB job records
    print("\n[1/3] Deleting DynamoDB job records...")
    try:
        table = clients.dynamodb.Table(settings.dynamodb_jobs_table)
        response = table.scan()
        items = response.get("Items", [])
        count = 0
        for item in items:
            table.delete_item(Key={"job_id": item["job_id"]})
            count += 1
        print(f"  Deleted {count} job records from {settings.dynamodb_jobs_table}")
    except Exception as e:
        print(f"  Warning: DynamoDB delete failed: {e}")

    # 2. Delete all S3 objects under jobs/
    print("\n[2/3] Deleting S3 job data...")
    try:
        paginator = clients.s3.get_paginator("list_objects_v2")
        total_deleted = 0
        for page in paginator.paginate(Bucket=settings.s3_bucket, Prefix="jobs/"):
            objects = page.get("Contents", [])
            if objects:
                to_delete = [{"Key": obj["Key"]} for obj in objects]
                for i in range(0, len(to_delete), 1000):
                    batch = to_delete[i:i + 1000]
                    clients.s3.delete_objects(
                        Bucket=settings.s3_bucket,
                        Delete={"Objects": batch, "Quiet": True},
                    )
                total_deleted += len(objects)
        print(f"  Deleted {total_deleted} S3 objects from {settings.s3_bucket}/jobs/")
    except Exception as e:
        print(f"  Warning: S3 delete failed: {e}")

    # 3. Clear local checkpoint files
    print("\n[3/3] Clearing local checkpoint files...")
    checkpoint_dir = os.path.join(os.path.dirname(__file__), "..", "backend", ".checkpoints")
    if os.path.exists(checkpoint_dir):
        shutil.rmtree(checkpoint_dir)
        print(f"  Deleted {checkpoint_dir}")
    else:
        print("  No local checkpoints found")

    print("\n" + "=" * 60)
    print("  Fresh start complete! All data has been deleted.")
    print("  You can now upload new codebases from the UI.")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="EMIP fresh start — delete all data")
    parser.add_argument("--force", action="store_true", help="Bypass the prod/staging guard")
    args = parser.parse_args()

    environment = get_settings().environment
    if environment in ("prod", "staging") and not args.force:
        print(
            f"Refusing to run: ENVIRONMENT={environment!r} is a protected environment.\n"
            "Fresh start would delete ALL jobs, analysis data and S3 objects.\n"
            "Re-run with --force only if you are certain."
        )
        sys.exit(1)

    confirm = input("\nThis will DELETE ALL jobs and analysis data. Type 'yes' to confirm: ")
    if confirm.lower() != "yes":
        print("Aborted.")
        sys.exit(0)
    main()
