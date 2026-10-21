import boto3, json, base64, urllib.request, urllib.error, os, time

# Step 1: Obtain fresh IdToken
client = boto3.client('cognito-idp', region_name='ap-southeast-1')
resp = client.initiate_auth(ClientId='usn7b60eevhmvgsao7ok63a8l', AuthFlow='USER_PASSWORD_AUTH', AuthParameters={'USERNAME':'test-user@local.test','PASSWORD':'[REDACTED_EXPOSED_LEGACY_PASSWORD]'})
id_token = resp['AuthenticationResult']['IdToken']
parts = id_token.split('.')
assert len(parts) == 3, f"Expected 3 JWT segments, got {len(parts)}"
payload = base64.urlsafe_b64decode(parts[1] + '=' * (4 - len(parts[1]) % 4))
claims = json.loads(payload)
assert claims.get('iss') == 'https://cognito-idp.ap-southeast-1.amazonaws.com/ap-southeast-1_zzeu6TjQs'
assert claims.get('aud') == 'usn7b60eevhmvgsao7ok63a8l'
assert claims.get('token_use') == 'id'
print(f"TOKEN_OK: iss={claims.get('iss')[:50]}..., aud={claims.get('aud')}, token_use={claims.get('token_use')}, exp={claims.get('exp')}")

API_BASE = 'https://ctgt5w6emf.execute-api.ap-southeast-1.amazonaws.com/Prod'

# Step 2: POST /documents/upload-session
print("\n=== Step 1: POST /documents/upload-session ===")
req = urllib.request.Request(
    f'{API_BASE}/documents/upload-session',
    headers={'Authorization': f'Bearer {id_token}'},
    method='POST'
)
try:
    with urllib.request.urlopen(req, timeout=15) as r:
        body = json.loads(r.read().decode('utf-8'))
        print(f"HTTP {r.status}: {body}")
        doc_id = body['doc_id']
        upload_url = body['upload_url']
        print(f"doc_id={doc_id}")
        print(f"upload_url={upload_url[:60]}...")
except urllib.error.HTTPError as e:
    print(f"HTTP {e.code}: {e.read()[:200].decode('utf-8', errors='replace')}")
    raise

# Step 3: Upload file to presigned URL
print("\n=== Step 2: Upload file to S3 ===")
test_content = b"Test document content for Policy Assistant E2E verification."
req = urllib.request.Request(
    upload_url,
    data=test_content,
    headers={'Content-Type': 'application/pdf'},
    method='PUT'
)
try:
    with urllib.request.urlopen(req, timeout=15) as r:
        print(f"Upload HTTP {r.status}")
except urllib.error.HTTPError as e:
    print(f"Upload HTTP {e.code}: {e.read()[:200].decode('utf-8', errors='replace')}")
    raise

# Step 4: POST /documents/submit
print("\n=== Step 3: POST /documents/submit ===")
req = urllib.request.Request(
    f'{API_BASE}/documents/submit',
    headers={'Authorization': f'Bearer {id_token}', 'Content-Type': 'application/json'},
    data=json.dumps({'doc_id': doc_id, 's3_key': f'uploads/{doc_id}/document'}).encode('utf-8'),
    method='POST'
)
try:
    with urllib.request.urlopen(req, timeout=15) as r:
        body = json.loads(r.read().decode('utf-8'))
        print(f"HTTP {r.status}: {body}")
except urllib.error.HTTPError as e:
    print(f"HTTP {e.code}: {e.read()[:200].decode('utf-8', errors='replace')}")
    raise

# Step 5: Poll GET /documents/{doc_id}/status
print("\n=== Step 4: GET /documents/{doc_id}/status ===")
for i in range(10):
    req = urllib.request.Request(
        f'{API_BASE}/documents/{doc_id}/status',
        headers={'Authorization': f'Bearer {id_token}'},
        method='GET'
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            body = json.loads(r.read().decode('utf-8'))
            print(f"HTTP {r.status}: {body}")
            if body.get('status') == 'processed':
                print("Document processing complete!")
                break
            elif body.get('status') == 'failed':
                print("Document processing failed!")
                break
            else:
                print("Waiting for processing...")
                time.sleep(2)
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code}: {e.read()[:200].decode('utf-8', errors='replace')}")
        break

# Step 6: GET /documents/{doc_id}/download
print("\n=== Step 5: GET /documents/{doc_id}/download ===")
req = urllib.request.Request(
    f'{API_BASE}/documents/{doc_id}/download',
    headers={'Authorization': f'Bearer {id_token}'},
    method='GET'
)
try:
    with urllib.request.urlopen(req, timeout=15) as r:
        body = json.loads(r.read().decode('utf-8'))
        print(f"HTTP {r.status}: {body}")
        download_url = body.get('download_url')
        if download_url:
            # Download the file
            req2 = urllib.request.Request(download_url, method='GET')
            with urllib.request.urlopen(req2, timeout=15) as r2:
                downloaded_content = r2.read()
                print(f"Downloaded {len(downloaded_content)} bytes")
                print(f"Content matches: {downloaded_content == test_content}")
except urllib.error.HTTPError as e:
    print(f"HTTP {e.code}: {e.read()[:200].decode('utf-8', errors='replace')}")
