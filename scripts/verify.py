"""Run offline acceptance checks and write a sanitized machine-readable summary.

Never deploys, uploads, creates AWS users, or enables live integration tests.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    env=os.environ.copy()
    env["PYTHONUTF8"]="1"
    env.pop("AWS_SAM_STACK_NAME",None)
    env.pop("POLICY_ASSISTANT_ID_TOKEN",None)
    env["PATH"]=str(Path(sys.executable).parent)+os.pathsep+env.get("PATH","")
    env["DEMO_PYTHON"]=sys.executable
    npm=shutil.which("npm.cmd" if os.name=="nt" else "npm")
    sam=shutil.which("sam.cmd" if os.name=="nt" else "sam")
    commands=[("python-lint",[sys.executable,"-m","ruff","check","policy_assistant","scripts","tests","--select","E9,F63,F7,F82"]),
        ("backend-typecheck",[sys.executable,"-m","mypy","--explicit-package-bases","--ignore-missing-imports","--check-untyped-defs","policy_assistant/app.py"]),
        ("frontend-syntax",[shutil.which("node"),"--check","frontend/app.js"]),
        ("backend",[sys.executable,"-B","-m","pytest","tests/unit","-q","-p","no:cacheprovider","--tb=short"]),
        ("live-tests-disabled",[sys.executable,"-B","-m","pytest","tests/integration","-q","-p","no:cacheprovider"]),
        ("frontend",[npm,"test"]),("browser-fixtures",[npm,"run","test:browser"]),
        ("full-stack-local",[npm,"run","test:local"]),("sam-lint",[sam,"validate","--lint"]),("sam-build",[sam,"build"])]
    results=[]
    for name,command in commands:
        print("Checking:",name,flush=True)
        if command[0] is None:
            result={"check":name,"exit_code":127,"result":"Required tool not installed"}
        else:
            start=time.monotonic()
            completed=subprocess.run(command,cwd=ROOT,env=env,text=True,encoding="utf-8",errors="replace",capture_output=True)
            result={"check":name,"exit_code":completed.returncode,"seconds":round(time.monotonic()-start,2)}
            print(completed.stdout,flush=True)
            if completed.returncode:print(completed.stderr,flush=True)
        results.append(result)
    output=ROOT/"docs/evidence/offline-acceptance.json"
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps({"scope":"offline; real application with simulated AWS; live tests disabled",
        "python":sys.version.split()[0],"checks":results,"passed":all(item["exit_code"]==0 for item in results)},indent=2)+"\n",encoding="utf-8")
    return 0 if all(item["exit_code"]==0 for item in results) else 1

if __name__=="__main__":raise SystemExit(main())
