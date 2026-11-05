"""Loopback-only offline demo: real Lambda code with moto AWS services.

No real AWS credentials, endpoints or Cognito authentication are used. Data is
in-memory and discarded on shutdown. Run: python -m scripts.demo_server
"""
import argparse
import importlib
import json
import os
from pathlib import Path
import secrets
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit, unquote

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()
    # Override rather than read workstation credentials; mock_aws intercepts all SDK calls.
    os.environ.update({"AWS_ACCESS_KEY_ID": "testing", "AWS_SECRET_ACCESS_KEY": "testing",
        "AWS_SESSION_TOKEN": "testing", "AWS_REGION": "ap-southeast-1",
        "AWS_DEFAULT_REGION": "ap-southeast-1", "AWS_EC2_METADATA_DISABLED": "true",
        "DOCUMENTS_BUCKET_NAME": "local-policy-documents", "POLICIES_TABLE_NAME": "LocalPolicies",
        "DOCUMENT_METADATA_TABLE_NAME": "LocalDocuments"})
    import boto3
    from moto import mock_aws
    with mock_aws():
        ddb = boto3.resource("dynamodb", region_name="ap-southeast-1")
        ddb.create_table(TableName="LocalPolicies", KeySchema=[{"AttributeName":"policy_id","KeyType":"HASH"}],
            AttributeDefinitions=[{"AttributeName":"policy_id","AttributeType":"S"}], BillingMode="PAY_PER_REQUEST")
        ddb.create_table(TableName="LocalDocuments", KeySchema=[{"AttributeName":"doc_id","KeyType":"HASH"}],
            AttributeDefinitions=[{"AttributeName":k,"AttributeType":t} for k,t in
                [("doc_id","S"),("owner_sub","S"),("created_at","S"),("status","S"),("dispatch_after","N")]],
            GlobalSecondaryIndexes=[{"IndexName":name,"KeySchema":[{"AttributeName":pk,"KeyType":"HASH"},{"AttributeName":sk,"KeyType":"RANGE"}],"Projection":{"ProjectionType":"ALL"}}
                for name,pk,sk in [("ByOwner","owner_sub","created_at"),("ByStatus","status","dispatch_after")]],
            BillingMode="PAY_PER_REQUEST")
        for policy in json.loads((ROOT/"sample_data/policies.json").read_text(encoding="utf-8")):
            ddb.Table("LocalPolicies").put_item(Item=policy)
        storage = boto3.client("s3", region_name="ap-southeast-1")
        storage.create_bucket(Bucket="local-policy-documents", CreateBucketConfiguration={"LocationConstraint":"ap-southeast-1"})
        storage.put_bucket_versioning(Bucket="local-policy-documents",VersioningConfiguration={"Status":"Enabled"})
        sqs=boto3.client("sqs",region_name="ap-southeast-1")
        dlq=sqs.create_queue(QueueName="local-dlq")["QueueUrl"]
        arn=sqs.get_queue_attributes(QueueUrl=dlq,AttributeNames=["QueueArn"])["Attributes"]["QueueArn"]
        queue=sqs.create_queue(QueueName="local-documents",Attributes={"VisibilityTimeout":"2",
            "RedrivePolicy":json.dumps({"deadLetterTargetArn":arn,"maxReceiveCount":3})})["QueueUrl"]
        os.environ["DOCUMENT_QUEUE_URL"]=queue
        from policy_assistant import app
        importlib.reload(app)
        capabilities, sessions = {}, {}
        stop=threading.Event()
        origin=""
        class LocalStorage:
            def __getattr__(self,name): return getattr(storage,name)
            def generate_presigned_post(self, Bucket, Key, Fields, Conditions, ExpiresIn):
                post=storage.generate_presigned_post(Bucket=Bucket,Key=Key,Fields=Fields,Conditions=Conditions,ExpiresIn=ExpiresIn)
                cap=secrets.token_urlsafe(32)
                capabilities[cap]=("post_object",{"Bucket":Bucket,"Key":Key},time.time()+ExpiresIn)
                post["url"]=origin+"/storage/"+cap
                return post
            def generate_presigned_url(self,operation,Params,ExpiresIn):
                cap=secrets.token_urlsafe(32)
                capabilities[cap]=(operation,Params,time.time()+ExpiresIn)
                return origin+"/storage/"+cap
        app._s3=lambda:LocalStorage()
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args): pass  # never log signed paths or Authorization
            def reply(self,status,data,kind="application/json"):
                encoded=json.dumps(data,default=str).encode() if kind=="application/json" else data
                self.send_response(status);self.send_header("Content-Type",kind)
                self.send_header("Content-Length",str(len(encoded)))
                self.send_header("Cache-Control","no-store")
                self.send_header("X-Content-Type-Options","nosniff")
                self.end_headers();self.wfile.write(encoded)
            def do_GET(self): self.handle_request()
            def do_POST(self): self.handle_request()
            def do_PUT(self): self.handle_request()
            def handle_request(self):
                try: self.dispatch()
                except (BrokenPipeError,ConnectionResetError): pass
                except Exception: self.reply(500,{"error":"Local demo request failed"})
            def dispatch(self):
                parsed=urlsplit(self.path);path=unquote(parsed.path)
                allowed={urlsplit(origin).netloc,"localhost:"+str(self.server.server_port)}
                if self.headers.get("Host") not in allowed:
                    return self.reply(403,{"error":"Loopback host required"})
                length=int(self.headers.get("Content-Length",0))
                if length>app.MAX_DOCUMENT_BYTES+65536: return self.reply(413,{"error":"Request too large"})
                body=self.rfile.read(length)
                if path=="/config.json":
                    return self.reply(200,{"mode":"local","apiBase":origin+"/api","region":"ap-southeast-1","clientId":"", "demoUsers":["alice@demo.local","bob@demo.local"]})
                if path=="/local-auth" and self.command=="POST":
                    user=json.loads(body).get("username")
                    if user not in ("alice@demo.local","bob@demo.local"): return self.reply(401,{"error":"Unknown demo user"})
                    token="local."+secrets.token_urlsafe(32)+".demo"
                    sessions[token]=(user,time.time()+3600)
                    return self.reply(200,{"AuthenticationResult":{"IdToken":token,"ExpiresIn":3600}})
                if path=="/local-auth/logout":
                    sessions.pop(self.headers.get("Authorization","").removeprefix("Bearer "),None)
                    return self.reply(200,{"signed_out":True})
                if path.startswith("/storage/"):
                    cap=capabilities.get(path.split("/")[-1])
                    if not cap or cap[2]<time.time():return self.reply(403,{"error":"Expired local capability"})
                    operation,params,_=cap
                    if operation=="post_object" and self.command=="POST":
                        from email.parser import BytesParser
                        from email.policy import default
                        multipart=BytesParser(policy=default).parsebytes(("Content-Type: "+self.headers.get("Content-Type","")+"\r\nMIME-Version: 1.0\r\n\r\n").encode()+body)
                        fields={part.get_param("name",header="content-disposition"):part.get_payload(decode=True) for part in multipart.iter_parts()}
                        data=fields.get("file",b"")
                        if not 5<=len(data)<=app.MAX_DOCUMENT_BYTES:return self.reply(413,{"error":"Size policy rejected"})
                        if fields.get("key")!=params["Key"].encode() or fields.get("Content-Type")!=b"application/pdf":return self.reply(403,{"error":"Upload policy rejected"})
                        storage.put_object(Bucket=params["Bucket"],Key=params["Key"],ContentType="application/pdf",Body=data)
                        return self.reply(201,{"uploaded":True})
                    if operation=="put_object" and self.command=="PUT":
                        storage.put_object(Bucket=params["Bucket"],Key=params["Key"],ContentType="application/pdf",Body=body)
                        return self.reply(200,{"uploaded":True})
                    if operation=="get_object" and self.command=="GET":
                        obj=storage.get_object(Bucket=params["Bucket"],Key=params["Key"],VersionId=params["VersionId"])
                        return self.reply(200,obj["Body"].read(),"application/pdf")
                    return self.reply(405,{"error":"Method not allowed"})
                if path.startswith("/api/"):
                    route=path[4:]
                    token=self.headers.get("Authorization","").removeprefix("Bearer ")
                    session=sessions.get(token)
                    if route!="/health" and (not session or session[1]<time.time()):return self.reply(401,{"error":"Unauthorized"})
                    ctx={"requestId":secrets.token_hex(8),"http":{"method":self.command,"path":route}}
                    if session:ctx["authorizer"]={"jwt":{"claims":{"sub":session[0]}}}
                    pieces=route.strip("/").split("/")
                    params={"policy_id":pieces[1]} if len(pieces)==2 and pieces[0]=="policies" else {}
                    if len(pieces)==3 and pieces[0]=="documents":params={"doc_id":pieces[1]}
                    event={"requestContext":ctx,"pathParameters":params,"body":body.decode() if body else None,
                        "queryStringParameters":{k:v[0] for k,v in parse_qs(parsed.query,keep_blank_values=True).items()}}
                    result=app.lambda_handler(event,None)
                    return self.reply(result["statusCode"],json.loads(result["body"]))
                files={"/":"index.html","/index.html":"index.html","/app.js":"app.js","/styles.css":"styles.css"}
                if path not in files or self.command!="GET":return self.reply(404,{"error":"Not found"})
                name=files[path];kind="text/javascript" if name.endswith(".js") else "text/css" if name.endswith(".css") else "text/html; charset=utf-8"
                return self.reply(200,(ROOT/"frontend"/name).read_bytes(),kind)
        server=ThreadingHTTPServer(("127.0.0.1",args.port),Handler)
        origin="http://127.0.0.1:"+str(server.server_port)
        def process():
            last_recovery=0
            while not stop.wait(.3):
                try:
                    if time.time()-last_recovery>120:
                        app.recovery_handler({},None);last_recovery=time.time()
                    for msg in sqs.receive_message(QueueUrl=queue,MaxNumberOfMessages=1,MessageSystemAttributeNames=["ApproximateReceiveCount"]).get("Messages",[]):
                        result=app.worker_handler({"Records":[{"messageId":msg["MessageId"],"body":msg["Body"],"attributes":msg.get("Attributes",{})}]},None)
                        if result["batchItemFailures"]:continue
                        sqs.delete_message(QueueUrl=queue,ReceiptHandle=msg["ReceiptHandle"])
                except Exception: pass  # failed message remains for retry/redrive; no raw exception/URLs printed
        thread=threading.Thread(target=process,daemon=True);thread.start()
        print("OFFLINE DEMO: simulated AWS/authentication; in-memory data only.",flush=True)
        print("DEMO_URL="+origin,flush=True)
        try:server.serve_forever()
        except KeyboardInterrupt:pass
        finally:stop.set();server.server_close();thread.join(timeout=5)


if __name__=="__main__":main()
