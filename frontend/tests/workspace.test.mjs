import{test}from'node:test';
import assert from'node:assert/strict';
import{readFile}from'node:fs/promises';
import{fileURLToPath}from'node:url';
import path from'node:path';
import{build}from'esbuild';
import{JSDOM,VirtualConsole}from'jsdom';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const html=await readFile(path.join(root,'index.html'),'utf8');
const mockAuth=`export const Log={NONE:0,setLevel(){}};export class WebStorageStateStore{};export class UserManager{constructor(){this.events={addUserLoaded(){},addAccessTokenExpired:fn=>window.__expire=fn};}async getUser(){return window.__fixtureUser;}async removeUser(){window.__fixtureUser=null;}async revokeTokens(){}stopSilentRenew(){}async signinRedirect(options){window.__signInRequested=true;window.__signInOptions=options;}}`;
const built=await build({absWorkingDir:root,entryPoints:['src/main.js'],bundle:true,write:false,format:'iife',loader:{'.css':'empty'},plugins:[{name:'unit-auth-only',setup(b){b.onResolve({filter:/^oidc-client-ts$/},()=>({path:'unit-auth',namespace:'unit'}));b.onLoad({filter:/.*/,namespace:'unit'},()=>({contents:mockAuth,loader:'js'}));}}]});
const script=built.outputFiles[0].text;
const json=(body,status=200)=>({ok:status>=200&&status<300,status,json:async()=>body});
async function until(check){for(let i=0;i<120;i++){if(check())return;await new Promise(r=>setTimeout(r,2));}throw new Error('Timed out waiting for synthetic DOM state');}
async function fixture(t,{admin=false,guest=false,view='assistant',override=()=>undefined,confirm=()=>false}={}){
 const errors=[];const vc=new VirtualConsole();vc.on('jsdomError',e=>errors.push(e.message));
 const dom=new JSDOM(html,{url:'https://ui.fixture.invalid/#'+view,runScripts:'outside-only',virtualConsole:vc});t.after(()=>dom.window.close());
 const w=dom.window;w.__fixtureUser=guest?null:{id_token:'unit-fixture-not-a-jwt',expired:false,profile:{sub:'synthetic-user'}};w.confirm=confirm;w.prompt=()=>null;w.scrollTo=options=>{w.__lastScroll=options;};
 w.HTMLDialogElement.prototype.showModal=function(){this.setAttribute('open','');};w.HTMLDialogElement.prototype.close=function(){this.removeAttribute('open');};
 const timer=w.setTimeout.bind(w);w.setTimeout=(fn,ms,...args)=>timer(fn,ms===2500?0:ms,...args);
 const calls=[];w.fetch=async(url,options={})=>{
  if(url==='./config.json')return json({apiBase:'https://api.fixture.invalid',clientId:'unit',userPoolId:'unit',region:'ap-southeast-1',authDomain:'https://auth.fixture.invalid'});
  const u=new URL(url);const key=u.pathname;calls.push({key,url:String(url),options});
  const custom=await override(key,options,w,u);if(custom!==undefined)return custom;
  if(key==='/me')return json({email:'unit@example.invalid',groups:admin?['administrators']:[],limits:{uploads_per_day:5,questions_per_day:20,tickets_per_day:5},ai_available:true});
  if(key==='/shop')return json({configured:false,profile:null,published_at:null});
  if(key==='/documents')return json({documents:[],next_token:null});
  if(key==='/conversations')return json({conversations:[],next_token:null});
  if(key==='/policies')return json({policies:[],next_token:null});
  if(key==='/tickets'||key==='/admin/tickets')return json({tickets:[],next_token:null});
  if(key==='/admin/quality')return json({month:'2026-11',available_months:['2026-11','2026-10'],started_at:null,counts:{answers:0,grounded:0,refused:0,helpful:0,not_helpful:0,scope_all:0,scope_policies:0,scope_documents:0},citation_rate:null,helpful_rate:null,average_response_ms:null});
  if(key==='/admin/overview')return json({usage:{upload:0,question:0,ticket:0,request:1},limits:{uploads:300,questions:2000,tickets:200,requests:100000},model_configured:true,month:'2026-11'});
  if(key==='/admin/policies')return json({policies:[],next_token:null});
  if(key==='/admin/audit')return json({events:[],next_token:null});
  if(key==='/admin/shop')return json({revision:null,current:null,draft:null,updated_at:null,published_at:null});
  throw new Error('Unexpected synthetic route '+key);
 };
 w.eval(script);await until(()=>guest?w.document.querySelector('#guest-welcome:not(.hidden)'):w.document.querySelector('#account-label').textContent==='unit@example.invalid');
 if(!guest)await until(()=>calls.some(c=>c.key==='/shop'));await new Promise(r=>setTimeout(r,5));
 const $=id=>w.document.getElementById(id);return{w,$,calls,errors,click:id=>$(id).click(),nav:view=>w.document.querySelector(`nav [data-view="${view}"]`).click(),submit:id=>$(id).dispatchEvent(new w.Event('submit',{bubbles:true,cancelable:true}))};
}

