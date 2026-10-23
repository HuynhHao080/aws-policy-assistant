const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const { webcrypto } = require('node:crypto');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../../frontend/app.js'), 'utf8');
const PDF = Buffer.from('%PDF-1.4\nsynthetic browser fixture\n%%EOF');
const HASH = require('node:crypto').createHash('sha256').update(PDF).digest('hex');
function setup(responses = []) {
    const elements = new Map();
    const calls = [];
    const state = { downloads: 0 };
    const get = id => {
        if (!elements.has(id)) elements.set(id, { value: '', textContent: '', dataset: {}, files: [], addEventListener() {} });
        return elements.get(id);
    };
    const context = vm.createContext({
        document: { getElementById: get, querySelectorAll: () => [], body: { appendChild() {} },
            createElement: () => ({ click() { state.downloads++; }, remove() {} }) },
        fetch: async (url, options) => { calls.push({url, options}); if (!responses.length) throw Error('unexpected request'); const next = responses.shift(); if (next instanceof Error) throw next; return { ok: next.status < 400, status: next.status, json: async () => next.body, arrayBuffer: async () => Uint8Array.from(next.bytes || PDF).buffer }; },
        URL: class extends URL { static createObjectURL() { return 'blob:test'; } static revokeObjectURL() {} },
        AbortSignal, TextDecoder, Blob, FormData, Uint8Array, crypto: webcrypto,
        setTimeout: callback => { callback(); return 0; },
    });
    get('api-base').value = 'https://api.example/Prod'; get('jwt-input').value = 'demo.token.fixture';
    vm.runInContext(source, context); vm.runInContext('connect()', context);
    const run = code => vm.runInContext(code, context);
    return { get, run, calls, state };
}
const ok = body => ({status:200, body});
test('JWT format is not presented as verified authentication and input is cleared', () => {
    const app = setup();
    assert.match(app.get('auth-status').textContent, /API sẽ xác thực/);
    assert.equal(app.get('jwt-input').value, '');
    app.run('clearSession()');
    assert.equal(app.run('authHeader'), null);
});
test('pending status is polled until processed', async () => {
    const app = setup([ok({status:'pending'}), ok({status:'processed'})]);
    assert.equal((await app.run('waitForProcessed("doc-a", 2, async () => {})')).status, 'processed');
    assert.equal(app.calls.length, 2);
});
test('polling timeout is a failure, not success', async () => {
    const app = setup([ok({status:'pending'}), ok({status:'pending'})]);
    await assert.rejects(app.run('waitForProcessed("doc-a", 2, async () => {})'), /chưa xác nhận thành công/);
});
test('unauthorized response stops the workflow', async () => {
    const app = setup([{status:401, body:{}}]);
    await assert.rejects(app.run('waitForProcessed("doc-a")'), /HTTP 401/);
    assert.equal(app.calls.length, 1);
});
test('download failure is not reported as completion', async () => {
    const app = setup([ok({download_url:'https://s3.example/private',sha256:HASH}), {status:403}]);
    await assert.rejects(app.run('downloadVerified("doc-a")'), /HTTP 403/);
    assert.equal(app.state.downloads, 0);
});
test('checksum mismatch prevents saving a file', async () => {
    const app = setup([ok({download_url:'https://s3.example/private',sha256:'0'.repeat(64)}), ok({})]);
    await assert.rejects(app.run('downloadVerified("doc-a")'), /SHA-256 không khớp/);
    assert.equal(app.state.downloads, 0);
});
test('verified download saves once, without forwarding JWT to S3', async () => {
    const app = setup([ok({download_url:'https://s3.example/private',sha256:HASH}), ok({})]);
    assert.equal(await app.run(`downloadVerified("doc-a", "${HASH}")`), HASH);
    assert.equal(app.state.downloads, 1);
    assert.equal(app.calls[1].options.headers, undefined);
});
test('full upload waits for processing and matches original, worker and download bytes', async () => {
    const app = setup([ok({doc_id:'doc-a', upload_url:'https://s3.example/private'}), ok({}), ok({status:'pending'}), ok({status:'pending'}), ok({status:'processed'}), ok({download_url:'https://s3.example/private', sha256:HASH}), ok({})]);
    app.get('file-input').files = [{ size:PDF.length, arrayBuffer:async () => Uint8Array.from(PDF).buffer }];
    await app.run('action("upload-result", uploadDocument)');
    assert.equal(app.get('upload-result').dataset.state, 'ok');
    assert.match(app.get('upload-result').textContent, /Hoàn tất/);
    assert.match(app.get('upload-result').textContent, new RegExp(HASH));
    assert.doesNotMatch(app.get('upload-result').textContent, /https:\/\//);
    assert.equal(app.calls[1].options.headers['Content-Type'], 'application/pdf');
    assert.equal(app.calls[1].options.headers.Authorization, undefined);
    assert.equal(app.get('doc-id').value, 'doc-a');
    assert.equal(app.state.downloads, 1);
});
test('full upload status error never produces a success message', async () => {
    const app = setup([ok({doc_id:'doc-a',upload_url:'https://s3.example/private'}), ok({}), ok({}), {status:500,body:{}}]);
    app.get('file-input').files = [{ size:PDF.length, arrayBuffer:async () => Uint8Array.from(PDF).buffer }];
    await app.run('action("upload-result", uploadDocument)');
    assert.equal(app.get('upload-result').dataset.state, 'error');
    assert.match(app.get('upload-result').textContent, /HTTP 500/);
    assert.equal(app.state.downloads, 0);
});

test('signed POST sends constrained fields and file last without credentials or manual multipart header', async () => {
    const fields = {key:'owner/doc.pdf', policy:'synthetic-policy', 'Content-Type':'application/pdf'};
    const app = setup([ok({doc_id:'doc-a',upload_url:'https://s3.example/private',upload_method:'POST',upload_fields:fields}),ok({}),ok({}),ok({status:'processed'}),ok({download_url:'https://s3.example/private',sha256:HASH}),ok({})]);
    app.get('file-input').files = [new Blob([PDF], {type:'application/pdf'})];
    await app.run('action("upload-result", uploadDocument)');
    assert.equal(app.get('upload-result').dataset.state, 'ok');
    const request = app.calls[1].options;
    assert.equal(request.method, 'POST');
    assert.equal(request.headers, undefined);
    assert.deepEqual([...request.body.keys()], [...Object.keys(fields), 'file']);
    assert.equal(request.body.get('key'), fields.key);
    assert.equal(request.body.get('file').size, PDF.length);
    assert.equal(app.state.downloads, 1);
});

function awsFields(app) {
    app.get('username').value = 'alice@example.test'; app.get('password').value = 'synthetic-password';
    app.get('region').value = 'ap-southeast-1'; app.get('client-id').value = 'fixtureclient123';
}
test('Cognito login clears password and retains tokens in memory only', async () => {
    const app = setup([ok({AuthenticationResult:{IdToken:'issued.fixture.token',AccessToken:'fixture-access',RefreshToken:'fixture-refresh',ExpiresIn:3600}})]);
    awsFields(app); await app.run('login()');
    assert.equal(app.get('password').value,'');
    assert.equal(app.run('authHeader'),'Bearer issued.fixture.token');
    assert.match(app.get('auth-status').textContent,/alice@example.test/);
    assert.equal(app.calls[0].url,'https://cognito-idp.ap-southeast-1.amazonaws.com/');
    assert.equal(app.calls[0].options.headers.Authorization,undefined);
});
test('failed Cognito login does not retain a previous account session', async () => {
    const app = setup([{status:400,body:{__type:'NotAuthorizedException',message:'private server details'}}]);
    awsFields(app); await assert.rejects(app.run('login()'),/Sai thông tin/);
    assert.equal(app.run('authHeader'),null); assert.equal(app.get('password').value,'');
});
test('new password challenge uses internal Cognito username while preserving form email', async () => {
    const app = setup([ok({ChallengeName:'NEW_PASSWORD_REQUIRED',Session:'fixture-session',ChallengeParameters:{USER_ID_FOR_SRP:'internal-user',requiredAttributes:'[]'}}),ok({AuthenticationResult:{IdToken:'issued.fixture.token',ExpiresIn:3600}})]);
    awsFields(app); await app.run('login()');
    assert.equal(app.get('new-password-field').hidden,false);
    app.get('new-password').value='synthetic-new-password';
    await app.run('login()');
    const body=JSON.parse(app.calls[1].options.body);
    assert.equal(body.ChallengeResponses.USERNAME,'internal-user');
    assert.equal(body.ChallengeName,'NEW_PASSWORD_REQUIRED');
    assert.equal(app.get('new-password').value,'');
    assert.equal(app.run('authHeader'),'Bearer issued.fixture.token');
});
test('MFA challenge sends the one-time code and clears the input', async () => {
    const app=setup([ok({ChallengeName:'SOFTWARE_TOKEN_MFA',Session:'fixture-session'}),ok({AuthenticationResult:{IdToken:'issued.fixture.token'}})]);
    awsFields(app);await app.run('login()');app.get('mfa-code').value='123456';await app.run('login()');
    assert.equal(JSON.parse(app.calls[1].options.body).ChallengeResponses.SOFTWARE_TOKEN_MFA_CODE,'123456');
    assert.equal(app.get('mfa-code').value,'');
});
test('expired sessions refresh once before calling the protected API', async () => {
    const app=setup([ok({AuthenticationResult:{IdToken:'fresh.fixture.token',AccessToken:'fresh-access',ExpiresIn:3600}}),ok({documents:[]})]);
    app.run('authSession={clientId:"fixtureclient123",region:"ap-southeast-1",refreshToken:"fixture-refresh",expiresAt:0}');
    await app.run('api("/documents")');
    assert.equal(JSON.parse(app.calls[0].options.body).AuthFlow,'REFRESH_TOKEN_AUTH');
    assert.equal(app.calls[1].options.headers.Authorization,'Bearer fresh.fixture.token');
});
test('signout clears local secrets even if remote revocation fails', async () => {
    const app=setup([{status:400,body:{__type:'NotAuthorizedException'}}]);
    app.run('authSession={accessToken:"fixture-access",region:"ap-southeast-1"}');
    await assert.rejects(app.run('signout()'),/chưa xác nhận thu hồi/);
    assert.equal(app.run('authHeader'),null);assert.equal(app.run('authSession'),null);
});
test('terminal failed processing stops polling immediately', async () => {
    const app=setup([ok({status:'failed',error_code:'INVALID_PDF'})]);
    await assert.rejects(app.run('waitForProcessed("doc-a")'),/PDF không hợp lệ/);
    assert.equal(app.calls.length,1);
});

test('exclusive auth modes hide advanced and signup; clear restores collapsed sections', () => {
    const app=setup();
    assert.equal(app.get('connection-title').dataset.authMode,'manual');
    for(const id of ['advanced-connection','signup-information'])assert.equal(app.get(id).hidden,true);
    assert.equal(app.get('login-form').hidden,true);
    app.run('clearSession()');
    assert.equal(app.get('connection-title').dataset.authMode,'unauthenticated');
    for(const id of ['advanced-connection','signup-information']){assert.equal(app.get(id).hidden,false);assert.equal(app.get(id).open,false);}
    app.run('acceptLogin({AuthenticationResult:{IdToken:"inert.fixture.only"}}, {region:"ap-southeast-1"}, "operator@example.test")');
    assert.equal(app.get('connection-title').dataset.authMode,'cognito');
    for(const id of ['advanced-connection','signup-information'])assert.equal(app.get(id).hidden,true);
    app.get('jwt-input').value='inert.manual.only';app.run('connect()');
    assert.equal(app.get('connection-title').dataset.authMode,'cognito');
    assert.equal(app.run('authHeader'),'Bearer inert.fixture.only');
    assert.equal(app.calls.length,0);
});

test('challenge cancellation restores logged out mode without signup or manual requests', () => {
    const app=setup();app.run('clearSession(); authChallenge={name:"SMS_MFA"}; renderAuthUI()');
    assert.equal(app.get('connection-title').dataset.authMode,'challenge');
    assert.equal(app.get('login-form').hidden,false);assert.equal(app.get('signout').hidden,true);
    assert.equal(app.get('advanced-connection').hidden,true);assert.equal(app.get('signup-information').hidden,true);
    app.run('clearSession()');assert.equal(app.get('connection-title').dataset.authMode,'unauthenticated');
    assert.equal(app.get('mfa-field').hidden,true);assert.equal(app.calls.length,0);
});
