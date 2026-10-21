import urllib.request, urllib.error, json, os

with open('jwt_token.tmp') as f:
    token = f.read().strip()

req = urllib.request.Request(
    'https://ctgt5w6emf.execute-api.ap-southeast-1.amazonaws.com/Prod/policies/POL-001',
    headers={'Authorization': f'Bearer {token}'}
)
try:
    with urllib.request.urlopen(req, timeout=15) as r:
        print('AUTHENTICATED POLICY LOOKUP:', r.status)
        body = r.read()[:200].decode('utf-8', errors='replace')
        print('Response snippet:', body[:100])
except urllib.error.HTTPError as e:
    print('AUTHENTICATED POLICY LOOKUP:', e.code)
    print('Response snippet:', e.read()[:200].decode('utf-8', errors='replace'))
except Exception as e:
    print('AUTHENTICATED POLICY LOOKUP: ERROR —', type(e).__name__, str(e)[:100])
