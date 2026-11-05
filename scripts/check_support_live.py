"""Two-account support/privacy/source-scope acceptance using only disposable data.

No owner account, owner PDF, existing policy, browser session or email is used.
"""
from pathlib import Path
from uuid import uuid4
from datetime import datetime, timezone
import base64
import json
import secrets
import sys
import time
import requests
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.check_admin_live import aws, UserNotFound
from tests.unit.pdf_fixture import pdf_bytes
sys.stdout.reconfigure(encoding="utf-8")


def main(triage_only=False):
    stack=aws("cloudformation","describe-stacks",StackName="policy-assistant")["Stacks"][0]
    if stack["StackStatus"]!="UPDATE_COMPLETE" or stack["StackId"].split(":")[4]!="629380420098":raise RuntimeError("Unexpected deployment")
    outputs={v["OutputKey"]:v["OutputValue"] for v in stack["Outputs"]}
    fn=aws("cloudformation","describe-stack-resource",StackName="policy-assistant",LogicalResourceId="PolicyAssistantFunction")["StackResourceDetail"]["PhysicalResourceId"]
    config=aws("lambda","get-function-configuration",FunctionName=fn)
    release=json.loads((ROOT/".deployment/release.json").read_text(encoding="utf-8"))
    if config["CodeSha256"]!=base64.b64encode(bytes.fromhex(release["code_sha256"])).decode():raise RuntimeError("Wrong code checksum")
    env=config["Environment"]["Variables"]
    if not env.get("SUPPORT_TABLE_NAME"):raise RuntimeError("Support table is not configured")
    base=outputs["PolicyAssistantApiUrl"].rstrip("/")
    pool,client=outputs["UserPoolId"],outputs["UserPoolClientId"]
    nonce=uuid4().hex
    users={role:{"username":"support-qa-"+nonce+"-"+role+"@example.invalid","password":secrets.token_urlsafe(28)+"Aa1!","created":False,"cleaned":False,"token":None,"sub":None} for role in ("a","b")}
    doc_id=None
    report={"checked_at":datetime.now(timezone.utc).isoformat(),"release":release,"scope":"Two disposable identities, one private synthetic PDF and consented synthetic support requests. No owner account/PDF/policy/browser session modified; no emails sent.","checks":[],"identities_cleaned":False,"support_purged":False,"pdf_versions_purged":False}
    if triage_only:
        report["scope"]="Support triage only: two disposable identities, consented synthetic order reference and support messages. No PDFs, AI/model invocation or emails. Prior PDF/AI acceptance remains historical."
        report["pdf_versions_purged"]=None
    report_path=ROOT/(".deployment/triage-live-acceptance.json" if triage_only else ".deployment/support-live-acceptance.json")
    def save():
        report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
        safe={"pool":pool,"users":[{"username":u["username"],"sub":u["sub"],"created":u["created"],"cleaned":u["cleaned"]} for u in users.values()],"doc_id":doc_id}
        (ROOT/".deployment/support-test-cleanup.json").write_text(json.dumps(safe,indent=2),encoding="utf-8")
    def check(label,condition):
        if not condition:raise RuntimeError("Failed: "+label)
        report["checks"].append(label);save();print("PASS "+label,flush=True)
    def call(role,path,method="GET",data=None,auth=True):
        headers={"Origin":outputs["FrontendUrl"].rstrip("/")}
        if auth:headers["Authorization"]="Bearer "+users[role]["token"]
        r=requests.request(method,base+path,json=data,headers=headers,timeout=45)
        try:body=r.json()
        except ValueError:body={}
        return r.status_code,body
    def ok(role,path,method="GET",data=None):
        code,body=call(role,path,method,data)
        if code!=200:raise RuntimeError(path.split("?")[0]+" returned HTTP "+str(code))
        return body
    def sign_in(role):
        user=users[role]
        auth=aws("cognito-idp","initiate-auth",ClientId=client,AuthFlow="USER_PASSWORD_AUTH",AuthParameters={"USERNAME":user["username"],"PASSWORD":user["password"]})
        user["token"]=auth["AuthenticationResult"]["IdToken"]
        user["sub"]=json.loads(base64.urlsafe_b64decode(user["token"].split(".")[1]+"=="))["sub"]
    def support_empty(role):
        return not aws("dynamodb","query",TableName=env["SUPPORT_TABLE_NAME"],KeyConditionExpression="owner_id=:owner",ExpressionAttributeValues={":owner":{"S":users[role]["sub"]}},ConsistentRead=True,ProjectionExpression="owner_id,ticket_id")["Items"]
    def wait_deleted(role):
        user=users[role];deadline=time.monotonic()+300
        while time.monotonic()<deadline:
            try:aws("cognito-idp","admin-get-user",UserPoolId=pool,Username=user["username"])
            except UserNotFound:user["cleaned"]=True;save();return
            time.sleep(5)
        raise RuntimeError("Timed out waiting for synthetic account cleanup: "+role)
    def begin_delete(role):
        user=users[role]
        if user["created"] and not user["cleaned"]:
            if user["token"]:
                code,_=call(role,"/account/delete","POST",{"confirmation":"DELETE"})
                if code!=200:raise RuntimeError("Synthetic account deletion request failed: "+role)
            else:
                aws("cognito-idp","admin-delete-user",UserPoolId=pool,Username=user["username"]);user["cleaned"]=True;save()
    try:
        check("Support routes require gateway authorization",call("a","/tickets",auth=False)[0]==401)
        for role,user in users.items():
            aws("cognito-idp","admin-create-user",UserPoolId=pool,Username=user["username"],MessageAction="SUPPRESS",UserAttributes=[{"Name":"email","Value":user["username"]},{"Name":"email_verified","Value":"true"}])
            user["created"]=True;save()
            aws("cognito-idp","admin-set-user-password",UserPoolId=pool,Username=user["username"],Password=user["password"],Permanent=True)
            sign_in(role);save()
        check("Ordinary customers cannot inspect the staff queue",call("a","/admin/tickets")[0]==403)
        if not triage_only:
            session=ok("a","/documents/upload-session","POST",{"filename":"support-private-qa.pdf"})
            doc_id=session["doc_id"];save()
            secret="PRIVATE-PDF-"+nonce
            body=pdf_bytes("Private QA verification code: "+secret+". Sample limit: 99 days. This is synthetic test data.")
            uploaded=requests.post(session["upload_url"],data=session["upload_fields"],files={"file":("support-private-qa.pdf",body,"application/pdf")},timeout=45)
            check("Private synthetic PDF upload succeeds without sending JWT to S3",uploaded.status_code in (200,201,204))
            ok("a","/documents/submit","POST",{"doc_id":doc_id,"s3_key":session["s3_key"]})
            deadline=time.monotonic()+180
            while time.monotonic()<deadline:
                doc=ok("a","/documents/"+doc_id+"/status")
                if doc["status"]=="processed":break
                if doc["status"]=="failed":raise RuntimeError("Synthetic PDF processing failed")
                time.sleep(3)
            check("Private PDF becomes ready",doc["status"]=="processed")
            answer=ok("a","/ask","POST",{"question":"What is the private QA verification code in this PDF?","source_scope":"documents","document_ids":[doc_id]})
            check("Documents-only generation cites only the selected owned PDF",answer["grounded"] and answer["source_scope"]=="documents" and all(c.get("doc_id")==doc_id and "policy_id" not in c for c in answer["citations"]) and secret.lower() in answer["answer"].lower())
            public=ok("a","/ask","POST",{"question":"What is the private QA verification code in my personal PDF?","source_scope":"policies","document_ids":[]})
            check("Policies-only generation excludes a ready private PDF",public["source_scope"]=="policies" and all("doc_id" not in c for c in public["citations"]) and secret not in public["answer"] and secret not in json.dumps(public["citations"]))
        else:
            secret="UNSHARED-SYNTHETIC-"+nonce
            answer={"conversation_id":"synthetic-not-attached"}
        check("Invalid empty selected-PDF scope is rejected",call("a","/ask","POST",{"question":"Test?","source_scope":"documents","document_ids":[]})[0]==400)
        check("Support sharing needs explicit consent",call("a","/tickets","POST",{"subject":"QA","message":"Support-only-"+nonce})[0]==400)
        first=ok("a","/tickets","POST",{"subject":"DEMO support QA "+nonce,"message":"Support-only-"+nonce,"consent":True,"conversation_id":answer["conversation_id"],"document_ids":[doc_id] if doc_id else [],"category":"warranty","order_ref":"QA-ORDER-"+nonce})
        tid=first["ticket_id"];url="/tickets/"+tid
        check("Support creation does not copy PDFs/history or guessed attachment fields",first["status"]=="open" and first["message_count"]==1 and secret not in json.dumps(first) and "document_ids" not in first and "conversation_id" not in first)
        check("Structured category and order reference persist with normal priority",first["category"]=="warranty" and first["order_ref"]=="QA-ORDER-"+nonce and first["priority"]=="normal")
        check("Customer cannot choose staff priority",call("a",url,"PATCH",{"expected_revision":first["revision"],"priority":"high","message":"Should fail"})[0]==400)
        check("Other customers cannot read a known ticket ID",call("b",url)[0]==404)
        check("Other customers cannot change or delete a known ticket ID",call("b",url,"PATCH",{"expected_revision":first["revision"],"message":"Intrusion"})[0]==404 and call("b",url,"DELETE",{"expected_revision":first["revision"],"confirmation":"DELETE"})[0]==404)
        check("Other customers cannot see the owner's support list",ok("b","/tickets")["tickets"]==[])
        ordinary_b=users["b"]["token"]
        aws("cognito-idp","admin-add-user-to-group",UserPoolId=pool,Username=users["b"]["username"],GroupName="administrators");sign_in("b")
        admin_url="/admin/tickets/"+users["a"]["sub"]+"/"+tid
        staff=ok("b",admin_url)
        check("Staff sees only explicitly submitted support text",staff["messages"][0]["body"]=="Support-only-"+nonce and secret not in json.dumps(staff))
        if not triage_only:
            check("Support administrator still cannot download or query customer PDF",call("b","/documents/"+doc_id+"/download")[0]==404 and call("b","/ask","POST",{"question":"Verification code?","source_scope":"documents","document_ids":[doc_id]})[0]==404)
        queue=ok("b","/admin/tickets?limit=1")
        check("Staff queue only exposes bounded summaries",len(queue["tickets"])<=1 and all("messages" not in row and "revision" not in row for row in queue["tickets"]))
        if queue.get("next_token"):
            from urllib.parse import quote
            check("Staff queue continuation token works",call("b","/admin/tickets?limit=1&next_token="+quote(queue["next_token"],safe=""))[0]==200)
        replied=ok("b",admin_url,"PATCH",{"expected_revision":staff["revision"],"action":"update","status":"resolved","priority":"high","message":"Synthetic staff reply, no external message or email."})
        filtered=ok("b","/admin/tickets?category=warranty&priority=high&order_ref=QA-ORDER-"+nonce)
        check("Combined staff filters find the exact synthetic order",any(x["ticket_id"]==tid for x in filtered["tickets"]))
        check("Wrong category returns no matching order",not ok("b","/admin/tickets?category=returns&order_ref=QA-ORDER-"+nonce)["tickets"])
        check("Invalid priority filter is rejected",call("b","/admin/tickets?priority=urgent")[0]==400)
        overview=ok("b","/admin/overview")
        check("Administrator sees support usage and configured limits",overview["usage"]["ticket"]>=1 and overview["limits"]["tickets"]>0 and "request" in overview["usage"])
        seen=ok("a",url)
        check("Staff priority is visible to the customer",seen["priority"]=="high")
        check("Customer sees the staff reply and resolved state",seen["status"]=="resolved" and seen["messages"][-1]["role"]=="staff")
        check("Stale customer update cannot overwrite a staff reply",call("a",url,"PATCH",{"expected_revision":first["revision"],"message":"Stale"})[0]==409)
        followup=ok("a",url,"PATCH",{"expected_revision":seen["revision"],"message":"Synthetic follow-up"})
        check("Customer follow-up reopens the request without extending retention",followup["status"]=="open" and followup["expires_at"]==first["expires_at"])
        closed=ok("a",url,"PATCH",{"action":"close","expected_revision":followup["revision"]})
        check("Customer can close the request",closed["status"]=="closed")
        check("Closed request rejects additional customer replies",call("a",url,"PATCH",{"expected_revision":closed["revision"],"message":"Closed"})[0]==409)
        check("Deleting a support request requires explicit confirmation",call("a",url,"DELETE",{"expected_revision":closed["revision"]})[0]==400)
        ok("a",url,"DELETE",{"expected_revision":closed["revision"],"confirmation":"DELETE"})
        check("Owner deletion removes that support request",call("a",url)[0]==404)
        second=ok("a","/tickets","POST",{"subject":"Account purge QA "+nonce,"message":"Disposable account purge fixture","consent":True})
        other=ok("b","/tickets","POST",{"subject":"Isolation QA "+nonce,"message":"Must survive deletion of customer A","consent":True})
        begin_delete("a")
        check("Deleting customer is blocked immediately",call("a","/tickets")[0]==410)
        check("Staff cannot inspect or change tickets of a deleting customer",call("b","/admin/tickets/"+users["a"]["sub"]+"/"+second["ticket_id"])[0]==404)
        wait_deleted("a")
        check("Account deletion purges all owned support rows",support_empty("a"))
        check("Deleting one customer preserves the other customer's request",call("b","/tickets/"+other["ticket_id"])[0]==200)
        if not triage_only:
            versions=[]
            for prefix in ("quarantine/"+doc_id+"/","uploads/"+doc_id+"/","documents/"+doc_id+"/"):
                obj=aws("s3api","list-object-versions",Bucket=env["DOCUMENTS_BUCKET_NAME"],Prefix=prefix)
                versions.extend(obj.get("Versions",[])+obj.get("DeleteMarkers",[]))
            check("Account cleanup purges all source/extraction PDF versions",not versions)
            report["pdf_versions_purged"]=True
        report["http_passed"]=True
    except Exception as exc:
        report["error"]=str(exc)[:300];print("Acceptance stopped: "+type(exc).__name__,flush=True)
    finally:
        save()
        for role in users:
            try:begin_delete(role)
            except Exception as exc:report["cleanup_error_"+role]=type(exc).__name__;save()
        for role,user in users.items():
            if user["created"] and not user["cleaned"]:
                try:wait_deleted(role)
                except Exception as exc:report["cleanup_error_"+role]=type(exc).__name__;save()
        report["identities_cleaned"]=all(not u["created"] or u["cleaned"] for u in users.values())
        report["support_purged"]=all(not u["sub"] or support_empty(role) for role,u in users.items())
        save();print("Synthetic identity/support cleanup:",report["identities_cleaned"],report["support_purged"],flush=True)
    if not report.get("http_passed") or not report["identities_cleaned"] or not report["support_purged"]:raise SystemExit(1)


if __name__=="__main__":
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--triage-only",action="store_true",help="No PDF upload or model invocation; verify only support/triage and cleanup")
    main(triage_only=parser.parse_args().triage_only)