test('guest welcome prevents private forms being interactive and directs sign-in without API calls',async t=>{const f=await fixture(t,{guest:true});assert.equal(f.$('guest-welcome').classList.contains('hidden'),false);assert.equal(f.$('question-form').hasAttribute('inert'),true);assert.equal(f.$('delete-account').disabled,true);f.click('guest-signin');await until(()=>f.w.__signInRequested);assert.equal(f.calls.length,0);assert.deepEqual(f.errors,[]);});
test('administrator tabs preserve form state and support keyboard navigation',async t=>{const f=await fixture(t,{admin:true,view:'admin'});await until(()=>f.calls.some(c=>c.key==='/admin/shop'));f.click('admin-tab-shop');assert.equal(f.$('admin-panel-shop').classList.contains('hidden'),false);const field=f.$('shop-shop_name');field.value='Unsent synthetic shop';field.dispatchEvent(new f.w.Event('input',{bubbles:true}));f.click('admin-tab-support');f.click('admin-tab-shop');assert.equal(field.value,'Unsent synthetic shop');f.$('admin-tab-shop').dispatchEvent(new f.w.KeyboardEvent('keydown',{key:'ArrowRight',bubbles:true}));assert.equal(f.$('admin-tab-quality').getAttribute('aria-selected'),'true');assert.deepEqual(f.errors,[]);});
test('customer cannot open administrator workspace via a direct hash',async t=>{const f=await fixture(t,{view:'admin'});await until(()=>f.$('view-label').textContent==='Tài khoản');assert.equal(f.w.location.hash,'#account');assert.equal(f.calls.some(c=>c.key.startsWith('/admin/')),false);});
test('invalid PDF-only question keeps the previous answer and draft without sending an AI request',async t=>{const f=await fixture(t);f.$('answer-area').textContent='Previous verified answer';f.$('question').value='Unsent question';f.$('source-scope').value='documents';f.submit('question-form');await until(()=>f.$('notice').textContent.includes('ít nhất'));assert.equal(f.$('answer-area').textContent,'Previous verified answer');assert.equal(f.$('question').value,'Unsent question');assert.equal(f.calls.some(c=>c.key==='/ask'),false);});
test('policy citations open full plaintext source in the current view',async t=>{const f=await fixture(t,{override:key=>key==='/ask'?json({answer:'Synthetic answer',grounded:true,source_scope:'policies',citations:[{source_id:'S1',title:'Synthetic policy',policy_id:'SYNTHETIC',excerpt:'Source excerpt'}]}):key==='/policies/SYNTHETIC'?json({policy_id:'SYNTHETIC',title:'Synthetic policy',content:'<script>Plain text only</script>',category:'Test'}):undefined});f.$('question').value='Synthetic question';f.submit('question-form');await until(()=>f.$('answer-area').textContent.includes('Synthetic answer'));f.$('answer-area').querySelector('.citation-card').click();await until(()=>f.$('policy-dialog-content').textContent.includes('<script>Plain text only</script>'));assert.equal(f.$('policy-dialog').open,true);assert.ok(f.$('policy-dialog-content').textContent.includes('Source excerpt'));assert.equal(f.$('policy-dialog-content').querySelector('script'),null);assert.equal(f.$('answer-area').textContent.includes('Synthetic answer'),true);});
test('errors are visible inside an open support dialog and preserve the unsent reply',async t=>{const id='t-'+'0'.repeat(20)+'-'+'a'.repeat(32);const row={ticket_id:id,subject:'Synthetic ticket',status:'open',updated_at:'2026-11-04T00:00:00Z',message_count:1};const f=await fixture(t,{view:'support',override:(key,o)=>key==='/tickets'?json({tickets:[row],next_token:null}):key==='/tickets/'+id?(o.method==='PATCH'?json({message:'Synthetic conflict'},409):json({...row,revision:'v1',messages:[{role:'customer',body:'Test message',created_at:row.updated_at}],expires_at:2000000000})):undefined});await until(()=>f.$('ticket-list').querySelector('button'));f.$('ticket-list').querySelector('button').click();await until(()=>f.$('ticket-dialog').open);f.$('ticket-reply-message').value='Keep my reply';f.submit('ticket-reply-form');await until(()=>!f.$('ticket-dialog-notice').classList.contains('hidden'));assert.equal(f.$('ticket-dialog-notice').getAttribute('role'),'alert');assert.equal(f.$('ticket-reply-message').value,'Keep my reply');});
test('navigation maintains browser history and canceled logout preserves unsent work',async t=>{const f=await fixture(t);f.$('question').value='Unsent question';const length=f.w.history.length;f.nav('documents');await until(()=>f.w.location.hash==='#documents');assert.equal(f.w.history.length,length+1);f.w.history.back();await until(()=>f.w.location.hash==='#assistant'&&f.$('view-label').textContent==='Trợ lý chính sách');assert.equal(f.$('question').value,'Unsent question');f.click('auth-button');await new Promise(r=>setTimeout(r,5));assert.equal(f.$('account-label').textContent,'unit@example.invalid');assert.equal(f.$('question').value,'Unsent question');assert.equal(f.$('auth-button').disabled,false);});
test('a late document list cannot replace the latest refresh',async t=>{let first,reads=0;const f=await fixture(t,{override:key=>{if(key!=='/documents')return;reads++;if(reads===1)return new Promise(resolve=>first=resolve);return json({documents:[],next_token:null});}});await until(()=>first);f.nav('documents');await until(()=>reads===2);first(json({documents:[{doc_id:'old',title:'STALE PRIVATE TITLE',status:'processed'}],next_token:null}));await new Promise(r=>setTimeout(r,10));assert.equal(f.$('documents-list').textContent.includes('STALE PRIVATE TITLE'),false);});

