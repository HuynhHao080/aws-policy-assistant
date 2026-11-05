"""Compact multilingual vectors: no continuously running vector database."""
import base64
import json
import math
import os
from array import array


def model_id():
    return os.environ.get("EMBEDDING_MODEL_ID", "")


def embed(service, texts, kind):
    vectors = []
    for start in range(0, len(texts), 96):
        batch = texts[start:start + 96]
        response = service.client("bedrock-runtime").invoke_model(modelId=model_id(), contentType="application/json", accept="application/json", body=json.dumps({"texts": [t[:2048] for t in batch], "input_type": kind, "truncate": "END", "embedding_types": ["int8"]}))
        try:
            result = json.loads(response["body"].read())
        finally:
            response["body"].close()
        values = result.get("embeddings", {}).get("int8")
        if not isinstance(values, list) or len(values) != len(batch):
            raise ValueError("Invalid embedding response")
        for vector in values:
            if len(vector) != 1024 or any(not isinstance(value, int) or not -128 <= value <= 127 for value in vector):
                raise ValueError("Invalid embedding vector")
            vectors.append(base64.b64encode(array("b", vector).tobytes()).decode())
    return vectors


def similarity(first, second):
    left, right = array("b", base64.b64decode(first)), array("b", base64.b64decode(second))
    if len(left) != 1024 or len(right) != 1024:
        return 0
    denominator = math.sqrt(sum(v * v for v in left) * sum(v * v for v in right))
    return sum(a * b for a, b in zip(left, right)) / denominator if denominator else 0
