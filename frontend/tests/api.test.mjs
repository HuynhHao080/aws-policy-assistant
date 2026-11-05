import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createApi,uploadPdf,validatePdf,ApiError} from '../src/api.js';

test('authentication is required before making any API request',async()=>{
  let called=false;const api=createApi('https://api.example.test/Prod',async()=>null,async()=>{called=true;});
  await assert.rejects(api('/documents'),error=>error instanceof ApiError&&error.status===401);assert.equal(called,false);
});
test('tokens only go to the configured API and data uses JSON body',async()=>{
  let request;const api=createApi('https://api.example.test/Prod/',async()=>'secret',async(url,options)=>{request={url,options};return{ok:true,status:200,json:async()=>({answer:'ok'})};});
  await api('/ask',{method:'POST',body:{question:'private'}});
  assert.equal(request.url,'https://api.example.test/Prod/ask');assert.equal(request.options.headers.Authorization,'Bearer secret');assert.equal(JSON.parse(request.options.body).question,'private');assert.equal(request.options.redirect,'error');
  await assert.rejects(api('//evil.example/test'));assert.throws(()=>createApi('http://public.example',async()=>'x'));
});
test('API errors preserve status and do not turn into successful results',async()=>{
  for(const status of [400,401,403,404,409,429,500,503]){
    const api=createApi('https://api.example.test',async()=>'secret',async()=>({ok:false,status,json:async()=>({message:'failed'})}));
    await assert.rejects(api('/ask'),error=>error.status===status&&error.message==='failed');
  }
});
test('malformed backend responses are rejected',async()=>{
  const api=createApi('https://api.example.test',async()=>'secret',async()=>({ok:true,status:200,json:async()=>{throw new Error('bad json');}}));
  await assert.rejects(api('/documents'),error=>error instanceof ApiError);
});
test('PDF constraints are enforced before obtaining an upload session',()=>{
  for(const file of [null,{name:'a.txt',size:3},{name:'a.pdf',size:0},{name:'a.pdf',size:10*1024*1024+1}])assert.throws(()=>validatePdf(file));
  validatePdf({name:'valid.PDF',size:10*1024*1024});
});
test('presigned multipart upload has no Cognito token and uses server-provided key',async()=>{
  const calls=[];let s3;const api=async(path,options)=>{calls.push({path,options});return path.includes('upload-session')?{doc_id:'doc-1',s3_key:'uploads/doc-1/document',upload_url:'https://bucket.s3.amazonaws.com',upload_fields:{key:'uploads/doc-1/document',policy:'signed-policy','Content-Type':'application/pdf'}}:{status:'pending'};};
  const file=new File(['%PDF-1.4'],'test.pdf',{type:'application/pdf'});
  const id=await uploadPdf(api,file,async(url,options)=>{s3={url,options};return{ok:true,status:204};});
  assert.equal(id,'doc-1');assert.equal(s3.options.method,'POST');assert.equal(s3.options.headers,undefined);assert.equal(s3.options.body.get('policy'),'signed-policy');assert.equal(s3.options.body.get('file').name,'test.pdf');assert.equal(calls[1].options.body.s3_key,'uploads/doc-1/document');
});
test('S3 failure never submits or reports upload success',async()=>{
  const calls=[];const api=async(path)=>{calls.push(path);return{doc_id:'doc-1',s3_key:'uploads/doc-1/document',upload_url:'https://bucket.s3.amazonaws.com',upload_fields:{key:'uploads/doc-1/document'}};};
  await assert.rejects(uploadPdf(api,new File(['%PDF-1.4'],'a.pdf'),async()=>({ok:false,status:403})),/403/);assert.equal(calls.length,1);
});
test('failed submit retains a document ID for recovery rather than false completion',async()=>{
  const api=async(path)=>{if(path.includes('upload-session'))return{doc_id:'doc-1',s3_key:'uploads/doc-1/document',upload_url:'https://bucket.s3.amazonaws.com',upload_fields:{key:'uploads/doc-1/document'}};throw new ApiError(503,'unavailable');};
  await assert.rejects(uploadPdf(api,new File(['%PDF-1.4'],'a.pdf'),async()=>({ok:true,status:204})),/doc-1/);
});
test('a response from a signed-out session cannot repopulate private UI',async()=>{
  let generation=0;
  const api=createApi('https://api.example.test',async()=>'token',async()=>{generation++;return{ok:true,status:200,json:async()=>({answer:'private'})};},()=>generation);
  await assert.rejects(api('/ask'),error=>error.status===401);
});