test('failed PDF validation clears the loading claim and releases the upload control',async t=>{const f=await fixture(t,{view:'documents'});f.submit('upload-form');await until(()=>f.$('notice').textContent.includes('Chọn PDF'));assert.ok(f.$('upload-status').textContent.includes('Chưa xác nhận'));assert.equal(f.$('upload-button').disabled,false);assert.equal(f.$('upload-button').hasAttribute('aria-busy'),false);assert.equal(f.calls.some(c=>c.key==='/documents/upload-session'),false);});
test('PDF completion announces readiness after token-free storage upload',async t=>{const f=await fixture(t,{view:'documents',override:(key,o)=>key==='/documents/upload-session'?json({doc_id:'owned',s3_key:'quarantine/owned/document',upload_url:'https://storage.fixture.invalid/upload-object',upload_fields:{key:'quarantine/owned/document'}}):key==='/upload-object'?(assert.equal(o.headers?.Authorization,undefined),json({})):key==='/documents/submit'?json({status:'pending'}):key==='/documents/owned/status'?json({title:'Synthetic PDF',status:'processed'}):undefined});Object.defineProperty(f.$('pdf-file'),'files',{configurable:true,value:[new f.w.File(['synthetic'],'test.pdf',{type:'application/pdf'})]});f.submit('upload-form');await until(()=>f.$('upload-status').textContent.includes('PDF đã sẵn sàng'));await until(()=>!f.$('upload-button').disabled);assert.ok(f.calls.some(c=>c.key==='/upload-object'));});
test('PDF status arriving after session expiry does not restore a private filename',async t=>{let release;const f=await fixture(t,{view:'documents',override:key=>key==='/documents/upload-session'?json({doc_id:'owned',s3_key:'quarantine/owned/document',upload_url:'https://storage.fixture.invalid/upload-object',upload_fields:{key:'quarantine/owned/document'}}):key==='/upload-object'?json({}):key==='/documents/submit'?json({status:'pending'}):key==='/documents/owned/status'?new Promise(resolve=>release=resolve):undefined});Object.defineProperty(f.$('pdf-file'),'files',{configurable:true,value:[new f.w.File(['synthetic'],'test.pdf',{type:'application/pdf'})]});f.submit('upload-form');await until(()=>release);f.$('policy-keyword').value='PRIVATE SEARCH';f.$('admin-ticket-order').value='PRIVATE ORDER';f.w.__expire();release(json({title:'PRIVATE SYNTHETIC FILENAME',status:'processed'}));await new Promise(r=>setTimeout(r,15));assert.equal(f.$('upload-status').textContent,'');assert.equal(f.$('policy-keyword').value,'');assert.equal(f.$('admin-ticket-order').value,'');assert.equal(f.$('document-count').textContent,'—');assert.equal(f.w.document.body.textContent.includes('PRIVATE SYNTHETIC FILENAME'),false);assert.equal(f.$('question-form').hasAttribute('inert'),true);});

test('unsaved administrator edits cancel page navigation without losing the form',async t=>{const f=await fixture(t,{admin:true,view:'admin'});await until(()=>f.calls.some(c=>c.key==='/admin/shop'));f.click('admin-tab-shop');f.$('shop-shop_name').value='Keep this draft';f.$('shop-shop_name').dispatchEvent(new f.w.Event('input',{bubbles:true}));f.nav('documents');await new Promise(r=>setTimeout(r,5));assert.equal(f.w.location.hash,'#admin');assert.equal(f.$('view-label').textContent,'Quản trị');assert.equal(f.$('shop-shop_name').value,'Keep this draft');});

