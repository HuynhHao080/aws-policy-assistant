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
