# Source handover and local reproduction

The canonical application is the existing `C:\Users\accli\Documents\Project\policy-assistant`. Source archives are review snapshots, separate from deployed Lambda ZIPs and the separate internship worklog. They do not carry live login/configuration, AWS credentials or Git history. A local archive does not update public Git or GitHub Pages.

## Build and check a review snapshot

```powershell
python scripts/source_bundle.py create --output .deployment/my-review/source.zip
python scripts/source_bundle.py verify --archive .deployment/my-review/source.zip --extract-to .deployment/my-review/fresh
```

Choose unused output/extraction paths: existing archives/folders are never overwritten. Each eligible file has a SHA256 and byte length in `SOURCE-MANIFEST.json`. ZIP timestamps/permissions/order are normalized; identical source bytes produce identical archives. Verification checks every file and rejects missing, modified or extra files, unsafe paths, Windows device names, symlinks and case collisions before extraction. This establishes internal consistency, not authenticity against an attacker able to replace both files and manifest; compare the whole archive SHA256 through a trusted channel.

Only explicit source roots and extensions are included. Excluded: `.git`, `.aws-sam`, `.deployment`, node_modules/dist, caches, actual frontend config, root authentication/session/signed-URL/download/PDF artifacts, the reference submodule and separate worklog. Basic key/JWT/private-key/signed-URL patterns stop export without printing matched values. Pattern checks cannot prove absence of all secrets or customer data. Review the manifest/content before external sharing. The tool makes no Git/cloud/model calls and performs no publication.

## Windows: use the Lambda runtime, not the default Python

The isolated check initially failed because `sam build` found Python3.13 although the template requests Python3.12. Resolve the actual3.12 executable and place its directory first in the **current terminal's** PATH:

```powershell
# Use an installed Python3.12. If py is unavailable, supply its actual python.exe path.
$runtimePython = (& py -3.12 -c 'import sys; print(sys.executable)').Trim()
if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $runtimePython)) { throw 'Install/select Python 3.12 first' }
$env:Path = (Split-Path -Parent $runtimePython) + ';' + $env:Path
& $runtimePython --version

# Run inside the extracted source folder.
& $runtimePython -m venv .venv
& ./.venv/Scripts/python.exe -m pip install -r policy_assistant/requirements.txt -r tests/requirements.txt
# Optional dated dependency snapshot instead of resolving current ranges:
# & ./.venv/Scripts/python.exe -m pip install -r docs/reproducibility/requirements-verified-2026-11-05.txt

# Local verification: keep opt-in live tests disabled; never paste tokens here.
$env:AWS_SAM_STACK_NAME = $null
$env:POLICY_ASSISTANT_ID_TOKEN = $null
$env:AWS_EC2_METADATA_DISABLED = 'true'
$env:SAM_CLI_TELEMETRY = '0'
& ./.venv/Scripts/python.exe -m pytest tests -q
npm ci --prefix frontend --ignore-scripts
npm run build --prefix frontend
npm test --prefix frontend
sam build --template-file template.yaml
sam validate --lint --region ap-southeast-1
```

Check each command's exit code and stop on failure; the example is a command sequence, not an unattended fail-fast release script. The dated Python snapshot has exact versions, not package hashes or proof of compatibility with every platform. SAM resolves its runtime dependencies separately. Use `frontend/package-lock.json` for browser dependencies. The actual isolated check used Python3.12, Node26.3.0 and SAM1.168.0.

The exported frontend config example is intentionally unconfigured and disables sign-in. A successful local build is not hosted-login or AWS acceptance. Fresh-account deployment, cross-account permissions and rollback/restore remain separate tasks; never run deploy/sync/live-test commands merely to reproduce the local checks. Current canonical-stack deployment instructions are in the production runbook.

Actual isolated results and limitations: [verification, 5 November 2026](VERIFICATION-2026-11-05.md).
