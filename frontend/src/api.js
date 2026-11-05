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
  catch(error) { error.message += ` Mã tài liệu: ${session.doc_id}. File đã tải lên; dùng Gửi xử lý trong thư viện để thử lại.`; throw error; }
  return session.doc_id;
}
export const statusText = {awaiting_upload:'Chờ gửi xử lý',pending:'Đang chờ',processing:'Đang đọc PDF',ocr_pending:'Đang nhận dạng chữ (OCR)',processed:'Sẵn sàng',failed:'Không xử lý được',deleting:'Đang xóa',deleted:'Đã xóa'};
