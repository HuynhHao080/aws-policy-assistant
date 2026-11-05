"use strict";
let apiBase = "";
let authHeader = null;
let config = { mode: "aws" };
let configLoaded = false;
let authSession = null;
let authChallenge = null;
let refreshInFlight = null;
let documentCursor = null;
let searchCursor = null;
let activeKeyword = "";
let authBusy = false;
let sessionGeneration = 0;
const TAB_SESSION_KEY = "policy-assistant.cognito.tab.v1";
const TAB_SESSION_MS = 8 * 60 * 60 * 1000;
const MAX_BYTES = 10 * 1024 * 1024;
const $ = id => document.getElementById(id);
function show(id, message, state = "info") { $(id).textContent = message; $(id).dataset.state = state; }
function dropTabSession() {
    try {
        const storage = globalThis.sessionStorage;
        if (!storage) return true;
        storage.removeItem(TAB_SESSION_KEY);
        return storage.getItem(TAB_SESSION_KEY) === null;
    } catch { return false; }
}
function configuredSession(settings) {
    try {
        return configLoaded && config.mode === "aws" && settings.region === config.region &&
            settings.clientId === config.clientId && validateApi(settings.apiBase) === validateApi(config.apiBase);
    } catch { return false; }
}
function saveTabSession() {
    if (!authSession?.persistUntil || !authSession.refreshToken || !configuredSession(authSession) || authSession.persistUntil <= Date.now()) {
        dropTabSession(); return false;
    }
    try {
        globalThis.sessionStorage.setItem(TAB_SESSION_KEY, JSON.stringify({ version: 1,
            refreshToken: authSession.refreshToken, until: authSession.persistUntil,
            apiBase: authSession.apiBase, region: authSession.region, clientId: authSession.clientId }));
        return true;
    } catch { dropTabSession(); authSession.persistUntil = null; return false; }
}
async function restoreTabSession() {
    let saved;
    try {
        const raw = globalThis.sessionStorage?.getItem(TAB_SESSION_KEY);
        if (!raw) return;
        saved = JSON.parse(raw);
        if (!saved || saved.version !== 1 || !configuredSession(saved) ||
            !Number.isFinite(saved.until) || saved.until <= Date.now() || saved.until > Date.now() + TAB_SESSION_MS ||
            typeof saved.refreshToken !== "string" || !/^[\x21-\x7e]{1,8192}$/.test(saved.refreshToken)) {
            dropTabSession(); return;
        }
    } catch { dropTabSession(); return; }
    const generation = sessionGeneration;
    authBusy = true; renderAuthUI(); show("auth-status", "Đang khôi phục phiên trong tab…");
    try {
        const settings = { apiBase: config.apiBase, region: config.region, clientId: config.clientId };
        const result = await cognito("InitiateAuth", { ClientId: settings.clientId,
            AuthFlow: "REFRESH_TOKEN_AUTH", AuthParameters: { REFRESH_TOKEN: saved.refreshToken } }, settings);
        if (generation !== sessionGeneration || authHeader || authChallenge) return;
        if (saved.until <= Date.now() || !result.AuthenticationResult?.IdToken || !result.AuthenticationResult.AccessToken) throw new Error();
        result.AuthenticationResult.RefreshToken ||= saved.refreshToken;
        acceptLogin(result, settings, "Tài khoản Cognito", saved.until);
        show("auth-status", "Đã khôi phục phiên Cognito trong tab này.", "ok");
    } catch {
        if (generation === sessionGeneration) { clearSession(); show("auth-status", "Không khôi phục được phiên. Hãy đăng nhập lại.", "error"); }
    } finally { authBusy = false; renderAuthUI(); }
}
function manualInputValid() {
    try {
        validateApi($("api-base").value.trim());
        return /^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$/.test($("jwt-input").value.trim());
    } catch { return false; }
}
function renderAuthUI() {
    const signedIn = !!authHeader && !!authSession;
    const manual = !!authHeader && !authSession;
    const challenge = !!authChallenge && !signedIn && !manual;
    const mode = signedIn ? "cognito" : manual ? "manual" : challenge ? "challenge" : "unauthenticated";
    $("connection-title").dataset.authMode = mode;
    for (const id of ["advanced-connection", "signup-information"]) {
        $(id).hidden = mode !== "unauthenticated";
        if ($(id).hidden) $(id).open = false;
    }
    if (configLoaded && config.mode !== "local") {
        show("environment-status", signedIn ? "AWS · Phiên Cognito đang hoạt động." : manual ? "AWS · Token thủ công · Danh tính chưa được xác minh." : challenge ? "AWS · Đang hoàn tất xác thực; chưa đăng nhập." : config.apiBase && config.clientId ? "AWS · Đăng nhập bằng tài khoản được cấp để bắt đầu." : "AWS · Cần cấu hình API URL và Cognito Client ID trong phần cấu hình kết nối.");
    }
    $("login-form").hidden = signedIn || manual;
    $("login-form").ariaBusy = String(authBusy);
    $("session-panel").hidden = !signedIn && !manual;
    $("session-panel").dataset.mode = manual ? "manual" : "cognito";
    $("signout").hidden = !signedIn;
    $("signout").disabled = authBusy;
    $("cancel-login").hidden = !challenge;
    $("cancel-login").disabled = authBusy;
    $("password-field").hidden = challenge;
    $("password").disabled = authBusy || challenge || config.mode === "local";
    $("new-password-field").hidden = !challenge || authChallenge.name !== "NEW_PASSWORD_REQUIRED";
    $("mfa-field").hidden = !challenge || authChallenge.name === "NEW_PASSWORD_REQUIRED";
    $("remember-field").hidden = challenge;
    $("remember-session").disabled = authBusy || challenge;
    $("username").readOnly = authBusy || challenge;
    for (const id of ["api-base", "region", "client-id"]) $(id).readOnly = authBusy || signedIn || challenge;
    $("new-password").disabled = authBusy;
    $("mfa-code").disabled = authBusy;
    $("jwt-input").disabled = authBusy;
    $("login").disabled = authBusy;
    $("login").textContent = authBusy ? "Đang xác thực…" : challenge ? (authChallenge.name === "NEW_PASSWORD_REQUIRED" ? "Đặt mật khẩu mới" : "Xác nhận mã") : "Đăng nhập";
    $("connect").disabled = authBusy || signedIn || challenge || !manualInputValid();
    $("manual-switch-help").hidden = !signedIn && !challenge;
    $("clear-token").hidden = signedIn || challenge || (!manual && !$("jwt-input").value);
    $("clear-token").disabled = authBusy;
    $("clear-token").textContent = manual ? "Xóa phiên giao diện" : "Xóa token đã nhập";
    $("connection-title").textContent = signedIn ? "Phiên làm việc của bạn" : manual ? "Kết nối thủ công" : challenge ? "Hoàn tất xác thực" : "Đăng nhập vào bàn làm việc";
    $("connection-help").textContent = signedIn ? (config.mode === "local" ? "Phiên demo offline đang hoạt động trên máy này. Đăng xuất để kết thúc phiên mô phỏng." : "Phiên Cognito đang được sử dụng. Đăng xuất để thu hồi phiên qua Cognito và xóa dữ liệu trên giao diện.") : manual ? "Token chỉ được giữ trong bộ nhớ. Xóa phiên giao diện không thu hồi token phía máy chủ." : "Dùng tài khoản được cấp để tra cứu chính sách và quản lý tài liệu riêng. Chỉ lưu phiên trong tab khi bạn chọn duy trì đăng nhập.";
    $("session-kind").textContent = signedIn ? (config.mode === "local" ? "Phiên demo offline" : "Phiên Cognito") : "Token thủ công · chưa xác minh danh tính";
    $("account-name").textContent = signedIn ? authSession.username : manual ? "Đã áp dụng token thủ công" : "";
    $("session-help").textContent = manual ? "API sẽ xác thực chữ ký, thời hạn và quyền khi nhận yêu cầu. Phiên này không tự gia hạn hoặc GlobalSignOut." : authSession?.persistUntil ? "Có thể khôi phục phiên khi tải lại tab trong tối đa 8 giờ kể từ lúc đăng nhập. Đăng xuất để kết thúc phiên." : "Bạn có thể tra cứu chính sách và sử dụng thư viện tài liệu riêng. Tải lại trang sẽ cần đăng nhập lại.";
}
function clearSession() {
    sessionGeneration++;
    const removed = dropTabSession();
    $("remember-session").checked = false;
    authHeader = null; authSession = null; authChallenge = null;
    $("advanced-connection").open = false;
    $("signup-information").open = false;
    documentCursor = null; searchCursor = null; activeKeyword = "";
    for (const id of ["jwt-input", "password", "new-password", "mfa-code", "doc-id", "file-input"]) $(id).value = "";
    for (const id of ["document-list", "document-result", "upload-result"]) $(id).textContent = "";
    for (const item of document.querySelectorAll("#steps li")) item.className = "";
    show("policy-result", "Kết quả sẽ xuất hiện tại đây.");
    $("documents-next").hidden = true; $("search-next").hidden = true;
    $("new-password-field").hidden = true; $("mfa-field").hidden = true;
    show("library-status", "Đăng nhập rồi chọn Làm mới danh sách.");
    show("auth-status", "Đã xóa phiên trên giao diện. Chưa đăng nhập; thao tác này không thu hồi token phía máy chủ.");
    renderAuthUI();
    return removed;
}
function connect() {
    if (authBusy) return;
    if (authSession || authChallenge) {
        show("auth-status", "Hãy Đăng xuất Cognito hoặc Hủy xác thực trước khi áp dụng token thủ công.");
        return;
    }
    try {
        const url = validateApi($("api-base").value.trim());
        const token = $("jwt-input").value.trim();
        if (!manualInputValid()) throw new Error();
        clearSession();
        apiBase = url;
        authHeader = "Bearer " + token;
        $("jwt-input").value = "";
        show("auth-status", "Phiên thủ công. API sẽ xác thực chữ ký, thời hạn và quyền truy cập khi gửi yêu cầu.", "ok");
    } catch { show("auth-status", "Kiểm tra API URL và định dạng token (3 phần). Phiên hiện có chưa bị thay đổi.", "error"); }
    renderAuthUI();
}
async function api(path, options = {}) {
    if (!apiBase || !authHeader) throw new Error("Hãy áp dụng API URL và token trước.");
    await refreshIfNeeded();
    let response;
    try { response = await fetch(apiBase + path, { ...options, headers: { Authorization: authHeader, ...(options.body ? { "Content-Type": "application/json" } : {}) }, signal: AbortSignal.timeout(15000) }); }
    catch { throw new Error("Không kết nối được API hoặc yêu cầu hết thời gian. Kiểm tra mạng, API URL và CORS."); }
    let body;
    try { body = await response.json(); } catch { throw new Error("API không trả JSON hợp lệ."); }
    if (!response.ok) {
        if (response.status === 401) { clearSession(); show("auth-status", "Phiên không hợp lệ hoặc đã hết hạn. Hãy đăng nhập lại.", "error"); }
        const hints = { 400: "Dữ liệu không hợp lệ.", 401: "Token không hợp lệ hoặc đã hết hạn.", 403: "Không được phép truy cập.", 404: "Không tìm thấy tài nguyên thuộc phiên này.", 409: "Tài liệu chưa sẵn sàng. Hãy kiểm tra trạng thái hoặc gửi lại.", 429: "Quá nhiều yêu cầu. Vui lòng đợi rồi thử lại.", 503: "Dịch vụ tạm chưa sẵn sàng. Có thể gửi xử lý lại cùng Document ID." };
        throw new Error(`HTTP ${response.status}: ${hints[response.status] || "Yêu cầu thất bại. Thử lại sau."}`);
    }
    return body;
}
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
async function waitForProcessed(docId, attempts = 30, pause = sleep) {
    for (let i = 0; i < attempts; i++) {
        const status = await api(`/documents/${encodeURIComponent(docId)}/status`);
        if (status.status === "processed") return status;
        if (status.status === "failed") throw new Error(status.error_code === "INVALID_PDF" ? "PDF không hợp lệ. Hãy tải lên tài liệu mới." : "Xử lý thất bại sau các lần thử. Có thể chọn Gửi xử lý lại.");
        if (!["pending", "uploading"].includes(status.status)) throw new Error("Tài liệu không ở trạng thái xử lý hợp lệ.");
        if (i < attempts - 1) await pause(2000);
    }
    throw new Error("Đang chờ worker. Giữ Document ID và kiểm tra lại; chưa xác nhận thành công.");
}
async function digest(bytes) {
    const hash = await crypto.subtle.digest("SHA-256", bytes);
    return Array.from(new Uint8Array(hash), b => b.toString(16).padStart(2, "0")).join("");
}
async function downloadVerified(docId, expectedHash) {
    const info = await api(`/documents/${encodeURIComponent(docId)}/download`);
    if (!info.download_url || !/^[a-f0-9]{64}$/.test(info.sha256 || "")) throw new Error("Thiếu bản tải về hoặc SHA-256 đã xác minh.");
    let response;
    try { response = await fetch(info.download_url, { signal: AbortSignal.timeout(30000), credentials: "omit", referrerPolicy: "no-referrer" }); }
    catch { throw new Error("Không tải được PDF. Kiểm tra kết nối và S3 CORS."); }
    if (!response.ok) throw new Error(`Tải PDF thất bại: HTTP ${response.status}.`);
    const bytes = await response.arrayBuffer();
    const actual = await digest(bytes);
    if (actual !== info.sha256 || (expectedHash && actual !== expectedHash)) throw new Error("SHA-256 không khớp. Chưa tải file xuống máy.");
    const url = URL.createObjectURL(new Blob([bytes], { type: "application/pdf" }));
    const link = document.createElement("a"); link.href = url; link.download = "policy-document.pdf";
    document.body.appendChild(link); link.click(); link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    return actual;
}
function step(index) { document.querySelectorAll("#steps li").forEach((el, i) => { el.className = i < index ? "done" : i === index ? "active" : ""; }); }
async function uploadDocument() {
    const file = $("file-input").files[0];
    if (!file || !file.size || file.size > MAX_BYTES) throw new Error("Chọn PDF không rỗng, tối đa 10 MiB.");
    const bytes = await file.arrayBuffer();
    if (new TextDecoder().decode(bytes.slice(0, 5)) !== "%PDF-") throw new Error("File không có định dạng PDF.");
    const expectedHash = await digest(bytes);
    step(0); show("upload-result", "Đang tạo phiên upload…");
    const session = await api("/documents/upload-session", { method: "POST", body: JSON.stringify({ filename: file.name || "document.pdf" }) });
    if (!session.doc_id || !session.upload_url) throw new Error("Phiên upload không hợp lệ.");
    $("doc-id").value = session.doc_id;
    step(1); show("upload-result", "Đang tải PDF lên S3…");
    let put;
    try {
        let body = file;
        const options = { method: "PUT", headers: { "Content-Type": "application/pdf" } };
        if (session.upload_method === "POST") {
            if (!session.upload_fields || typeof session.upload_fields !== "object") throw new Error();
            body = new FormData();
            for (const [key, value] of Object.entries(session.upload_fields)) body.append(key, value);
            body.append("file", file);
            options.method = "POST"; delete options.headers;
        }
        put = await fetch(session.upload_url, { ...options, body, signal: AbortSignal.timeout(60000), credentials: "omit", referrerPolicy: "no-referrer" });
    }
    catch { throw new Error("Upload S3 thất bại hoặc hết thời gian. Tạo phiên mới để thử lại."); }
    if (!put.ok) throw new Error(`Upload S3 thất bại: HTTP ${put.status}.`);
    step(2); show("upload-result", "Đang gửi yêu cầu xử lý…");
    await api("/documents/submit", { method: "POST", body: JSON.stringify({ doc_id: session.doc_id }) });
    step(3); show("upload-result", "Đang chờ worker xác minh phiên bản PDF…");
    await waitForProcessed(session.doc_id);
    step(4); show("upload-result", "Đang tải bản đối chiếu và kiểm tra SHA-256…");
    const hash = await downloadVerified(session.doc_id, expectedHash);
    step(5); show("upload-result", `Hoàn tất · ${session.doc_id}\nSHA-256 khớp file gốc, worker và bản tải về:\n${hash}`, "ok");
}
async function action(target, fn) {
    if (authBusy) return;
    authBusy = true;
    const buttons = [...document.querySelectorAll("button")];
    buttons.forEach(button => { button.disabled = true; });
    renderAuthUI();
    try { await fn(); } catch (error) { show(target, error.message, "error"); }
    finally { authBusy = false; buttons.forEach(button => { button.disabled = false; }); renderAuthUI(); }
}
function documentId() { const id = $("doc-id").value.trim(); if (!id) throw new Error("Nhập Document ID trước."); return id; }
$("connect").addEventListener("click", connect);
$("clear-token").addEventListener("click", clearSession);
$("cancel-login").addEventListener("click", () => { clearSession(); show("auth-status", "Đã hủy xác thực. Bạn có thể đăng nhập lại."); });
for (const id of ["api-base", "jwt-input"]) $(id).addEventListener("input", renderAuthUI);
$("lookup").addEventListener("click", () => action("policy-result", async () => {
    const id = $("policy-id").value.trim(); if (!id) throw new Error("Nhập Policy ID.");
    show("policy-result", JSON.stringify(await api(`/policies/${encodeURIComponent(id)}`), null, 2), "ok");
}));
$("search").addEventListener("click", () => action("policy-result", () => searchPolicies(false)));
$("search-next").addEventListener("click", () => action("policy-result", () => searchPolicies(true)));
$("upload").addEventListener("click", () => action("upload-result", uploadDocument));
$("status").addEventListener("click", () => action("document-result", async () => show("document-result", JSON.stringify(await api(`/documents/${encodeURIComponent(documentId())}/status`), null, 2), "ok")));
$("retry-submit").addEventListener("click", () => action("document-result", async () => show("document-result", JSON.stringify(await api("/documents/submit", { method: "POST", body: JSON.stringify({ doc_id: documentId() }) }), null, 2), "ok")));
$("download").addEventListener("click", () => action("document-result", async () => { const hash = await downloadVerified(documentId()); show("document-result", `Đã tải PDF. SHA-256 khớp worker: ${hash}`, "ok"); }));

