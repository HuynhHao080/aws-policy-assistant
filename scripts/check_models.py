"""Minimal billable inference probe using synthetic text only; never logs vectors."""
import json
import boto3
from botocore.config import Config

client = boto3.client("bedrock-runtime", region_name="ap-southeast-1", config=Config(connect_timeout=5, read_timeout=45, retries={"max_attempts": 1}))
response = client.invoke_model(modelId="cohere.embed-multilingual-v3", contentType="application/json", accept="application/json", body=json.dumps({"texts": ["Synthetic policy: refunds within 30 days."], "input_type": "search_document", "embedding_types": ["int8"], "truncate": "END"}))
result = json.loads(response["body"].read())
response["body"].close()
assert len(result["embeddings"]["int8"][0]) == 1024
print("Cohere multilingual embedding: PASS (1024 dimensions)")
result = client.converse(modelId="apac.amazon.nova-micro-v1:0", messages=[{"role": "user", "content": [{"text": "Reply only with OK."}]}], inferenceConfig={"maxTokens": 8, "temperature": 0})
assert result["output"]["message"]["content"]
print("Nova Micro inference: PASS; usage:", json.dumps(result.get("usage", {})))
