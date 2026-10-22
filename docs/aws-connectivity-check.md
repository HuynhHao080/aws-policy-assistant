# Read-only AWS connectivity recovery

Latest round: 2026-10-21 07:47â€“07:49 UTC. Authenticated STS and CloudFormation calls returned ConnectTimeoutError. DNS resolved all endpoints; direct CloudFormation/S3 TCP/TLS succeeded, while STS connection timed out. This does not establish a root cause, valid credentials, or working signed API access. No additional automatic attempts are scheduled.

## Checks on the workstation

Run these from the same terminal/network as the project. They do not change AWS resources:

```powershell
Resolve-DnsName sts.ap-southeast-1.amazonaws.com
Test-NetConnection sts.ap-southeast-1.amazonaws.com -Port 443
Test-NetConnection cloudformation.ap-southeast-1.amazonaws.com -Port 443
Test-NetConnection s3.ap-southeast-1.amazonaws.com -Port 443
Get-Date -AsUTC
```

Check the active VPN/network route and approved outbound HTTPS rules with the network administrator. Check whether the network requires an approved HTTPS proxy; the unsigned diagnostic detected no proxy. Inspect proxy settings locally without copying values containing usernames/passwords into evidence. Do not disable TLS verification or broadly disable the firewall. DNS/TCP success alone does not prove authenticated SDK access. A local clock problem typically produces a signature error rather than proving the observed connection timeout's cause.

After a network/configuration change, make **one bounded** identity attempt. Keep the complete identity output private and display only its suffix:

```powershell
$savedReviewAttempts = $env:AWS_MAX_ATTEMPTS
try {
    $env:AWS_MAX_ATTEMPTS = '1'
    $reviewAccount = aws sts get-caller-identity --region ap-southeast-1 --query Account --output text --no-cli-pager --cli-connect-timeout 5 --cli-read-timeout 10 2>$null
    if ($LASTEXITCODE -eq 0 -and $reviewAccount -match '^\d{12}$') {
        'Account suffix: ' + $reviewAccount.Substring(8)
    } else {
        'BLOCKED: STS did not return a verified account; stop and record the UTC time.'
    }
} finally {
    $env:AWS_MAX_ATTEMPTS = $savedReviewAttempts
    Remove-Variable reviewAccount -ErrorAction SilentlyContinue
}
```

If identity succeeds, compare suffix 0098 and the exact private expected account. From `policy-assistant-github`, run:

```powershell
.venv/Scripts/python.exe -m scripts.verify_review_artifact
.venv/Scripts/python.exe -m scripts.review_test_candidate
```

These tools read only. The artifact tool checks the exact candidate IDs/ARN account/region/stack, 45 Add-only actions, original/processed template equality, IAM/SQS/S3 controls and all three functions' actual S3 ZIP content against built file SHA-256 hashes. It never uses presigned URLs or treats ETag as SHA-256. An assertion failure is FAIL, not a connectivity success. Retain the evidence and stop on a fresh timeout; do not run a loop. Review the resulting JSON before changing the readiness decision. Successful predeployment verification still does not authorize executing the change set.

Do not publish CLI `--debug`, SDK raw errors, environment dumps, credentials, Authorization headers, JWTs, passwords or signed URLs. Evidence should contain safe error classes, UTC times, masked identities and explicit VERIFIED/BLOCKED/NOT_RUN states.


## Windows configuration review — 2026-10-21 07:53:42–07:54:04 UTC

AWS CLI 2.36.17 is available on Windows 11. No environment variable names matching PROXY/AWS_ENDPOINT/AWS_CA_BUNDLE were present. The single local AWS config profile had no endpoint, CA bundle or proxy override detected. urllib found no proxy; the inspected Windows Internet Settings flags/values did not indicate an enabled proxy or PAC URL. These checks do not exclude every system/network policy or endpoint-security mechanism. Default region is us-west-2; this project explicitly selects ap-southeast-1. No region/configuration/credentials changes were made.

DNS resolved all three regional endpoints. Direct STS and CloudFormation connections timed out; S3 TCP 443/TLS 1.3 succeeded. Connectivity is intermittent across endpoints compared with the previous sample. **Root cause remains UNDETERMINED.** There is no evidence to classify the error as IAM AccessDenied, expired credentials or an invalid CA certificate. Potential network route, VPN, egress/firewall or required-proxy issues need review by the network owner; none is confirmed.

Because the prerequisite STS/CloudFormation connections remain blocked, **no signed AWS API call was retried in this round**. Latest AVAILABLE/45 Add evidence remains historical. Preserve `evidence/aws-windows-network-review.json`, ask the network administrator to check access to the named endpoints on TCP 443, then use the bounded identity check above only after an actual connectivity/configuration change. Do not change credentials or disable certificate verification to work around a connection timeout.


## Recovery observed after owner-reported 4G switch

2026-10-21 08:07:36–08:07:38 UTC: all three endpoints passed direct TCP 443 and TLS verification from the execution environment. Subsequent signed STS/CloudFormation calls and S3 GetObject succeeded during 2026-10-21T08:07:43.948327+00:00 to 2026-10-21T08:08:59.475170+00:00. This establishes operational recovery during that window, not proof of the previous root cause. No credentials, proxy, CA or TLS verification settings were changed. See `evidence/aws-4g-connectivity.json` and `evidence/aws-final-readiness.json`. No execution or deployment is authorized by connectivity recovery.