function validateApi(value) {
    const url = new URL(value);
    if (url.username || url.password || url.search || url.hash ||
        (url.protocol !== "https:" && !(url.protocol === "http:" && ["localhost", "127.0.0.1"].includes(url.hostname)))) throw new Error("API URL không hợp lệ.");
    return url.href.replace(/\/$/, "");
}
async function loadConfig() {
    try {
        const response = await fetch("config.json", { cache: "no-store" });
        if (!response.ok) throw new Error();
        const loaded = await response.json();
        if (loaded.mode === "local" && !["localhost", "127.0.0.1"].includes(window.location.hostname)) throw new Error();
        config = loaded;
        configLoaded = true;
        $("api-base").value = loaded.apiBase || "";
        $("region").value = loaded.region || "ap-southeast-1";
        $("client-id").value = loaded.clientId || "";
        if (loaded.mode === "local") {
            $("username").value = "alice@demo.local";
            $("password").disabled = true;
            show("environment-status", "DEMO OFFLINE · AWS và đăng nhập được giả lập · Dữ liệu chỉ trong bộ nhớ · alice@demo.local / bob@demo.local");
        } else show("environment-status", loaded.apiBase && loaded.clientId ? "AWS · Đăng nhập bằng tài khoản được cấp để bắt đầu." : "AWS · Cần cấu hình API URL và Cognito Client ID trong phần cấu hình kết nối.");
    } catch { show("environment-status", "Chưa đọc được config.json. Có thể cấu hình kết nối thủ công."); }
    renderAuthUI();
    if (configLoaded) await restoreTabSession();
}
async function cognito(operation, body, settings) {
    const region = settings.region;
    if (!/^[a-z]{2}(?:-gov)?-[a-z]+-\d$/.test(region)) throw new Error("AWS Region không hợp lệ.");
    const suffix = region.startsWith("cn-") ? "amazonaws.com.cn" : "amazonaws.com";
    let response;
    try { response = await fetch(`https://cognito-idp.${region}.${suffix}/`, { method: "POST", headers: {
        "Content-Type": "application/x-amz-json-1.1", "X-Amz-Target": "AWSCognitoIdentityProviderService." + operation },
        body: JSON.stringify(body), signal: AbortSignal.timeout(15000), credentials: "omit" }); }
    catch { throw new Error("Không kết nối được dịch vụ đăng nhập."); }
    let result;
    try { result = await response.json(); } catch { throw new Error("Dịch vụ đăng nhập không trả dữ liệu hợp lệ."); }
    if (!response.ok) {
        const code = (result.__type || "").split("#").pop();
        const messages = { NotAuthorizedException: "Sai thông tin đăng nhập hoặc phiên đã hết hạn.", UserNotConfirmedException: "Tài khoản chưa được xác nhận. Liên hệ quản trị viên.", PasswordResetRequiredException: "Tài khoản cần đặt lại mật khẩu. Liên hệ quản trị viên.", InvalidPasswordException: "Mật khẩu mới chưa đạt yêu cầu của hệ thống.", CodeMismatchException: "Mã xác thực không đúng.", ExpiredCodeException: "Mã xác thực đã hết hạn.", TooManyRequestsException: "Đăng nhập quá nhiều lần. Hãy đợi rồi thử lại." };
        throw new Error(messages[code] || "Không đăng nhập được. Kiểm tra cấu hình và tài khoản.");
    }
    return result;
}
function acceptLogin(result, settings, username, persistUntil = null) {
    const tokens = result.AuthenticationResult;
    if (!tokens || !tokens.IdToken) throw new Error("Chưa nhận được phiên đăng nhập hợp lệ.");
    const keepInTab = persistUntil !== null || $("remember-session").checked;
    clearSession();
    apiBase = settings.apiBase;
    authHeader = "Bearer " + tokens.IdToken;
    authSession = { ...settings, username, refreshToken: tokens.RefreshToken, accessToken: tokens.AccessToken,
        expiresAt: Date.now() + Number(tokens.ExpiresIn || 3600) * 1000,
        persistUntil: keepInTab && configuredSession(settings) ? (persistUntil || Date.now() + TAB_SESSION_MS) : null };
    const persisted = saveTabSession();
    show("auth-status", `Đã đăng nhập: ${username}${config.mode === "local" ? " (demo offline)" : ""}.`, "ok");
    if (keepInTab && !persisted) show("auth-status", "Đã đăng nhập. Không lưu được phiên trong tab; tải lại trang sẽ cần đăng nhập lại.", "ok");
    show("library-status", "Chọn Làm mới danh sách để xem tài liệu của bạn.");
    renderAuthUI();
}
async function login() {
    const keepInTab = $("remember-session").checked;
    const username = $("username").value.trim();
    const password = $("password").value;
    const newPassword = $("new-password").value;
    const code = $("mfa-code").value.trim();
    $("password").value = ""; $("new-password").value = ""; $("mfa-code").value = "";
    if (!authChallenge) clearSession();
    $("remember-session").checked = keepInTab;
    if (!username) throw new Error("Nhập tài khoản đăng nhập.");
    const settings = { apiBase: validateApi($("api-base").value.trim()), region: $("region").value.trim(), clientId: $("client-id").value.trim() };
    let result;
    if (config.mode === "local") {
        const response = await fetch("/local-auth", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ username }) });
        if (!response.ok) throw new Error("Chọn alice@demo.local hoặc bob@demo.local để dùng demo.");
        result = await response.json();
    } else {
        if (!/^[a-z0-9]{1,128}$/.test(settings.clientId)) throw new Error("Cognito Client ID không hợp lệ.");
        if (authChallenge) {
            if (username !== (authChallenge.formUsername || authChallenge.username) || JSON.stringify(settings) !== JSON.stringify(authChallenge.settings)) {
                clearSession(); throw new Error("Cấu hình đã thay đổi. Hãy đăng nhập lại.");
            }
            const responses = { USERNAME: authChallenge.username };
            if (authChallenge.name === "NEW_PASSWORD_REQUIRED") {
                if (!newPassword) throw new Error("Nhập mật khẩu mới.");
                responses.NEW_PASSWORD = newPassword;
            } else {
                if (!code) throw new Error("Nhập mã xác thực.");
                responses[{ SMS_MFA: "SMS_MFA_CODE", SOFTWARE_TOKEN_MFA: "SOFTWARE_TOKEN_MFA_CODE", EMAIL_OTP: "EMAIL_OTP_CODE" }[authChallenge.name]] = code;
            }
            result = await cognito("RespondToAuthChallenge", { ClientId: settings.clientId, ChallengeName: authChallenge.name, Session: authChallenge.session, ChallengeResponses: responses }, settings);
        } else {
            if (!password) throw new Error("Nhập mật khẩu.");
            result = await cognito("InitiateAuth", { ClientId: settings.clientId, AuthFlow: "USER_PASSWORD_AUTH", AuthParameters: { USERNAME: username, PASSWORD: password } }, settings);
        }
    }
    if (result.ChallengeName) {
        if (!["NEW_PASSWORD_REQUIRED", "SMS_MFA", "SOFTWARE_TOKEN_MFA", "EMAIL_OTP"].includes(result.ChallengeName)) throw new Error("Tài khoản yêu cầu bước xác thực chưa được hỗ trợ. Liên hệ quản trị viên.");
        const attrs = JSON.parse(result.ChallengeParameters?.requiredAttributes || "[]");
        if (attrs.length) throw new Error("Tài khoản thiếu thuộc tính bắt buộc. Liên hệ quản trị viên hoàn thiện tài khoản.");
        authChallenge = { name: result.ChallengeName, session: result.Session, username: result.ChallengeParameters?.USER_ID_FOR_SRP || username, settings };
        // Cognito can return an internal username; retain the email separately for form comparisons.
        authChallenge.formUsername = username;
        renderAuthUI();
        show("auth-status", result.ChallengeName === "NEW_PASSWORD_REQUIRED" ? "Cần đặt mật khẩu mới. Nhập bên dưới rồi xác nhận." : "Nhập mã xác thực rồi xác nhận.");
        return;
    }
    acceptLogin(result, settings, username);
}
async function refreshIfNeeded() {
    if (!authSession || authSession.expiresAt > Date.now() + 30000) return;
    if (!authSession.refreshToken) { clearSession(); throw new Error("Phiên đã hết hạn. Hãy đăng nhập lại."); }
    if (!refreshInFlight) {
        const current = authSession;
        refreshInFlight = (async () => {
            try {
                const result = await cognito("InitiateAuth", { ClientId: current.clientId, AuthFlow: "REFRESH_TOKEN_AUTH", AuthParameters: { REFRESH_TOKEN: current.refreshToken } }, current);
                if (authSession !== current) throw new Error("Phiên đã thay đổi.");
                if (!result.AuthenticationResult?.IdToken) throw new Error("Không gia hạn được phiên.");
                authHeader = "Bearer " + result.AuthenticationResult.IdToken;
                authSession = { ...current, accessToken: result.AuthenticationResult.AccessToken,
                    expiresAt: Date.now() + Number(result.AuthenticationResult.ExpiresIn || 3600) * 1000 };
                if (result.AuthenticationResult.RefreshToken) authSession.refreshToken = result.AuthenticationResult.RefreshToken;
                saveTabSession();
            } catch { if (authSession === current) clearSession(); throw new Error("Phiên đã hết hạn. Hãy đăng nhập lại."); }
            finally { refreshInFlight = null; }
        })();
    }
    await refreshInFlight;
    renderAuthUI();
}
async function signout() {
    const previous = authSession, header = authHeader;
    const locallyCleared = clearSession();
    if (config.mode === "local" && header) {
        const response = await fetch("/local-auth/logout", { method: "POST", headers: { Authorization: header } });
        if (!response.ok) throw new Error("Đã xóa phiên local; chưa xác nhận thu hồi phiên trên máy chủ demo.");
    } else if (previous?.accessToken) {
        try { await cognito("GlobalSignOut", { AccessToken: previous.accessToken }, previous); }
        catch { throw new Error("Đã xóa phiên trên giao diện; chưa xác nhận thu hồi phiên Cognito. Hãy đăng nhập lại để thử đăng xuất toàn cục."); }
    }
    if (!locallyCleared) throw new Error("Đã xóa phiên trong bộ nhớ nhưng chưa xác nhận xóa phiên lưu trong tab. Hãy đóng tab và kiểm tra cài đặt trình duyệt.");
    show("auth-status", "Đã đăng xuất và xóa dữ liệu phiên trên giao diện.", "ok");
}
async function searchPolicies(next) {
    if (!next) { activeKeyword = $("keyword").value.trim(); searchCursor = null; }
    if (!activeKeyword) throw new Error("Nhập từ khóa.");
    const result = await api(`/policies?keyword=${encodeURIComponent(activeKeyword)}&limit=5${next && searchCursor ? "&next_token=" + encodeURIComponent(searchCursor) : ""}`);
    searchCursor = result.next_token;
    $("search-next").hidden = !searchCursor;
    show("policy-result", JSON.stringify(result, null, 2), "ok");
}
function cell(text, tag = "td") { const el = document.createElement(tag); el.textContent = text; return el; }
async function listDocuments(next = false) {
    const result = await api(`/documents?limit=10${next && documentCursor ? "&next_token=" + encodeURIComponent(documentCursor) : ""}`);
    if (!next) $("document-list").textContent = "";
    const labels = { uploading: "Chưa gửi xử lý", pending: "Đang xử lý", processed: "Đã xác minh", failed: "Xử lý thất bại" };
    for (const item of result.documents || []) {
        const row = document.createElement("tr");
        const name = cell(item.filename || "document.pdf"); name.appendChild(cell(item.doc_id, "small"));
        const status = cell(""); const badge = cell(labels[item.status] || item.status, "span"); badge.className = "badge " + item.status; status.appendChild(badge);
        if (item.error_code) status.appendChild(cell(item.error_code === "INVALID_PDF" ? "Cần tải lên PDF mới" : "Có thể gửi xử lý lại", "small"));
        const actions = cell(""); const button = cell("Chọn tài liệu", "button"); button.className = "secondary";
        button.addEventListener("click", () => { $("doc-id").value = item.doc_id; show("document-result", `Đã chọn: ${item.filename || item.doc_id}. Có thể kiểm tra trạng thái, gửi xử lý lại hoặc tải PDF.`); $("doc-id").focus(); });
        actions.appendChild(button); row.append(name, status, actions); $("document-list").appendChild(row);
    }
    documentCursor = result.next_token;
    $("documents-next").hidden = !documentCursor;
    show("library-status", $("document-list").children.length ? "Danh sách tài liệu của phiên hiện tại." : "Chưa có tài liệu. Chọn PDF để bắt đầu.", "ok");
}
$("login-form").addEventListener("submit", event => { event.preventDefault(); action("auth-status", login); });
$("signout").addEventListener("click", () => action("auth-status", signout));
$("refresh-documents").addEventListener("click", () => action("library-status", () => listDocuments(false)));
$("documents-next").addEventListener("click", () => action("library-status", () => listDocuments(true)));
renderAuthUI();
if (typeof window !== "undefined") loadConfig();
