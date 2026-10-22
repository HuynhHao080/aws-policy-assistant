"""Create a source handover and static frontend ZIP without accessing AWS."""
import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

ROOT=Path(__file__).resolve().parents[1]


def build(output):
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=True)
    extensions={".py",".md",".txt",".json",".js",".cjs",".html",".css",".yaml",".yml",".toml",".mmd",".ps1",".png",".patch"}
    selected=[]
    for directory in ("policy_assistant","frontend","tests","scripts","docs","sample_data",".github"):
        for file in (ROOT/directory).rglob("*"):
            if file.is_file() and file.suffix in extensions and not any(part.startswith(("__pycache__",".pytest_cache")) for part in file.relative_to(ROOT).parts):selected.append(file)
    for name in ("README.md","PROJECT_SUMMARY.md","template.yaml","samconfig.toml","architecture.mmd","package.json","package-lock.json",".gitignore"):
        selected.append(ROOT/name)
    manifest={str(file.relative_to(ROOT)).replace("\\","/"):hashlib.sha256(file.read_bytes()).hexdigest() for file in sorted(set(selected))}
    source=output/"policy-assistant-source.zip"
    with ZipFile(source,"w",ZIP_DEFLATED) as archive:
        for name in manifest:archive.write(ROOT/name,name)
    frontend=output/"policy-assistant-frontend.zip"
    with ZipFile(frontend,"w",ZIP_DEFLATED) as archive:
        for name in ("index.html","app.js","styles.css","config.json"):archive.write(ROOT/"frontend"/name,name)
    archives=[source,frontend]
    worklog=ROOT.parent/"aws-internship-worklog"
    if worklog.is_dir():
        worklog_files=[]
        for directory in ("content","static","layouts","archetypes","themes",".github"):
            for file in (worklog/directory).rglob("*"):
                if file.is_file() and not any(part in {".git","node_modules","__pycache__",".DS_Store"} for part in file.relative_to(worklog).parts):worklog_files.append(file)
        worklog_files += [worklog/"config.toml",worklog/".gitignore"]
        worklog_files=[file for file in sorted(set(worklog_files)) if file.exists()]
        worklog_archive=output/"aws-internship-worklog-source.zip"
        with ZipFile(worklog_archive,"w",ZIP_DEFLATED) as archive:
            for file in worklog_files:archive.write(file,str(file.relative_to(worklog)).replace("\\","/"))
        bundle=output/"policy-assistant-complete-project.zip"
        with ZipFile(bundle,"w",ZIP_DEFLATED) as archive:
            for name in manifest:archive.write(ROOT/name,"application/"+name)
            for file in worklog_files:archive.write(file,"worklog/"+str(file.relative_to(worklog)).replace("\\","/"))
            archive.writestr("START_HERE.md", "# Policy Assistant complete MVP v1\n\nApplication: application/README.md. On Windows run pwsh -File application/scripts/start-demo.ps1. For other environments use Python 3.12 with requirements in the application. Report: worklog/ (Hugo 0.167.0). Offline acceptance is recorded under application/docs/evidence/. This is an uncommitted source handover, not a deployed or live-certified service. Read application/docs/operations.md before any AWS operation. Previously committed credentials still require rotation; Git history is not included.\n")
        archives += [worklog_archive,bundle]
    result={"scope":"Local handover only; not deployed or live-certified", "files":manifest,
        "archives":{file.name:hashlib.sha256(file.read_bytes()).hexdigest() for file in archives}}
    (output/"manifest.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print("Created source ZIP, frontend ZIP and SHA-256 manifest in",output)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",default=str(ROOT/"dist"/"handover"))
    args=parser.parse_args();build(args.output)

if __name__=="__main__":main()
