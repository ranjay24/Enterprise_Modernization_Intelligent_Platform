import os
from dotenv import load_dotenv

load_dotenv()

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
S3_BUCKET = os.getenv("S3_BUCKET", "emip-artifacts")
DYNAMODB_TABLE = os.getenv("DYNAMODB_TABLE", "emip-jobs")
BEDROCK_MODEL_PRIMARY = os.getenv("BEDROCK_MODEL_PRIMARY", "anthropic.claude-haiku-4-5-20251001-v1:0")
BEDROCK_MODEL_FALLBACK = os.getenv("BEDROCK_MODEL_FALLBACK", "anthropic.claude-sonnet-4-5-20250929-v1:0")
BEDROCK_MODEL_CODEGEN = os.getenv("BEDROCK_MODEL_CODEGEN", "anthropic.claude-opus-4-5-20250929-v1:0")
MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", "100"))
MAX_TOKENS_HAIKU = 80000
MAX_TOKENS_OPUS = 180000