test('answer feedback sends only structured fields and preserves revision across changes',async t=>{const id='2026-11-04T00:00:00+00:00#feedback';const sent=[];const f=await fixture(t,{override:(key,o)=>key==='/ask'?json({conversation_id:id,quality_version:1,quality_month:'2026-11',answer:'Synthetic answer',grounded:false,citations:[]}):key.endsWith('/feedback')?(sent.push(JSON.parse(o.body)),json({conversation_id:id,quality_month:'2026-11',feedback:{...JSON.parse(o.body),revision:'v'+sent.length,updated_at:'2026-11-04T00:00:0'+sent.length+'Z'}})):undefined});f.$('question').value='PRIVATE SYNTHETIC QUESTION';f.submit('question-form');await until(()=>f.$('answer-area').querySelector('.answer-feedback'));const box=f.$('answer-area').querySelector('.answer-feedback');box.querySelector('button').click();await until(()=>box.textContent.includes('Đã ghi nhận: hữu ích'));const buttons=box.querySelectorAll('button');buttons[1].click();box.querySelector('select').value='unclear';buttons[3].click();await until(()=>sent.length===2);assert.deepEqual(sent[0],{rating:'helpful',reason:null,expected_revision:null});assert.equal(sent[1].expected_revision,'v1');assert.equal(JSON.stringify(sent).includes('PRIVATE'),false);});
test('quality dashboard shows measured counts and changes the cohort month',async t=>{const f=await fixture(t,{admin:true,view:'admin',override:(key,o,w,u)=>key==='/admin/quality'?json({month:u.searchParams.get('month')||'2026-11',available_months:['2026-11','2026-10'],started_at:'2026-11-04T00:00:00Z',counts:{answers:4,grounded:3,refused:1,helpful:2,not_helpful:1,scope_all:2,scope_policies:1,scope_documents:1},citation_rate:75,helpful_rate:66.7,average_response_ms:1200}):undefined});await until(()=>f.$('quality-overview').textContent.includes('75%'));f.click('admin-tab-quality');assert.equal(f.$('admin-panel-quality').classList.contains('hidden'),false);assert.equal(f.$('export-quality').disabled,false);f.$('quality-month').value='2026-10';f.$('quality-month').dispatchEvent(new f.w.Event('change'));await until(()=>f.calls.some(c=>c.url.endsWith('?month=2026-10')));assert.equal(f.$('quality-month').value,'2026-10');});
test('policy validity fields load the saved window and reject an inverted draft locally',async t=>{
 const fields={title:'Synthetic refund',category:'Support',content:'DEMO refund policy',keywords:[],effective_from:'2026-11-06',effective_until:'2026-11-10'};
 const record={policy_id:'SYNTHETIC',revision:'rev-1',publication_state:'published',validity_state:'upcoming',current:fields,draft:null};
 const f=await fixture(t,{admin:true,view:'admin',override:(key,options)=>key==='/admin/policies'?json({policies:[{...record,...fields}],next_token:null}):key==='/admin/policies/SYNTHETIC'?json(record):undefined});
 await until(()=>f.$('admin-policy-list').querySelector('button'));
 assert.match(f.$('admin-policy-list').textContent,/Chưa tới ngày/);
 f.$('admin-policy-list').querySelector('button').click();await until(()=>f.$('policy-effective-from').value==='2026-11-06');
 assert.match(f.$('policy-window-preview').textContent,/UTC\+7/);
 f.$('policy-effective-until').value='2026-11-05';f.$('policy-effective-until').dispatchEvent(new f.w.Event('input',{bubbles:true}));
 assert.match(f.$('policy-window-preview').textContent,/không được trước/);
 f.submit('admin-policy-form');await until(()=>f.$('notice').textContent.includes('không được trước'));
 assert.equal(f.calls.some(c=>c.options.method==='PATCH'),false);assert.deepEqual(f.errors,[]);
});
test('admin validity filter is sent explicitly without discarding the open draft',async t=>{
 const f=await fixture(t,{admin:true,view:'admin'});await until(()=>f.calls.some(c=>c.key==='/admin/policies'));
 f.$('admin-policy-form').elements.title.value='Unsent policy';f.$('admin-policy-form').elements.title.dispatchEvent(new f.w.Event('input',{bubbles:true}));
 f.$('admin-policy-validity').value='expired';f.submit('admin-policy-search');
 await until(()=>f.calls.some(c=>c.url.includes('validity=expired')));
 assert.equal(f.$('admin-policy-form').elements.title.value,'Unsent policy');assert.deepEqual(f.errors,[]);
});
test('a corrupt imported policy window remains editable for repair',async t=>{
 const fields={title:'Synthetic legacy import',category:'Support',content:'DEMO policy',keywords:[],effective_until:'invalid'};
 const record={policy_id:'SYNTHETIC',revision:'rev-1',publication_state:'published',validity_state:'invalid',current:fields,draft:null};
 const f=await fixture(t,{admin:true,view:'admin',override:key=>key==='/admin/policies'?json({policies:[{...record,...fields}],next_token:null}):key==='/admin/policies/SYNTHETIC'?json(record):undefined});
 await until(()=>f.$('admin-policy-list').querySelector('button'));f.$('admin-policy-list').querySelector('button').click();
 await until(()=>f.$('admin-policy-form').elements.title.value===fields.title);
 assert.match(f.$('policy-live-validity').textContent,/không hợp lệ/);assert.equal(f.$('policy-effective-until').value,'');assert.deepEqual(f.errors,[]);
});
test('staff note save preserves a public draft and public reply preserves a private note draft',async t=>{
 const id='t-'+'0'.repeat(20)+'-'+'b'.repeat(32),route='/admin/tickets/customer/'+id;
 let record={ticket_id:id,owner_id:'customer',subject:'Synthetic case',status:'open',revision:'v1',updated_at:'2026-11-05T00:00:00Z',expires_at:2000000000,message_count:1,messages:[{role:'customer',body:'Shared request',created_at:'2026-11-05T00:00:00Z'}],assignment:'mine',assigned_to:'synthetic-user',internal_notes:[],internal_note_count:0,assignment_events:[]};
 const f=await fixture(t,{admin:true,view:'admin',override:(key,o)=>{
  if(key==='/admin/tickets')return json({tickets:[record],next_token:null});
  if(key===route){if(o.method==='PATCH'){const body=JSON.parse(o.body);if(body.action==='note')record={...record,revision:'v2',internal_notes:[{author:'synthetic-user',body:body.note,created_at:record.updated_at}],internal_note_count:1};else record={...record,revision:'v3',status:body.status};}return json(record);}
 }});
 await until(()=>f.$('admin-ticket-list').querySelector('button'));f.$('admin-ticket-list').querySelector('button').click();await until(()=>f.$('ticket-dialog').open);
 f.$('ticket-reply-message').value='Unsent public reply';f.$('ticket-note-text').value='PRIVATE INTERNAL NOTE';f.submit('ticket-note-form');
 await until(()=>f.$('ticket-internal-notes').textContent.includes('PRIVATE INTERNAL NOTE'));
 assert.equal(f.$('ticket-reply-message').value,'Unsent public reply');assert.equal(f.$('ticket-note-text').value,'');assert.equal(f.$('ticket-thread').textContent.includes('PRIVATE INTERNAL NOTE'),false);
 f.$('ticket-note-text').value='Unsent second internal note';f.submit('ticket-reply-form');await until(()=>f.calls.filter(c=>c.key===route&&c.options.method==='PATCH').length===2&&!f.$('send-ticket-reply').disabled);
 assert.equal(f.$('ticket-note-text').value,'Unsent second internal note');assert.equal(f.$('ticket-reply-message').value,'');assert.deepEqual(f.errors,[]);
});
test('private ticket drafts guard close/reload and session expiry clears internal content',async t=>{
 const id='t-'+'0'.repeat(20)+'-'+'c'.repeat(32),record={ticket_id:id,owner_id:'customer',subject:'Synthetic case',status:'open',revision:'v1',updated_at:'2026-11-05T00:00:00Z',expires_at:2000000000,message_count:1,messages:[],assignment:'mine',assigned_to:'synthetic-user',internal_notes:[{author:'synthetic-user',body:'PRIVATE STORED NOTE',created_at:'2026-11-05T00:00:00Z'}],internal_note_count:1,assignment_events:[]};
 const f=await fixture(t,{admin:true,view:'admin',override:key=>key==='/admin/tickets'?json({tickets:[record],next_token:null}):key==='/admin/tickets/customer/'+id?json(record):undefined});
 await until(()=>f.$('admin-ticket-list').querySelector('button'));f.$('admin-ticket-list').querySelector('button').click();await until(()=>f.$('ticket-dialog').open);
 f.$('ticket-note-text').value='UNSENT PRIVATE NOTE';f.click('close-ticket-dialog');assert.equal(f.$('ticket-dialog').open,true);
 const before=f.calls.length;f.click('reload-ticket');await new Promise(r=>setTimeout(r,5));assert.equal(f.calls.length,before);
 f.w.__expire();await until(()=>!f.$('ticket-dialog').open);
 assert.equal(f.$('ticket-note-text').value,'');assert.equal(f.$('ticket-internal-notes').textContent,'');assert.equal(f.$('ticket-assignment-label').textContent,'');assert.deepEqual(f.errors,[]);
});
test('assignment queue filter is explicit and does not discard an unsent internal note',async t=>{
 const f=await fixture(t,{admin:true,view:'admin'});await until(()=>f.calls.some(c=>c.key==='/admin/tickets'));
 f.$('ticket-note-text').value='Unsent staff draft';f.$('admin-ticket-assignee').value='mine';f.$('admin-ticket-assignee').dispatchEvent(new f.w.Event('change',{bubbles:true}));
 await until(()=>f.calls.some(c=>c.key==='/admin/tickets'&&c.url.includes('assignee=mine')));
 assert.equal(f.$('ticket-note-text').value,'Unsent staff draft');assert.deepEqual(f.errors,[]);
});
test('customer dialog has no staff note or assignment controls',async t=>{
 const id='t-'+'0'.repeat(20)+'-'+'d'.repeat(32),record={ticket_id:id,subject:'Customer request',status:'open',revision:'v1',updated_at:'2026-11-05T00:00:00Z',expires_at:2000000000,message_count:1,messages:[]};
 const f=await fixture(t,{view:'support',override:key=>key==='/tickets'?json({tickets:[record],next_token:null}):key==='/tickets/'+id?json(record):undefined});
 await until(()=>f.$('ticket-list').querySelector('button'));f.$('ticket-list').querySelector('button').click();await until(()=>f.$('ticket-dialog').open);
 assert.equal(f.$('ticket-staff-controls').classList.contains('hidden'),true);assert.equal(f.$('ticket-note-fields').disabled,true);assert.equal(f.$('claim-ticket').disabled,true);assert.equal(f.$('ticket-internal-notes').textContent,'');assert.deepEqual(f.errors,[]);
});

