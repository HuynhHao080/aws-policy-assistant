"""Read-only model readiness check for the Singapore API endpoint."""
import boto3

PROFILE = "global.anthropic.claude-haiku-5-5"
BASE_MODEL = "anthropic.claude-haiku-5-5"
client = boto3.client("bedrock", region_name="ap-southeast-1")
profile = client.get_inference_profile(inferenceProfileIdentifier=PROFILE)
access = client.get_foundation_model_availability(modelId=BASE_MODEL)
if profile["status"] != "ACTIVE" or access["authorizationStatus"] != "AUTHORIZED":
    raise SystemExit("Haiku 5.5 profile is unavailable or unauthorized")
print(PROFILE, profile["status"], access["authorizationStatus"])
