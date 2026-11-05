"""Synthetic authenticated shop-draft acceptance; never publishes fake shop information."""
import base64
import json
import secrets
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
import requests
from check_admin_live import aws, UserNotFound

ROOT=Path(__file__).resolve().parents[1]


def main():
    stack=aws("cloudformation","describe-stacks",StackName="policy-assistant")["Stacks"][0]
    assert stack["StackStatus"]=="UPDATE_COMPLETE" and stack["StackId"].split(":")[4]=="629380420098"
    outputs={v["OutputKey"]:v["OutputValue"] for v in stack["Outputs"]}
    release=json.loads((ROOT/".deployment/release.json").read_text(encoding="utf-8"))
    function=aws("cloudformation","describe-stack-resource",StackName="policy-assistant",LogicalResourceId="PolicyAssistantFunction")["StackResourceDetail"]["PhysicalResourceId"]
    config=aws("lambda","get-function-configuration",FunctionName=function)
    assert base64.b64decode(config["CodeSha256"]).hex()==release["code_sha256"]
    nonce=uuid4().hex;username="shop-qa-"+nonce+"@example.invalid";password=secrets.token_urlsafe(28)+"Aa1!"
    pool,client=outputs["UserPoolId"],outputs["UserPoolClientId"];base=outputs["PolicyAssistantApiUrl"].rstrip("/")
    token=None;ordinary=None;created=False;draft_attempted=False;initial=None
    report={"checked_at":datetime.now(timezone.utc).isoformat(),"release":release,"scope":"One disposable identity; private nonce-guarded incomplete shop draft only. No fake public profile, owner identity, policies/PDFs, model invocation or email sends.","checks":[],"profile_cleaned":False,"account_cleaned":False,"http_passed":False}
    def save():
        (ROOT/".deployment/shop-live-acceptance.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
        (ROOT/".deployment/shop-test-cleanup.json").write_text(json.dumps({"pool":pool,"username":username,"nonce":nonce,"created":created,"account_cleaned":report["account_cleaned"],"profile_cleaned":report["profile_cleaned"]},indent=2),encoding="utf-8")
    def call(path,method="GET",data=None,bearer=None):
        headers={"Origin":outputs["FrontendUrl"].rstrip("/")}
        if bearer is not False:headers["Authorization"]="Bearer "+(bearer or token)
        response=requests.request(method,base+path,json=data,headers=headers,timeout=40)
        try:body=response.json()
        except ValueError:body={}
        return response.status_code,body
    def ok(path,method="GET",data=None):
        code,body=call(path,method,data)
        if code!=200:raise RuntimeError("Unexpected HTTP "+str(code)+" for "+path)
        return body
    def check(label,value):
        if not value:raise RuntimeError("Failed: "+label)
        report["checks"].append(label);save();print("PASS "+label,flush=True)
    def sign_in():return aws("cognito-idp","initiate-auth",ClientId=client,AuthFlow="USER_PASSWORD_AUTH",AuthParameters={"USERNAME":username,"PASSWORD":password})["AuthenticationResult"]["IdToken"]
    draft={"shop_name":"QA-PRIVATE-"+nonce,"mode":"live","support_email":"","support_phone":"","support_hours":"","returns_instructions":"","support_message":"Unpublished synthetic draft only"}
    try:
        api_id=base.split("//",1)[1].split(".",1)[0]
        routes=aws("apigatewayv2","get-routes",ApiId=api_id)["Items"]
        chosen=[r for r in routes if r["RouteKey"] in {"GET /shop","GET /admin/shop","PATCH /admin/shop"}]
        check("All three deployed shop routes explicitly enforce JWT",len(chosen)==3 and all(r.get("AuthorizationType")=="JWT" and r.get("AuthorizerId") for r in chosen))
        check("Shop endpoint requires gateway authorization",call("/shop",bearer=False)[0] in (401,403))
        aws("cognito-idp","admin-create-user",UserPoolId=pool,Username=username,MessageAction="SUPPRESS",UserAttributes=[{"Name":"email","Value":username},{"Name":"email_verified","Value":"true"}]);created=True;save()
        aws("cognito-idp","admin-set-user-password",UserPoolId=pool,Username=username,Password=password,Permanent=True)
        token=sign_in();ordinary=token
        baseline=ok("/shop")
        check("Customer receives only published profile fields",set(baseline)=={"configured","profile","published_at"})
        check("Customer cannot inspect shop drafts",call("/admin/shop")[0]==403)
        check("Customer cannot change shared shop settings",call("/admin/shop","PATCH",{"expected_revision":None,"action":"save_draft","draft":draft})[0]==403)
        aws("cognito-idp","admin-add-user-to-group",UserPoolId=pool,Username=username,GroupName="administrators");token=sign_in()
        initial=ok("/admin/shop")
        if initial["draft"] is not None:raise RuntimeError("Existing operator draft detected; no shared draft writes performed")
        revision=initial["revision"]
        check("Malformed contact input is rejected",call("/admin/shop","PATCH",{"expected_revision":revision,"action":"save_draft","draft":{**draft,"support_email":"invalid-email"}})[0]==400)
        draft_attempted=True
        saved=ok("/admin/shop","PATCH",{"expected_revision":revision,"action":"save_draft","draft":draft})
        check("Saving a shop draft leaves customer profile unchanged",saved["draft"]==draft and ok("/shop")==baseline)
        check("Old customer JWT still cannot read a shop draft",call("/admin/shop",bearer=ordinary)[0]==403)
        check("Stale shared revision cannot overwrite a draft",call("/admin/shop","PATCH",{"expected_revision":revision,"action":"save_draft","draft":draft})[0]==409)
        check("Publication requires explicit confirmation",call("/admin/shop","PATCH",{"expected_revision":saved["revision"],"action":"publish"})[0]==400)
        check("Incomplete live shop information cannot be published",call("/admin/shop","PATCH",{"expected_revision":saved["revision"],"action":"publish","confirmed":True})[0]==400)
        check("Failed publication preserves the customer snapshot",ok("/shop")==baseline)
        cleared=ok("/admin/shop","PATCH",{"expected_revision":saved["revision"],"action":"discard_draft"})
        check("Discard removes only the synthetic draft",cleared["draft"] is None and cleared["current"]==initial["current"] and ok("/shop")==baseline)
        report["profile_cleaned"]=True
        events=ok("/admin/audit")["events"]
        check("Shop writes record audit metadata without contact or draft content",any(x["action"]=="shop.save_draft" for x in events) and nonce not in json.dumps(events))
        report["http_passed"]=True
    except Exception as exc:
        report["error"]=str(exc)[:300];print("Shop acceptance stopped: "+type(exc).__name__,flush=True)
    finally:
        if draft_attempted and not report["profile_cleaned"]:
            try:
                current=ok("/admin/shop")
                if current.get("draft",{} ) and current["draft"].get("shop_name")==draft["shop_name"]:
                    current=ok("/admin/shop","PATCH",{"expected_revision":current["revision"],"action":"discard_draft"})
                report["profile_cleaned"]=not current.get("draft") and current.get("current")==initial.get("current")
            except Exception as exc:report["profile_cleanup_error"]=type(exc).__name__
        if created:
            try:
                if not token:token=sign_in()
                code,_=call("/account/delete","POST",{"confirmation":"DELETE"})
                if code!=200:raise RuntimeError("Cleanup request failed")
                deadline=time.monotonic()+300
                while time.monotonic()<deadline:
                    try:aws("cognito-idp","admin-get-user",UserPoolId=pool,Username=username)
                    except UserNotFound:report["account_cleaned"]=True;break
                    time.sleep(5)
            except Exception as exc:report["account_cleanup_error"]=type(exc).__name__
        save();print("Shop draft/account cleanup:",report["profile_cleaned"],report["account_cleaned"],flush=True)
    if not all(report[k] for k in ("http_passed","profile_cleaned","account_cleaned")):raise SystemExit(1)


if __name__=="__main__":main()
