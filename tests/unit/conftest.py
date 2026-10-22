"""Import the handler without consulting workstation credentials or metadata.

The temporary environment is restored before collection of live tests. Individual
unit fixtures supply their own moto services/credentials.
"""
import os
import boto3
from unittest.mock import patch

previous_session = boto3.DEFAULT_SESSION
with patch.dict(os.environ, {"AWS_ACCESS_KEY_ID": "testing", "AWS_SECRET_ACCESS_KEY": "testing",
    "AWS_SESSION_TOKEN": "testing", "AWS_DEFAULT_REGION": "ap-southeast-1",
    "AWS_REGION": "ap-southeast-1", "AWS_EC2_METADATA_DISABLED": "true"}):
    from policy_assistant import app  # noqa: F401
boto3.DEFAULT_SESSION = previous_session