test('history keeps the original excerpt when its policy expires', async t => {
  const f = await fixture(t, {
    view: 'history',
    override: key => {
      if (key === '/conversations') return json({
        conversations: [{
          conversation_id: 'archived-policy-answer',
          created_at: '2026-11-04T00:00:00Z',
          question: 'Chính sách lúc đó là gì?',
          answer: 'Trả lời từ bản cũ',
          grounded: true,
          citations: [{source_id: 'S1', policy_id: 'ARCHIVED', title: 'Bảo hành', excerpt: 'Đoạn trích lúc hỏi'}],
        }],
      });
      if (key === '/policies/ARCHIVED') return json({message: 'Not found'}, 404);
    },
  });
  await until(() => f.$('history-list').querySelector('.citation-card'));
  f.$('history-list').querySelector('.citation-card').click();
  await until(() => f.$('policy-dialog-content').textContent.includes('hết hiệu lực'));
  assert.equal(f.$('policy-dialog').open, true);
  assert.equal(f.$('policy-dialog-content').querySelector('blockquote').textContent, 'Đoạn trích lúc hỏi');
});

test('PDF citation displays its page and excerpt even when the original PDF is unavailable', async t => {
  const f = await fixture(t, {
    override: key => {
      if (key === '/ask') return json({
        answer: 'Synthetic PDF answer',
        grounded: true,
        citations: [{source_id: 'S1', doc_id: 'owned', title: 'Hướng dẫn', page: 3, excerpt: 'Nội dung trang 3'}],
      });
      if (key === '/documents/owned/download') return json({message: 'Not found'}, 404);
    },
  });
  f.$('question').value = 'Tìm thông tin trong PDF';
  f.submit('question-form');
  await until(() => f.$('answer-area').querySelector('.citation-card'));
  f.$('answer-area').querySelector('.citation-card').click();
  await until(() => f.$('policy-dialog').open);
  assert.match(f.$('policy-dialog-title').textContent, /Trang 3/);
  assert.equal(f.calls.some(call => call.key.endsWith('/download')), false);
  [...f.$('policy-dialog-content').querySelectorAll('button')].find(b => b.textContent === 'Tải PDF gốc').click();
  await until(() => f.$('policy-dialog-content').textContent.includes('không còn truy cập'));
  assert.equal(f.$('policy-dialog-content').querySelector('blockquote').textContent, 'Nội dung trang 3');
});

