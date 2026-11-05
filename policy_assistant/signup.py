"""Bound public account creation before Cognito sends verification email."""
import os
import time
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError


def handler(event, context):
    if event.get("triggerSource") != "PreSignUp_SignUp":
        return event
    stamp = datetime.now(timezone.utc)
    client = boto3.client("dynamodb", region_name=os.environ.get("AWS_REGION", "ap-southeast-1"))
    updates = []
    for key, limit in ((f"global#signup#{stamp:%Y-%m}", 100), ("global#signup#lifetime", 1000)):
        updates.append({"Update": {"TableName": os.environ["USAGE_TABLE_NAME"], "Key": {"pk": {"S": key}}, "UpdateExpression": "ADD #n :one", "ConditionExpression": "attribute_not_exists(#n) OR #n < :limit", "ExpressionAttributeNames": {"#n": "count"}, "ExpressionAttributeValues": {":one": {"N": "1"}, ":limit": {"N": str(limit)}}}})
    try:
        client.transact_write_items(TransactItems=updates)
    except ClientError:
        raise ValueError("Registration is temporarily unavailable. Please try again later.") from None
    return event
