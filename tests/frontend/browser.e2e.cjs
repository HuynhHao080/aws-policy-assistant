// Actual headless browser + mocked API/S3. Never contacts AWS.
const { test } = require('node:test');
const assert = require('node:assert/strict');
const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const root = path.resolve(__dirname, '../../frontend');
const PDF = Buffer.from('%PDF-1.4\nsynthetic browser fixture\n%%EOF');
const HASH = crypto.createHash('sha256').update(PDF).digest('hex');

test('browser: upload/download integrity, errors, responsive layout and no page exceptions', async () => {
    const server = http.createServer((request, response) => {
        const files = {'/':'index.html','/app.js':'app.js','/styles.css':'styles.css'};
        const file = files[request.url];
        if (!file) { response.writeHead(404); response.end(); return; }
        response.setHeader('Content-Type', file.endsWith('.js') ? 'text/javascript' : file.endsWith('.css') ? 'text/css' : 'text/html; charset=utf-8');
        response.end(fs.readFileSync(path.join(root,file)));
    });
    await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
    let browser;
    try {
        browser = await chromium.launch(process.platform === 'win32' ? {channel:'msedge',headless:true} : {headless:true});
        const page = await browser.newPage({viewport:{width:1440,height:1100},acceptDownloads:true});
        const errors = [];
        page.on('pageerror', error => errors.push(error.message));
        let polls = 0, failStatus = false, unauthorized = false, puts = 0;
        await page.route('https://policy.test/**', async route => {
            const url = new URL(route.request().url());
            const headers = {'access-control-allow-origin':'*','access-control-allow-headers':'authorization,content-type','access-control-allow-methods':'GET,POST,OPTIONS'};
            if (route.request().method() === 'OPTIONS') return route.fulfill({status:204,headers});
            let status = 200, body;
            if (unauthorized) { status=401; body={error:'Unauthorized'}; }
            else if (url.pathname.endsWith('/upload-session')) body={doc_id:'doc-browser-fixture',upload_url:'https://storage.test/file'};
            else if (url.pathname.endsWith('/submit')) body={status:'pending'};
            else if (url.pathname.endsWith('/status')) {
                if (failStatus) { status=500; body={error:'server failure'}; }
                else body={doc_id:'doc-browser-fixture',status:++polls>1?'processed':'pending',sha256:HASH};
            }
            else if (url.pathname.endsWith('/download')) body={download_url:'https://storage.test/file',sha256:HASH};
            else body={policy_id:'POL-001',title:'Synthetic policy'};
            await route.fulfill({status,headers,contentType:'application/json',body:JSON.stringify(body)});
        });
        await page.route('https://storage.test/**', async route => {
            const headers={'access-control-allow-origin':'*','access-control-allow-methods':'PUT,GET,OPTIONS','access-control-allow-headers':'content-type'};
            assert.equal(route.request().headers().authorization, undefined);
            if (route.request().method() === 'OPTIONS') return route.fulfill({status:204,headers});
            if (route.request().method() === 'PUT') {
                puts++; assert.deepEqual(route.request().postDataBuffer(),PDF);
                assert.equal(route.request().headers()['content-type'],'application/pdf');
                return route.fulfill({status:200,headers});
            }
            await route.fulfill({status:200,headers,contentType:'application/pdf',body:PDF});
        });
        await page.goto(`http://127.0.0.1:${server.address().port}`);
        await page.locator('summary').click();
        await page.locator('#api-base').fill('https://policy.test/Prod');
        await page.locator('#jwt-input').fill('fixture.token.only');
        await page.locator('#connect').click();
        assert.equal(await page.locator('#jwt-input').inputValue(),'');
        await page.locator('#file-input').setInputFiles({name:'synthetic.pdf',mimeType:'application/pdf',buffer:PDF});
        const saved = page.waitForEvent('download');
        await page.locator('#upload').click();
        const download = await saved;
        const stream = await download.createReadStream();
        const chunks=[]; for await (const chunk of stream) chunks.push(chunk);
        assert.deepEqual(Buffer.concat(chunks),PDF);
        await page.waitForFunction(() => document.getElementById('upload-result').dataset.state === 'ok');
        assert.match(await page.locator('#upload-result').innerText(),new RegExp(HASH));
        assert.doesNotMatch(await page.locator('body').innerText(),/storage\.test|fixture\.token\.only/);
        assert.ok(polls >= 2); assert.equal(puts,1);
        fs.mkdirSync(path.resolve(__dirname,'../../docs/evidence'),{recursive:true});
        await page.screenshot({path:path.resolve(__dirname,'../../docs/evidence/frontend-desktop.png'),fullPage:true});
        unauthorized = true;
        await page.locator('#lookup').click();
        await page.waitForFunction(() => document.getElementById('policy-result').dataset.state === 'error');
        assert.match(await page.locator('#policy-result').innerText(),/HTTP 401/);
        unauthorized = false; failStatus = true;
        await page.locator('#jwt-input').fill('fixture.token.only');
        await page.locator('#connect').click();
        await page.locator('#file-input').setInputFiles({name:'synthetic.pdf',mimeType:'application/pdf',buffer:PDF});
        await page.locator('#upload').click();
        await page.waitForFunction(() => document.getElementById('upload-result').dataset.state === 'error');
        assert.match(await page.locator('#upload-result').innerText(),/HTTP 500/);
        await page.setViewportSize({width:390,height:844});
        assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth),true);
        await page.locator('#clear-token').click();
        await page.screenshot({path:path.resolve(__dirname,'../../docs/evidence/frontend-mobile.png'),fullPage:true});
        assert.deepEqual(errors,[]);
    } finally {
        if (browser) await browser.close();
        await new Promise(resolve => server.close(resolve));
    }
});