test('an answer arriving late preserves the next question being composed', async t => {
  let respond;
  const f = await fixture(t, {
    override: key => key === '/ask' ? new Promise(resolve => { respond = resolve; }) : undefined,
  });
  f.$('question').value = 'Câu đầu tiên';
  f.submit('question-form');
  await until(() => respond);
  f.$('question').value = 'Câu đang soạn';
  f.$('question').dispatchEvent(new f.w.Event('input', {bubbles: true}));
  respond(json({answer: 'Trả lời câu đầu', grounded: false, citations: []}));
  await until(() => f.$('answer-area').textContent.includes('Trả lời câu đầu'));
  assert.equal(f.$('question').value, 'Câu đang soạn');
  assert.match(f.$('question-count').textContent, /^13 /);
});

test('recovering an uploaded PDF reuses its existing ID and asks from that PDF only', async t => {
  let uploaded = false;
  let submits = 0;
  let question;
  const document = {doc_id:'owned', title:'Synthetic PDF', s3_key:'quarantine/owned/document'};
  const f = await fixture(t, {
    view: 'documents',
    override: (key, options) => {
      if (key === '/documents') return json({documents: uploaded ? [
        {...document, status: submits > 1 ? 'processed' : 'awaiting_upload'},
        {doc_id:'other', title:'Other PDF', status:'processed'},
      ] : [], next_token:null});
      if (key === '/documents/upload-session') return json({
        ...document, upload_url:'https://storage.fixture.invalid/upload-object',
        upload_fields:{key:document.s3_key},
      });
      if (key === '/upload-object') { uploaded = true; return json({}); }
      if (key === '/documents/submit') {
        assert.deepEqual(JSON.parse(options.body), {doc_id:'owned', s3_key:document.s3_key});
        return ++submits === 1 ? json({message:'Transient failure'}, 503) : json({status:'pending'});
      }
      if (key === '/documents/owned/status') return json({...document,status:'processed'});
      if (key === '/ask') {
        question = JSON.parse(options.body);
        return json({answer:'Synthetic answer', citations:[], grounded:false});
      }
    },
  });
  Object.defineProperty(f.$('pdf-file'), 'files', {configurable:true, value:[new f.w.File(['synthetic'],'test.pdf',{type:'application/pdf'})]});
  f.submit('upload-form');
  const findButton = label => [...f.$('documents-list').querySelectorAll('button')].find(b => b.textContent === label);
  await until(() => findButton('Gửi xử lý'));
  assert.match(f.$('upload-status').textContent, /Tệp đã tải lên/);
  findButton('Gửi xử lý').click();
  await until(() => f.$('upload-status').textContent.includes('PDF đã sẵn sàng'));
  const row = [...f.$('documents-list').rows].find(row => row.textContent.includes('Synthetic PDF'));
  [...row.querySelectorAll('button')].find(b => b.textContent === 'Hỏi từ PDF này').click();
  await until(() => f.$('source-scope').value === 'documents');
  f.$('question').value = 'Tìm quy định trong PDF';
  f.submit('question-form');
  await until(() => question);
  assert.deepEqual(question.document_ids, ['owned']);
  assert.equal(question.source_scope, 'documents');
  assert.equal(f.calls.filter(c => c.key === '/upload-object').length, 1);
});

test('history can compare a shop policy and a PDF excerpt without new API calls', async t => {
  const f = await fixture(t, {
    view:'history',
    override:key => key === '/conversations' ? json({conversations:[{
      conversation_id:'comparison',
      created_at:'2026-11-04T00:00:00Z',
      question:'Thời hạn là bao lâu?',
      answer:'Nguồn ghi hai mốc khác nhau.',
      grounded:true,
      citations:[
        {source_id:'S1', policy_id:'RETURNS', title:'Đổi trả', excerpt:'7 ngày kể từ ngày nhận'},
        {source_id:'S2', doc_id:'owned', title:'Tài liệu khách', page:2, excerpt:'14 ngày kể từ ngày mua'},
      ],
    }]}) : undefined,
  });
  const compare = () => [...f.$('history-list').querySelectorAll('button')].find(b => b.textContent === 'Đối chiếu 2 nguồn');
  await until(compare);
  const calls = f.calls.length;
  compare().click();
  await until(() => f.$('policy-dialog').open);
  const excerpts = [...f.$('policy-dialog-content').querySelectorAll('blockquote')].map(b => b.textContent);
  assert.deepEqual(excerpts,['7 ngày kể từ ngày nhận','14 ngày kể từ ngày mua']);
  assert.match(f.$('policy-dialog-content').textContent, /PDF cá nhân.*Trang 2/);
  assert.equal(f.calls.length,calls);
});

