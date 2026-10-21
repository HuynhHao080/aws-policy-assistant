with open('docs/evidence-index.md', 'r', encoding='utf-8') as f:
    content = f.read()

old = '''## Deployment Evidence

| Evidence | Path | Supports | Status |
|----------|------|----------|--------|
| CloudFormation stack | AWS Console / `aws cloudformation describe-stacks` | Stack `policy-assistant`, status `UPDATE_COMPLETE`, region `ap-southeast-1` | Historical — verified during Phase L deployment |'''

new = '''## CloudWatch Monitoring Evidence

| Evidence | Path | Supports | Status |
|----------|------|----------|--------|
| CloudWatch Error Alarm | `template.yaml` | Lambda Errors > 0 alarm | Local — defined but NOT deployed |
| CloudWatch Duration Alarm | `template.yaml` | Lambda Duration > 5000ms alarm | Local — defined but NOT deployed |
| CloudWatch Dashboard | `template.yaml` | Lambda metrics dashboard (Invocations, Errors, Duration, Throttles) | Local — defined but NOT deployed |

## Deployment Evidence

| Evidence | Path | Supports | Status |
|----------|------|----------|--------|
| CloudFormation stack | AWS Console / `aws cloudformation describe-stacks` | Stack `policy-assistant`, status `UPDATE_COMPLETE`, region `ap-southeast-1` | Historical — verified during Phase L deployment |'''

if old in content:
    content = content.replace(old, new, 1)
    with open('docs/evidence-index.md', 'w', encoding='utf-8') as f:
        f.write(content)
    print('SUCCESS: Updated evidence-index.md')
else:
    print('FAILED: Could not find old text')
    idx = content.find('## Deployment Evidence')
    if idx >= 0:
        print(repr(content[idx:idx+200]))
