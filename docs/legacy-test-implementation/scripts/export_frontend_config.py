"""Export public deployment outputs to frontend configuration. Read-only AWS call.

No JWTs, passwords or presigned URLs are read or exported.
"""
import argparse
import json
from pathlib import Path
import boto3


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stack",required=True)
    parser.add_argument("--region",default="ap-southeast-1")
    parser.add_argument("--output",default="frontend/config.json")
    args=parser.parse_args()
    try:
        stack=boto3.client("cloudformation",region_name=args.region).describe_stacks(StackName=args.stack)["Stacks"][0]
        outputs={x["OutputKey"]:x["OutputValue"] for x in stack["Outputs"]}
        config={"mode":"aws","apiBase":outputs["PolicyAssistantApiUrl"].rstrip("/"),
            "region":args.region,"clientId":outputs["CognitoClientId"]}
        Path(args.output).write_text(json.dumps(config,indent=2)+"\n",encoding="utf-8")
        print("Public frontend configuration exported. No credentials were exported.")
        return 0
    except Exception:
        print("Configuration export failed; confirm the stack/region and read permissions. No raw SDK error was printed.")
        return 1

if __name__=="__main__":raise SystemExit(main())
