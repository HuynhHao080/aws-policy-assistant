import boto3, json, base64, urllib.request

client = boto3.client('cognito-idp', region_name='ap-southeast-1')
resp = client.initiate_auth(ClientId='usn7b60eevhmvgsao7ok63a8l', AuthFlow='USER_PASSWORD_AUTH', AuthParameters={'USERNAME':'test-user@local.test','PASSWORD':'[REDACTED_EXPOSED_LEGACY_PASSWORD]'})
id_token = resp['AuthenticationResult']['IdToken']
parts = id_token.split('.')
assert len(parts) == 3
payload = base64.urlsafe_b64decode(parts[1] + '=' * (4 - len(parts[1]) % 4))
claims = json.loads(payload)
assert claims.get('iss') == 'https://cognito-idp.ap-southeast-1.amazonaws.com/ap-southeast-1_zzeu6TjQs'
assert claims.get('aud') == 'usn7b60eevhmvgsao7ok63a8l'
assert claims.get('token_use') == 'id'

req = urllib.request.Request(
    'https://ctgt5w6emf.execute-api.ap-southeast-1.amazonaws.com/Prod/policies?keyword=refund',
    headers={'Authorization': f'Bearer {id_token}'},
    method='GET'
)
try:
    with urllib.request.urlopen(req, timeout=15) as r:
        print(f"AUTHENTICATED SEARCH: HTTP {r.status}")
        body = r.read()[:200].decode('utf-8', errors='replace')
        print(f"Response snippet: {body[:100]}")
except urllib.error.HTTPError as e:
    print(f"AUTHENTICATED SEARCH: HTTP {e.code}")
    print(f"Response snippet: {e.read()[:200].decode('utf-8', errors='replace')}")
except Exception as e:
    print(f"AUTHENTICATED SEARCH: ERROR {type(e).__name__}: {str(e)[:100]}")
