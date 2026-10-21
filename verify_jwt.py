import boto3, json, base64, urllib.request
client = boto3.client('cognito-idp', region_name='ap-southeast-1')
resp = client.initiate_auth(ClientId='usn7b60eevhmvgsao7ok63a8l', AuthFlow='USER_PASSWORD_AUTH', AuthParameters={'USERNAME':'test-user@local.test','PASSWORD':'[REDACTED_EXPOSED_LEGACY_PASSWORD]'})
id_token = resp['AuthenticationResult']['IdToken']
with open('jwt_token.tmp', 'w') as f: f.write(id_token)
parts = id_token.split('.')
assert len(parts) == 3, f"Expected 3 segments, got {len(parts)}"
payload = base64.urlsafe_b64decode(parts[1] + '=' * (4 - len(parts[1]) % 4))
claims = json.loads(payload)
assert claims.get('iss') == 'https://cognito-idp.ap-southeast-1.amazonaws.com/ap-southeast-1_zzeu6TjQs'
assert claims.get('aud') == 'usn7b60eevhmvgsao7ok63a8l'
assert claims.get('token_use') == 'id'
print("TOKEN_FORMAT_OK")
req = urllib.request.Request('https://ctgt5w6emf.execute-api.ap-southeast-1.amazonaws.com/Prod/policies/POL-001', headers={'Authorization': f'Bearer {id_token}'}, method='GET')
try:
    with urllib.request.urlopen(req, timeout=15) as r:
        print(f"AUTHENTICATED_LOOKUP: HTTP {r.status}")
        body = r.read()[:200].decode('utf-utf-8', errors='replace')
        print(f"RESPONSE_SNIPPET: {body[:100]}")
except urllib.error.HTTPError as e:
    print(f"AUTHENTICATED_LOOKUP: HTTP {e.code}")
    print(f"RESPONSE_SNIPPET: {e.read()[:200].decode('utf-8', errors='replace')}")
except Exception as e:
    print(f"AUTHENTICATED_LOOKUP: ERROR {type(e).__name__}: {str(e)[:100]}")
