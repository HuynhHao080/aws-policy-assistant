export const feedbackReasons={missing_info:'Thiếu thông tin cần thiết',incorrect:'Nội dung có vẻ chưa đúng',citation:'Nguồn trích dẫn chưa phù hợp',unclear:'Cách giải thích khó hiểu',other:'Lý do khác'};
const empty=()=>({rating:null,reason:null,revision:null});
export class FeedbackStore{
  constructor(api){this.api=api;this.epoch=0;this.records=new Map();this.busy=new Set();}
  clear(){this.epoch++;this.records.clear();this.busy.clear();}
  register(answer){
    if(answer.quality_version!==1||typeof answer.conversation_id!=='string'||typeof answer.quality_month!=='string')return null;
    const id=answer.conversation_id,old=this.records.get(id),value=answer.feedback||empty();
    if(!old||(!this.busy.has(id)&&(value.updated_at||'')>=(old.feedback.updated_at||'')))this.records.set(id,{conversation_id:id,quality_month:answer.quality_month,feedback:value});
    return this.records.get(id);
  }
  async update(id,rating,reason=null){
    const item=this.records.get(id);if(!item||this.busy.has(id))throw new Error('Đang xử lý hoặc chưa tải đánh giá.');
    if(![null,'helpful','not_helpful'].includes(rating)||(rating==='not_helpful'?typeof reason!=='string'||!Object.hasOwn(feedbackReasons,reason):reason!==null))throw new Error('Chọn đánh giá và lý do hợp lệ.');
    const epoch=this.epoch;this.busy.add(id);
    try{
      const result=await this.api(`/conversations/${encodeURIComponent(id)}/feedback`,{method:'PATCH',body:{rating,reason,expected_revision:item.feedback.revision??null}});
      if(epoch!==this.epoch)throw new Error('Phiên đăng nhập đã thay đổi.');
      if(result?.conversation_id!==id||!result.feedback||typeof result.feedback.revision!=='string'||![null,'helpful','not_helpful'].includes(result.feedback.rating))throw new Error('Chưa xác nhận được đánh giá. Hãy tải lại lịch sử.');
      this.records.set(id,result);return result;
    }catch(error){if(error.status===409)throw Object.assign(new Error('Đánh giá đã thay đổi hoặc cuộc hỏi đáp chưa hỗ trợ chức năng này. Hãy làm mới lịch sử trước khi gửi lại.'),{status:409});if(error.status===404)throw Object.assign(new Error('Cuộc hỏi đáp đã xóa hoặc hết hạn lưu.'),{status:404});throw error;}
    finally{if(epoch===this.epoch)this.busy.delete(id);}
  }
}
