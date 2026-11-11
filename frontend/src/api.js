export class ApiError extends Error {
  constructor(status, message) { super(message); this.status = status; }
}
export function createApi(base, getToken, fetcher = fetch, sessionKey = () => null) {
  const endpoint = new URL(base);
  if (endpoint.protocol !== 'https:' && !(endpoint.protocol === 'http:' && ['localhost','127.0.0.1'].includes(endpoint.hostname))) throw new Error('Cấu hình API phải dùng HTTPS.');
  const root = endpoint.href.replace(/\/$/, '');
  return async function api(path, options = {}) {
    if (!path.startsWith('/') || path.startsWith('//')) throw new Error('Đường dẫn yêu cầu không hợp lệ.');
    const token = await getToken();
    if (!token) throw new ApiError(401, 'Vui lòng đăng nhập để tiếp tục.');
    const session = sessionKey();
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 45000);
    try {
      const response = await fetcher(root + path, { method: options.method || 'GET', headers: { Authorization: `Bearer ${token}`, ...(options.body !== undefined ? {'Content-Type':'application/json'} : {}) }, ...(options.body !== undefined ? {body:JSON.stringify(options.body)} : {}), signal: controller.signal, credentials:'omit', referrerPolicy:'no-referrer', redirect:'error' });
      let payload;
      try { payload = await response.json(); } catch { throw new ApiError(response.status || 502, 'Dịch vụ trả về dữ liệu không hợp lệ.'); }
      if (sessionKey() !== session) throw new ApiError(401, 'Phiên đăng nhập đã thay đổi.');
      if (!response.ok) throw new ApiError(response.status, payload.message || payload.error || 'Yêu cầu chưa thành công.');
      return payload;
    } catch (error) {
      if (error.name === 'AbortError') throw new ApiError(408, 'Dịch vụ phản hồi chậm. Kiểm tra trạng thái trước khi gửi lại.');
      throw error;
    } finally { clearTimeout(timer); }
  };
}
export function validatePdf(file) {
  if (!file || !/\.pdf$/i.test(file.name) || !file.size || file.size > 10 * 1024 * 1024) throw new Error('Chọn PDF có dữ liệu, không quá 10 MiB.');
}
export async function uploadPdf(api, file, fetcher = fetch) {
  validatePdf(file);
  const session = await api('/documents/upload-session', {method:'POST',body:{filename:file.name}});
  if (!session.doc_id || !session.s3_key || !session.upload_fields || new URL(session.upload_url).protocol !== 'https:') throw new Error('Phiên tải lên không hợp lệ.');
  const form = new FormData();
  for (const [key,value] of Object.entries(session.upload_fields)) form.append(key,value);
  form.append('file',file);
  const response = await fetcher(session.upload_url,{method:'POST',body:form,credentials:'omit',referrerPolicy:'no-referrer',redirect:'error',signal:AbortSignal.timeout(120000)});
  if (!response.ok) throw new Error(`Tải file chưa thành công (HTTP ${response.status}).`);
  try { await api('/documents/submit',{method:'POST',body:{doc_id:session.doc_id,s3_key:session.s3_key}}); }
  catch (error) {
    throw Object.assign(new Error(`Mã tài liệu: ${session.doc_id}. File đã tải lên; dùng Gửi xử lý trong thư viện để thử lại.`, {cause: error}), {
      status: error.status,
      uploadedDocId: session.doc_id,
    });
  }
  return session.doc_id;
}
export const statusText = {awaiting_upload:'Chờ gửi xử lý',pending:'Đang chờ',processing:'Đang đọc PDF',ocr_pending:'Đang nhận dạng chữ (OCR)',processed:'Sẵn sàng',failed:'Không xử lý được',deleting:'Đang xóa',deleted:'Đã xóa'};

export const pdfErrorText = {
  invalid_pdf: 'Tệp không phải PDF hợp lệ. Hãy xuất lại tài liệu dưới dạng PDF.',
  encrypted_pdf: 'PDF có mật khẩu. Hãy tải bản không mã hóa.',
  active_pdf_content: 'PDF có nội dung tương tác. Hãy xuất bản PDF tĩnh rồi tải lại.',
  pdf_size_limit: 'Tệp vượt 10 MiB. Hãy nén hoặc chia nhỏ PDF.',
  pdf_page_limit: 'PDF vượt 100 trang. Hãy chia tài liệu thành nhiều tệp.',
  pdf_text_limit: 'Văn bản quá dài. Hãy chia PDF theo từng phần.',
  ocr_page_limit: 'PDF scan vượt 10 trang. Hãy chia nhỏ hoặc xuất bản có văn bản.',
  ocr_no_text: 'OCR không đọc được chữ. Hãy kiểm tra chất lượng bản scan.',
  ocr_failed: 'OCR xử lý thất bại. Hãy thử bản scan rõ hơn hoặc PDF có văn bản.',
  scanned_pdf_requires_ocr: 'PDF scan cần nhận dạng chữ. Hãy dùng PDF có văn bản.',
  invalid_upload_session: 'Phiên tải lên không hợp lệ. Hãy chọn lại tệp.',
  processing_retry_limit: 'Đã hết lượt tự phục hồi. Hãy kiểm tra tệp trước khi tải lại.',
  processing_temporarily_unavailable: 'Dịch vụ xử lý tạm gián đoạn. Hãy làm mới sau.',
  recovering_stalled_job: 'Hệ thống đang khôi phục lượt xử lý.',
};
