import {test} from 'node:test';
import assert from 'node:assert/strict';
import {SupportClient,supportPayload,questionPayload} from '../src/support-client.js';
const id='t-'+'0'.repeat(20)+'-'+'a'.repeat(32);
const record=(extra={})=>({ticket_id:id,revision:'v1',subject:'Support',status:'open',messages:[{role:'customer',body:'Shared test',created_at:'2026-10-30T00:00:00Z'}],message_count:1,expires_at:2000000000,...extra});

test('support needs explicit consent and only shares approved text fields',()=>{
 const input={subject:' Test ',message:' Text ',consent:true,document_ids:['private'],conversation_id:'private',answer:'private'};
 assert.deepEqual(supportPayload(input),{subject:'Test',message:'Text',consent:true});
 for(const consent of [false,undefined,'true'])assert.throws(()=>supportPayload({...input,consent}));
 assert.throws(()=>supportPayload({...input,message:'x'.repeat(1501)}));
});

test('policies-only scope strips every personal PDF ID; documents-only needs a selection',()=>{
 assert.deepEqual(questionPayload('Q',['private'],'policies'),{question:'Q',document_ids:[],source_scope:'policies'});
 assert.throws(()=>questionPayload('Q',[],'documents'));
 assert.deepEqual(questionPayload('Q',['owned'],'documents').document_ids,['owned']);
 assert.throws(()=>questionPayload('Q',[],'invalid'));
});

test('customer support creation returns an owned route without automatic attachments',async()=>{
 let sent;const client=new SupportClient(async(path,options)=>{sent={path,options};return record();});
 await client.create({subject:'Test',message:'Text',consent:true});
 assert.equal(sent.path,'/tickets');assert.deepEqual(sent.options.body,{subject:'Test',message:'Text',consent:true});
 assert.equal(client.route,'/tickets/'+id);assert.equal(client.staff,false);
});

test('staff route needs a validated owner and retains revision on updates',async()=>{
 const calls=[];const client=new SupportClient(async(path,options)=>{calls.push({path,options});return record({owner_id:'alice',revision:options?'v2':'v1'});});
 await client.open({ticket_id:id,owner_id:'alice'},true);await client.update('Reply','resolved');
 assert.equal(calls[1].path,'/admin/tickets/alice/'+id);
 assert.deepEqual(calls[1].options.body,{expected_revision:'v1',action:'update',message:'Reply',status:'resolved'});
 assert.equal(client.record.revision,'v2');await assert.rejects(client.remove());
 await assert.rejects(client.open({ticket_id:id,owner_id:'../private'},true));
});

test('customers cannot select staff status and deletes require a loaded revision',async()=>{
 const calls=[];const client=new SupportClient(async(path,options)=>{calls.push({path,options});return options?.method==='DELETE'?{deleted:true}:record();});
 await client.open({ticket_id:id});await client.update('Follow-up','resolved');
 assert.equal(calls[1].options.body.status,undefined);
 await client.remove();assert.deepEqual(calls[2].options.body,{expected_revision:'v1',confirmation:'DELETE'});assert.equal(client.record,null);
});

test('late support responses cannot restore private data after sign-out',async()=>{
 let finish;const client=new SupportClient(()=>new Promise(resolve=>{finish=resolve;}));
 const pending=client.open({ticket_id:id});client.clear();finish(record());await assert.rejects(pending);assert.equal(client.record,null);assert.equal(client.busy,false);
});

test('conflicts preserve the loaded thread and do not claim successful submission',async()=>{
 let fail=false;const client=new SupportClient(async()=>{if(fail)throw Object.assign(new Error('Conflict'),{status:409});return record();});
 await client.open({ticket_id:id});fail=true;await assert.rejects(client.update('Unsent',null),e=>e.status===409);
 assert.equal(client.record.revision,'v1');assert.equal(client.busy,false);
});

test('malformed thread output is rejected and in-flight selection is blocked',async()=>{
 let finish;const client=new SupportClient(()=>new Promise(resolve=>{finish=resolve;}));const pending=client.open({ticket_id:id});await assert.rejects(client.open({ticket_id:id}));finish(null);await assert.rejects(pending);assert.equal(client.record,null);
});


test('structured support only transmits validated explicit metadata',()=>{
 const raw={subject:'Test',message:'Text',consent:true,category:'warranty',order_ref:' ORDER-001 ',priority:'high',document_ids:['private']};
 assert.deepEqual(supportPayload(raw),{subject:'Test',message:'Text',consent:true,category:'warranty',order_ref:'ORDER-001'});
 for(const extra of [{category:['warranty']},{category:'unknown'},{order_ref:null},{order_ref:'x'.repeat(81)},{order_ref:'line\nnext'}])assert.throws(()=>supportPayload({...raw,...extra}));
});

test('staff priority updates retain revision and never grant customer controls',async()=>{
 const calls=[];const client=new SupportClient(async(path,options)=>{calls.push({path,options});return record({owner_id:'alice',priority:'normal'});});
 await client.open({ticket_id:id,owner_id:'alice'},true);await client.update('','in_progress','reply','high');
 assert.equal(calls[1].options.body.priority,'high');assert.equal(calls[1].options.body.expected_revision,'v1');
 await assert.rejects(client.update('','open','reply','urgent'));await assert.rejects(client.update('','open','reply',['high']));
 await client.open({ticket_id:id});await assert.rejects(client.update('Text',null,'reply','high'));
});
