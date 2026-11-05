import './app.css';
import {FeedbackStore,feedbackReasons} from './feedback.js';
import {LatestTask,pollDocument} from './ui-flow.js';
import {ShopEditor,shopFields} from './shop-editor.js';
import { UserManager, WebStorageStateStore, Log } from 'oidc-client-ts';
import { createApi, uploadPdf, statusText } from './api.js';
import { PolicyEditor, policyStates, validityStates, validityText } from './policy-editor.js';
import { SupportClient, supportStates, supportCategories, supportPriorities, questionPayload } from './support-client.js';

Log.setLevel(Log.NONE);
const $ = id => document.getElementById(id);
const state = { user:null, profile:null, docs:[], docToken:null, historyToken:null, policyToken:null, policyKeyword:'', auditToken:null, selected:new Set(), cache:new Map(), view:'assistant' };
let manager, api, config;
const latestTasks=new LatestTask();
const feedbackStore=new FeedbackStore((path,options)=>{needApi();return api(path,options);});
let qualityReport=null;
let sessionEpoch=0, signingOut=false;
let adminPolicyToken=null,adminPolicyKeyword='',adminListEpoch=0;
let ticketToken=null,adminTicketToken=null,ticketListEpoch=0,adminTicketListEpoch=0;
const shopEditor=new ShopEditor((path,options)=>{needApi();return api(path,options);},renderShopControls);
const supportClient=new SupportClient((path,options)=>{needApi();return api(path,options);},renderSupportControls);
const policyEditor=new PolicyEditor((path,options)=>{needApi();return api(path,options);},renderPolicyEditorStatus);
const labels = {assistant:'Trợ lý chính sách',documents:'Tài liệu của tôi',policies:'Chính sách chung',history:'Lịch sử hỏi đáp',support:'Yêu cầu hỗ trợ',shop:'Thông tin shop',admin:'Quản trị',account:'Tài khoản'};
function node(tag, content, className) { const element=document.createElement(tag); if(content!==undefined) element.textContent=content; if(className) element.className=className; return element; }
function noticeAt(target,message,error=false){target.replaceChildren(node('span',message,'notice-message'));const close=node('button','×','notice-dismiss');close.type='button';close.setAttribute('aria-label','Ẩn thông báo');close.onclick=()=>target.classList.add('hidden');target.append(close);target.className=`notice${error?' error':''}`;target.setAttribute('role',error?'alert':'status');}
function notify(message,error=false){if($('ticket-dialog').open){noticeAt($('ticket-dialog-notice'),message,error);return;}noticeAt($('notice'),message,error);}
function fail(error){const message=error.status===401?'Phiên đăng nhập đã hết hạn hoặc bạn chưa đăng nhập. Hãy đăng nhập để tiếp tục.':error.status===403?'Tài khoản này không có quyền thực hiện thao tác.':error.status===429?'Đã đạt hạn mức sử dụng trong ngày hoặc tháng. Hãy kiểm tra hạn mức và thử lại sau.':error instanceof TypeError&&/fetch|network/i.test(error.message)?'Kết nối bị gián đoạn. Hãy kiểm tra trạng thái trước khi gửi lại để tránh tạo trùng dữ liệu.':error.message||'Chưa thể hoàn tất. Vui lòng thử lại.';notify(message,true);}
function button(label,action,className='text-button') { const item=node('button',label,className);item.type='button';item.addEventListener('click',()=>guard(item,action));return item; }
async function guard(control,action) { if(control?.disabled)return; if(control){control.disabled=true;control.setAttribute('aria-busy','true');}try{return await action();}catch(error){fail(error);}finally{if(control){control.disabled=false;control.removeAttribute('aria-busy');}if(control?.closest('#admin-policy-form')||control?.id==='new-policy')renderPolicyEditorStatus();if(control?.closest('#ticket-reply-form'))renderSupportControls();if(control?.closest('#shop-form')||control?.id==='reload-shop')renderShopControls();} }
function needApi() { if(!api)throw new Error('Dịch vụ chưa được kết nối.');if(!state.user)throw Object.assign(new Error('Vui lòng đăng nhập.'),{status:401}); }
function groups() { const value=state.profile?.groups||[];return Array.isArray(value)?value:String(value).replace(/[\[\]"]/g,'').split(',').map(s=>s.trim()); }
function signedIn() {
  $('guest-welcome').classList.toggle('hidden',Boolean(state.user));
  document.querySelectorAll('form').forEach(form=>{if(state.user)form.removeAttribute('inert');else form.setAttribute('inert','');});
  document.querySelectorAll('[data-auth-control]').forEach(control=>{control.disabled=!state.user;});
  document.querySelector('.danger-zone').classList.toggle('hidden',!state.user);

  $('support-limit-note').textContent=`Chỉ chia sẻ thông tin bạn nhập. PDF và lịch sử hỏi đáp không tự đính kèm. Không gửi email tự động; xem phản hồi tại mục này. Tối đa ${state.profile?.limits?.tickets_per_day??5} yêu cầu/ngày UTC, 20 tin nhắn/yêu cầu; lưu tối đa 90 ngày từ khi tạo.`;
  $('account-label').textContent=state.profile?.email||'Khách';$('avatar').textContent=(state.profile?.email||'P')[0].toUpperCase();$('auth-button').textContent=state.user?'Đăng xuất':'Đăng nhập / Đăng ký';$('admin-nav').classList.toggle('hidden',!groups().includes('administrators'));
  $('profile-info').replaceChildren();
  if(state.profile){$('profile-info').append(node('p',state.profile.email),node('p',`Mỗi ngày (UTC): ${state.profile.limits.uploads_per_day} lượt tải PDF và ${state.profile.limits.questions_per_day} câu hỏi, ${state.profile.limits.tickets_per_day??5} yêu cầu hỗ trợ. Hạn mức chung của dịch vụ vẫn được áp dụng.`, 'small'));
    if(!state.profile.ai_available)notify('AI chưa được cấu hình. Bạn vẫn có thể quản lý tài liệu và tìm chính sách.');}
}
function clearPrivateState() {
  feedbackStore.clear();qualityReport=null;$('quality-overview').replaceChildren();$('quality-feedback').replaceChildren();$('quality-month').replaceChildren();$('export-quality').disabled=true;
  latestTasks.clear();state.policyToken=null;state.policyKeyword='';state.auditToken=null;$('document-count').textContent='—';$('policy-keyword').value='';$('ticket-lookup-form').reset();$('admin-ticket-category').value='';$('admin-ticket-priority').value='';$('admin-ticket-filter').value='open';for(const id of ['more-documents','more-sources','more-history','more-policies','more-tickets','more-admin-tickets','more-audit'])$(id).classList.add('hidden');$('answer-area').setAttribute('aria-busy','false');$('question-count').textContent='0 / 2.000 ký tự';$('policy-dialog').close();$('policy-dialog-content').replaceChildren();
  shopEditor.clear();fillShopEditor(null);$('shop-profile').replaceChildren(node('p','Đăng nhập để xem thông tin shop.'));$('shop-context').classList.add('hidden');
  supportClient.clear();ticketToken=null;adminTicketToken=null;ticketListEpoch++;adminTicketListEpoch++;
  $('ticket-dialog').close();$('ticket-thread').replaceChildren();$('new-ticket-form').reset();$('ticket-reply-form').reset();
  policyEditor.clear();adminPolicyToken=null;adminPolicyKeyword='';adminListEpoch++;
  sessionEpoch++;state.user=null;state.profile=null;state.docs=[];state.selected.clear();state.cache.clear();state.docToken=null;state.historyToken=null;
  for(const id of ['answer-area','history-list','documents-list','source-selector','audit-list','usage-overview','policy-results','admin-policy-list','ticket-list','admin-ticket-list'])$(id).replaceChildren();
  $('question').value='';$('pdf-file').value='';$('upload-status').textContent='';$('delete-confirmation').value='';fillPolicyEditor(null);$('admin-policy-keyword').value='';$('more-admin-policies').classList.add('hidden');
  $('notice').classList.add('hidden');signedIn();
}
async function navigate(view,{historyMode='push',focus=false}={}) {
  if(!labels[view])view='assistant';
  if(view==='admin'&&!groups().includes('administrators')){view='account';notify('Quản trị chỉ dành cho tài khoản được cấp quyền.',true);}
  if(state.view==='admin'&&view!=='admin'&&(policyEditor.dirty||shopEditor.dirty)&&!confirm('Rời trang khi có thay đổi chưa lưu?'))return false;
  if(state.view!==view&&(state.view==='support'||$('ticket-dialog').open)&&supportUnsaved()&&!confirm('Rời trang khi nội dung hỗ trợ chưa được gửi?'))return false;
  state.view=view;
  document.querySelectorAll('[data-panel]').forEach(panel=>panel.classList.toggle('hidden',panel.dataset.panel!==view));
  document.querySelectorAll('nav [data-view]').forEach(control=>{const active=control.dataset.view===view;control.classList.toggle('active',active);if(active)control.setAttribute('aria-current','page');else control.removeAttribute('aria-current');});
  $('view-label').textContent=labels[view];if(historyMode==='none'&&location.hash!==`#${view}`)history.replaceState(null,'',`#${view}`);if(historyMode!=='none'&&location.hash!==`#${view}`)history[historyMode==='replace'?'replaceState':'pushState'](null,'',`#${view}`);
  if(focus){const heading=document.querySelector(`[data-panel="${view}"] h1`);heading?.setAttribute('tabindex','-1');heading?.focus({preventScroll:true});window.scrollTo({top:0,left:0,behavior:'auto'});}
  if(!state.user)return true;
  if(view==='documents'||view==='assistant')await loadDocs(false);
  if(view==='history')await loadHistory(false);
  if(view==='support')await loadTickets();
  if(view==='shop')await loadShopProfile();
  if(view==='admin')await loadAdmin();
  return true;
}
window.addEventListener('hashchange',()=>guard(null,async()=>{if(!await navigate(location.hash.slice(1),{historyMode:'none',focus:true}))history.replaceState(null,'',`#${state.view}`);}));
function renderSources() {
  $('source-selector').replaceChildren();
  const visible=new Map(state.docs.map(d=>[d.doc_id,d]));for(const id of state.selected)if(state.cache.has(id))visible.set(id,state.cache.get(id));const ready=[...visible.values()].filter(d=>d.status==='processed');
  for(const doc of ready){const label=node('label',undefined,'source-option');const check=node('input');check.type='checkbox';check.disabled=$('source-scope').value==='policies';check.checked=state.selected.has(doc.doc_id);check.addEventListener('change',()=>{if(check.checked&&state.selected.size>=10){check.checked=false;notify('Chọn tối đa 10 tài liệu.',true);return;}check.checked?state.selected.add(doc.doc_id):state.selected.delete(doc.doc_id);updateScopeLabel();});const name=node('span',doc.title||doc.filename);name.append(node('small',`${doc.page_count||'—'} trang · Sẵn sàng`));label.append(check,name);$('source-selector').append(label);}
  if(!ready.length)$('source-selector').append(node('p','Chưa có PDF đã xử lý. Tải tài liệu có văn bản để bắt đầu.','empty-small'));updateScopeLabel();
}
async function loadDocs(more=false) {
  needApi();const isCurrent=latestTasks.begin('documents');const result=await api(`/documents?limit=20${more&&state.docToken?`&next_token=${encodeURIComponent(state.docToken)}`:''}`);
  if(!isCurrent())return;
  state.docs=more?[...state.docs,...result.documents]:result.documents;state.docToken=result.next_token;
  $('more-documents').classList.toggle('hidden',!state.docToken);$('more-sources').classList.toggle('hidden',!state.docToken);$('document-count').textContent=`${state.docs.length}${state.docToken?'+':''}`;
  $('documents-list').replaceChildren();
  for(const doc of state.docs){state.cache.set(doc.doc_id,doc);if(doc.status!=='processed')state.selected.delete(doc.doc_id);}
  for(const doc of state.docs){const tr=node('tr');const name=node('td');name.append(node('div',doc.title||doc.filename||'Tài liệu','doc-title'),node('small',doc.created_at?new Date(doc.created_at).toLocaleDateString('vi-VN'):''));const status=node('td');status.append(node('span',statusText[doc.status]||doc.status,`badge ${doc.status}`));if(doc.error_code)status.append(node('span',({scanned_pdf_requires_ocr:'PDF scan: chuyển sang PDF có văn bản trước khi tải lại.',encrypted_pdf:'PDF có mật khẩu. Hãy tải bản không mã hóa.',invalid_pdf:'Tệp không phải PDF hợp lệ.',pdf_page_limit:'Vượt giới hạn 100 trang.',processing_retry_limit:'Xử lý thất bại nhiều lần. Hãy tải lại.'})[doc.error_code]||'Đang chờ khôi phục hoặc cần tải lại.', 'error-code'));const actions=node('td');
    if(doc.status==='processed')actions.append(button('Tải PDF',()=>download(doc.doc_id)));
    if(doc.status==='awaiting_upload')actions.append(button('Gửi xử lý',async()=>{await api('/documents/submit',{method:'POST',body:{doc_id:doc.doc_id,s3_key:doc.s3_key}});notify('Đã gửi xử lý.');await loadDocs();}));
    if(doc.status!=='deleting')actions.append(button('Đổi tên',async()=>{const title=prompt('Tên tài liệu mới',doc.title||doc.filename);if(!title?.trim())return;await api(`/documents/${doc.doc_id}`,{method:'PATCH',body:{title}});await loadDocs();}),button('Xóa',async()=>{if(!confirm(`Xóa vĩnh viễn PDF “${doc.title||doc.filename}” và dữ liệu trích xuất?`))return;await api(`/documents/${doc.doc_id}`,{method:'DELETE'});state.selected.delete(doc.doc_id);state.cache.delete(doc.doc_id);notify('Đã tiếp nhận yêu cầu xóa tài liệu.');await loadDocs();}));
    tr.append(name,status,node('td',String(doc.page_count||'—')),actions);$('documents-list').append(tr);}
  if(!state.docs.length){const row=node('tr');const td=node('td','Chưa có tài liệu. Tải PDF đầu tiên của bạn ở phía trên.','empty-small');td.colSpan=4;row.append(td);$('documents-list').append(row);}renderSources();
}
async function download(docId) {
  const data=await api(`/documents/${encodeURIComponent(docId)}/download`);const url=new URL(data.download_url);if(url.protocol!=='https:')throw new Error('Đường dẫn tải không hợp lệ.');const anchor=node('a');anchor.href=url.href;anchor.rel='noopener noreferrer';anchor.download='policy-document.pdf';anchor.click();
}
function renderAnswer(question,result,target=$('answer-area'),append=false) {
  if(!append)target.replaceChildren();target.append(node('div',question,'question-bubble'),node('div',result.grounded?'TRẢ LỜI TỪ NGUỒN THAM KHẢO':'CHƯA ĐỦ THÔNG TIN','answer-label'),node('p',result.answer,'answer-text'),node('small',({all:'Nguồn: chính sách chung + PDF cá nhân',policies:'Nguồn: chỉ chính sách chung',documents:'Nguồn: chỉ PDF đã chọn'})[result.source_scope||'all'],'small muted'));
  renderFeedback(result,target);
  for(const source of result.citations||[]){const card=button('',async()=>{if(source.doc_id)await download(source.doc_id);else{const policy=await api(`/policies/${encodeURIComponent(source.policy_id)}`);$('policy-dialog-title').textContent=policy.title;$('policy-dialog-content').replaceChildren();showPolicy(policy,$('policy-dialog-content'));$('policy-dialog').showModal();}},'citation-card');card.append(node('strong',`${source.source_id} · ${source.title}${source.page?` — Trang ${source.page}`:''}`),node('p',source.excerpt));target.append(card);}target.append(button('Nhờ nhân viên hỗ trợ',async()=>{
    if(supportUnsaved()&&!confirm('Thay nội dung hỗ trợ đang soạn bằng câu hỏi này?'))return;
    $('new-ticket-form').reset();$('new-ticket-subject').value='Cần làm rõ chính sách';$('new-ticket-message').value=question.slice(0,1500);$('ticket-consent').checked=false;
    await navigate('support',{focus:true});notify(question.length>1500?'Đã chép 1.500 ký tự đầu để bạn xem lại. Chưa gửi cho nhân viên.':'Đã chép câu hỏi để bạn xem lại. Chưa gửi cho nhân viên; PDF và đoạn trích không đính kèm.');
  }));target.scrollTop=target.scrollHeight;
}
function renderFeedback(answer,target){
  const saved=feedbackStore.register(answer);if(!saved)return;
  const box=node('div',undefined,'answer-feedback'),heading=node('strong','Câu trả lời này có hữu ích?');
  const controls=node('div',undefined,'actions'),status=node('p','','small muted');status.setAttribute('role','status');
  const up=node('button','Hữu ích','secondary'),down=node('button','Chưa hữu ích','secondary'),clear=node('button','Rút đánh giá','text-button');
  const reasons=node('select');reasons.setAttribute('aria-label','Lý do đánh giá chưa hữu ích');reasons.append(new Option('Chọn lý do',''));for(const [key,label]of Object.entries(feedbackReasons))reasons.append(new Option(label,key));
  const send=node('button','Gửi đánh giá','secondary');const reasonRow=node('div',undefined,'feedback-reason hidden');reasonRow.append(reasons,send);
  for(const control of [up,down,clear,send])control.type='button';controls.append(up,down,clear);box.append(heading,controls,reasonRow,status);target.append(box);
  function render(){status.setAttribute('role','status');const value=feedbackStore.records.get(saved.conversation_id)?.feedback||{};up.setAttribute('aria-pressed',String(value.rating==='helpful'));down.setAttribute('aria-pressed',String(value.rating==='not_helpful'));clear.classList.toggle('hidden',!value.rating);status.textContent=value.rating==='helpful'?'Đã ghi nhận: hữu ích.':value.rating==='not_helpful'?`Đã ghi nhận: ${feedbackReasons[value.reason]||'chưa hữu ích'}.`:'Chỉ chia sẻ đánh giá có cấu trúc; không gửi thêm câu hỏi hoặc PDF cho quản trị.';}
  async function submit(rating,reason=null){const epoch=sessionEpoch;for(const c of [up,down,clear,send,reasons])c.disabled=true;status.textContent='Đang ghi nhận đánh giá…';try{await feedbackStore.update(saved.conversation_id,rating,reason);if(epoch!==sessionEpoch)return;reasonRow.classList.add('hidden');render();}catch(error){if(epoch!==sessionEpoch)return;status.textContent=error.status===429?'Đã hết hạn mức thay đổi phản hồi. Hãy thử lại sau.':error.message;status.setAttribute('role','alert');}finally{if(epoch===sessionEpoch)for(const c of [up,down,clear,send,reasons])c.disabled=false;}}
  up.onclick=()=>submit('helpful');down.onclick=()=>{reasonRow.classList.remove('hidden');reasons.value=feedbackStore.records.get(saved.conversation_id)?.feedback?.reason||'';reasons.focus();};clear.onclick=()=>submit(null);send.onclick=()=>{if(!reasons.value){status.textContent='Chọn lý do trước khi gửi đánh giá.';return;}submit('not_helpful',reasons.value);};render();
}
async function loadQuality(){
  needApi();const isCurrent=latestTasks.begin('quality');const month=$('quality-month').value;
  const report=await api(`/admin/quality${month?`?month=${encodeURIComponent(month)}`:''}`);if(!isCurrent())return;qualityReport=report;
  $('quality-month').replaceChildren();for(const value of report.available_months)$('quality-month').append(new Option(value,value,value===report.month,value===report.month));
  $('quality-overview').replaceChildren();for(const [label,value,note]of [['Câu trả lời đã lưu',report.counts.answers,'Từ khi bật theo dõi'],['Có nguồn trích dẫn',report.citation_rate===null?'—':`${report.citation_rate}%`,'Không phải điểm chính xác'],['Thời gian xử lý TB',report.average_response_ms===null?'—':`${(report.average_response_ms/1000).toFixed(2)} s`,'Trước bước lưu, phía máy chủ'],['Phản hồi hữu ích',report.helpful_rate===null?'—':`${report.helpful_rate}%`,`${report.counts.helpful+report.counts.not_helpful} đánh giá hiện ghi nhận`]]){const card=node('div',undefined,'usage-card');card.append(node('span',label),node('strong',String(value)),node('span',note));$('quality-overview').append(card);}
  const detail=$('quality-feedback');detail.replaceChildren(node('h3','Phản hồi và phạm vi nguồn'));if(!report.started_at)detail.append(node('p','Chưa có dữ liệu trong tháng này. Số liệu sẽ xuất hiện sau câu trả lời mới; không tự phân tích lại lịch sử cũ.','empty-small'));
  const meter=node('meter');meter.min=0;meter.max=Math.max(1,report.counts.helpful+report.counts.not_helpful);meter.value=report.counts.helpful;meter.setAttribute('aria-label',`${report.counts.helpful} hữu ích, ${report.counts.not_helpful} chưa hữu ích`);detail.append(meter,node('p',`Hữu ích: ${report.counts.helpful} · Chưa hữu ích: ${report.counts.not_helpful} · Chưa đủ nguồn: ${report.counts.refused}`,'small'));
  for(const [key,label]of Object.entries(feedbackReasons))detail.append(node('p',`${label}: ${report.counts['reason_'+key]}`,'small'));
  detail.append(node('p',`Phạm vi kết hợp: ${report.counts.scope_all} · Chính sách: ${report.counts.scope_policies} · PDF đã chọn: ${report.counts.scope_documents}`,'small muted'));$('export-quality').disabled=false;
}
$('quality-month').onchange=()=>guard($('quality-month'),loadQuality);$('refresh-quality').onclick=()=>guard($('refresh-quality'),loadQuality);
$('export-quality').onclick=()=>guard($('export-quality'),()=>{if(!qualityReport)throw new Error('Tải báo cáo trước khi xuất.');const url=URL.createObjectURL(new Blob([JSON.stringify(qualityReport,null,2)],{type:'application/json'}));const link=node('a');link.href=url;link.download=`policy-assistant-quality-${qualityReport.month}.json`;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
function showPolicy(policy,target) {const card=node('article',undefined,'policy-card');card.append(node('div',`${policy.policy_id} / ${policy.category||'Chính sách'}`,'policy-meta'),node('h2',policy.title));if(policy.effective_from||policy.effective_until)card.append(node('p',validityText(policy),'small muted'));card.append(node('p',policy.content));target.append(card);}
async function searchPolicies(more=false){needApi();const isCurrent=latestTasks.begin('policies');if(!more){state.policyKeyword=$('policy-keyword').value.trim();state.policyToken=null;$('policy-results').replaceChildren();}const result=await api(`/policies?keyword=${encodeURIComponent(state.policyKeyword)}&limit=10${state.policyToken?`&next_token=${encodeURIComponent(state.policyToken)}`:''}`);if(!isCurrent())return;for(const item of result.policies)showPolicy(item,$('policy-results'));state.policyToken=result.next_token;$('more-policies').classList.toggle('hidden',!state.policyToken);if(!result.policies.length&&!state.policyToken)$('policy-results').append(node('p','Không còn kết quả phù hợp.','empty-small'));}
async function loadHistory(more=false){needApi();const isCurrent=latestTasks.begin('history');const result=await api(`/conversations${more&&state.historyToken?`?next_token=${encodeURIComponent(state.historyToken)}`:''}`);if(!isCurrent())return;if(!more)$('history-list').replaceChildren();for(const item of result.conversations){const card=node('article',undefined,'history-card');card.append(node('small',new Date(item.created_at).toLocaleString('vi-VN'),'small'));renderAnswer(item.question,item,card,true);card.append(button('Xóa cuộc hỏi đáp',async()=>{if(!confirm('Xóa cuộc hỏi đáp này?'))return;await api(`/conversations/${encodeURIComponent(item.conversation_id)}`,{method:'DELETE'});card.remove();}));$('history-list').append(card);}state.historyToken=result.next_token;$('more-history').classList.toggle('hidden',!state.historyToken);if(!more&&!result.conversations.length&&!state.historyToken)$('history-list').append(node('p','Chưa có cuộc hỏi đáp nào.','empty-small'));}
async function loadAudit(more=false){const isCurrent=latestTasks.begin('audit');const result=await api(`/admin/audit${more&&state.auditToken?`?next_token=${encodeURIComponent(state.auditToken)}`:''}`);if(!isCurrent())return;if(!more)$('audit-list').replaceChildren();for(const item of result.events){const action=({'policy.put':'Công bố chính sách','policy.draft':'Lưu bản nháp','policy.publish':'Công bố chính sách','policy.archive':'Ngừng công bố','policy.archive.demo':'Ngừng công bố DEMO','policy.discard_draft':'Bỏ bản nháp','policy.delete':'Xóa chính sách','shop.save_draft':'Lưu nháp thông tin shop','shop.publish':'Công bố thông tin shop','shop.unpublish':'Ngừng công bố thông tin shop','shop.discard_draft':'Bỏ nháp thông tin shop','ticket.update':'Cập nhật hỗ trợ','ticket.delete':'Xóa yêu cầu hỗ trợ'})[item.action]||item.action;const row=node('div',`${action} · ${item.resource}`,'audit-event');row.append(node('small',`${new Date(item.event_id.split('#')[0]).toLocaleString('vi-VN')} · ${item.actor}`));$('audit-list').append(row);}state.auditToken=result.next_token;$('more-audit').classList.toggle('hidden',!state.auditToken);}
async function loadAdmin(){needApi();const result=await api('/admin/overview');$('usage-overview').replaceChildren();for(const [title,value,caption]of[['Lượt tải tháng này',result.usage.upload,`/ ${result.limits.uploads} lượt`],['Câu hỏi tháng này',result.usage.question,`/ ${result.limits.questions} lượt`],['Yêu cầu hỗ trợ tháng này',result.usage.ticket??0,`/ ${result.limits.tickets??200} lượt`],['Lượt gọi dịch vụ tháng này',result.usage.request??0,`/ ${result.limits.requests??100000} lượt`],['Dịch vụ AI',result.model_configured?'Đã cấu hình':'Chưa cấu hình',result.month]]){const card=node('div',undefined,'usage-card');card.append(node('span',title),node('strong',String(value)),node('span',caption));$('usage-overview').append(card);}await Promise.all([loadAudit(),loadAdminPolicies(),loadTicketQueue(),loadShopEditor(),loadQuality()]);}

function renderPolicyEditorStatus(){
  const r=policyEditor.record, busy=policyEditor.busy,dirty=policyEditor.dirty;
  $('admin-policy-fields').disabled=busy;$('new-policy').disabled=busy;
  $('admin-policy-form').elements.policy_id.readOnly=Boolean(r);
  $('policy-editor-heading').textContent=r?`Chỉnh sửa ${r.policy_id}`:'Soạn chính sách mới';
  $('policy-editor-badge').textContent=r?(policyStates[r.publication_state]||'Chưa công bố'):'Bản nháp';
  $('policy-editor-status').textContent=busy?'Đang xử lý…':dirty?'Có thay đổi chưa lưu. Lưu bản nháp để có thể công bố.':r?.draft?(r.publication_state==='published'?'Có bản nháp riêng. Thời hạn bản đã công bố được giữ nguyên.':'Bản nháp đã lưu. Xem lại nội dung trước khi công bố.'):r?.publication_state==='published'?`Bản đã công bố: ${validityStates[r.validity_state||'active']}. Mọi chỉnh sửa được lưu riêng thành bản nháp.`:r?'Chính sách chưa được dùng để trả lời khách hàng.':'Lưu bản nháp trước khi xem lại và công bố.';
  $('publish-policy').disabled=busy||dirty||!r||(!r.draft&&!(r.publication_state==='archived'&&r.current));
  $('publish-policy').textContent=r?.publication_state==='archived'&&!r.draft?'Công bố lại bản đã lưu':'Công bố bản nháp';
  $('archive-policy').disabled=busy||dirty||r?.publication_state!=='published';
  $('discard-policy-draft').disabled=busy||dirty||!r?.draft;
}
function renderPolicyValidityPreview(){
  const form=$('admin-policy-form');
  try{$('policy-window-preview').textContent=validityText({effective_from:form.elements.effective_from.value,effective_until:form.elements.effective_until.value});}
  catch(error){$('policy-window-preview').textContent=error.message;}
}
function fillPolicyEditor(record){
  const form=$('admin-policy-form');form.reset();const fields=record?.draft||record?.current;
  form.elements.policy_id.value=record?.policy_id||'';
  for(const key of ['title','category','content','effective_from','effective_until'])form.elements[key].value=fields?.[key]||'';
  form.elements.keywords.value=(fields?.keywords||[]).join(', ');
  $('policy-live-preview').classList.toggle('hidden',!record?.current);
  $('policy-live-caption').textContent=record?.publication_state==='published'?`Bản đã công bố · ${validityStates[record.validity_state||'active']}`:'Xem bản đã ngừng công bố';
  try{$('policy-live-validity').textContent=record?.current?validityText(record.current):'';}
  catch{$('policy-live-validity').textContent='Thời hạn đã lưu không hợp lệ. Sửa ngày và lưu bản nháp để khắc phục.';}
  $('policy-live-title').textContent=record?.current?.title||'';$('policy-live-content').textContent=record?.current?.content||'';
  renderPolicyEditorStatus();renderPolicyValidityPreview();
}
async function loadAdminPolicies(more=false){
  needApi();const epoch=++adminListEpoch;const keyword=adminPolicyKeyword;
  const result=await api(`/admin/policies?limit=20&keyword=${encodeURIComponent(keyword)}&validity=${encodeURIComponent($('admin-policy-validity').value)}${more&&adminPolicyToken?`&next_token=${encodeURIComponent(adminPolicyToken)}`:''}`);
  if(epoch!==adminListEpoch)return;if(!more)$('admin-policy-list').replaceChildren();
  for(const policy of result.policies){
    const row=node('article',undefined,'admin-policy-row'),info=node('div'),meta=node('div',undefined,'policy-row-meta');
    info.append(node('strong',policy.title),node('small',`${policy.policy_id} · ${policy.category||'Chưa phân nhóm'}`));
    meta.append(node('span',policyStates[policy.publication_state]||'Chưa công bố',`policy-badge ${policy.publication_state}`));
    if(policy.publication_state==='published')meta.append(node('span',validityStates[policy.validity_state||'active']||'Cần kiểm tra ngày',`validity-badge ${policy.validity_state||'active'}`));
    if(policy.has_draft)meta.append(node('span','Có bản nháp','policy-draft-flag'));
    const edit=button('Mở để sửa',async()=>{if(policyEditor.dirty&&!confirm('Bỏ thay đổi chưa lưu để mở chính sách khác?'))return;const record=await policyEditor.open(policy.policy_id);fillPolicyEditor(record);$('admin-policy-form').scrollIntoView({block:'start'});},'secondary');edit.setAttribute('aria-label',`Mở để sửa ${policy.policy_id}`);
    row.append(info,meta,edit);$('admin-policy-list').append(row);
  }
  adminPolicyToken=result.next_token;$('more-admin-policies').classList.toggle('hidden',!adminPolicyToken);
  if(!$('admin-policy-list').children.length&&!adminPolicyToken)$('admin-policy-list').append(node('p','Chưa có chính sách phù hợp. Chọn Soạn mới để bắt đầu.','empty-small'));
}

function updateScopeLabel(){
  const scope=$('source-scope').value;
  $('scope-label').textContent=scope==='policies'?'Chỉ chính sách chung':scope==='documents'?`Chỉ PDF đã chọn (${state.selected.size})`:state.selected.size?`${state.selected.size} PDF đã chọn + chính sách chung`:'Chính sách chung + tài liệu gần đây';
}
function renderShopControls(){
  const busy=shopEditor.busy,r=shopEditor.record;
  $('shop-fields').disabled=busy||!shopEditor.loaded;$('reload-shop').disabled=busy;
  $('publish-shop').disabled=busy||shopEditor.dirty||!r?.draft;$('unpublish-shop').disabled=busy||shopEditor.dirty||!r?.current;$('discard-shop').disabled=busy||shopEditor.dirty||!r?.draft;
  $('shop-editor-status').textContent=busy?'Đang tải / cập nhật…':!shopEditor.loaded?'Chưa tải thông tin shop.':shopEditor.dirty?'Có thay đổi chưa lưu.':r?.draft?'Bản nháp đã lưu; khách vẫn thấy nội dung công bố trước đó.':r?.current?'Thông tin đang được công bố.':'Chưa có thông tin shop được công bố.';
}
function readShopForm(){const raw={mode:$('shop-mode').value};for(const key of Object.keys(shopFields))raw[key]=$('shop-'+key).value;return raw;}
function shopCard(value,target){
  target.replaceChildren();if(!value){target.append(node('p','Shop chưa công bố thông tin vận hành. Bạn có thể gửi yêu cầu hỗ trợ trong ứng dụng.'));return;}
  target.append(node('span',value.mode==='live'?'THÔNG TIN VẬN HÀNH':'DEMO — THÔNG TIN THỬ','policy-badge'),node('h2',value.shop_name));
  for(const [key,label]of Object.entries({support_email:'Email hỗ trợ',support_phone:'Điện thoại hỗ trợ',support_hours:'Giờ hỗ trợ',returns_instructions:'Tiếp nhận đổi trả',support_message:'Lời nhắn từ shop'})){const group=node('div',undefined,'shop-detail');group.append(node('strong',label),node('p',value[key]||'Chưa được shop cung cấp.'));target.append(group);}
}
function fillShopEditor(record){const raw=record?.draft||record?.current||{};for(const key of Object.keys(shopFields))$('shop-'+key).value=raw[key]||'';$('shop-mode').value=raw.mode||'demo';$('shop-confirm').checked=false;shopCard(record?.current,$('shop-current-preview'));renderShopControls();}
async function loadShopProfile(){needApi();const data=await api('/shop');shopCard(data.profile,$('shop-profile'));$('shop-context').textContent=data.configured?(data.profile.mode==='demo'?`DEMO — ${data.profile.shop_name}. Thông tin chỉ để kiểm thử.`:`Shop: ${data.profile.shop_name}. Xem kênh liên hệ tại Thông tin shop.`):'Shop chưa công bố thông tin vận hành. Nội dung DEMO chỉ để kiểm thử.';$('shop-context').classList.remove('hidden');}
async function loadShopEditor(){if(shopEditor.dirty)return;fillShopEditor(await shopEditor.load());}
for(const key of [...Object.keys(shopFields),'mode'])$('shop-'+key).addEventListener('input',()=>{$('shop-confirm').checked=false;shopEditor.markDirty();});
$('shop-form').onsubmit=event=>{event.preventDefault();guard($('save-shop'),async()=>{fillShopEditor(await shopEditor.save(readShopForm()));notify('Đã lưu nháp thông tin shop. Chưa công bố cho khách.');});};
$('reload-shop').onclick=()=>guard($('reload-shop'),async()=>{if(shopEditor.dirty&&!confirm('Bỏ thay đổi chưa lưu để tải lại thông tin shop?'))return;fillShopEditor(await shopEditor.load());});
for(const [id,action,promptText]of [['publish-shop','publish','Công bố bản nháp thông tin shop đã lưu cho mọi khách đã đăng nhập?'],['unpublish-shop','unpublish','Ngừng hiển thị thông tin shop cho khách?'],['discard-shop','discard_draft','Bỏ bản nháp thông tin shop đã lưu?']])$(id).onclick=()=>guard($(id),async()=>{if(!confirm(promptText))return;const confirmed=$('shop-confirm').checked;fillShopEditor(await shopEditor.act(action,confirmed));await loadShopProfile();await loadAudit();notify('Đã cập nhật trạng thái thông tin shop.');});
$('refresh-shop').onclick=()=>guard($('refresh-shop'),loadShopProfile);
function triageUnsaved(){return Boolean(supportClient.staff&&supportClient.record&&($('staff-ticket-priority').value!==(supportClient.record.priority||'normal')||$('staff-ticket-status').value!==supportClient.record.status));}
function supportUnsaved(){return Boolean($('new-ticket-subject').value.trim()||$('new-ticket-message').value.trim()||$('new-ticket-order').value.trim()||$('new-ticket-category').value!=='general'||$('ticket-reply-message').value.trim()||triageUnsaved());}
function renderSupportControls(){
  const r=supportClient.record,busy=supportClient.busy,staff=supportClient.staff,limit=(r?.message_count||0)>=20;
  $('new-ticket-fields').disabled=busy;$('ticket-reply-fields').disabled=busy;
  $('staff-ticket-status-label').classList.toggle('hidden',!staff);$('staff-ticket-priority-label').classList.toggle('hidden',!staff);
  $('ticket-reply-message').required=!staff;
  $('ticket-reply-message').disabled=busy||limit||(!staff&&r?.status==='closed');
  $('send-ticket-reply').disabled=busy||!r||(!staff&&(limit||r.status==='closed'));
  $('send-ticket-reply').textContent=staff?'Gửi phản hồi / Cập nhật':'Gửi bổ sung';
  $('close-own-ticket').classList.toggle('hidden',staff);$('delete-own-ticket').classList.toggle('hidden',staff);
  $('close-own-ticket').disabled=busy||!r||r.status==='closed';$('delete-own-ticket').disabled=busy||!r;
  $('close-ticket-dialog').disabled=busy;
}
function showTicket(){
  const r=supportClient.record;if(!r)return;
  $('ticket-dialog-title').textContent=r.subject;
  $('ticket-dialog-meta').textContent=`#${r.ticket_id.slice(-8).toUpperCase()} · ${supportStates[r.status]} · ${supportCategories[r.category||'general']} · Ưu tiên: ${supportPriorities[r.priority||'normal']}${r.order_ref?` · Mã đơn khách cung cấp: ${r.order_ref}`:''} · ${r.message_count}/20 tin nhắn · Lưu đến ${new Date(r.expires_at*1000).toLocaleDateString('vi-VN')}`;
  $('ticket-thread').replaceChildren();
  for(const message of r.messages){const card=node('article',undefined,`support-message ${message.role}`);card.append(node('strong',message.role==='staff'?'Nhân viên hỗ trợ':supportClient.staff?'Khách hàng':'Bạn'),node('small',new Date(message.created_at).toLocaleString('vi-VN')),node('p',message.body));$('ticket-thread').append(card);}
  $('ticket-dialog-notice').classList.add('hidden');$('ticket-reply-message').value='';$('staff-ticket-status').value=r.status;$('staff-ticket-priority').value=r.priority||'normal';
  $('ticket-reply-note').textContent=supportClient.staff?'Phản hồi được gửi trong ứng dụng cho khách. Không gửi email tự động.':r.status==='closed'?'Yêu cầu đã đóng. Bạn có thể gửi yêu cầu mới nếu cần hỗ trợ thêm.':r.message_count>=20?'Đã đủ 20 tin nhắn. Bạn có thể đóng yêu cầu hoặc gửi yêu cầu mới.':'Nội dung bổ sung sẽ được chia sẻ với bộ phận hỗ trợ.';
  renderSupportControls();if(!$('ticket-dialog').open)$('ticket-dialog').showModal();
}
function closeSupportDialog(){if(supportClient.busy)return;if(($('ticket-reply-message').value.trim()||triageUnsaved())&&!confirm('Bỏ phản hồi hoặc thay đổi xử lý chưa lưu?'))return;$('ticket-reply-message').value='';$('ticket-dialog-notice').classList.add('hidden');$('ticket-dialog').close();}
function supportRow(row,staff){
  const card=node('article',undefined,'support-row'),head=node('div');head.append(node('strong',row.subject),node('small',`#${row.ticket_id.slice(-8).toUpperCase()} · ${new Date(row.updated_at).toLocaleString('vi-VN')} · ${row.message_count} tin nhắn`));
  head.append(node('small',`${supportCategories[row.category||'general']} · Ưu tiên: ${supportPriorities[row.priority||'normal']}${row.order_ref?` · Đơn: ${row.order_ref}`:''}`,`triage-meta ${row.priority||'normal'}`));
  const open=button('Xem yêu cầu',async()=>{if($('ticket-reply-message').value.trim()&&!confirm('Bỏ phản hồi chưa gửi để mở yêu cầu khác?'))return;await supportClient.open(row,staff);showTicket();},'secondary');open.setAttribute('aria-label',`Mở yêu cầu ${row.ticket_id}`);
  card.append(head,node('span',supportStates[row.status],`support-status ${row.status}`),open);return card;
}
async function loadTickets(more=false){
  needApi();const epoch=++ticketListEpoch;const result=await api(`/tickets?limit=20${more&&ticketToken?`&next_token=${encodeURIComponent(ticketToken)}`:''}`);if(epoch!==ticketListEpoch)return;
  if(!more)$('ticket-list').replaceChildren();for(const row of result.tickets)$('ticket-list').append(supportRow(row,false));ticketToken=result.next_token;$('more-tickets').classList.toggle('hidden',!ticketToken);
  if(!$('ticket-list').children.length&&!ticketToken)$('ticket-list').append(node('p','Chưa có yêu cầu. Nội dung mới sẽ chỉ được chia sẻ khi bạn bấm Gửi yêu cầu.','empty-small'));
}
async function loadTicketQueue(more=false){
  needApi();const epoch=++adminTicketListEpoch,filter=$('admin-ticket-filter').value;
  const result=await api(`/admin/tickets?limit=20${filter?`&status=${encodeURIComponent(filter)}`:''}${$('admin-ticket-category').value?`&category=${encodeURIComponent($('admin-ticket-category').value)}`:''}${$('admin-ticket-priority').value?`&priority=${encodeURIComponent($('admin-ticket-priority').value)}`:''}${$('admin-ticket-order').value.trim()?`&order_ref=${encodeURIComponent($('admin-ticket-order').value.trim())}`:''}${more&&adminTicketToken?`&next_token=${encodeURIComponent(adminTicketToken)}`:''}`);if(epoch!==adminTicketListEpoch)return;
  if(!more)$('admin-ticket-list').replaceChildren();for(const row of result.tickets)$('admin-ticket-list').append(supportRow(row,true));adminTicketToken=result.next_token;$('more-admin-tickets').classList.toggle('hidden',!adminTicketToken);
  if(!$('admin-ticket-list').children.length&&!adminTicketToken)$('admin-ticket-list').append(node('p','Chưa có yêu cầu ở trạng thái này.','empty-small'));
}
async function refreshSupportLists(){await Promise.all([loadTickets(),...(groups().includes('administrators')?[loadTicketQueue(),loadAudit()]:[])]);}

function adminSection(key,focus=false){
  const tabs=[...document.querySelectorAll('.admin-tabs [role="tab"]')];if(!tabs.some(t=>t.dataset.adminTarget===key))return;
  for(const tab of tabs){const active=tab.dataset.adminTarget===key;tab.setAttribute('aria-selected',String(active));tab.tabIndex=active?0:-1;if(active&&focus)tab.focus();}
  document.querySelectorAll('[data-admin-panel]').forEach(panel=>panel.classList.toggle('hidden',panel.dataset.adminPanel!==key));
}
document.addEventListener('click',event=>{const target=event.target.closest('[data-admin-target]');if(target)adminSection(target.dataset.adminTarget,target.getAttribute('role')!=='tab');});
document.querySelector('.admin-tabs').addEventListener('keydown',event=>{const tabs=[...document.querySelectorAll('.admin-tabs [role="tab"]')],i=tabs.indexOf(event.target);if(i<0||!['ArrowRight','ArrowLeft','Home','End'].includes(event.key))return;event.preventDefault();const next=event.key==='Home'?0:event.key==='End'?tabs.length-1:(i+(event.key==='ArrowRight'?1:-1)+tabs.length)%tabs.length;adminSection(tabs[next].dataset.adminTarget,true);});
$('guest-signin').onclick=()=>$('auth-button').click();
$('close-policy-dialog').onclick=()=>$('policy-dialog').close();
document.addEventListener('click',event=>{const nav=event.target.closest('[data-view]');if(nav)guard(nav,()=>navigate(nav.dataset.view,{focus:true}));const suggestion=event.target.closest('[data-question]');if(suggestion){if(!state.user){notify('Đăng nhập để đặt câu hỏi và xem nguồn trả lời.',true);$('auth-button').focus();return;}$('question').value=suggestion.dataset.question;$('question').dispatchEvent(new Event('input',{bubbles:true}));$('question').focus();}});
$('auth-button').addEventListener('click',()=>guard($('auth-button'),async()=>{if(!manager)throw new Error('Đăng nhập chưa được cấu hình.');if(signingOut)return;if(state.user){if(hasUnsavedWork()&&!confirm('Đăng xuất và bỏ các nội dung chưa gửi hoặc chưa lưu?'))return;signingOut=true;manager.stopSilentRenew();clearPrivateState();try{await manager.revokeTokens(['refresh_token']);}catch{}await manager.removeUser();location.assign(`${config.authDomain}/logout?client_id=${encodeURIComponent(config.clientId)}&logout_uri=${encodeURIComponent(location.origin+'/')}`);}else await manager.signinRedirect();}));
$('question').addEventListener('input',()=>{$('question-count').textContent=`${$('question').value.length.toLocaleString('vi-VN')} / 2.000 ký tự`;});
$('question-form').addEventListener('submit',event=>{event.preventDefault();guard($('ask-button'),async()=>{
  needApi();const question=$('question').value.trim();if(!question)return;
  const payload=questionPayload(question,[...state.selected],$('source-scope').value),epoch=sessionEpoch;
  $('answer-area').setAttribute('aria-busy','true');$('answer-area').replaceChildren(node('p','Đang tìm nguồn và chuẩn bị câu trả lời…','loading-state'));
  try{const result=await api('/ask',{method:'POST',body:payload});if(epoch!==sessionEpoch)return;renderAnswer(question,result);$('question').value='';$('question-count').textContent='0 / 2.000 ký tự';}
  catch(error){if(epoch!==sessionEpoch)return;$('answer-area').replaceChildren(node('p','Chưa nhận được câu trả lời. Câu hỏi vẫn được giữ để bạn xem lại. Nếu kết nối bị ngắt, kiểm tra Lịch sử trước khi gửi lại.','empty-small'));throw error;}
  finally{if(epoch===sessionEpoch)$('answer-area').setAttribute('aria-busy','false');}
});});
$('upload-form').addEventListener('submit',event=>{event.preventDefault();guard($('upload-button'),async()=>{
  needApi();const epoch=sessionEpoch,isCurrent=()=>epoch===sessionEpoch;$('upload-status').textContent='Đang tải file…';
  try{const docId=await uploadPdf(api,$('pdf-file').files[0]);if(!isCurrent())return;$('pdf-file').value='';$('upload-status').textContent='File đã được tiếp nhận. Đang xử lý nội dung…';
    const doc=await pollDocument(api,docId,{isCurrent,onStatus:doc=>{const message=`${doc.title||'Tài liệu'}: ${statusText[doc.status]||doc.status}`;if($('upload-status').textContent!==message)$('upload-status').textContent=message;}});
    if(!isCurrent())return;
    if(doc?.status==='processed')$('upload-status').textContent='PDF đã sẵn sàng. Bạn có thể chọn làm nguồn hỏi đáp.';
    else if(doc?.status==='failed')$('upload-status').textContent='PDF chưa xử lý được. Xem lỗi trong thư viện bên dưới; không cần tải lại khi chưa kiểm tra nguyên nhân.';
    else if(doc?.status!=='deleted')$('upload-status').textContent='File đã tiếp nhận và vẫn đang xử lý. OCR có thể mất thêm thời gian; dùng Làm mới để kiểm tra, không cần tải lại.';
    await loadDocs();
  }catch(error){if(!isCurrent())return;$('upload-status').textContent='Chưa xác nhận được bước tải/xử lý. Xem thông báo và làm mới thư viện trước khi thử lại.';throw error;}
});});
$('refresh-documents').onclick=()=>guard($('refresh-documents'),()=>loadDocs());$('more-documents').onclick=()=>guard($('more-documents'),()=>loadDocs(true));$('more-sources').onclick=()=>guard($('more-sources'),()=>loadDocs(true));
$('policy-form').onsubmit=event=>{event.preventDefault();guard(event.submitter,()=>searchPolicies());};$('more-policies').onclick=()=>guard($('more-policies'),()=>searchPolicies(true));
$('refresh-history').onclick=()=>guard($('refresh-history'),()=>loadHistory());$('more-history').onclick=()=>guard($('more-history'),()=>loadHistory(true));$('refresh-admin').onclick=()=>guard($('refresh-admin'),loadAdmin);$('more-audit').onclick=()=>guard($('more-audit'),()=>loadAudit(true));
$('admin-policy-form').addEventListener('input',()=>{policyEditor.markDirty();renderPolicyValidityPreview();});
$('admin-policy-form').onsubmit=event=>{event.preventDefault();guard(event.submitter,async()=>{
  const raw=Object.fromEntries(new FormData(event.target));const record=await policyEditor.save(raw.policy_id.trim(),raw);fillPolicyEditor(record);notify(record.publication_state==='published'?'Đã lưu bản nháp. Bản đang công bố được giữ nguyên.':'Đã lưu bản nháp. Nội dung chưa được công bố.');await Promise.all([loadAdminPolicies(),loadAudit()]);
});};
$('new-policy').onclick=()=>guard($('new-policy'),()=>{if(policyEditor.dirty&&!confirm('Bỏ thay đổi chưa lưu để soạn chính sách mới?'))return;policyEditor.newPolicy();fillPolicyEditor(null);});
$('admin-policy-search').onsubmit=event=>{event.preventDefault();guard(event.submitter,()=>{adminPolicyKeyword=$('admin-policy-keyword').value.trim();return loadAdminPolicies();});};
$('more-admin-policies').onclick=()=>guard($('more-admin-policies'),()=>loadAdminPolicies(true));
for(const [id,action,message]of [['publish-policy','publish','Công bố nội dung đã lưu cho tất cả tài khoản?'],['archive-policy','archive','Ngừng công bố chính sách này? Nội dung được giữ lại để có thể công bố lại.'],['discard-policy-draft','discard_draft','Bỏ bản nháp đã lưu? Bản đang công bố được giữ nguyên.']]){
  $(id).onclick=()=>guard($(id),async()=>{if(!confirm(action==='publish'?`${message}\n${validityText(policyEditor.record?.draft||policyEditor.record?.current||{})}`:message))return;const record=await policyEditor.transition(action);fillPolicyEditor(record);notify(action==='publish'?'Đã công bố chính sách.':action==='archive'?'Đã ngừng công bố. Bạn có thể công bố lại bản đã lưu.':'Đã bỏ bản nháp; bản công bố được giữ nguyên.');await Promise.all([loadAdminPolicies(),loadAudit()]);});
}
function hasUnsavedWork(){return Boolean($('question').value.trim()||policyEditor.dirty||shopEditor.dirty||supportUnsaved());}
window.addEventListener('beforeunload',event=>{if(hasUnsavedWork()){event.preventDefault();event.returnValue='';}});
$('source-scope').addEventListener('change',()=>renderSources());
$('refresh-tickets').onclick=()=>guard($('refresh-tickets'),()=>loadTickets());
$('more-tickets').onclick=()=>guard($('more-tickets'),()=>loadTickets(true));
$('admin-ticket-filter').onchange=()=>guard($('admin-ticket-filter'),()=>loadTicketQueue());
for(const id of ['admin-ticket-category','admin-ticket-priority'])$(id).onchange=()=>guard($(id),()=>loadTicketQueue());
$('ticket-lookup-form').onsubmit=event=>{event.preventDefault();guard(event.submitter,()=>loadTicketQueue());};
$('admin-ticket-order').oninput=()=>{adminTicketListEpoch++;adminTicketToken=null;$('admin-ticket-list').replaceChildren();$('more-admin-tickets').classList.add('hidden');};
$('more-admin-tickets').onclick=()=>guard($('more-admin-tickets'),()=>loadTicketQueue(true));
$('close-ticket-dialog').onclick=closeSupportDialog;
$('ticket-dialog').addEventListener('cancel',event=>{event.preventDefault();closeSupportDialog();});
$('new-ticket-form').onsubmit=event=>{event.preventDefault();guard($('create-ticket'),async()=>{
  const data={subject:$('new-ticket-subject').value,message:$('new-ticket-message').value,consent:$('ticket-consent').checked,category:$('new-ticket-category').value,order_ref:$('new-ticket-order').value};
  await supportClient.create(data);$('new-ticket-form').reset();showTicket();notify('Đã tiếp nhận yêu cầu. Bạn có thể theo dõi phản hồi và trạng thái ngay tại đây.');await refreshSupportLists();
});};
$('ticket-reply-form').onsubmit=event=>{event.preventDefault();guard($('send-ticket-reply'),async()=>{
  await supportClient.update($('ticket-reply-message').value,$('staff-ticket-status').value,'reply',supportClient.staff?$('staff-ticket-priority').value:undefined);showTicket();notify('Đã cập nhật yêu cầu hỗ trợ.');await refreshSupportLists();
});};
$('close-own-ticket').onclick=()=>guard($('close-own-ticket'),async()=>{if(!confirm('Đóng yêu cầu hỗ trợ này? Bạn vẫn có thể xem lại hoặc xóa nội dung.'))return;await supportClient.update('',null,'close');showTicket();await refreshSupportLists();});
$('delete-own-ticket').onclick=()=>guard($('delete-own-ticket'),async()=>{if(!confirm('Xóa vĩnh viễn toàn bộ yêu cầu và phản hồi? Không thể khôi phục từ ứng dụng.'))return;await supportClient.remove();$('ticket-dialog').close();$('ticket-thread').replaceChildren();$('ticket-reply-form').reset();notify('Đã xóa yêu cầu hỗ trợ.');await refreshSupportLists();});
$('export-tickets').onclick=()=>guard($('export-tickets'),async()=>{needApi();const items=[];let token;do{const result=await api(`/tickets?limit=50${token?`&next_token=${encodeURIComponent(token)}`:''}`);for(const row of result.tickets)items.push(await api(`/tickets/${encodeURIComponent(row.ticket_id)}`));token=result.next_token;}while(token);const url=URL.createObjectURL(new Blob([JSON.stringify(items,null,2)],{type:'application/json'}));const link=node('a');link.href=url;link.download='policy-assistant-support.json';link.click();URL.revokeObjectURL(url);});
$('export-history').onclick=()=>guard($('export-history'),async()=>{needApi();const items=[];let token;do{const result=await api(`/conversations${token?`?next_token=${encodeURIComponent(token)}`:''}`);items.push(...result.conversations);token=result.next_token;}while(token);const url=URL.createObjectURL(new Blob([JSON.stringify(items,null,2)],{type:'application/json'}));const link=node('a');link.href=url;link.download='policy-assistant-history.json';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
$('delete-account').onclick=()=>guard($('delete-account'),async()=>{needApi();if($('delete-confirmation').value!=='DELETE')throw new Error('Nhập chính xác DELETE để xác nhận.');if(!confirm('Xóa vĩnh viễn tài khoản, tất cả PDF và lịch sử? Không thể hoàn tác trong ứng dụng.'))return;await api('/account/delete',{method:'POST',body:{confirmation:'DELETE'}});signingOut=true;manager.stopSilentRenew();await manager.removeUser();clearPrivateState();notify('Đã tiếp nhận yêu cầu xóa. Tài khoản hiện bị chặn và dữ liệu sẽ được xóa ở nền.');});

async function start(){
  signedIn();renderShopControls();
  const response=await fetch('./config.json',{cache:'no-store'});if(!response.ok)throw new Error('Chưa tải được cấu hình ứng dụng.');config=await response.json();
  if(!config.apiBase||!config.clientId||!config.userPoolId||!config.authDomain){$('config-warning').classList.remove('hidden');$('auth-button').disabled=true;return;}
  const authDomain=new URL(config.authDomain);if(authDomain.protocol!=='https:')throw new Error('Địa chỉ đăng nhập phải dùng HTTPS.');config.authDomain=authDomain.origin;
  const issuer=`https://cognito-idp.${config.region}.amazonaws.com/${config.userPoolId}`;
  manager=new UserManager({authority:issuer,client_id:config.clientId,redirect_uri:location.origin+'/',post_logout_redirect_uri:location.origin+'/',response_type:'code',scope:'openid email profile',loadUserInfo:false,automaticSilentRenew:true,userStore:new WebStorageStateStore({store:sessionStorage}),stateStore:new WebStorageStateStore({store:sessionStorage}),metadata:{issuer,authorization_endpoint:config.authDomain+'/oauth2/authorize',token_endpoint:config.authDomain+'/oauth2/token',jwks_uri:issuer+'/.well-known/jwks.json',userinfo_endpoint:config.authDomain+'/oauth2/userInfo',revocation_endpoint:config.authDomain+'/oauth2/revoke'}});
  manager.events.addUserLoaded(user=>{if(!signingOut)state.user=user;});manager.events.addAccessTokenExpired(()=>{manager.stopSilentRenew();clearPrivateState();manager.removeUser().catch(()=>{});notify('Phiên đăng nhập hết hạn. Hãy đăng nhập lại.',true);});
  if(new URLSearchParams(location.search).has('code')||new URLSearchParams(location.search).has('error')){try{state.user=await manager.signinRedirectCallback();}catch{history.replaceState(null,'',location.pathname);throw new Error('Đăng nhập chưa hoàn tất hoặc liên kết đã hết hạn. Hãy thử đăng nhập lại.');}history.replaceState(null,'',location.pathname);}
  else state.user=await manager.getUser();
  api=createApi(config.apiBase,async()=>{if(state.user?.expired){const epoch=sessionEpoch;const user=await manager.signinSilent();if(epoch!==sessionEpoch)return null;state.user=user;}return state.user?.id_token;},fetch,()=>sessionEpoch);
  if(state.user){state.profile=await api('/me');signedIn();try{await loadShopProfile();}catch{if(state.user){$('shop-context').textContent='Chưa tải được thông tin shop. Bạn có thể làm mới tại mục Thông tin shop.';$('shop-context').classList.remove('hidden');}}}
  await navigate(location.hash.slice(1)||'assistant',{historyMode:'replace'});
}
window.addEventListener('pageshow',async event=>{if(!event.persisted||!manager)return;if(signingOut){await manager.removeUser();clearPrivateState();location.reload();return;}const stored=await manager.getUser();if(!stored||stored.expired)clearPrivateState();else if(stored.profile.sub!==state.user?.profile.sub)location.reload();});
start().catch(fail);
