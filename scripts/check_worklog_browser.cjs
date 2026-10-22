// Visual QA of a local generated Hugo site. Never publishes or requests external URLs.
const { chromium } = require('playwright');
const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const root = path.resolve(process.argv[2] || '');
const prefix = '/aws-internship-worklog/';
const evidence = path.resolve(__dirname, '../docs/evidence');
const mime = {'.html':'text/html; charset=utf-8','.css':'text/css','.js':'application/javascript','.json':'application/json','.png':'image/png','.jpg':'image/jpeg','.svg':'image/svg+xml','.woff2':'font/woff2','.woff':'font/woff','.ttf':'font/ttf'};
const server = http.createServer((req,res) => {
    let file;
    try {
        const route = decodeURI(req.url.split('?')[0]);
        if (!route.startsWith(prefix)) { res.writeHead(404).end(); return; }
        file = path.resolve(root, route.slice(prefix.length));
        if (file !== root && !file.startsWith(root + path.sep)) { res.writeHead(403).end(); return; }
        if (fs.statSync(file).isDirectory()) file = path.join(file,'index.html');
        res.setHeader('Content-Type',mime[path.extname(file)] || 'application/octet-stream');
        res.end(fs.readFileSync(file));
    } catch { res.writeHead(404).end(); }
});

(async () => {
    assert.ok(process.argv[2] && fs.existsSync(path.join(root,'index.html')), 'Pass a generated site directory');
    await new Promise(resolve => server.listen(0,'127.0.0.1',resolve));
    let browser;
    const results = [];
    try {
        browser = await chromium.launch(process.platform === 'win32' ? {channel:'msedge',headless:true} : {headless:true});
        const page = await browser.newPage({viewport:{width:1440,height:1000}});
        const origin = 'http://127.0.0.1:' + server.address().port;
        const errors = [];
        page.on('pageerror', error => errors.push(error.message));
        await page.route('**/*', route => new URL(route.request().url()).origin === origin ? route.continue() : route.abort());
        for (const language of ['en','vi']) {
            for (const chapter of ['workshop','cost']) {
                const route = (language === 'vi' ? 'vi/' : '') + '5-workshop/5.7-policyassistant/' + (chapter === 'cost' ? 'cost/' : '');
                await page.setViewportSize({width:1440,height:1000});
                await page.goto(origin + prefix + route);
                await page.screenshot({path:path.join(evidence,`${chapter}-site-${language}-desktop.png`),fullPage:true});
                await page.setViewportSize({width:390,height:844});
                // Theme uses debounced viewport handlers; wait until its layout has settled.
                await page.waitForTimeout(350);
                await page.screenshot({path:path.join(evidence,`${chapter}-site-${language}-mobile.png`),fullPage:true});
                const metrics = await page.evaluate(() => ({viewport:innerWidth,documentWidth:document.documentElement.scrollWidth,bodyWidth:document.getElementById('body').getBoundingClientRect().width,sidebarLeft:getComputedStyle(document.getElementById('sidebar')).left}));
                results.push({language,chapter,...metrics});
                console.log(JSON.stringify(results.at(-1)));
                if (metrics.documentWidth > metrics.viewport) console.log(await page.evaluate(() => [...document.querySelectorAll('body *')].filter(element => !element.closest('table') && element.getBoundingClientRect().right > innerWidth).slice(-8).map(element => ({tag:element.tagName,id:element.id,class:element.className,right:element.getBoundingClientRect().right,display:getComputedStyle(element).display,overflow:getComputedStyle(element).overflowX}))));
            }
        }
        const passed = results.every(result => result.documentWidth <= result.viewport) && errors.length === 0;
        fs.writeFileSync(path.join(evidence,'worklog-browser.json'),JSON.stringify({scope:'Local generated EN/VI site, desktop/mobile; external requests blocked',passed,results,page_errors:errors},null,2)+'\n');
        assert.equal(passed,true,'Generated site must fit mobile viewport without page exceptions');
    } finally {
        if (browser) await browser.close();
        server.close();
    }
})().catch(error => { console.error(error.message); process.exitCode = 1; });
