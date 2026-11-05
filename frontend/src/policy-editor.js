// The editor keeps a saved revision separate from local, unsaved changes.
export const policyStates = {published:'Đã công bố',draft:'Chưa công bố',archived:'Đã ngừng công bố',unpublished:'Chưa công bố'};
export const validityStates = {active:'Đang có hiệu lực',upcoming:'Chưa tới ngày hiệu lực',expired:'Đã hết hiệu lực',invalid:'Cần kiểm tra ngày',unpublished:'Chưa công bố'};
export function validityBounds(raw) {
  const result={};
  for(const key of ['effective_from','effective_until']){
    if(!Object.hasOwn(raw,key))continue;
    const value=raw[key];
    if(value===''){result[key]='';continue;}
    if(typeof value!=='string'||!/^\d{4}-\d{2}-\d{2}$/.test(value)||Number(value.slice(0,4))<1)throw new Error('Nhập ngày hợp lệ theo định dạng năm-tháng-ngày.');
    const date=new Date(`${value}T00:00:00Z`);
    if(Number.isNaN(date.getTime())||date.toISOString().slice(0,10)!==value)throw new Error('Ngày hiệu lực không tồn tại trên lịch.');
    result[key]=value;
  }
  if(result.effective_from&&result.effective_until&&result.effective_until<result.effective_from)throw new Error('Ngày kết thúc không được trước ngày bắt đầu.');
  return result;
}
export function validityText(raw) {
  const value=validityBounds(raw);
  const format=date=>date.split('-').reverse().join('/');
  return `${value.effective_from?`Từ ${format(value.effective_from)}`:'Không giới hạn ngày bắt đầu'} · ${value.effective_until?`Đến hết ${format(value.effective_until)}`:'Không giới hạn ngày kết thúc'} · Giờ Việt Nam (UTC+7)`;
}
export function draftPayload(raw) {
  const draft = {};
  for (const [key,max] of [['title',180],['category',80],['content',20000]]) {
    if (typeof raw[key] !== 'string' || !raw[key].trim() || raw[key].trim().length > max) throw new Error('Điền đủ tiêu đề, nhóm và nội dung trong giới hạn cho phép.');
    draft[key] = raw[key].trim();
  }
  draft.keywords = Array.isArray(raw.keywords) ? raw.keywords.map(k=>typeof k==='string'?k.trim():k) : String(raw.keywords||'').split(',').map(k=>k.trim()).filter(Boolean);
  if (draft.keywords.length>30 || draft.keywords.some(k=>typeof k!=='string'||k.length>80)) throw new Error('Nhập tối đa 30 từ khóa, mỗi từ khóa tối đa 80 ký tự.');
  Object.assign(draft,validityBounds(raw));
  return draft;
}
export class PolicyEditor {
  constructor(api, onChange=()=>{}) { this.api=api;this.onChange=onChange;this.record=null;this.dirty=false;this.busy=false;this.epoch=0; }
  clear() { this.epoch++;this.record=null;this.dirty=false;this.busy=false;this.onChange(); }
  newPolicy() { if(this.busy)throw new Error('Đang xử lý chính sách. Vui lòng chờ.');this.clear(); }
  markDirty() { this.dirty=true;this.onChange(); }
  async call(id,options) {
    if(this.busy)throw new Error('Đang xử lý chính sách. Vui lòng chờ.');
    if(!/^[A-Za-z0-9_-]{1,80}$/.test(id))throw new Error('Mã chính sách chỉ gồm chữ, số, dấu gạch ngang hoặc gạch dưới.');
    const epoch=this.epoch;this.busy=true;this.onChange();
    try {
      const record=await this.api(`/admin/policies/${encodeURIComponent(id)}`,options);
      if(epoch!==this.epoch)throw new Error('Phiên soạn thảo đã thay đổi.');
      if(record.policy_id!==id || typeof record.revision!=='string' || !record.revision)throw new Error('Phản hồi chính sách không hợp lệ. Hãy tải lại.');
      this.record=record;this.dirty=false;return record;
    } catch(error) {
      if(error.status===409)throw Object.assign(new Error('Chính sách đã thay đổi hoặc thao tác chưa phù hợp. Bản soạn được giữ nguyên; hãy mở lại bản mới nhất để đối chiếu trước khi lưu.'),{status:409});
      throw error;
    } finally { if(epoch===this.epoch){this.busy=false;this.onChange();} }
  }
  open(id) { return this.call(id); }
  save(id,raw) {
    if(this.record && this.record.policy_id!==id)throw new Error('Mã chính sách đang sửa không thể thay đổi. Chọn Soạn mới để dùng mã khác.');
    return this.call(id,{method:'PATCH',body:{action:'save_draft',expected_revision:this.record?.revision??null,draft:draftPayload(raw)}});
  }
  transition(action) {
    if(!this.record)throw new Error('Mở và lưu chính sách trước khi thao tác.');
    if(this.dirty)throw new Error('Có thay đổi chưa lưu. Lưu bản nháp trước khi tiếp tục.');
    if(!['publish','archive','discard_draft'].includes(action))throw new Error('Thao tác không hợp lệ.');
    return this.call(this.record.policy_id,{method:'PATCH',body:{action,expected_revision:this.record.revision}});
  }
}
