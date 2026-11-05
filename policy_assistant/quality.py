"""Private answer feedback and aggregate-only quality measurements; no model calls."""
import re
import time
from datetime import datetime, timezone, timedelta
from urllib.parse import unquote
from uuid import uuid4
from boto3.dynamodb.conditions import Key
from boto3.dynamodb.types import TypeSerializer
from botocore.exceptions import ClientError
try:
    from .service import Problem,now
except ImportError:
    from service import Problem,now

REASONS={"missing_info","incorrect","citation","unclear","other"}
COUNTERS=("answers","grounded","refused","latency_ms","sources","scope_all","scope_policies","scope_documents","helpful","not_helpful")+tuple("reason_"+r for r in sorted(REASONS))


def month_valid(value):
    return isinstance(value,str) and bool(re.fullmatch(r"[0-9]{4}-(0[1-9]|1[0-2])",value))


def account_guard(service,owner):
    return {"ConditionCheck":{"TableName":service.table("USAGE_TABLE_NAME").name,"Key":{"pk":{"S":"account#"+owner}},"ConditionExpression":"attribute_not_exists(#state) OR #state<>:deleting","ExpressionAttributeNames":{"#state":"state"},"ExpressionAttributeValues":{":deleting":{"S":"deleting"}}}}


def commit(service,ops):
    token=uuid4().hex
    for attempt in range(3):
        try:
            service.client("dynamodb").transact_write_items(TransactItems=ops,ClientRequestToken=token)
            return
        except ClientError as exc:
            code=exc.response["Error"]["Code"];reasons=exc.response.get("CancellationReasons",[])
            if code=="TransactionCanceledException" and any(x.get("Code")=="ConditionalCheckFailed" for x in reasons):
                raise Problem(409,"Answer, feedback or account changed. Reload before retrying") from None
            conflicts=code=="TransactionCanceledException" and any(x.get("Code")=="TransactionConflict" for x in reasons) and all(x.get("Code") in (None,"None","TransactionConflict") for x in reasons)
            if not conflicts or attempt==2:raise
            # Retry only the same persistence transaction, never retrieval/model generation.
            time.sleep(.02*(2**attempt))


def aggregate_update(service,month,deltas,existing=False):
    if not month_valid(month) or not set(deltas)<=set(COUNTERS):raise ValueError("Invalid internal metric")
    names={"#start":"started_at","#expiry":"expires_at"};values={":stamp":{"S":now()},":ttl":{"N":str(int(time.time())+65*86400)}}
    additions=[];conditions=[]
    for i,(key,value) in enumerate(deltas.items()):
        alias="#c"+str(i);name=":d"+str(i);names[alias]=key;values[name]={"N":str(value)};additions.append(alias+" "+name)
        if existing and value<0:
            lower=":lower"+str(i);values[lower]={"N":str(-value)};conditions.append(alias+">="+lower)
    update={"TableName":service.table("USAGE_TABLE_NAME").name,"Key":{"pk":{"S":"quality#"+month}},"UpdateExpression":"SET #start=if_not_exists(#start,:stamp), #expiry=:ttl ADD "+", ".join(additions),"ExpressionAttributeNames":names,"ExpressionAttributeValues":values}
    if existing:
        values[":clock"]={"N":str(int(time.time()))};update["ConditionExpression"]="attribute_exists(pk) AND #expiry>:clock"+(" AND "+" AND ".join(conditions) if conditions else "")
    return {"Update":update}


def save_answer(service,owner,item,response_ms):
    month=item["created_at"][:7];item.update(quality_month=month,quality_version=1,response_ms=max(0,int(response_ms)))
    deltas={k:0 for k in COUNTERS};deltas.update(answers=1,grounded=int(bool(item["grounded"])),refused=int(not item["grounded"]),latency_ms=item["response_ms"],sources=len(item["citations"]))
    deltas["scope_"+item["source_scope"]]=1
    encode=TypeSerializer().serialize
    put={"Put":{"TableName":service.table("HISTORY_TABLE_NAME").name,"Item":{k:encode(v) for k,v in item.items()},"ConditionExpression":"attribute_not_exists(conversation_id)"}}
    commit(service,[put,aggregate_update(service,month,deltas),account_guard(service,owner)])


