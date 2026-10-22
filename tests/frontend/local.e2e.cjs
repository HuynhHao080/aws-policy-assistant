// Real browser -> real Lambda handlers -> simulated AWS, without API route stubs.
const { test } = require('node:test');
const assert = require('node:assert/strict');
const { spawn } = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('playwright');
const root = path.resolve(__dirname,'../..');
const python = process.env.DEMO_PYTHON || (fs.existsSync(path.join(root,'.venv/Scripts/python.exe')) ? path.join(root,'.venv/Scripts/python.exe') : 'python');

test('local full stack: login, real backend upload/hash/download, private library and two-user denial', {timeout:60000}, async () => {
    const processHandle = spawn(python,['-B','-m','scripts.demo_server','--port','0'],{cwd:root,stdio:['ignore','pipe','pipe']});
    let browser;
    try {
        const origin = await new Promise((resolve,reject) => {
            let output='';
            const timer=setTimeout(() => reject(Error('Offline demo did not start within 20 seconds')),20000);
            processHandle.stdout.on('data',chunk => { output+=chunk; const match=output.match(/DEMO_URL=(http:\/\/127\.0\.0\.1:\d+)/);if(match){clearTimeout(timer);resolve(match[1]);} });
            processHandle.on('exit',code => {clearTimeout(timer);reject(Error('Offline demo exited early: '+code));});
            processHandle.on('error',error => {clearTimeout(timer);reject(error);});
        });
        // Drain SDK logs without printing request details.
        processHandle.stderr.on('data',()=>{});
        browser=await chromium.launch(process.platform==='win32'?{channel:'msedge',headless:true}:{headless:true});
        const page=await browser.newPage({viewport:{width:1440,height:1100},acceptDownloads:true});
        const errors=[];page.on('pageerror',error=>errors.push(error.message));
        // Reject any accidental external network from the offline demo page.
        await page.route('**/*',route => new URL(route.request().url()).origin===origin ? route.continue() : route.abort());
        await page.goto(origin);
        await page.waitForFunction(()=>document.getElementById('environment-status').textContent.includes('DEMO OFFLINE'));
        await page.locator('#login').click();
        await page.waitForFunction(()=>document.getElementById('auth-status').textContent.includes('Đã đăng nhập'));
        await page.locator('#lookup').click();
        await page.waitForFunction(()=>document.getElementById('policy-result').textContent.includes('Customer Refund Policy'));
        const PDF=Buffer.from('%PDF-1.4\nfull stack synthetic fixture\n%%EOF');
        await page.locator('#file-input').setInputFiles({name:'policy-demo.pdf',mimeType:'application/pdf',buffer:PDF});
        const downloadEvent=page.waitForEvent('download');
        await page.locator('#upload').click();
        const downloaded=await downloadEvent;
        const stream=await downloaded.createReadStream(),chunks=[];for await(const part of stream)chunks.push(part);
        assert.deepEqual(Buffer.concat(chunks),PDF);
        await page.waitForFunction(()=>document.getElementById('upload-result').dataset.state==='ok');
        const docId=await page.locator('#doc-id').inputValue();
        await page.locator('#refresh-documents').click();
        await page.waitForFunction(()=>document.querySelectorAll('#document-list tr').length===1);
        assert.match(await page.locator('#document-list').innerText(),/policy-demo.pdf/);
        assert.match(await page.locator('#document-list').innerText(),/Đã xác minh/);
        const evidence=path.join(root,'docs/evidence');fs.mkdirSync(evidence,{recursive:true});
        await page.screenshot({path:path.join(evidence,'full-stack-desktop.png'),fullPage:true});
        await page.setViewportSize({width:390,height:844});
        assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
        await page.screenshot({path:path.join(evidence,'full-stack-mobile.png'),fullPage:true});
        await page.locator('#signout').click();
        await page.waitForFunction(()=>document.getElementById('auth-status').textContent.includes('Đã đăng xuất'));
        assert.equal(await page.locator('#doc-id').inputValue(),'');
        assert.equal(await page.locator('#document-list').innerText(),'');
        await page.locator('#username').fill('bob@demo.local');await page.locator('#login').click();
        await page.waitForFunction(()=>document.getElementById('auth-status').textContent.includes('bob@demo.local'));
        await page.locator('#refresh-documents').click();
        await page.waitForFunction(()=>document.getElementById('library-status').textContent.includes('Chưa có tài liệu'));
        await page.locator('#doc-id').fill(docId);await page.locator('#status').click();
        await page.waitForFunction(()=>document.getElementById('document-result').dataset.state==='error');
        assert.match(await page.locator('#document-result').innerText(),/HTTP 404/);
        assert.deepEqual(errors,[]);
    } finally {
        if(browser)await browser.close();
        processHandle.kill();
    }
});
