"""Import the Lambda module with offline credentials before test collection."""
import os
from unittest.mock import patch

with patch.dict(os.environ, {
    "AWS_ACCESS_KEY_ID": "testing", "AWS_SECRET_ACCESS_KEY": "testing",
    "AWS_DEFAULT_REGION": "ap-southeast-1", "AWS_EC2_METADATA_DISABLED": "true",
}):
    from policy_assistant import app  # noqa: F401