def feedback_view(item):
    return {"conversation_id":item["conversation_id"],"quality_month":item["quality_month"],"feedback":item.get("feedback",{"rating":None,"reason":None,"revision":None})}


def feedback(service,owner,encoded_id,data):
    conversation_id=unquote(encoded_id)
    if not re.fullmatch(r"[A-Za-z0-9:.+_#-]{1,100}",conversation_id):raise Problem(400,"Invalid conversation ID")
    rating=data.get("rating");reason=data.get("reason")
    if rating is not None and (not isinstance(rating,str) or rating not in {"helpful","not_helpful"}):raise Problem(400,"Invalid feedback rating")
    if rating=="not_helpful":
        if not isinstance(reason,str) or reason not in REASONS:raise Problem(400,"Select a feedback reason")
    elif reason is not None:raise Problem(400,"Only negative feedback accepts a reason")
    if "expected_revision" not in data or (data["expected_revision"] is not None and not isinstance(data["expected_revision"],str)):raise Problem(400,"Feedback revision is required")
    result=service.table("HISTORY_TABLE_NAME").query(KeyConditionExpression=Key("owner_id").eq(owner)&Key("conversation_id").eq(conversation_id),ConsistentRead=True,Limit=1)
    item=next(iter(result.get("Items",[])),None)
    if not item or int(item.get("expires_at",0))<=int(time.time()):raise Problem(404,"Conversation not found")
    if item.get("quality_version")!=1 or not month_valid(item.get("quality_month")):raise Problem(409,"Feedback is available for answers created after quality tracking was enabled")
    old=item.get("feedback",{});expected=data["expected_revision"]
    if (old.get("rating"),old.get("reason"))==(rating,reason):return feedback_view(item)
    if expected!=old.get("revision"):raise Problem(409,"Feedback changed. Reload before retrying")
    service.quota(owner,"feedback")
    deltas={k:0 for k in COUNTERS}
    for value,sign in [(old,-1),({"rating":rating,"reason":reason},1)]:
        if value.get("rating"):
            deltas[value["rating"]]+=sign
            if value.get("reason"):deltas["reason_"+value["reason"]]+=sign
    deltas={k:v for k,v in deltas.items() if v}
    item["feedback"]={"rating":rating,"reason":reason,"revision":uuid4().hex,"updated_at":now()}
    encode=TypeSerializer().serialize
    put={"TableName":service.table("HISTORY_TABLE_NAME").name,"Item":{k:encode(v) for k,v in item.items()},"ConditionExpression":"attribute_exists(conversation_id) AND expires_at>:clock AND "+("#f.#r=:old" if expected else "attribute_not_exists(#f.#r)"),"ExpressionAttributeNames":{"#f":"feedback","#r":"revision"},"ExpressionAttributeValues":{":clock":{"N":str(int(time.time()))}}}
    if expected:put["ExpressionAttributeValues"][":old"]={"S":expected}
    commit(service,[{"Put":put},aggregate_update(service,item["quality_month"],deltas,existing=True),account_guard(service,owner)])
    return feedback_view(item)


def summary(service,params):
    today=datetime.now(timezone.utc);months=[today.strftime("%Y-%m"),(today.replace(day=1)-timedelta(days=1)).strftime("%Y-%m")]
    month=params.get("month",months[0])
    if not isinstance(month,str) or month not in months:raise Problem(400,"Choose the current or previous UTC month")
    row=service.table("USAGE_TABLE_NAME").get_item(Key={"pk":"quality#"+month},ConsistentRead=True).get("Item",{})
    if int(row.get("expires_at",0))<=int(time.time()):row={}
    counts={k:max(0,int(row.get(k,0))) for k in COUNTERS};votes=counts["helpful"]+counts["not_helpful"]
    return {"month":month,"available_months":months,"started_at":row.get("started_at"),"counts":counts,"citation_rate":round(100*counts["grounded"]/counts["answers"],1) if counts["answers"] else None,"helpful_rate":round(100*counts["helpful"]/votes,1) if votes else None,"average_response_ms":round(counts["latency_ms"]/counts["answers"]) if counts["answers"] else None,"feedback_limits":{"per_user_day":50,"global_month":5000},"measurement":"Persisted answers after tracking enabled; citation presence and user opinion do not prove factual correctness. Anonymous cohort totals can remain after private history deletion."}
