export const shopFields={shop_name:100,support_email:254,support_phone:40,support_hours:240,returns_instructions:1000,support_message:1000};
export function shopDraft(raw){
  if(!raw||typeof raw!=='object'||Array.isArray(raw))throw new Error('Thông tin shop chưa hợp lệ.');
  const out={};
  for(const [key,max]of Object.entries(shopFields)){const value=raw[key]??'';if(typeof value!=='string'||value.trim().length>max)throw new Error(`Kiểm tra độ dài trường ${key}.`);out[key]=value.trim();}
  out.mode=raw.mode??'demo';if(!['demo','live'].includes(out.mode))throw new Error('Chọn chế độ thông tin shop hợp lệ.');
  return out;
}
export class ShopEditor{
  constructor(api,onChange=()=>{}){this.api=api;this.onChange=onChange;this.epoch=0;this.loaded=false;this.busy=false;this.dirty=false;this.record=null;}
  clear(){this.epoch++;this.loaded=false;this.busy=false;this.dirty=false;this.record=null;this.onChange();}
  markDirty(){this.dirty=true;this.onChange();}
  async request(work){
    if(this.busy)throw new Error('Đang cập nhật thông tin shop.');
    const epoch=this.epoch;this.busy=true;this.onChange();
    try{const data=await work();if(epoch!==this.epoch)throw new Error('Phiên đăng nhập đã thay đổi.');
      if(!data||typeof data!=='object'||!(data.revision===null||(typeof data.revision==='string'&&data.revision))||!Object.hasOwn(data,'current')||!Object.hasOwn(data,'draft'))throw new Error('Chưa xác nhận được thông tin shop. Hãy tải lại.');
      for(const field of ['current','draft'])if(data[field]!==null)shopDraft(data[field]);
      this.record=data;this.loaded=true;this.dirty=false;return data;
    }catch(error){if(error.status===409)throw Object.assign(new Error('Thông tin shop đã thay đổi hoặc chưa đủ điều kiện công bố. Nội dung đang soạn được giữ; tải lại trước khi gửi lại.'),{status:409});if(error.status===400)throw Object.assign(new Error('Kiểm tra tên shop, email/số điện thoại và các mục bắt buộc. Cần xác nhận thông tin trước khi công bố.'),{status:400});throw error;}
    finally{if(epoch===this.epoch){this.busy=false;this.onChange();}}
  }
  load(){return this.request(()=>this.api('/admin/shop'));}
  save(raw){if(!this.loaded)throw new Error('Tải thông tin shop trước khi lưu.');const body={action:'save_draft',expected_revision:this.record.revision,draft:shopDraft(raw)};return this.request(()=>this.api('/admin/shop',{method:'PATCH',body}));}
  act(action,confirmed=false){
    if(!this.loaded||this.dirty)throw new Error('Lưu bản nháp hoặc tải lại trước khi thực hiện.');
    if(!['publish','unpublish','discard_draft'].includes(action))throw new Error('Thao tác không hợp lệ.');
    if(['publish','discard_draft'].includes(action)&&!this.record.draft)throw new Error('Chưa có bản nháp đã lưu.');
    if(action==='unpublish'&&!this.record.current)throw new Error('Chưa có thông tin đang công bố.');
    if(action==='publish'&&confirmed!==true)throw new Error('Xác nhận rằng thông tin đã kiểm tra và được phép hiển thị cho khách.');
    const body={action,expected_revision:this.record.revision};if(action==='publish')body.confirmed=true;
    return this.request(()=>this.api('/admin/shop',{method:'PATCH',body}));
  }
}