test('history filters paginated records by Vietnamese text and reuses a question without submitting', async t => {
  const first = {conversation_id:'shipping', created_at:'2026-11-10T00:00:00Z', question:'Giao hàng khi nào?', answer:'Xem lịch giao hàng.', grounded:false};
  const second = {conversation_id:'warranty', created_at:'2026-11-09T00:00:00Z', question:'Bảo hành củ sạc bao lâu?', answer:'Mười hai tháng.', grounded:true,
    citations:[{source_id:'S1', policy_id:'WARRANTY', title:'Chính sách phụ kiện', excerpt:'Bảo hành 12 tháng'}]};
  const f = await fixture(t, {
    view:'history',
    override:(key, options, window, url) => {
      if (key === '/conversations') return json(url.searchParams.has('next_token')
        ? {conversations:[second],next_token:null}
        : {conversations:[first],next_token:'older'});
    },
  });
  await until(() => f.$('history-list').querySelector('details'));
  f.$('history-filter').value = 'bao hanh';
  f.$('history-filter').dispatchEvent(new f.w.Event('input', {bubbles:true}));
  assert.match(f.$('history-results').textContent, /^0 \/ 1/);
  f.click('more-history');
  await until(() => f.$('history-list').querySelector('[data-conversation-id="warranty"]'));
  assert.match(f.$('history-results').textContent, /^1 \/ 2/);
  const filter = f.$('history-source-filter');
  filter.value = 'unanswered';
  filter.dispatchEvent(new f.w.Event('change'));
  assert.match(f.$('history-results').textContent, /^0 \/ 2/);
  filter.value = 'grounded';
  filter.dispatchEvent(new f.w.Event('change'));
  const record = f.$('history-list').querySelector('[data-conversation-id="warranty"]');
  assert.equal(record.hidden, false);
  record.open = true;
  const reuse = [...record.querySelectorAll('button')].find(b => b.textContent === 'Dùng lại câu hỏi');
  f.$('question').value = 'Giữ câu đang soạn';
  reuse.click();
  await until(() => !reuse.disabled);
  assert.equal(f.$('question').value, 'Giữ câu đang soạn');
  f.$('question').value = '';
  reuse.click();
  await until(() => f.$('question').value === second.question);
  assert.equal(f.w.location.hash, '#assistant');
  assert.equal(f.calls.some(call => call.key === '/ask'), false);
});

test('copy answer writes only displayed text and citations to the clipboard', async t => {
  const f = await fixture(t, {
    override:key => key === '/ask' ? json({
      answer:'Bảo hành 12 tháng.',
      grounded:true,
      citations:[{source_id:'S1',doc_id:'private-id',page:4,title:'Hướng dẫn',excerpt:'Thời hạn 12 tháng'}],
    }) : undefined,
  });
  let copied;
  Object.defineProperty(f.w.navigator, 'clipboard', {value:{writeText:async value => { copied=value; }}});
  f.$('question').value = 'Câu hỏi riêng của tôi';
  f.submit('question-form');
  const copy = () => [...f.$('answer-area').querySelectorAll('button')].find(b => b.textContent === 'Sao chép câu trả lời');
  await until(copy);
  copy().click();
  await until(() => copied);
  assert.equal(copied, 'Bảo hành 12 tháng.\n\nNguồn tham khảo\n\nS1 · Hướng dẫn — Trang 4\nThời hạn 12 tháng');
});

test('navigation disclosure closes on Escape and after choosing a page', async t => {
  const f = await fixture(t);
  const toggle = f.$('nav-toggle');
  const navigation = f.$('main-navigation');
  f.click('nav-toggle');
  assert.equal(toggle.getAttribute('aria-expanded'), 'true');
  const history = navigation.querySelector('[data-view="history"]');
  history.dispatchEvent(new f.w.KeyboardEvent('keydown', {key:'Escape',bubbles:true,cancelable:true}));
  assert.equal(toggle.getAttribute('aria-expanded'), 'false');
  assert.equal(f.w.document.activeElement, toggle);
  f.click('nav-toggle');
  f.nav('history');
  await until(() => f.w.location.hash === '#history');
  assert.equal(toggle.getAttribute('aria-expanded'), 'false');
  assert.equal(history.getAttribute('aria-current'), 'page');
  assert.equal(f.w.document.activeElement.textContent, 'Lịch sử hỏi đáp.');
});

