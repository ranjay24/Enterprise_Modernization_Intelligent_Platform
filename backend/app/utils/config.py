import os

from dotenv import load_dotenv

load_dotenv()

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
S3_BUCKET = os.getenv("S3_BUCKET", "emip-artifacts-dev")
DYNAMODB_TABLE = os.getenv("DYNAMODB_TABLE", "emip-jobs-dev")
BEDROCK_MODEL_PRIMARY = os.getenv("BEDROCK_MODEL_PRIMARY", "amazon.nova-pro-v1:0")
BEDROCK_MODEL_FALLBACK = os.getenv("BEDROCK_MODEL_FALLBACK", "amazon.nova-lite-v1:0")
BEDROCK_MODEL_CODEGEN = os.getenv("BEDROCK_MODEL_CODEGEN", "amazon.nova-pro-v1:0")
MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", "100"))
MAX_TOKENS_MODEL = 8000
