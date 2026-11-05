export const supportStates={open:'Mới tiếp nhận',in_progress:'Đang xử lý',resolved:'Đã phản hồi',closed:'Đã đóng'};
export const supportCategories={general:'Chính sách / Khác',warranty:'Bảo hành',returns:'Đổi trả / Hoàn tiền',shipping:'Giao hàng',order:'Đơn hàng'};
export const supportPriorities={low:'Thấp',normal:'Bình thường',high:'Cao'};
const validId=id=>typeof id==='string'&&/^t-[0-9]{20}-[a-f0-9]{32}$/.test(id);
export function supportPayload(raw){
  if(raw.consent!==true)throw new Error('Xác nhận chia sẻ nội dung với bộ phận hỗ trợ trước khi gửi.');
  const data={consent:true};
  for(const [key,max]of[['subject',180],['message',1500]]){
    if(typeof raw[key]!=='string'||!raw[key].trim()||raw[key].trim().length>max)throw new Error('Nhập tiêu đề tối đa 180 ký tự và nội dung tối đa 1.500 ký tự.');
    data[key]=raw[key].trim();
  }
  if(raw.category!==undefined){if(typeof raw.category!=='string'||!Object.hasOwn(supportCategories,raw.category))throw new Error('Chọn loại yêu cầu hợp lệ.');data.category=raw.category;}
  if(raw.order_ref!==undefined){if(typeof raw.order_ref!=='string'||raw.order_ref.trim().length>80||/[\x00-\x1f\x7f]/.test(raw.order_ref))throw new Error('Mã đơn tối đa 80 ký tự, không xuống dòng.');data.order_ref=raw.order_ref.trim();}
  return data;
}
export function questionPayload(question,ids,scope='all'){
  if(!['all','policies','documents'].includes(scope))throw new Error('Chọn phạm vi tra cứu hợp lệ.');
  if(scope==='documents'&&!ids.length)throw new Error('Chọn ít nhất một PDF đã xử lý.');
  return{question,document_ids:scope==='policies'?[]:[...ids],source_scope:scope};
}
export class SupportClient{
  constructor(api,onChange=()=>{}){this.api=api;this.onChange=onChange;this.epoch=0;this.busy=false;this.record=null;this.staff=false;this.route=null;}
  clear(){this.epoch++;this.busy=false;this.record=null;this.route=null;this.staff=false;this.onChange();}
  async perform(work){
    if(this.busy)throw new Error('Đang xử lý yêu cầu hỗ trợ. Vui lòng chờ.');
    const epoch=this.epoch;this.busy=true;this.onChange();
    try{const result=await work();if(epoch!==this.epoch)throw new Error('Phiên đăng nhập đã thay đổi.');return result;}
    catch(error){if(error.status===429)throw Object.assign(new Error('Đã hết hạn mức sử dụng trong ngày hoặc tháng. Nội dung chưa gửi vẫn được giữ; hãy thử lại sau khi hạn mức được đặt lại.'),{status:429});if(error.status===404)throw Object.assign(new Error('Yêu cầu không còn tồn tại hoặc đã hết thời hạn lưu. Hãy làm mới danh sách.'),{status:404});if(error.status===409)throw Object.assign(new Error('Yêu cầu đã thay đổi hoặc không thể cập nhật. Nội dung bạn đang gõ được giữ nguyên; mở lại yêu cầu để kiểm tra trạng thái và giới hạn 20 tin nhắn.'),{status:409});throw error;}
    finally{if(epoch===this.epoch){this.busy=false;this.onChange();}}
  }
  accept(record,staff,owner,expectedId){
    if(!record||typeof record!=='object'||!validId(record.ticket_id)||typeof record.revision!=='string'||!record.revision||!Array.isArray(record.messages)||record.messages.length>20||!supportStates[record.status]||(expectedId&&record.ticket_id!==expectedId)||(staff&&record.owner_id!==owner))throw new Error('Phản hồi hỗ trợ không hợp lệ. Hãy tải lại.');
    this.record=record;this.staff=staff;this.route=staff?`/admin/tickets/${encodeURIComponent(owner)}/${record.ticket_id}`:`/tickets/${record.ticket_id}`;
    return record;
  }
  async create(raw){const body=supportPayload(raw),epoch=this.epoch;return this.perform(async()=>{const r=await this.api('/tickets',{method:'POST',body});if(epoch!==this.epoch)throw new Error('Phiên đăng nhập đã thay đổi.');return this.accept(r,false);});}
  async open(row,staff=false){
    if(!validId(row.ticket_id)||(staff&&!/^[A-Za-z0-9_-]{1,128}$/.test(row.owner_id||'')))throw new Error('Mã yêu cầu không hợp lệ.');
    const route=staff?`/admin/tickets/${encodeURIComponent(row.owner_id)}/${row.ticket_id}`:`/tickets/${row.ticket_id}`,epoch=this.epoch;
    return this.perform(async()=>{const r=await this.api(route);if(epoch!==this.epoch)throw new Error('Phiên đăng nhập đã thay đổi.');return this.accept(r,staff,row.owner_id,row.ticket_id);});
  }
  async update(message,status,action='reply',priority){
    if(!this.record)throw new Error('Mở yêu cầu trước khi phản hồi.');
    if(typeof message!=='string'||message.trim().length>1500)throw new Error('Nội dung tối đa 1.500 ký tự.');
    if(!this.staff&&!['reply','close'].includes(action))throw new Error('Thao tác không hợp lệ.');
    if(this.staff&&!supportStates[status])throw new Error('Trạng thái không hợp lệ.');
    const body={expected_revision:this.record.revision,action:this.staff?'update':action,message:message.trim()};if(this.staff)body.status=status;
    if(priority!==undefined){if(!this.staff||typeof priority!=='string'||!Object.hasOwn(supportPriorities,priority))throw new Error('Chỉ nhân viên được chọn mức ưu tiên hợp lệ.');body.priority=priority;}
    const route=this.route,staff=this.staff,owner=this.record.owner_id,id=this.record.ticket_id,epoch=this.epoch;
    return this.perform(async()=>{const r=await this.api(route,{method:'PATCH',body});if(epoch!==this.epoch)throw new Error('Phiên đăng nhập đã thay đổi.');return this.accept(r,staff,owner,id);});
  }
  async remove(){
    if(!this.record||this.staff)throw new Error('Chỉ chủ yêu cầu mới có thể xóa yêu cầu của mình.');
    const route=this.route,revision=this.record.revision,epoch=this.epoch;
    return this.perform(async()=>{const r=await this.api(route,{method:'DELETE',body:{expected_revision:revision,confirmation:'DELETE'}});if(epoch!==this.epoch)throw new Error('Phiên đăng nhập đã thay đổi.');if(r.deleted!==true)throw new Error('Chưa xác nhận được việc xóa yêu cầu.');this.record=null;this.route=null;return r;});
  }
}
