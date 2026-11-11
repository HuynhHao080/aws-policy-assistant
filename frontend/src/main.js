import './app.css';
import './workspace.css';
import {FeedbackStore,feedbackReasons} from './feedback.js';
import {LatestTask,pollDocument} from './ui-flow.js';
import {ShopEditor,shopFields} from './shop-editor.js';
import { UserManager, WebStorageStateStore, Log } from 'oidc-client-ts';
import { createApi, uploadPdf, statusText, pdfErrorText } from './api.js';
import { PolicyEditor, policyStates, validityStates, validityText } from './policy-editor.js';
import { SavedPolicies, policyLinkRoute } from './policy-library.js';
import { SupportClient, supportStates, supportCategories, supportPriorities, questionPayload } from './support-client.js';

Log.setLevel(Log.NONE);
const $ = id => document.getElementById(id);
const state = { user:null, profile:null, docs:[], docToken:null, historyToken:null, policyToken:null, policyKeyword:'', auditToken:null, selected:new Set(), cache:new Map(), view:'assistant' };
let manager, api, config;
const latestTasks=new LatestTask();
const savedPolicies = new SavedPolicies({
  getItem: key => localStorage.getItem(key),
  setItem: (key, value) => localStorage.setItem(key, value),
  removeItem: key => localStorage.removeItem(key),
});
let policyLibraryMode = 'browse';
const feedbackStore=new FeedbackStore((path,options)=>{needApi();return api(path,options);});
let qualityReport=null;
let documentPreview = null;
let sessionEpoch=0, signingOut=false;
let adminPolicyToken=null,adminPolicyKeyword='',adminListEpoch=0;
let ticketToken=null,adminTicketToken=null,ticketListEpoch=0,adminTicketListEpoch=0;
const adminQueueRows = new Map();
const customerTicketRows = new Map();
const shopEditor=new ShopEditor((path,options)=>{needApi();return api(path,options);},renderShopControls);
const supportClient=new SupportClient((path,options)=>{needApi();return api(path,options);},renderSupportControls);
const policyEditor=new PolicyEditor((path,options)=>{needApi();return api(path,options);},renderPolicyEditorStatus);
const labels = {assistant:'Trợ lý chính sách',documents:'Tài liệu của tôi',policies:'Chính sách chung',history:'Lịch sử hỏi đáp',support:'Yêu cầu hỗ trợ',shop:'Thông tin shop',admin:'Quản trị',account:'Tài khoản'};
function node(tag, content, className) { const element=document.createElement(tag); if(content!==undefined) element.textContent=content; if(className) element.className=className; return element; }
function noticeAt(target,message,error=false){target.replaceChildren(node('span',message,'notice-message'));const close=node('button','×','notice-dismiss');close.type='button';close.setAttribute('aria-label','Ẩn thông báo');close.onclick=()=>target.classList.add('hidden');target.append(close);target.className=`notice${error?' error':''}`;target.setAttribute('role',error?'alert':'status');}
function notify(message,error=false){if($('ticket-dialog').open){noticeAt($('ticket-dialog-notice'),message,error);return;}noticeAt($('notice'),message,error);}
function fail(error){const message=error.status===401?'Phiên đăng nhập đã hết hạn hoặc bạn chưa đăng nhập. Hãy đăng nhập để tiếp tục.':error.status===403?'Tài khoản này không có quyền thực hiện thao tác.':error.status===429?'Đã đạt hạn mức sử dụng trong ngày hoặc tháng. Hãy kiểm tra hạn mức và thử lại sau.':error instanceof TypeError&&/fetch|network/i.test(error.message)?'Kết nối bị gián đoạn. Hãy kiểm tra trạng thái trước khi gửi lại để tránh tạo trùng dữ liệu.':error.message||'Chưa thể hoàn tất. Vui lòng thử lại.';notify(message,true);}
function button(label,action,className='text-button') { const item=node('button',label,className);item.type='button';item.addEventListener('click',()=>guard(item,action));return item; }
async function guard(control,action) { if(control?.disabled)return; if(control){control.disabled=true;control.setAttribute('aria-busy','true');}try{return await action();}catch(error){fail(error);}finally{if(control){control.disabled=false;control.removeAttribute('aria-busy');}if(control?.closest('#admin-policy-form')||['new-policy','restore-policy'].includes(control?.id))renderPolicyEditorStatus();if(control?.closest('#ticket-dialog'))renderSupportControls();if(control?.closest('#shop-form')||control?.id==='reload-shop')renderShopControls();} }
function needApi() { if(!api)throw new Error('Dịch vụ chưa được kết nối.');if(!state.user)throw Object.assign(new Error('Vui lòng đăng nhập.'),{status:401}); }
function groups() { const value=state.profile?.groups||[];return Array.isArray(value)?value:String(value).replace(/[\[\]"]/g,'').split(',').map(s=>s.trim()); }
function signedIn() {
  savedPolicies.selectAccount(state.user?.profile?.sub);
  $('saved-policy-count').textContent = savedPolicies.items.length;
  $('guest-welcome').classList.toggle('hidden',Boolean(state.user));
  $('history-toolbar').classList.toggle('hidden', !state.user);
  $('document-toolbar').classList.toggle('hidden', !state.user);
  document.querySelectorAll('form').forEach(form=>{if(state.user)form.removeAttribute('inert');else form.setAttribute('inert','');});
  document.querySelectorAll('[data-auth-control]').forEach(control=>{control.disabled=!state.user;});
  document.querySelector('.danger-zone').classList.toggle('hidden',!state.user);

  $('support-limit-note').textContent=`Chỉ chia sẻ thông tin bạn nhập. PDF và lịch sử hỏi đáp không tự đính kèm. Không gửi email tự động; xem phản hồi tại mục này. Tối đa ${state.profile?.limits?.tickets_per_day??5} yêu cầu/ngày UTC, 20 tin nhắn/yêu cầu; lưu tối đa 90 ngày từ khi tạo.`;
  $('account-label').textContent=state.profile?.email||'Khách';$('avatar').textContent=(state.profile?.email||'P')[0].toUpperCase();$('auth-button').textContent=state.user?'Đăng xuất':'Đăng nhập / Đăng ký';$('admin-nav').classList.toggle('hidden',!groups().includes('administrators'));
  $('profile-info').replaceChildren();
  if(state.profile){
    const limits = state.profile.limits;
    const stats = node('dl', undefined, 'account-stats');
    for (const [label, value] of [
      ['Lượt tải PDF', limits.uploads_per_day],
      ['Câu hỏi', limits.questions_per_day],
      ['Yêu cầu hỗ trợ', limits.tickets_per_day ?? 5],
    ]) {
      const stat = node('div');
      stat.append(node('dt', label), node('dd', String(value)));
      stats.append(stat);
    }
    $('profile-info').append(node('p', state.profile.email, 'profile-email'), node('p', 'Hạn mức mỗi ngày (UTC)', 'small muted'), stats);
    if(!state.profile.ai_available)notify('AI chưa được cấu hình. Bạn vẫn có thể quản lý tài liệu và tìm chính sách.');}
}
let followupContext = null;
const followupBox = node('div', undefined, 'followup-context hidden');
const followupLabel = node('span');
followupLabel.setAttribute('role', 'status');
followupBox.append(followupLabel, button('Bỏ câu hỏi trước', () => {
  setFollowupContext(null);
  $('question').focus();
}, 'secondary'));
$('question').before(followupBox);

function setFollowupContext(context) {
  followupContext = context;
  followupLabel.textContent = context ? `Hỏi tiếp về: ${context.question.slice(0, 120)}${context.question.length > 120 ? '…' : ''}` : '';
  followupBox.classList.toggle('hidden', !context);
}

async function startFollowup(question, conversationId) {
  const epoch = sessionEpoch;
  if (state.view !== 'assistant' && !await navigate('assistant', {focus:true})) return;
  if (!state.user || epoch !== sessionEpoch) return;
  setFollowupContext({question, conversationId});
  $('question').focus();
}

function clearPrivateState() {
  setFollowupContext(null);
  policyLibraryMode = 'browse';
  $('browse-policies').setAttribute('aria-pressed', 'true');
  $('saved-policies').setAttribute('aria-pressed', 'false');
  $('policy-library-status').textContent = '';
  $('document-filter').value = '';
  $('document-status-filter').value = 'all';
  $('document-results').textContent = '';
  $('document-text-dialog').close();
  clearDocumentPreview();
  $('history-filter').value = '';
  $('history-source-filter').value = 'all';
  $('history-results').textContent = '';
  feedbackStore.clear();qualityReport=null;$('quality-overview').replaceChildren();$('quality-feedback').replaceChildren();$('quality-month').replaceChildren();$('export-quality').disabled=true;
  latestTasks.clear();state.policyToken=null;state.policyKeyword='';state.auditToken=null;$('document-count').textContent='—';$('policy-keyword').value='';$('ticket-lookup-form').reset();$('admin-ticket-category').value='';$('admin-ticket-priority').value='';$('admin-ticket-filter').value='open';$('admin-ticket-assignee').value='all';for(const id of ['more-documents','more-sources','more-history','more-policies','more-tickets','more-admin-tickets','more-audit'])$(id).classList.add('hidden');$('answer-area').setAttribute('aria-busy','false');$('question-count').textContent='0 / 2.000 ký tự';$('policy-dialog').close();$('policy-dialog-content').replaceChildren();
  shopEditor.clear();fillShopEditor(null);$('shop-profile').replaceChildren(node('p','Đăng nhập để xem thông tin shop.'));$('shop-context').classList.add('hidden');
  supportClient.clear();resetAdminQueue();customerTicketRows.clear();customerTicketFilter.value='all';customerTicketStatus.textContent='';ticketToken=null;adminTicketToken=null;ticketListEpoch++;adminTicketListEpoch++;
  $('ticket-dialog').close();$('ticket-thread').replaceChildren();$('new-ticket-form').reset();setSupportAnswer('');$('ticket-reply-form').reset();$('ticket-note-form').reset();$('ticket-takeover-form').reset();$('ticket-internal-notes').replaceChildren();$('ticket-assignment-history').replaceChildren();$('ticket-assignment-label').textContent='';$('ticket-note-count').textContent='';$('ticket-staff-controls').classList.add('hidden');
  policyEditor.clear();adminPolicyToken=null;adminPolicyKeyword='';adminListEpoch++;
  sessionEpoch++;state.user=null;state.profile=null;state.docs=[];state.selected.clear();state.cache.clear();state.docToken=null;state.historyToken=null;
  for(const id of ['answer-area','history-list','documents-list','source-selector','audit-list','usage-overview','policy-results','admin-policy-list','ticket-list','admin-ticket-list'])$(id).replaceChildren();
  $('question').value='';$('pdf-file').value='';$('upload-status').textContent='';$('delete-confirmation').value='';fillPolicyEditor(null);$('admin-policy-keyword').value='';$('more-admin-policies').classList.add('hidden');
  $('notice').classList.add('hidden');signedIn();
}
async function navigate(view,{historyMode='push',focus=false}={}) {
  const linkedPolicy = policyLinkRoute(view);
  if (linkedPolicy) view = 'policies';
  if(!Object.hasOwn(labels,view))view='assistant';
  if(view==='admin'&&!groups().includes('administrators')){view='account';notify('Quản trị chỉ dành cho tài khoản được cấp quyền.',true);}
  if(state.view==='admin'&&view!=='admin'&&(policyEditor.dirty||shopEditor.dirty)&&!confirm('Rời trang khi có thay đổi chưa lưu?'))return false;
  if(state.view!==view&&(state.view==='support'||$('ticket-dialog').open)&&supportUnsaved()&&!confirm('Rời trang khi nội dung hỗ trợ chưa được gửi?'))return false;
  state.view=view;
  if ($('policy-dialog').open) $('policy-dialog').close();
  setNavigationOpen(false);
  document.querySelectorAll('[data-panel]').forEach(panel=>panel.classList.toggle('hidden',panel.dataset.panel!==view));
  document.querySelectorAll('nav [data-view]').forEach(control=>{const active=control.dataset.view===view;control.classList.toggle('active',active);if(active)control.setAttribute('aria-current','page');else control.removeAttribute('aria-current');});
  $('view-label').textContent=labels[view];
  const hash = linkedPolicy ? `#policy/${linkedPolicy}` : `#${view}`;
  if (location.hash !== hash) history[historyMode === 'push' ? 'pushState' : 'replaceState'](null, '', hash);
  if(focus){const heading=document.querySelector(`[data-panel="${view}"] h1`);heading?.setAttribute('tabindex','-1');heading?.focus({preventScroll:true});window.scrollTo({top:0,left:0,behavior:'auto'});}
  if (!state.user) {
    if (linkedPolicy) $('policy-library-status').textContent = 'Đăng nhập để mở chính sách từ liên kết này.';
    return true;
  }
  if (linkedPolicy) await openLibraryPolicy(linkedPolicy);
  if(view==='documents'||view==='assistant')await loadDocs(false);
  if(view==='history')await loadHistory(false);
  if(view==='support')await loadTickets();
  if(view==='shop')await loadShopProfile();
  if(view==='admin')await loadAdmin();
  return true;
}
function setNavigationOpen(open) {
  const toggle = $('nav-toggle');
  toggle.setAttribute('aria-expanded', String(open));
  toggle.textContent = open ? 'Đóng menu' : 'Menu';
}

$('nav-toggle').addEventListener('click', () => {
  setNavigationOpen($('nav-toggle').getAttribute('aria-expanded') !== 'true');
});
document.querySelector('.sidebar').addEventListener('keydown', event => {
  if (event.key !== 'Escape' || $('nav-toggle').getAttribute('aria-expanded') !== 'true') return;
  event.preventDefault();
  setNavigationOpen(false);
  $('nav-toggle').focus();
});
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
  state.docs=more?[...new Map([...state.docs,...result.documents].map(doc => [doc.doc_id,doc])).values()]:result.documents;state.docToken=result.next_token;
  $('more-documents').classList.toggle('hidden',!state.docToken);$('more-sources').classList.toggle('hidden',!state.docToken);$('document-count').textContent=`${state.docs.length}${state.docToken?'+':''}`;
  $('documents-list').replaceChildren();
  for(const doc of state.docs){state.cache.set(doc.doc_id,doc);if(doc.status!=='processed')state.selected.delete(doc.doc_id);}
  for(const doc of state.docs){const tr=node('tr');tr.dataset.documentId=doc.doc_id;const name=node('td');name.append(node('div',doc.title||doc.filename||'Tài liệu','doc-title'),node('small',doc.created_at?new Date(doc.created_at).toLocaleDateString('vi-VN'):''));const status=node('td');status.append(node('span',statusText[doc.status]||doc.status,`badge ${doc.status}`));if(doc.error_code)status.append(node('span',pdfErrorText[doc.error_code] || 'Hãy làm mới trạng thái hoặc kiểm tra lại tệp.', 'error-code'));const actions=node('td',undefined,'document-actions');
    if (doc.status === 'processed') {
      actions.append(button('Hỏi từ PDF này', async () => {
        const epoch = sessionEpoch;
        if (!await navigate('assistant', {focus:true}) || epoch !== sessionEpoch) return;
        const selected = state.cache.get(doc.doc_id);
        if (selected?.status !== 'processed') throw new Error('PDF chưa sẵn sàng. Hãy làm mới thư viện.');
        state.selected.clear();
        state.selected.add(doc.doc_id);
        $('source-scope').value = 'documents';
        renderSources();
        $('question').focus();
      }, 'secondary'), button('Xem văn bản', () => openDocumentText(doc.doc_id), 'secondary'), button('Tải PDF', () => download(doc.doc_id)));
    }
    if (doc.status === 'awaiting_upload') {
      actions.append(button('Gửi xử lý', async () => {
        await api('/documents/submit', {method:'POST', body:{doc_id:doc.doc_id, s3_key:doc.s3_key}});
        await trackDocument(doc.doc_id);
      }, 'secondary'));
    }
    if(doc.status!=='deleting')actions.append(button('Đổi tên',async()=>{const title=prompt('Tên tài liệu mới',doc.title||doc.filename);if(!title?.trim())return;await api(`/documents/${doc.doc_id}`,{method:'PATCH',body:{title}});await loadDocs();}),button('Xóa',async()=>{if(!confirm(`Xóa vĩnh viễn PDF “${doc.title||doc.filename}” và dữ liệu trích xuất?`))return;await api(`/documents/${doc.doc_id}`,{method:'DELETE'});state.selected.delete(doc.doc_id);state.cache.delete(doc.doc_id);notify('Đã tiếp nhận yêu cầu xóa tài liệu.');await loadDocs();}));
    const pages = node('td', String(doc.page_count || '—'), 'document-pages');
    pages.setAttribute('aria-label', doc.page_count ? `${doc.page_count} trang` : 'Chưa có số trang');
    tr.append(name,status,pages,actions);$('documents-list').append(tr);}
  if(!state.docs.length){const row=node('tr');const td=node('td',state.docToken?'Trang này chưa có tài liệu. Chọn Xem thêm để tiếp tục.':'Chưa có tài liệu. Tải PDF đầu tiên của bạn ở phía trên.','empty-small');td.colSpan=4;row.append(td);$('documents-list').append(row);}
  applyDocumentFilters();
  renderSources();
}
function applyDocumentFilters() {
  const query = historySearchText($('document-filter').value).trim();
  const filter = $('document-status-filter').value;
  const working = new Set(['awaiting_upload', 'pending', 'processing', 'ocr_pending']);
  const docs = new Map(state.docs.map(doc => [doc.doc_id, doc]));
  let visible = 0;
  for (const row of $('documents-list').querySelectorAll('[data-document-id]')) {
    const doc = docs.get(row.dataset.documentId);
    const statusMatches = filter === 'all' || (filter === 'working' ? working.has(doc.status) : doc.status === filter);
    const textMatches = historySearchText(`${doc.title || ''} ${doc.filename || ''}`).includes(query);
    row.hidden = !statusMatches || !textMatches;
    if (!row.hidden) visible++;
  }
  $('document-results').textContent = `${visible} / ${state.docs.length} PDF đã tải danh sách${state.docToken ? ' · Chọn Xem thêm để tìm tiếp.' : ''}`;
}

function clearDocumentPreview() {
  documentPreview = null;
  $('document-text-title').textContent = 'Văn bản PDF';
  $('document-page-number').textContent = '';
  $('document-text-status').textContent = '';
  $('document-text-content').replaceChildren();
  $('document-text-find-tools').classList.add('hidden');
  $('document-text-find').value = '';
  $('document-text-matches').textContent = '';
  $('retry-document-text').classList.add('hidden');
  $('jump-document-page').classList.add('hidden');
  $('document-page-input').value = '';
  for (const id of ['previous-document-page', 'next-document-page', 'copy-document-page', 'download-document-page']) $(id).disabled = true;
}

function renderDocumentText() {
  const query = historySearchText($('document-text-find').value).trim();
  let matches = 0;
  const fragments = (documentPreview?.chunks || []).map(text => {
    const paragraph = node('p', undefined, 'document-text-fragment');
    if (!query) {
      paragraph.textContent = text;
      return paragraph;
    }
    let normalized = '';
    const starts = [];
    const ends = [];
    for (const part of text.matchAll(/\P{M}\p{M}*|\p{M}+/gu)) {
      const folded = historySearchText(part[0]);
      normalized += folded;
      for (let i = 0; i < folded.length; i++) {
        starts.push(part.index);
        ends.push(part.index + part[0].length);
      }
    }
    let previous = 0;
    let index = normalized.indexOf(query);
    while (index !== -1) {
      const start = starts[index];
      const end = ends[index + query.length - 1];
      paragraph.append(text.slice(previous, start), node('mark', text.slice(start, end)));
      matches++;
      previous = end;
      index = normalized.indexOf(query, index + query.length);
    }
    paragraph.append(text.slice(previous));
    return paragraph;
  });
  $('document-text-content').replaceChildren(...fragments);
  $('document-text-matches').textContent = query ? `${matches} kết quả trong các đoạn hiển thị` : '';
}

async function openDocumentText(docId, page = 1) {
  const dialog = $('document-text-dialog');
  const isCurrent = latestTasks.begin('document-preview');
  const search = documentPreview?.docId === docId ? $('document-text-find').value : '';
  clearDocumentPreview();
  documentPreview = {docId, page};
  $('document-text-find').value = search;
  $('document-page-number').textContent = `Trang ${page}`;
  $('document-text-status').textContent = 'Đang tải văn bản…';
  if (!dialog.open) dialog.showModal();
  try {
    const data = await api(`/documents/${encodeURIComponent(docId)}/text?page=${page}`);
    if (!isCurrent() || !dialog.open) return;
    if (data.doc_id !== docId || data.page !== page || !Number.isInteger(data.page_count)
      || data.page_count < page || data.page_count > 100 || !Array.isArray(data.chunks)
      || data.chunks.some(chunk => typeof chunk !== 'string')) {
      throw new Error('Dữ liệu văn bản không hợp lệ.');
    }
    documentPreview = {docId, page, chunks:data.chunks};
    $('document-text-title').textContent = data.title || 'Văn bản PDF';
    $('document-page-number').textContent = `Trang ${page} / ${data.page_count}`;
    $('document-text-status').textContent = data.truncated
      ? 'Văn bản dài. Hiển thị tối đa 20.000 ký tự của trang.'
      : data.chunks.length ? 'Các đoạn trích của trang' : 'Trang này không có văn bản trích xuất.';
    $('document-text-find-tools').classList.toggle('hidden', !data.chunks.length);
    renderDocumentText();
    $('previous-document-page').disabled = page <= 1;
    $('next-document-page').disabled = page >= data.page_count;
    $('copy-document-page').disabled = !data.chunks.length;
    $('download-document-page').disabled = !data.chunks.length;
    $('document-page-input').max = data.page_count;
    $('document-page-input').value = page;
    $('jump-document-page').classList.toggle('hidden', data.page_count <= 1);
  } catch (error) {
    if (!isCurrent() || !dialog.open) return;
    $('document-text-status').textContent = [403,404,409,410].includes(error.status)
      ? 'Văn bản PDF hiện không còn truy cập được.'
      : 'Chưa tải được văn bản trang này.';
    $('retry-document-text').classList.toggle('hidden', [403,404,409,410].includes(error.status));
  }
}

$('document-filter').addEventListener('input', applyDocumentFilters);
$('document-status-filter').addEventListener('change', applyDocumentFilters);
$('document-text-find').addEventListener('input', renderDocumentText);
$('close-document-text').onclick = () => $('document-text-dialog').close();
$('document-text-dialog').addEventListener('close', () => {
  if (!$('document-text-dialog').open) {
    latestTasks.begin('document-preview');
    clearDocumentPreview();
  }
});
$('previous-document-page').onclick = () => openDocumentText(documentPreview.docId, documentPreview.page - 1);
$('next-document-page').onclick = () => openDocumentText(documentPreview.docId, documentPreview.page + 1);
$('retry-document-text').onclick = () => openDocumentText(documentPreview.docId, documentPreview.page);
$('jump-document-page').onsubmit = event => {
  event.preventDefault();
  const input = $('document-page-input');
  const page = input.valueAsNumber;
  if (!documentPreview?.chunks || !input.reportValidity() || page === documentPreview.page) return;
  openDocumentText(documentPreview.docId, page);
};
$('copy-document-page').onclick = async () => {
  const preview = documentPreview;
  if (!preview?.chunks?.length) return;
  const control = $('copy-document-page');
  control.disabled = true;
  try {
    await navigator.clipboard.writeText(preview.chunks.join('\n\n'));
    if (documentPreview === preview) $('document-text-status').textContent = 'Đã sao chép văn bản trang.';
  } catch {
    if (documentPreview === preview) $('document-text-status').textContent = 'Bạn có thể chọn văn bản để sao chép thủ công.';
  } finally {
    if (documentPreview === preview) control.disabled = false;
  }
};
$('download-document-page').onclick = () => {
  const preview = documentPreview;
  if (!preview?.chunks?.length) return;
  const url = URL.createObjectURL(new Blob([preview.chunks.join('\n\n')], {type:'text/plain;charset=utf-8'}));
  const link = node('a');
  link.href = url;
  link.download = `policy-assistant-trang-${preview.page}.txt`;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
};
async function trackDocument(docId) {
  const isCurrent = latestTasks.begin('document-processing');
  const status = $('upload-status');
  status.textContent = 'Đã gửi xử lý. Đang kiểm tra trạng thái PDF…';
  try {
    await loadDocs();
    const doc = await pollDocument(api, docId, {
      isCurrent,
      onStatus: item => {
        status.textContent = `${item.title || 'Tài liệu'} · ${statusText[item.status] || item.status}`;
      },
    });
    if (!isCurrent()) return;
    if (doc?.status === 'processed') status.textContent = 'PDF đã sẵn sàng. Chọn Hỏi từ PDF này trong thư viện.';
    else if (doc?.status === 'failed') status.textContent = pdfErrorText[doc.error_code] || 'PDF chưa xử lý được. Kiểm tra lỗi trong thư viện.';
    else if (doc?.status !== 'deleted') status.textContent = 'PDF vẫn đang xử lý. Dùng Làm mới để kiểm tra tiếp.';
    await loadDocs();
  } catch (error) {
    if (!isCurrent()) return;
    status.textContent = 'Đã gửi xử lý. Hãy làm mới thư viện để kiểm tra trạng thái.';
    throw error;
  }
}
async function download(docId, isCurrent = () => true) {
  const data = await api(`/documents/${encodeURIComponent(docId)}/download`);
  if (!isCurrent()) return;
  const url = new URL(data.download_url);
  if (url.protocol !== 'https:') throw new Error('Đường dẫn tải không hợp lệ.');
  const anchor = node('a');
  anchor.href = url.href;
  anchor.rel = 'noopener noreferrer';
  anchor.download = 'policy-document.pdf';
  anchor.click();
}
function citationTitle(source) {
  return `${source.source_id} · ${source.title}${source.page ? ` — Trang ${source.page}` : ''}`;
}

const sourceScopeLabels = {
  all: 'chính sách chung + PDF cá nhân',
  policies: 'chỉ chính sách chung',
  documents: 'chỉ PDF đã chọn',
};

function citationValidity(source) {
  return source.effective_from || source.effective_until ? validityText(source) : '';
}

function downloadAnswer(question, result, sources) {
  const citations = sources.map(source => [
    citationTitle(source),
    citationValidity(source),
    source.excerpt,
  ].filter(Boolean).join('\n'));
  const content = [
    'Policy Assistant',
    'Câu hỏi\n' + question,
    'Câu trả lời\n' + result.answer,
    'Phạm vi nguồn: ' + (sourceScopeLabels[result.source_scope] || sourceScopeLabels.all),
    ...(citations.length ? ['Đoạn trích tại thời điểm trả lời', ...citations] : ['Chưa đủ nguồn tham khảo']),
  ].join('\n\n');
  const url = URL.createObjectURL(new Blob([content], {type:'text/plain;charset=utf-8'}));
  const link = node('a');
  link.href = url;
  link.download = 'policy-assistant-cau-tra-loi.txt';
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function compareCitations(sources, returnSource) {
  const dialog = $('policy-dialog');
  $('policy-dialog-title').textContent = 'Đối chiếu nguồn tham khảo';
  const cards = sources.map(source => {
    const card = node('article', undefined, 'comparison-source');
    const kind = source.doc_id ? 'PDF cá nhân' : 'Chính sách chung';
    card.append(node('p', kind, 'small muted'), node('h3', citationTitle(source)));
    const validity = citationValidity(source);
    if (validity) card.append(node('p', validity, 'small muted'));
    card.append(node('blockquote', source.excerpt || 'Đoạn trích chưa có trong lịch sử này.', 'citation-excerpt'));
    if (source.doc_id || source.policy_id) {
      const action = button('Mở nguồn', () => openCitation(source, () => compareCitations(sources, source)), 'secondary');
      action.setAttribute('aria-label', 'Mở nguồn ' + citationTitle(source));
      card.append(action);
    }
    return card;
  });
  $('policy-dialog-content').replaceChildren(...cards);
  if (!dialog.open) dialog.showModal();
  if (returnSource) cards[sources.indexOf(returnSource)]?.querySelector('button')?.focus();
}

async function openCitation(source, back) {
  const dialog = $('policy-dialog');
  const content = $('policy-dialog-content');
  const current = node('section');
  const quote = node('blockquote', source.excerpt || 'Đoạn trích chưa có trong lịch sử này.', 'citation-excerpt');
  $('policy-dialog-title').textContent = citationTitle(source);
  content.replaceChildren(node('h3', 'Đoạn trích dùng để trả lời'));
  const validity = citationValidity(source);
  if (validity) content.append(node('p', validity, 'small muted'));
  content.append(quote, current);
  const backButton = back && button('Về phần đối chiếu', back, 'secondary');
  if (backButton) content.prepend(backButton);
  if (!dialog.open) dialog.showModal();
  backButton?.focus();

  const epoch = sessionEpoch;
  const isCurrent = () => epoch === sessionEpoch && dialog.open && content.contains(current);
  if (source.doc_id) {
    const status = node('p', '', 'small muted');
    status.setAttribute('role', 'status');
    const action = button('Tải PDF gốc', async () => {
      status.textContent = 'Đang lấy liên kết tải PDF…';
      try {
        await download(source.doc_id, isCurrent);
        if (isCurrent()) status.textContent = 'Đã mở liên kết tải PDF.';
      } catch (error) {
        if (!isCurrent()) return;
        status.textContent = [403, 404].includes(error.status)
          ? 'PDF gốc không còn truy cập được.'
          : 'Chưa tải được PDF. Bạn có thể thử lại.';
      }
    }, 'secondary');
    const page = Number.isInteger(source.page) && source.page >= 1 && source.page <= 100 ? source.page : 1;
    current.append(button('Xem văn bản trang', () => {
      dialog.close();
      return openDocumentText(source.doc_id, page);
    }, 'secondary'), action, status);
    return;
  }
  if (!source.policy_id) return;

  const status = node('p', 'Đang tải chính sách hiện hành…', 'small muted');
  status.setAttribute('role', 'status');
  current.append(node('h3', 'Chính sách hiện hành'), status);
  try {
    const policy = await api(`/policies/${encodeURIComponent(source.policy_id)}`);
    if (!isCurrent()) return;
    status.textContent = 'Nội dung công bố hiện tại có thể đã thay đổi kể từ khi trả lời.';
    showPolicy(policy, current);
  } catch (error) {
    if (!isCurrent()) return;
    status.textContent = error.status === 404
      ? 'Chính sách hiện không còn được công bố hoặc đã hết hiệu lực.'
      : 'Chưa tải được chính sách hiện hành. Mở lại nguồn để thử lại.';
  }
}
function renderAnswer(question, result, target = $('answer-area'), inHistory = false) {
  if (!inHistory) {
    target.replaceChildren(node('div', question, 'question-bubble'));
  }
  target.append(node('div', result.grounded ? 'Có nguồn tham khảo' : 'Chưa đủ thông tin', 'answer-label'),
    node('p', result.answer, 'answer-text'),
    node('small', 'Nguồn: ' + (sourceScopeLabels[result.source_scope] || sourceScopeLabels.all), 'small muted'));
  renderFeedback(result,target);
  const sources = result.citations || [];
  for (const source of sources) {
    const card = button('', () => openCitation(source), 'citation-card');
    card.append(node('strong', citationTitle(source)));
    target.append(card);
  }
  const actions = node('div', undefined, 'answer-actions');
  if (result.conversation_id) actions.append(button('Hỏi tiếp', () => startFollowup(question, result.conversation_id), 'secondary'));
  if (sources.length > 1) actions.append(button(`Đối chiếu ${sources.length} nguồn`, () => compareCitations(sources), 'secondary'));
  actions.append(button('Sao chép câu trả lời', async () => {
    if (!navigator.clipboard?.writeText) throw new Error('Trình duyệt chưa cấp quyền sao chép. Bạn có thể chọn và sao chép văn bản.');
    const epoch = sessionEpoch;
    const citations = sources.map(source => `${citationTitle(source)}\n${source.excerpt || ''}`);
    await navigator.clipboard.writeText([result.answer, ...(citations.length ? ['Nguồn tham khảo', ...citations] : [])].join('\n\n'));
    if (epoch === sessionEpoch) notify(citations.length ? 'Đã sao chép câu trả lời và các nguồn đi kèm.' : 'Đã sao chép câu trả lời.');
  }, 'secondary'));
  actions.append(button('Tải câu trả lời (.txt)', () => downloadAnswer(question, result, sources), 'secondary'));
  actions.append(button('Nhờ nhân viên hỗ trợ', () => prepareSupportDraft(question, result.answer)));
  target.append(actions);
  target.scrollTop = 0;
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
function policyActions(policy, open = true) {
  const actions = node('div', undefined, 'policy-library-actions');
  const status = node('p', '', 'small muted');
  status.setAttribute('role', 'status');
  if (open) actions.append(button('Đọc chính sách', () => openLibraryPolicy(policy.policy_id), 'secondary'));
  const save = button('', () => {
    try {
      savedPolicies.toggle(policy);
      refreshPolicyBookmarks();
      status.textContent = savedPolicies.has(policy.policy_id) ? 'Đã lưu trên thiết bị này.' : 'Đã bỏ lưu.';
    } catch (error) {
      status.textContent = error.name === 'QuotaExceededError' || error.name === 'SecurityError'
        ? 'Trình duyệt chưa cho phép lưu trên thiết bị.' : error.message;
    }
  }, 'secondary');
  save.dataset.savedPolicy = policy.policy_id;
  updatePolicyBookmark(save);
  actions.append(save, button('Sao chép liên kết', async () => {
    const href = `${location.origin}${location.pathname}#policy/${policy.policy_id}`;
    try {
      await navigator.clipboard.writeText(href);
      status.textContent = 'Đã sao chép liên kết.';
    } catch {
      status.replaceChildren(node('span', 'Liên kết để sao chép'), node('code', href));
    }
  }), status);
  return actions;
}

function updatePolicyBookmark(control) {
  const saved = savedPolicies.has(control.dataset.savedPolicy);
  control.textContent = saved ? 'Bỏ lưu' : 'Lưu chính sách';
  control.setAttribute('aria-pressed', String(saved));
}

function refreshPolicyBookmarks() {
  $('saved-policy-count').textContent = savedPolicies.items.length;
  document.querySelectorAll('[data-saved-policy]').forEach(updatePolicyBookmark);
  if (policyLibraryMode === 'saved') renderSavedPolicies();
}

function policyCard(policy) {
  const card = node('article', undefined, 'policy-card policy-directory-card');
  card.append(node('div', [policy.category, policy.policy_id].filter(Boolean).join(' · '), 'policy-meta'), node('h2', policy.title));
  if (policy.effective_from || policy.effective_until) card.append(node('p', validityText(policy), 'small muted'));
  if (policy.content) {
    const excerpt = policy.content.trim().replace(/\s+/g, ' ');
    card.append(node('p', excerpt.length > 240 ? excerpt.slice(0, 240) + '…' : excerpt));
  }
  card.append(policyActions(policy));
  return card;
}

async function openLibraryPolicy(id) {
  const dialog = $('policy-dialog');
  const content = $('policy-dialog-content');
  const panel = node('div');
  content.replaceChildren(panel);
  $('policy-dialog-title').textContent = 'Chính sách';
  panel.append(node('p', 'Đang tải chính sách…', 'loading-state'));
  if (!dialog.open) dialog.showModal();
  const isCurrent = latestTasks.begin('policy-detail');
  try {
    const policy = await api(`/policies/${encodeURIComponent(id)}`);
    if (!isCurrent() || !dialog.open || !content.contains(panel)) return;
    if (policy.policy_id !== id) throw new Error('Dữ liệu chính sách không hợp lệ.');
    $('policy-dialog-title').textContent = policy.title;
    panel.replaceChildren();
    showPolicy(policy, panel);
    panel.append(policyActions(policy, false));
  } catch (error) {
    if (!isCurrent() || !dialog.open || !content.contains(panel)) return;
    panel.replaceChildren(node('p', error.status === 404
      ? 'Chính sách hiện không còn được công bố hoặc đã hết hiệu lực.'
      : 'Chưa tải được chính sách. Mở lại để thử lại.', 'empty-small'));
    const bookmark = savedPolicies.items.find(item => item.policy_id === id);
    if (bookmark) panel.append(policyActions(bookmark, false));
  }
}

function renderSavedPolicies() {
  const query = historySearchText($('policy-keyword').value).trim();
  const matches = savedPolicies.items.filter(item => historySearchText(`${item.title} ${item.policy_id}`).includes(query));
  $('policy-results').replaceChildren(...matches.map(policyCard));
  $('policy-library-status').textContent = `${matches.length} / ${savedPolicies.items.length} chính sách lưu trên thiết bị này`;
  if (!matches.length) $('policy-results').append(node('p', savedPolicies.items.length ? 'Chưa tìm thấy mục đã lưu phù hợp.' : 'Bạn chưa lưu chính sách nào.', 'empty-small'));
}

function setPolicyLibraryMode(mode) {
  latestTasks.begin('policies');
  policyLibraryMode = mode;
  state.policyToken = null;
  $('browse-policies').setAttribute('aria-pressed', String(mode === 'browse'));
  $('saved-policies').setAttribute('aria-pressed', String(mode === 'saved'));
  $('more-policies').classList.add('hidden');
  if (mode === 'saved') renderSavedPolicies();
  else {
    $('policy-results').replaceChildren();
    $('policy-library-status').textContent = 'Nhập từ khóa để tìm trong chính sách đang công bố.';
  }
}

async function searchPolicies(more = false) {
  needApi();
  if (policyLibraryMode === 'saved') {
    renderSavedPolicies();
    return;
  }
  const isCurrent = latestTasks.begin('policies');
  if (!more) {
    state.policyKeyword = $('policy-keyword').value.trim();
    state.policyToken = null;
    $('policy-results').replaceChildren();
    $('more-policies').classList.add('hidden');
  }
  if (!state.policyKeyword || (more && !state.policyToken)) {
    $('policy-library-status').textContent = 'Nhập từ khóa để tìm chính sách.';
    return;
  }
  $('policy-library-status').textContent = 'Đang tìm chính sách…';
  const cursor = state.policyToken ? `&next_token=${encodeURIComponent(state.policyToken)}` : '';
  try {
    const result = await api(`/policies?keyword=${encodeURIComponent(state.policyKeyword)}&limit=10${cursor}`);
    if (!isCurrent()) return;
    $('policy-results').append(...result.policies.map(policyCard));
    state.policyToken = result.next_token;
    $('more-policies').classList.toggle('hidden', !state.policyToken);
    $('policy-library-status').textContent = `${$('policy-results').children.length} kết quả đã tải${state.policyToken ? ' · Còn trang tiếp theo' : ''}`;
  } catch (error) {
    if (!isCurrent()) return;
    $('policy-library-status').textContent = 'Chưa tải được kết quả.';
    throw error;
  }
}

function historySearchText(value) {
  return String(value ?? '').toLowerCase().normalize('NFD').replace(/\p{M}/gu, '').replaceAll('đ', 'd');
}

function applyHistoryFilters() {
  const terms = historySearchText($('history-filter').value).trim().split(/\s+/).filter(Boolean);
  const source = $('history-source-filter').value;
  const cards = [...$('history-list').querySelectorAll('[data-conversation-id]')];
  let visible = 0;
  for (const card of cards) {
    const matches = (source === 'all' || card.dataset.source === source)
      && terms.every(term => card.dataset.search.includes(term));
    card.hidden = !matches;
    if (matches) visible++;
  }
  const pagination = state.historyToken ? ' · Có thể tải thêm để tìm trong các cuộc hỏi đáp cũ hơn.' : '';
  $('history-results').textContent = cards.length
    ? `${visible} / ${cards.length} cuộc đã tải${pagination}`
    : state.historyToken ? 'Trang này chưa có cuộc hỏi đáp còn lưu. Chọn Tải thêm để tiếp tục.' : 'Chưa có cuộc hỏi đáp nào.';
}

async function putQuestionInComposer(value) {
  const field = $('question');
  const draft = field.value;
  if (draft.trim() && draft !== value && !confirm('Thay câu hỏi đang soạn?')) return;
  const epoch = sessionEpoch;
  if (state.view !== 'assistant' && !await navigate('assistant', {focus:true})) return;
  if (!state.user || epoch !== sessionEpoch || field.value !== draft) return;
  setFollowupContext(null);
  field.value = value;
  field.dispatchEvent(new Event('input', {bubbles:true}));
  field.focus();
}

async function loadHistory(more = false) {
  needApi();
  const isCurrent = latestTasks.begin('history');
  const list = $('history-list');
  if (more && !state.historyToken) return;
  $('history-results').textContent = 'Đang tải lịch sử…';
  let result;
  try {
    result = await api(`/conversations${more ? `?next_token=${encodeURIComponent(state.historyToken)}` : ''}`);
  } catch (error) {
    if (!isCurrent()) return;
    applyHistoryFilters();
    throw error;
  }
  if (!isCurrent()) return;
  if (!more) list.replaceChildren();
  const existing = new Set([...list.querySelectorAll('[data-conversation-id]')].map(card => card.dataset.conversationId));
  for (const item of result.conversations) {
    if (existing.has(item.conversation_id)) continue;
    const card = node('details', undefined, 'history-card');
    card.dataset.conversationId = item.conversation_id;
    card.dataset.source = item.grounded ? 'grounded' : 'unanswered';
    card.dataset.search = historySearchText([item.question, item.answer, ...(item.citations || []).map(source => source.title)].join(' '));
    card.open = !list.children.length;
    const summary = node('summary');
    const date = node('time', new Date(item.created_at).toLocaleString('vi-VN'), 'small');
    date.dateTime = item.created_at;
    const meta = node('span', undefined, 'history-meta');
    meta.append(date, node('span', item.grounded ? 'Có nguồn' : 'Thiếu nguồn', 'history-source'));
    summary.append(node('strong', item.question), meta);
    const body = node('div', undefined, 'history-body');
    renderAnswer(item.question, item, body, true);
    body.querySelector('.answer-actions').append(
      button('Dùng lại câu hỏi', () => putQuestionInComposer(item.question), 'secondary'),
      button('Xóa cuộc hỏi đáp', async () => {
        if (!confirm('Xóa cuộc hỏi đáp này?')) return;
        await api(`/conversations/${encodeURIComponent(item.conversation_id)}`, {method:'DELETE'});
        if (followupContext?.conversationId === item.conversation_id) setFollowupContext(null);
        for (const row of list.querySelectorAll('[data-conversation-id]')) {
          if (row.dataset.conversationId === item.conversation_id) row.remove();
        }
        applyHistoryFilters();
      }),
    );
    card.append(summary, body);
    list.append(card);
    existing.add(item.conversation_id);
  }
  state.historyToken = result.next_token;
  $('more-history').classList.toggle('hidden', !state.historyToken);
  applyHistoryFilters();
}

async function loadAudit(more=false){const isCurrent=latestTasks.begin('audit');const result=await api(`/admin/audit${more&&state.auditToken?`?next_token=${encodeURIComponent(state.auditToken)}`:''}`);if(!isCurrent())return;if(!more)$('audit-list').replaceChildren();for(const item of result.events){const action=({'policy.put':'Công bố chính sách','policy.draft':'Lưu bản nháp','policy.restore_previous':'Khôi phục bản trước thành bản nháp','policy.publish':'Công bố chính sách','policy.archive':'Ngừng công bố','policy.archive.demo':'Ngừng công bố DEMO','policy.discard_draft':'Bỏ bản nháp','policy.delete':'Xóa chính sách','shop.save_draft':'Lưu nháp thông tin shop','shop.publish':'Công bố thông tin shop','shop.unpublish':'Ngừng công bố thông tin shop','shop.discard_draft':'Bỏ nháp thông tin shop','ticket.update':'Cập nhật hỗ trợ','ticket.delete':'Xóa yêu cầu hỗ trợ'})[item.action]||item.action;const row=node('div',`${action} · ${item.resource}`,'audit-event');row.append(node('small',`${new Date(item.event_id.split('#')[0]).toLocaleString('vi-VN')} · ${item.actor}`));$('audit-list').append(row);}state.auditToken=result.next_token;$('more-audit').classList.toggle('hidden',!state.auditToken);}
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
  restorePolicy.disabled=busy||dirty||Boolean(r?.draft)||!r?.previous_publication?.snapshot;
}
const previousPolicy = node('details', undefined, 'policy-card hidden');
const previousPolicyContent = node('div');
const restorePolicy = button('Khôi phục thành bản nháp', async () => {
  if (!confirm('Dùng nội dung bản trước để tạo bản nháp?')) return;
  const record = await policyEditor.transition('restore_previous');
  fillPolicyEditor(record);
  notify('Đã khôi phục nội dung vào bản nháp. Hãy kiểm tra trước khi công bố.');
  await Promise.all([loadAdminPolicies(), loadAudit()]);
}, 'secondary');
restorePolicy.id = 'restore-policy';
previousPolicy.append(node('summary', 'Bản công bố trước'), previousPolicyContent, restorePolicy);
$('policy-live-preview').after(previousPolicy);

function renderPreviousPolicy(record) {
  const previous = record?.previous_publication;
  previousPolicy.open = false;
  previousPolicy.classList.toggle('hidden', !previous?.snapshot);
  previousPolicyContent.replaceChildren();
  if (!previous?.snapshot) return;
  if (previous.published_at) previousPolicyContent.append(node('p',
    new Date(previous.published_at).toLocaleString('vi-VN'), 'small muted'));
  previousPolicyContent.append(node('h3', previous.snapshot.title));
  try {
    previousPolicyContent.append(node('p', validityText(previous.snapshot), 'small muted'));
  } catch {
    previousPolicyContent.append(node('p', 'Thời hạn đã lưu không hợp lệ.', 'small muted'));
  }
  previousPolicyContent.append(node('p', previous.snapshot.content, 'citation-excerpt'));
  if (record.draft) previousPolicyContent.append(node('p', 'Xử lý bản nháp hiện có trước khi khôi phục.', 'small muted'));
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
  renderPreviousPolicy(record);renderPolicyEditorStatus();renderPolicyValidityPreview();
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
function ticketDraftUnsaved(){return Boolean($('ticket-reply-message').value.trim()||$('ticket-note-text').value.trim()||$('ticket-takeover-reason').value.trim()||triageUnsaved());}
function readSupportDraft() {
  return {
    subject: $('new-ticket-subject').value,
    message: $('new-ticket-message').value,
    consent: $('ticket-consent').checked,
    category: $('new-ticket-category').value,
    order_ref: $('new-ticket-order').value,
  };
}
function supportUnsaved() {
  const {subject, message, consent, category, order_ref} = readSupportDraft();
  return Boolean(subject.trim() || message.trim() || consent || category !== 'general' || order_ref.trim() || ticketDraftUnsaved());
}

const attachAnswer = button('Thêm câu trả lời vào yêu cầu', () => {
  const field = $('new-ticket-message');
  const message = [field.value.trimEnd(), 'Câu trả lời từ trợ lý:', supportAnswer].filter(Boolean).join('\n\n');
  if (message.length > field.maxLength) {
    throw new Error('Nội dung vượt 1.500 ký tự. Hãy rút ngắn yêu cầu hoặc tóm tắt câu trả lời bằng lời của bạn.');
  }
  field.value = message;
  $('ticket-consent').checked = false;
  setSupportAnswer('');
  field.focus();
}, 'secondary');
let supportAnswer = '';
$('new-ticket-message').after(attachAnswer);
setSupportAnswer('');

function setSupportAnswer(answer) {
  supportAnswer = answer;
  attachAnswer.classList.toggle('hidden', !answer);
}

async function prepareSupportDraft(question, answer) {
  const epoch = sessionEpoch;
  const draft = readSupportDraft();
  if (draft.message.trim() && !confirm('Thay nội dung yêu cầu đang soạn bằng câu hỏi này?')) return;
  if (!await navigate('support', {focus:true}) || epoch !== sessionEpoch || state.view !== 'support') return;
  if (JSON.stringify(readSupportDraft()) !== JSON.stringify(draft) || supportClient.busy) return;
  if (!draft.subject.trim()) $('new-ticket-subject').value = 'Cần làm rõ chính sách';
  const field = $('new-ticket-message');
  field.value = question.slice(0, field.maxLength);
  $('ticket-consent').checked = false;
  setSupportAnswer(answer);
  field.focus();
  notify(question.length > field.maxLength
    ? 'Đã chép phần đầu của câu hỏi. Hãy xem lại trước khi gửi.'
    : 'Đã chép câu hỏi vào bản nháp. Bạn có thể chọn thêm câu trả lời trước khi gửi.');
}

function renderSupportControls(){
  const r=supportClient.record,busy=supportClient.busy,staff=supportClient.staff,limit=(r?.message_count||0)>=20;
  const other=staff&&r?.assignment==='other';
  $('new-ticket-fields').disabled=busy;$('ticket-reply-fields').disabled=busy||other;
  $('ticket-staff-controls').classList.toggle('hidden',!staff||!r);
  $('ticket-note-fields').disabled=busy||!staff||!r||(r.internal_note_count||0)>=20;
  $('ticket-takeover-form').classList.toggle('hidden',!other);$('ticket-takeover-fields').disabled=busy||!other;
  $('claim-ticket').disabled=busy||!staff||!r||(r.assignment&&r.assignment!=='unassigned');
  $('release-ticket').disabled=busy||!staff||r?.assignment!=='mine';
  $('reload-ticket').disabled=busy||!r;
  $('ticket-reply-label').textContent=staff?'Nội dung gửi cho khách (không phải ghi chú nội bộ)':'Nội dung bổ sung';
  $('staff-ticket-status-label').classList.toggle('hidden',!staff);$('staff-ticket-priority-label').classList.toggle('hidden',!staff);
  $('ticket-reply-message').required=!staff;
  $('ticket-reply-message').disabled=busy||other||limit||(!staff&&r?.status==='closed');
  $('send-ticket-reply').disabled=busy||other||!r||(!staff&&(limit||r.status==='closed'));
  $('send-ticket-reply').textContent=staff?'Gửi phản hồi / Cập nhật':'Gửi bổ sung';
  $('close-own-ticket').classList.toggle('hidden',staff);$('delete-own-ticket').classList.toggle('hidden',staff);
  $('close-own-ticket').disabled=busy||!r||r.status==='closed';$('delete-own-ticket').disabled=busy||!r;
  $('close-ticket-dialog').disabled=busy;
}
function renderStaffTicket(){
  const r=supportClient.record,staff=supportClient.staff;
  $('ticket-internal-notes').replaceChildren();$('ticket-assignment-history').replaceChildren();$('ticket-assignment-label').textContent='';$('ticket-note-count').textContent='';
  if(!staff||!r)return;
  const label=id=>id===state.user?.profile?.sub?'Bạn':id?`Nhân viên ${id.slice(0,8)}`:'Chưa phân công';
  $('ticket-assignment-label').textContent=r.assignment==='mine'?'Bạn đang phụ trách yêu cầu này.':r.assignment==='other'?`${label(r.assigned_to)} đang phụ trách. Cần nhận bàn giao trước khi phản hồi hoặc đổi trạng thái.`:'Chưa có người phụ trách. Bạn có thể nhận yêu cầu.';
  $('ticket-note-count').textContent=`${r.internal_note_count||0}/20`;
  for(const note of r.internal_notes||[]){const card=node('article',undefined,'internal-note');card.append(node('strong',label(note.author)),node('small',new Date(note.created_at).toLocaleString('vi-VN')),node('p',note.body));$('ticket-internal-notes').append(card);}
  if(!r.internal_notes?.length)$('ticket-internal-notes').append(node('p','Chưa có ghi chú nội bộ.','small muted'));
  const verbs={claim:'Nhận phụ trách',release:'Trả về hàng đợi',takeover:'Nhận bàn giao'};
  for(const event of [...(r.assignment_events||[])].reverse()){const card=node('article',undefined,'assignment-event');card.append(node('strong',`${verbs[event.action]||'Thay đổi phân công'} · ${label(event.actor)}`),node('small',new Date(event.created_at).toLocaleString('vi-VN')));if(event.reason)card.append(node('p',event.reason));$('ticket-assignment-history').append(card);}
}
function showTicket({preserveDrafts=false}={}){
  const r=supportClient.record;if(!r)return;
  $('ticket-dialog-title').textContent=r.subject;
  $('ticket-dialog-meta').textContent=`#${r.ticket_id.slice(-8).toUpperCase()} · ${supportStates[r.status]} · ${supportCategories[r.category||'general']} · Ưu tiên: ${supportPriorities[r.priority||'normal']}${r.order_ref?` · Mã đơn khách cung cấp: ${r.order_ref}`:''} · ${r.message_count}/20 tin nhắn · Lưu đến ${new Date(r.expires_at*1000).toLocaleDateString('vi-VN')}`;
  $('ticket-thread').replaceChildren();
  for(const message of r.messages){const card=node('article',undefined,`support-message ${message.role}`);card.append(node('strong',message.role==='staff'?'Nhân viên hỗ trợ':supportClient.staff?'Khách hàng':'Bạn'),node('small',new Date(message.created_at).toLocaleString('vi-VN')),node('p',message.body));$('ticket-thread').append(card);}
  $('ticket-dialog-notice').classList.add('hidden');
  if(!preserveDrafts){$('ticket-reply-message').value='';$('staff-ticket-status').value=r.status;$('staff-ticket-priority').value=r.priority||'normal';$('ticket-note-form').reset();$('ticket-takeover-form').reset();}
  $('ticket-reply-note').textContent=supportClient.staff?'Phản hồi được gửi trong ứng dụng cho khách. Không gửi email tự động.':r.status==='closed'?'Yêu cầu đã đóng. Bạn có thể gửi yêu cầu mới nếu cần hỗ trợ thêm.':r.message_count>=20?'Đã đủ 20 tin nhắn. Bạn có thể đóng yêu cầu hoặc gửi yêu cầu mới.':'Nội dung bổ sung sẽ được chia sẻ với bộ phận hỗ trợ.';
  renderStaffTicket();renderSupportControls();if(!$('ticket-dialog').open)$('ticket-dialog').showModal();
}
function closeSupportDialog(){if(supportClient.busy)return;if(ticketDraftUnsaved()&&!confirm('Bỏ phản hồi, ghi chú hoặc thay đổi chưa lưu?'))return;$('ticket-reply-message').value='';$('ticket-note-form').reset();$('ticket-takeover-form').reset();$('ticket-dialog-notice').classList.add('hidden');$('ticket-dialog').close();}
function supportRow(row,staff){
  const card=node('article',undefined,'support-row'),head=node('div');head.append(node('strong',row.subject),node('small',`#${row.ticket_id.slice(-8).toUpperCase()} · ${new Date(row.updated_at).toLocaleString('vi-VN')} · ${row.message_count} tin nhắn`));
  head.append(node('small',`${supportCategories[row.category||'general']} · Ưu tiên: ${supportPriorities[row.priority||'normal']}${row.order_ref?` · Đơn: ${row.order_ref}`:''}`,`triage-meta ${row.priority||'normal'}`));
  if(staff)head.append(node('small',row.assignment==='mine'?'Bạn phụ trách':row.assignment==='other'?'Nhân viên khác phụ trách':'Chưa có người nhận','assignment-label'));
  if (!staff && row.last_staff_reply_at) {
    const replied = new Date(row.last_staff_reply_at);
    head.append(node('small', `Nhân viên phản hồi lúc ${replied.toLocaleString('vi-VN')}`, 'assignment-label'));
  }
  if (staff && row.customer_waiting_since) {
    const since = new Date(row.customer_waiting_since);
    head.append(node('small', `Chờ phản hồi từ ${since.toLocaleString('vi-VN')}`, 'assignment-label'));
  }
  const open=button('Xem yêu cầu',async()=>{if(ticketDraftUnsaved()&&!confirm('Bỏ các nội dung chưa lưu để mở yêu cầu khác?'))return;await supportClient.open(row,staff);showTicket();},'secondary');open.setAttribute('aria-label',`Mở yêu cầu ${row.ticket_id}`);
  card.append(head,node('span',supportStates[row.status],`support-status ${row.status}`),open);return card;
}
const customerTicketFilter = node('select');
for (const [value, label] of [
  ['all', 'Tất cả yêu cầu'], ['replied', 'Có phản hồi từ nhân viên'], ['active', 'Đang mở hoặc xử lý'],
]) {
  const option = node('option', label);
  option.value = value;
  customerTicketFilter.append(option);
}
const customerTicketFilterLabel = node('label');
customerTicketFilterLabel.append(node('span', 'Lọc yêu cầu'), customerTicketFilter);
const customerTicketStatus = node('p', '', 'small muted');
customerTicketStatus.setAttribute('role', 'status');
$('ticket-list').before(customerTicketFilterLabel, customerTicketStatus);
customerTicketFilter.addEventListener('change', renderCustomerTickets);

function renderCustomerTickets() {
  const rows = [...customerTicketRows.values()];
  const filter = customerTicketFilter.value;
  const visible = filter === 'replied'
    ? rows.filter(row => row.last_staff_reply_at).sort((a,b) => Date.parse(b.last_staff_reply_at) - Date.parse(a.last_staff_reply_at))
    : filter === 'active' ? rows.filter(row => ['open', 'in_progress'].includes(row.status)) : rows;
  const list = $('ticket-list');
  list.replaceChildren(...visible.map(row => supportRow(row, false)));
  customerTicketStatus.textContent = `Hiển thị ${visible.length}/${rows.length} yêu cầu đã tải.`;
  if (!visible.length) list.append(node('p',
    ticketToken ? 'Trang đã tải chưa có yêu cầu phù hợp. Hãy tải thêm.' : 'Chưa có yêu cầu phù hợp.',
    'empty-small'));
}

async function loadTickets(more=false){
  needApi();
  const epoch = ++ticketListEpoch;
  const cursor = more && ticketToken ? `&next_token=${encodeURIComponent(ticketToken)}` : '';
  const result = await api('/tickets?limit=20' + cursor);
  if (epoch !== ticketListEpoch) return;
  if (!more) customerTicketRows.clear();
  for (const row of result.tickets) customerTicketRows.set(row.ticket_id, row);
  ticketToken = result.next_token;
  $('more-tickets').classList.toggle('hidden', !ticketToken);
  renderCustomerTickets();
}
const adminQueueFilter = node('input');
adminQueueFilter.type = 'checkbox';
const adminQueueFilterLabel = node('label');
adminQueueFilterLabel.append(adminQueueFilter, node('span', 'Chỉ xem khách đang chờ phản hồi'));
const adminQueueStatus = node('p', '', 'small muted');
adminQueueStatus.setAttribute('role', 'status');
$('admin-ticket-list').before(adminQueueFilterLabel, adminQueueStatus);
adminQueueFilter.addEventListener('change', renderAdminQueue);

function resetAdminQueue() {
  adminQueueRows.clear();
  adminQueueFilter.checked = false;
  adminQueueStatus.textContent = '';
}

function renderAdminQueue() {
  const rows = [...adminQueueRows.values()];
  const waiting = rows.filter(row => row.customer_waiting_since);
  const visible = adminQueueFilter.checked
    ? waiting.sort((a,b) => Date.parse(a.customer_waiting_since) - Date.parse(b.customer_waiting_since))
    : rows;
  adminQueueStatus.textContent = `${waiting.length}/${rows.length} yêu cầu đã tải đang chờ phản hồi.`;
  const list = $('admin-ticket-list');
  list.replaceChildren(...visible.map(row => supportRow(row, true)));
  if (!visible.length) list.append(node('p',
    adminTicketToken ? 'Trang đã tải chưa có yêu cầu phù hợp. Hãy tải thêm.' : 'Chưa có yêu cầu phù hợp.',
    'empty-small'));
}

async function loadTicketQueue(more=false){
  needApi();const epoch=++adminTicketListEpoch,filter=$('admin-ticket-filter').value;
  const result=await api(`/admin/tickets?limit=20&assignee=${encodeURIComponent($('admin-ticket-assignee').value)}${filter?`&status=${encodeURIComponent(filter)}`:''}${$('admin-ticket-category').value?`&category=${encodeURIComponent($('admin-ticket-category').value)}`:''}${$('admin-ticket-priority').value?`&priority=${encodeURIComponent($('admin-ticket-priority').value)}`:''}${$('admin-ticket-order').value.trim()?`&order_ref=${encodeURIComponent($('admin-ticket-order').value.trim())}`:''}${more&&adminTicketToken?`&next_token=${encodeURIComponent(adminTicketToken)}`:''}`);if(epoch!==adminTicketListEpoch)return;
  if (!more) adminQueueRows.clear();
  for (const row of result.tickets) adminQueueRows.set(JSON.stringify([row.owner_id, row.ticket_id]), row);
  adminTicketToken = result.next_token;
  $('more-admin-tickets').classList.toggle('hidden', !adminTicketToken);
  renderAdminQueue();
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
document.addEventListener('click',event=>{const nav=event.target.closest('[data-view]');if(nav)guard(nav,()=>navigate(nav.dataset.view,{focus:true}));const suggestion=event.target.closest('[data-question]');if(suggestion){if(!state.user){notify('Đăng nhập để đặt câu hỏi và xem nguồn trả lời.',true);$('auth-button').focus();return;}guard(suggestion, () => putQuestionInComposer(suggestion.dataset.question));}});
$('auth-button').addEventListener('click',()=>guard($('auth-button'),async()=>{if(!manager)throw new Error('Đăng nhập chưa được cấu hình.');if(signingOut)return;if(state.user){if(hasUnsavedWork()&&!confirm('Đăng xuất và bỏ các nội dung chưa gửi hoặc chưa lưu?'))return;signingOut=true;manager.stopSilentRenew();clearPrivateState();try{await manager.revokeTokens(['refresh_token']);}catch{}await manager.removeUser();location.assign(`${config.authDomain}/logout?client_id=${encodeURIComponent(config.clientId)}&logout_uri=${encodeURIComponent(location.origin+'/')}`);}else await manager.signinRedirect({state:{policy:policyLinkRoute(location.hash.slice(1))}});}));
$('question').addEventListener('input',()=>{$('question-count').textContent=`${$('question').value.length.toLocaleString('vi-VN')} / 2.000 ký tự`;});
$('question-form').addEventListener('submit',event=>{event.preventDefault();guard($('ask-button'),async()=>{
  needApi();const submittedDraft=$('question').value;const question=submittedDraft.trim();if(!question)return;
  const payload=questionPayload(question,[...state.selected],$('source-scope').value),epoch=sessionEpoch;
  const submittedContext = followupContext;
  if (submittedContext) payload.context_conversation_id = submittedContext.conversationId;
  $('answer-area').setAttribute('aria-busy','true');$('answer-area').replaceChildren(node('p','Đang tìm nguồn và chuẩn bị câu trả lời…','loading-state'));
  try {
    const result = await api('/ask', {method:'POST', body:payload});
    if (epoch !== sessionEpoch) return;
    renderAnswer(question, result);
    if ($('question').value === submittedDraft && followupContext === submittedContext) {
      setFollowupContext(null);
      $('question').value = '';
      $('question-count').textContent = '0 / 2.000 ký tự';
    }
  }
  catch(error){if(epoch!==sessionEpoch)return;$('answer-area').replaceChildren(node('p','Chưa nhận được câu trả lời. Câu hỏi vẫn được giữ để bạn xem lại. Nếu kết nối bị ngắt, kiểm tra Lịch sử trước khi gửi lại.','empty-small'));throw error;}
  finally{if(epoch===sessionEpoch)$('answer-area').setAttribute('aria-busy','false');}
});});
$('upload-form').addEventListener('submit',event=>{event.preventDefault();guard($('upload-button'),async()=>{
  needApi();const epoch=sessionEpoch,isCurrent=()=>epoch===sessionEpoch;$('upload-status').textContent='Đang tải file…';
  let docId;
  try {
    docId = await uploadPdf(api, $('pdf-file').files[0]);
  } catch (error) {
    if (!isCurrent()) return;
    if (error.uploadedDocId) {
      $('pdf-file').value = '';
      $('upload-status').textContent = 'Tệp đã tải lên. Kiểm tra trạng thái trong thư viện và chọn Gửi xử lý nếu còn chờ.';
      try { await loadDocs(); } catch { /* The refresh button remains available. */ }
    } else {
      $('upload-status').textContent = 'Chưa xác nhận tải lên. Xem thông báo và làm mới thư viện trước khi thử lại.';
    }
    if (isCurrent()) throw error;
    return;
  }
  if (!isCurrent()) return;
  $('pdf-file').value = '';
  await trackDocument(docId);
});});
$('refresh-documents').onclick=()=>guard($('refresh-documents'),()=>loadDocs());$('more-documents').onclick=()=>guard($('more-documents'),()=>loadDocs(true));$('more-sources').onclick=()=>guard($('more-sources'),()=>loadDocs(true));
$('browse-policies').onclick = () => setPolicyLibraryMode('browse');
$('saved-policies').onclick = () => setPolicyLibraryMode('saved');
$('policy-keyword').addEventListener('input', () => {
  if (policyLibraryMode === 'saved') renderSavedPolicies();
});
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
$('history-filter').addEventListener('input', applyHistoryFilters);
$('history-source-filter').addEventListener('change', applyHistoryFilters);
$('choose-source').addEventListener('click', () => $('source-scope').focus());
$('source-scope').addEventListener('change',()=>renderSources());
$('refresh-tickets').onclick=()=>guard($('refresh-tickets'),()=>loadTickets());
$('more-tickets').onclick=()=>guard($('more-tickets'),()=>loadTickets(true));
$('admin-ticket-filter').onchange=()=>guard($('admin-ticket-filter'),()=>loadTicketQueue());
for(const id of ['admin-ticket-category','admin-ticket-priority','admin-ticket-assignee'])$(id).onchange=()=>guard($(id),()=>loadTicketQueue());
$('ticket-lookup-form').onsubmit=event=>{event.preventDefault();guard(event.submitter,()=>loadTicketQueue());};
$('admin-ticket-order').oninput=()=>{adminTicketListEpoch++;adminTicketToken=null;resetAdminQueue();$('admin-ticket-list').replaceChildren();$('more-admin-tickets').classList.add('hidden');};
$('more-admin-tickets').onclick=()=>guard($('more-admin-tickets'),()=>loadTicketQueue(true));
$('close-ticket-dialog').onclick=closeSupportDialog;
$('ticket-dialog').addEventListener('cancel',event=>{event.preventDefault();closeSupportDialog();});
$('new-ticket-form').onsubmit=event=>{event.preventDefault();guard($('create-ticket'),async()=>{
  const epoch = sessionEpoch;
  await supportClient.create(readSupportDraft());
  if (epoch !== sessionEpoch) return;
  $('new-ticket-form').reset();
  setSupportAnswer('');
  if (state.view === 'support') showTicket();
  notify('Đã tiếp nhận yêu cầu. Bạn có thể theo dõi phản hồi trong Hỗ trợ.');
  await refreshSupportLists();
});};
$('ticket-reply-form').onsubmit=event=>{event.preventDefault();guard($('send-ticket-reply'),async()=>{
  await supportClient.update($('ticket-reply-message').value,$('staff-ticket-status').value,'reply',supportClient.staff?$('staff-ticket-priority').value:undefined);$('ticket-reply-message').value='';$('staff-ticket-status').value=supportClient.record.status;$('staff-ticket-priority').value=supportClient.record.priority||'normal';showTicket({preserveDrafts:true});notify('Đã cập nhật yêu cầu hỗ trợ.');await refreshSupportLists();
});};
for(const [id,action] of [['claim-ticket','claim'],['release-ticket','release']])$(id).onclick=()=>guard($(id),async()=>{await supportClient.staffAction(action);showTicket({preserveDrafts:true});notify(action==='claim'?'Bạn đã nhận phụ trách. Chưa gửi tin nhắn cho khách.':'Đã trả yêu cầu về hàng đợi.');await refreshSupportLists();});
$('ticket-note-form').onsubmit=event=>{event.preventDefault();guard($('save-ticket-note'),async()=>{await supportClient.staffAction('note',$('ticket-note-text').value);$('ticket-note-text').value='';showTicket({preserveDrafts:true});notify('Đã lưu ghi chú nội bộ. Không gửi cho khách.');await refreshSupportLists();});};
$('ticket-takeover-form').onsubmit=event=>{event.preventDefault();guard($('takeover-ticket'),async()=>{await supportClient.staffAction('takeover',$('ticket-takeover-reason').value);$('ticket-takeover-reason').value='';showTicket({preserveDrafts:true});notify('Đã nhận bàn giao và lưu lý do nội bộ.');await refreshSupportLists();});};
$('reload-ticket').onclick=()=>guard($('reload-ticket'),async()=>{if(ticketDraftUnsaved()&&!confirm('Tải lại sẽ bỏ nội dung chưa lưu trong yêu cầu này. Tiếp tục?'))return;const r=supportClient.record;await supportClient.open({ticket_id:r.ticket_id,owner_id:r.owner_id},supportClient.staff);showTicket();});
$('close-own-ticket').onclick=()=>guard($('close-own-ticket'),async()=>{if(!confirm('Đóng yêu cầu hỗ trợ này? Bạn vẫn có thể xem lại hoặc xóa nội dung.'))return;await supportClient.update('',null,'close');showTicket();await refreshSupportLists();});
$('delete-own-ticket').onclick=()=>guard($('delete-own-ticket'),async()=>{if(!confirm('Xóa vĩnh viễn toàn bộ yêu cầu và phản hồi? Không thể khôi phục từ ứng dụng.'))return;await supportClient.remove();$('ticket-dialog').close();$('ticket-thread').replaceChildren();$('ticket-reply-form').reset();notify('Đã xóa yêu cầu hỗ trợ.');await refreshSupportLists();});
$('export-tickets').onclick=()=>guard($('export-tickets'),async()=>{needApi();const items=[];let token;do{const result=await api(`/tickets?limit=50${token?`&next_token=${encodeURIComponent(token)}`:''}`);for(const row of result.tickets)items.push(await api(`/tickets/${encodeURIComponent(row.ticket_id)}`));token=result.next_token;}while(token);const url=URL.createObjectURL(new Blob([JSON.stringify(items,null,2)],{type:'application/json'}));const link=node('a');link.href=url;link.download='policy-assistant-support.json';link.click();URL.revokeObjectURL(url);});
$('export-history').onclick=()=>guard($('export-history'),async()=>{needApi();const items=[];let token;do{const result=await api(`/conversations${token?`?next_token=${encodeURIComponent(token)}`:''}`);items.push(...result.conversations);token=result.next_token;}while(token);const url=URL.createObjectURL(new Blob([JSON.stringify(items,null,2)],{type:'application/json'}));const link=node('a');link.href=url;link.download='policy-assistant-history.json';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
$('delete-account').onclick=()=>guard($('delete-account'),async()=>{needApi();if($('delete-confirmation').value!=='DELETE')throw new Error('Nhập chính xác DELETE để xác nhận.');if(!confirm('Xóa vĩnh viễn tài khoản, tất cả PDF và lịch sử? Không thể hoàn tác trong ứng dụng.'))return;await api('/account/delete',{method:'POST',body:{confirmation:'DELETE'}});signingOut=true;manager.stopSilentRenew();try{savedPolicies.removeAccount();}catch{}await manager.removeUser();clearPrivateState();notify('Đã tiếp nhận yêu cầu xóa. Tài khoản hiện bị chặn và dữ liệu sẽ được xóa ở nền.');});

async function start(){
  signedIn();renderShopControls();
  const response=await fetch('./config.json',{cache:'no-store'});if(!response.ok)throw new Error('Chưa tải được cấu hình ứng dụng.');config=await response.json();
  if(!config.apiBase||!config.clientId||!config.userPoolId||!config.authDomain){$('config-warning').classList.remove('hidden');$('auth-button').disabled=true;return;}
  const authDomain=new URL(config.authDomain);if(authDomain.protocol!=='https:')throw new Error('Địa chỉ đăng nhập phải dùng HTTPS.');config.authDomain=authDomain.origin;
  const issuer=`https://cognito-idp.${config.region}.amazonaws.com/${config.userPoolId}`;
  manager=new UserManager({authority:issuer,client_id:config.clientId,redirect_uri:location.origin+'/',post_logout_redirect_uri:location.origin+'/',response_type:'code',scope:'openid email profile',loadUserInfo:false,automaticSilentRenew:true,userStore:new WebStorageStateStore({store:sessionStorage}),stateStore:new WebStorageStateStore({store:sessionStorage}),metadata:{issuer,authorization_endpoint:config.authDomain+'/oauth2/authorize',token_endpoint:config.authDomain+'/oauth2/token',jwks_uri:issuer+'/.well-known/jwks.json',userinfo_endpoint:config.authDomain+'/oauth2/userInfo',revocation_endpoint:config.authDomain+'/oauth2/revoke'}});
  manager.events.addUserLoaded(user=>{if(!signingOut)state.user=user;});manager.events.addAccessTokenExpired(()=>{manager.stopSilentRenew();clearPrivateState();manager.removeUser().catch(()=>{});notify('Phiên đăng nhập hết hạn. Hãy đăng nhập lại.',true);});
  if(new URLSearchParams(location.search).has('code')||new URLSearchParams(location.search).has('error')){try{state.user=await manager.signinRedirectCallback();}catch{history.replaceState(null,'',location.pathname);throw new Error('Đăng nhập chưa hoàn tất hoặc liên kết đã hết hạn. Hãy thử đăng nhập lại.');}const linked = policyLinkRoute('policy/' + (state.user?.state?.policy || ''));history.replaceState(null,'',location.pathname+(linked ? '#policy/'+linked : ''));}
  else state.user=await manager.getUser();
  api=createApi(config.apiBase,async()=>{if(state.user?.expired){const epoch=sessionEpoch;const user=await manager.signinSilent();if(epoch!==sessionEpoch)return null;state.user=user;}return state.user?.id_token;},fetch,()=>sessionEpoch);
  if(state.user){state.profile=await api('/me');signedIn();try{await loadShopProfile();}catch{if(state.user){$('shop-context').textContent='Chưa tải được thông tin shop. Bạn có thể làm mới tại mục Thông tin shop.';$('shop-context').classList.remove('hidden');}}}
  await navigate(location.hash.slice(1)||'assistant',{historyMode:'replace'});
}
window.addEventListener('pageshow',async event=>{if(!event.persisted||!manager)return;if(signingOut){await manager.removeUser();clearPrivateState();location.reload();return;}const stored=await manager.getUser();if(!stored||stored.expired)clearPrivateState();else if(stored.profile.sub!==state.user?.profile.sub)location.reload();});
start().catch(fail);