test('auth UX: real browser state transitions with all services mocked', {timeout:120000}, async t => {
    const server=http.createServer((request,response)=>{
        if(request.url==='/config.json'){
            response.setHeader('Content-Type','application/json');
            return response.end(JSON.stringify({mode:'aws',apiBase:'https://policy.test/Prod',region:'ap-southeast-1',clientId:'fixtureclient123'}));
        }
        const file={'/':'index.html','/app.js':'app.js','/styles.css':'styles.css'}[request.url];
        if(!file){response.writeHead(404);return response.end();}
        response.setHeader('Content-Type',file.endsWith('.js')?'text/javascript':file.endsWith('.css')?'text/css':'text/html; charset=utf-8');
        response.end(fs.readFileSync(path.join(root,file)));
    });
    await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
    let browser;
    const origin=`http://127.0.0.1:${server.address().port}`;
    async function capture(page,name){
        const directory=path.resolve(__dirname,'../../docs/evidence');fs.mkdirSync(directory,{recursive:true});
        const mask=[];
        for(const id of ['password','new-password','mfa-code','jwt-input']){
            const input=page.locator('#'+id);
            if(await input.isVisible()&&await input.inputValue())mask.push(input);
        }
        await page.screenshot({path:path.join(directory,'d25-mock-'+name+'.png'),fullPage:true,mask});
    }
    // Inert fixture strings only. No real identities, passwords or tokens.
    const fixture={id:'fixture.identity.value',access:'fixture-access-only',refresh:'fixture-refresh-only',manual:'fixture.manual.value',password:'fixture-password-only',newPassword:'fixture-new-password-only'};
    async function scenario(options,run){
        const context=await browser.newContext({viewport:{width:1440,height:1100}});
        const page=await context.newPage();
        const state={operations:[],api:[],pageErrors:0,sensitiveConsole:0,external:0,downloads:0,...options};
        page.on('pageerror',()=>state.pageErrors++);
        page.on('console',msg=>{if(Object.values(fixture).some(v=>msg.text().includes(v)))state.sensitiveConsole++;});
        await page.route('**/*',async route=>{
            const request=route.request(),url=new URL(request.url());
            if(url.origin===origin)return route.continue();
            const headers={'access-control-allow-origin':origin,'access-control-allow-headers':'authorization,content-type,x-amz-target','access-control-allow-methods':'GET,POST,OPTIONS'};
            const reply=(status,body)=>route.fulfill({status,headers,contentType:'application/json',body:JSON.stringify(body)});
            if(!['cognito-idp.ap-southeast-1.amazonaws.com','policy.test'].includes(url.hostname)){state.external++;return route.abort();}
            if(request.method()==='OPTIONS')return route.fulfill({status:204,headers});
            if(url.hostname==='cognito-idp.ap-southeast-1.amazonaws.com'){
                const operation=request.headers()['x-amz-target'].split('.').pop();
                state.operations.push(operation);
                const body=request.postDataJSON();
                if(operation==='GlobalSignOut'){
                    assert.ok(body.AccessToken===fixture.access);
                    return state.signoutFailure?reply(400,{__type:'NotAuthorizedException'}):reply(200,{});
                }
                if(operation==='InitiateAuth'&&body.AuthFlow==='REFRESH_TOKEN_AUTH'){
                    state.refreshes=(state.refreshes||0)+1;
                    assert.ok(body.AuthParameters.REFRESH_TOKEN===fixture.refresh);
                    return state.refreshFailure?reply(400,{__type:'NotAuthorizedException'}):reply(200,{AuthenticationResult:{IdToken:fixture.id,AccessToken:fixture.access,ExpiresIn:3600}});
                }
                if(state.loginDelay)await new Promise(resolve=>{state.releaseLogin=resolve;});
                if(state.loginFailure)return reply(400,{__type:'NotAuthorizedException',message:'private-error-fixture'});
                if(operation==='InitiateAuth'&&state.challenge)return reply(200,{ChallengeName:state.challenge,Session:'fixture-challenge-session',ChallengeParameters:{USER_ID_FOR_SRP:'fixture-internal-user',requiredAttributes:'[]'}});
                if(operation==='RespondToAuthChallenge'){
                    assert.equal(body.ChallengeName,state.challenge);
                    assert.equal(body.ChallengeResponses.USERNAME,'fixture-internal-user');
                    if(state.challengeFailure)return reply(400,{__type:'CodeMismatchException'});
                    const key=state.challenge==='NEW_PASSWORD_REQUIRED'?'NEW_PASSWORD':{SMS_MFA:'SMS_MFA_CODE',SOFTWARE_TOKEN_MFA:'SOFTWARE_TOKEN_MFA_CODE',EMAIL_OTP:'EMAIL_OTP_CODE'}[state.challenge];
                    assert.ok(body.ChallengeResponses[key]===(state.challenge==='NEW_PASSWORD_REQUIRED'?fixture.newPassword:'123456'));
                }
                return reply(200,{AuthenticationResult:{IdToken:fixture.id,AccessToken:fixture.access,RefreshToken:fixture.refresh,ExpiresIn:state.expiresIn||3600}});
            }
            state.api.push({method:request.method(),path:url.pathname});
            if(state.apiUnauthorized)return reply(401,{error:'Unauthorized'});
            if(url.pathname.endsWith('/submit')){
                assert.equal(request.postDataJSON().doc_id,'doc-ui-fixture');
                return state.retryConflict?reply(409,{error:'Conflict'}):reply(200,{doc_id:'doc-ui-fixture',status:'pending'});
            }
            if(url.pathname.endsWith('/documents'))return reply(200,{documents:[{doc_id:'doc-ui-fixture',filename:'synthetic.pdf',status:'processed'}]});
            return reply(200,{policies:[{policy_id:'POL-001',title:'Synthetic policy'}]});
        });
        try{
            await page.goto(origin);
            await page.waitForFunction(()=>document.getElementById('environment-status').textContent.startsWith('AWS · Đăng nhập'));
            const login=async()=>{await page.locator('#username').fill('operator@example.test');await page.locator('#password').fill(fixture.password);await page.locator('#login').click();};
            const authenticated=async()=>{await page.waitForFunction(()=>document.getElementById('login-form').hidden);assert.equal(await page.locator('#signout').isVisible(),true);};
            await run(page,state,{login,authenticated,fixture});
            assert.equal(state.external,0,'external network was blocked');
            assert.equal(state.pageErrors,0,'no page exceptions');
            assert.equal(state.sensitiveConsole,0,'no fixture secrets logged');
            assert.equal(await page.evaluate(()=>localStorage.length+sessionStorage.length),0,'no auth storage');
        }finally{await context.close();}
    }
    try{
        browser=await chromium.launch(process.platform==='win32'?{channel:'msedge',headless:true}:{headless:true});
        await t.test('logged out: login only, advanced closed, apply disabled until valid input',()=>scenario({},async(page,state,{fixture})=>{
            assert.equal(await page.locator('#login-form').isVisible(),true);
            assert.equal(await page.locator('#signout').isVisible(),false);
            assert.equal(await page.locator('#clear-token').isVisible(),false);
            assert.equal(await page.locator('#advanced-connection').evaluate(el=>el.open),false);
            await capture(page,'logged-out');
            await page.locator('summary').click();
            assert.equal(await page.locator('#connect').isDisabled(),true);
            await page.locator('#jwt-input').fill(fixture.manual);
            await page.locator('#api-base').fill('http://policy.test/Prod');
            assert.equal(await page.locator('#connect').isDisabled(),true);
            await page.locator('#api-base').fill('https://policy.test/Prod?secret=fixture');
            assert.equal(await page.locator('#connect').isDisabled(),true);
            await page.locator('#api-base').fill('https://policy.test/Prod');
            assert.equal(await page.locator('#connect').isEnabled(),true);
            await page.locator('#clear-token').click();
            assert.equal(await page.locator('#connect').isDisabled(),true);
            assert.equal(state.operations.length+state.api.length,0);
        }));
        await t.test('Cognito login/logout: state, loading and existing GlobalSignOut',()=>scenario({loginDelay:true},async(page,state,{login,authenticated})=>{
            await login();await page.waitForFunction(()=>document.getElementById('login').disabled);
            assert.equal(await page.locator('#signout').isVisible(),false);
            while(!state.releaseLogin)await new Promise(resolve=>setTimeout(resolve,10));
            state.releaseLogin();state.loginDelay=false;await authenticated();
            assert.match(await page.locator('#account-name').innerText(),/operator@example.test/);
            assert.equal(await page.locator('#password').inputValue(),'');
            assert.equal(await page.locator('#clear-token').isVisible(),false);
            await capture(page,'cognito');
            await page.locator('#signout').click();
            await page.waitForFunction(()=>document.getElementById('auth-status').textContent.includes('Đã đăng xuất'));
            assert.equal(await page.locator('#signout').isVisible(),false);
            assert.equal(state.operations.filter(x=>x==='GlobalSignOut').length,1);
            assert.match(await page.locator('#auth-status').innerText(),/Đã đăng xuất/);
        }));
        await t.test('failed login never shows an authenticated session',()=>scenario({loginFailure:true},async(page,state,{login})=>{
            await login();await page.waitForFunction(()=>document.getElementById('auth-status').dataset.state==='error');
            assert.equal(await page.locator('#login-form').isVisible(),true);
            assert.equal(await page.locator('#signout').isVisible(),false);
            assert.equal(await page.locator('#session-panel').isVisible(),false);
            assert.equal(await page.locator('#password').inputValue(),'');
            assert.doesNotMatch(await page.locator('body').innerText(),/private-error-fixture/);
        }));
        await t.test('manual session and clear are local, not verified login or GlobalSignOut',()=>scenario({},async(page,state,{fixture})=>{
            await page.locator('summary').click();await page.locator('#jwt-input').fill(fixture.manual);await page.locator('#connect').click();
            assert.equal(await page.locator('#login-form').isVisible(),false);
            assert.equal(await page.locator('#signout').isVisible(),false);
            assert.equal(await page.locator('#clear-token').isVisible(),true);
            assert.match(await page.locator('#session-kind').innerText(),/chưa xác minh/i);
            assert.equal(await page.locator('#jwt-input').inputValue(),'');
            assert.equal(state.operations.length+state.api.length,0);
            await capture(page,'manual');
            await page.locator('#clear-token').click();
            assert.equal(await page.locator('#login-form').isVisible(),true);
            assert.equal(await page.locator('#clear-token').isVisible(),false);
            assert.match(await page.locator('#auth-status').innerText(),/không thu hồi token/);
        }));
        await t.test('Cognito to manual requires logout and preserves the existing session until then',()=>scenario({},async(page,state,{login,authenticated,fixture})=>{
            await login();await authenticated();await page.locator('summary').click();await page.locator('#jwt-input').fill(fixture.manual);
            assert.equal(await page.locator('#connect').isDisabled(),true);
            assert.equal(await page.locator('#manual-switch-help').isVisible(),true);
            await page.evaluate(()=>connect());
            assert.equal(await page.locator('#signout').isVisible(),true);
            assert.match(await page.locator('#account-name').innerText(),/operator@example.test/);
            await page.locator('#signout').click();
            await page.locator('#jwt-input').fill(fixture.manual);await page.locator('#connect').click();
            assert.match(await page.locator('#session-kind').innerText(),/Token thủ công/i);
            assert.equal(state.operations.filter(x=>x==='GlobalSignOut').length,1);
        }));
        for(const challenge of ['NEW_PASSWORD_REQUIRED','SMS_MFA','SOFTWARE_TOKEN_MFA','EMAIL_OTP']){
            await t.test('challenge '+challenge+': not logged in before completion',()=>scenario({challenge},async(page,state,{login,authenticated,fixture})=>{
                await login();await page.waitForFunction(()=>!document.getElementById('cancel-login').hidden);
                assert.equal(await page.locator('#signout').isVisible(),false);
                assert.equal(await page.locator('#password-field').isVisible(),false);
                assert.equal(await page.locator('#username').getAttribute('readonly'),'');
                if(challenge==='SMS_MFA')await capture(page,'challenge');
                if(challenge==='NEW_PASSWORD_REQUIRED')await page.locator('#new-password').fill(fixture.newPassword);
                else await page.locator('#mfa-code').fill('123456');
                await page.locator('#login').click();await authenticated();
                assert.equal(await page.locator('#new-password').inputValue(),'');assert.equal(await page.locator('#mfa-code').inputValue(),'');
                assert.equal(state.operations.filter(x=>x==='RespondToAuthChallenge').length,1);
            }));
        }
        await t.test('challenge cancellation is local and wrong MFA stays a challenge',()=>scenario({challenge:'SMS_MFA',challengeFailure:true},async(page,state,{login})=>{
            await login();await page.locator('#mfa-code').fill('123456');await page.locator('#login').click();
            await page.waitForFunction(()=>document.getElementById('auth-status').dataset.state==='error');
            assert.equal(await page.locator('#signout').isVisible(),false);
            assert.equal(await page.locator('#mfa-field').isVisible(),true);
            const before=state.operations.length;await page.locator('#cancel-login').click();
            assert.equal(await page.locator('#password-field').isVisible(),true);
            assert.equal(await page.locator('#mfa-field').isVisible(),false);
            assert.equal(state.operations.length,before);
        }));
        await t.test('refresh preserves Cognito UI and a 401 clears it',()=>scenario({expiresIn:1},async(page,state,{login,authenticated})=>{
            await login();await authenticated();await page.locator('#search').click();
            await page.waitForFunction(()=>document.getElementById('policy-result').dataset.state==='ok');
            assert.equal(state.refreshes,1);assert.equal(await page.locator('#signout').isVisible(),true);
            state.apiUnauthorized=true;await page.locator('#refresh-documents').click();
            await page.waitForFunction(()=>!document.getElementById('login-form').hidden);
            assert.equal(await page.locator('#signout').isVisible(),false);
            assert.match(await page.locator('#auth-status').innerText(),/hết hạn/);
        }));
        await t.test('refresh failure and logout failure return to login without false revocation success',()=>scenario({expiresIn:1,refreshFailure:true},async(page,state,{login,authenticated})=>{
            await login();await authenticated();await page.locator('#search').click();
            await page.waitForFunction(()=>document.getElementById('policy-result').dataset.state==='error');
            assert.equal(await page.locator('#login-form').isVisible(),true);assert.equal(state.api.length,0);
            state.expiresIn=3600;state.signoutFailure=true;await login();await authenticated();await page.locator('#signout').click();
            await page.waitForFunction(()=>document.getElementById('auth-status').dataset.state==='error');
            assert.equal(await page.locator('#signout').isVisible(),false);
            assert.match(await page.locator('#auth-status').innerText(),/chưa xác nhận thu hồi/);
        }));
        await t.test('search, library, Retry responses, desktop/mobile and no visible secrets',()=>scenario({},async(page,state,{login,authenticated})=>{
            await login();await authenticated();await page.locator('#search').click();
            await page.waitForFunction(()=>document.getElementById('policy-result').dataset.state==='ok');
            await page.locator('#refresh-documents').click();await page.waitForFunction(()=>document.querySelectorAll('#document-list tr').length===1);
            await page.getByRole('button',{name:'Chọn tài liệu',exact:true}).click();await page.locator('#retry-submit').click();
            await page.waitForFunction(()=>document.getElementById('document-result').textContent.includes('pending'));
            assert.equal(state.api.filter(x=>x.method==='POST'&&x.path.endsWith('/submit')).length,1);
            state.retryConflict=true;await page.locator('#retry-submit').click();await page.waitForFunction(()=>document.getElementById('document-result').dataset.state==='error');
            assert.match(await page.locator('#document-result').innerText(),/HTTP 409/);
            for(const width of [1440,390]){
                await page.setViewportSize({width,height:900});
                assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
                assert.equal(await page.locator('#login-form').isVisible(),false);assert.equal(await page.locator('#signout').isVisible(),true);
                const text=await page.locator('body').innerText();assert.equal(Object.values(fixture).some(value=>text.includes(value)),false);
                if(width===390)await capture(page,'mobile-cognito');
            }
        }));
    }finally{if(browser)await browser.close();await new Promise(resolve=>server.close(resolve));}
});