test('PDF library filters rows and the reader pages through safe text', async t => {
  const f = await fixture(t, {
    view:'documents',
    override:(key, options, window, url) => {
      if (key === '/documents') return json({documents:[
        {doc_id:'owned', title:'Bảo hành củ sạc', status:'processed',page_count:2},
        {doc_id:'working', title:'Đổi trả', status:'pending'},
      ],next_token:null});
      if (key === '/documents/owned/text') {
        const page = Number(url.searchParams.get('page'));
        return json({doc_id:'owned',title:'Bảo hành củ sạc',page,page_count:2,chunks:page === 1 ? ['Bảo hành <script>plain</script>'] : [],truncated:false});
      }
    },
  });
  await until(() => f.$('documents-list').querySelector('[data-document-id="owned"]'));
  f.$('document-filter').value = 'bao hanh';
  f.$('document-filter').dispatchEvent(new f.w.Event('input', {bubbles:true}));
  assert.match(f.$('document-results').textContent, /^1 \/ 2/);
  assert.equal(f.$('documents-list').querySelector('[data-document-id="working"]').hidden,true);
  [...f.$('documents-list').querySelectorAll('button')].find(b => b.textContent === 'Xem văn bản').click();
  await until(() => f.$('document-page-number').textContent === 'Trang 1 / 2');
  assert.equal(f.$('document-text-content').textContent, 'Bảo hành <script>plain</script>');
  assert.equal(f.$('document-text-content').querySelector('script'), null);
  f.$('document-text-find').value = 'bao hanh';
  f.$('document-text-find').dispatchEvent(new f.w.Event('input', {bubbles:true}));
  assert.equal(f.$('document-text-content').querySelector('mark').textContent, 'Bảo hành');
  assert.match(f.$('document-text-matches').textContent, /^1 kết quả/);
  let download;
  f.w.URL.createObjectURL = () => 'blob:synthetic';
  f.w.URL.revokeObjectURL = () => {};
  f.w.HTMLAnchorElement.prototype.click = function () { download = this.download; };
  f.click('download-document-page');
  assert.equal(download, 'policy-assistant-trang-1.txt');
  assert.equal(f.$('previous-document-page').disabled, true);
  f.click('next-document-page');
  await until(() => f.$('document-page-number').textContent === 'Trang 2 / 2');
  assert.equal(f.$('copy-document-page').disabled, true);
  assert.equal(f.$('download-document-page').disabled, true);
  assert.equal(f.$('next-document-page').disabled, true);
  assert.match(f.$('document-text-status').textContent, /không có văn bản/);
  f.$('document-page-input').value = '1';
  f.submit('jump-document-page');
  await until(() => f.$('document-page-number').textContent === 'Trang 1 / 2');
});

test('PDF page response cannot restore private text after session expiry', async t => {
  let respond;
  const f = await fixture(t, {
    view:'documents',
    override:key => {
      if (key === '/documents') return json({documents:[{doc_id:'owned',title:'Test PDF',status:'processed'}]});
      if (key === '/documents/owned/text') return new Promise(resolve => { respond = resolve; });
    },
  });
  const open = () => [...f.$('documents-list').querySelectorAll('button')].find(b => b.textContent === 'Xem văn bản');
  await until(open);
  open().click();
  await until(() => respond);
  f.w.__expire();
  respond(json({doc_id:'owned',page:1,page_count:1,chunks:['PRIVATE EXTRACT'],truncated:false}));
  await new Promise(resolve => setTimeout(resolve, 10));
  assert.equal(f.$('document-text-dialog').open,false);
  assert.equal(f.$('document-text-content').textContent,'');
  assert.equal(f.$('copy-document-page').disabled,true);
});

test('policy search saves only a shortcut and opens the latest published text', async t => {
  const original = {policy_id:'WARRANTY',title:'Bảo hành phụ kiện',category:'Bảo hành',content:'A'.repeat(350)};
  const f = await fixture(t, {
    view:'policies',
    override:key => {
      if (key === '/policies') return json({policies:[original],next_token:null});
      if (key === '/policies/WARRANTY') return json({...original,content:'Nội dung công bố mới'});
    },
  });
  f.$('policy-keyword').value = 'bảo hành';
  f.submit('policy-form');
  await until(() => f.$('policy-results').querySelector('.policy-directory-card'));
  assert.equal(f.$('policy-results').textContent.includes(original.content), false);
  f.$('policy-results').querySelector('[data-saved-policy]').click();
  assert.equal(f.$('saved-policy-count').textContent, '1');
  assert.deepEqual(JSON.parse(f.w.localStorage.getItem('policy-assistant:saved-policies:synthetic-user')),
    [{policy_id:'WARRANTY',title:'Bảo hành phụ kiện'}]);
  f.click('saved-policies');
  [...f.$('policy-results').querySelectorAll('button')].find(b => b.textContent === 'Đọc chính sách').click();
  await until(() => f.$('policy-dialog-content').textContent.includes('Nội dung công bố mới'));
  let copied;
  Object.defineProperty(f.w.navigator, 'clipboard', {value:{writeText:async value => { copied=value; }}});
  [...f.$('policy-dialog-content').querySelectorAll('button')].find(b => b.textContent === 'Sao chép liên kết').click();
  await until(() => copied);
  assert.equal(copied, 'https://ui.fixture.invalid/#policy/WARRANTY');
  f.w.__expire();
  assert.equal(f.$('saved-policy-count').textContent,'0');
  assert.equal(f.$('policy-dialog-content').textContent,'');
});

test('a shared policy route opens the correct published policy', async t => {
  const f = await fixture(t, {
    view:'policy/RETURNS',
    override:key => key === '/policies/RETURNS'
      ? json({policy_id:'RETURNS',title:'Đổi trả',content:'Chính sách đang công bố.'}) : undefined,
  });
  await until(() => f.$('policy-dialog-content').textContent.includes('Chính sách đang công bố.'));
  assert.equal(f.w.location.hash, '#policy/RETURNS');
  assert.equal(f.$('policy-dialog').open, true);
  assert.equal(f.$('view-label').textContent, 'Chính sách chung');
});


test('a guest can carry a shared policy through sign-in', async t => {
  const f = await fixture(t, {guest:true,view:'policy/RETURNS'});
  await until(() => f.$('policy-library-status').textContent.includes('Đăng nhập'));
  f.click('guest-signin');
  await until(() => f.w.__signInRequested);
  assert.equal(f.w.__signInOptions.state.policy, 'RETURNS');
  assert.equal(f.calls.length, 0);
});
