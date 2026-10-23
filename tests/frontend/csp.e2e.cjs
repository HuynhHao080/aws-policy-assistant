const test=require('node:test');const assert=require('node:assert/strict');const http=require('node:http');const fs=require('node:fs');const path=require('node:path');const crypto=require('node:crypto');const cp=require('node:child_process');const {chromium}=require('playwright');
const root=path.resolve(__dirname,'../..');
function safeSpawnDiagnostic(result) {
  const safeCode = value => typeof value === 'string' && /^[A-Z][A-Z0-9_]{0,31}$/.test(value) ? value : null;
  return JSON.stringify({
    status: Number.isInteger(result.status) ? result.status : null,
    error_code: safeCode(result.error?.code),
    signal: safeCode(result.signal),
  });
}

function selectPython() {
  const probe = executable => {
    try {
      return cp.spawnSync(executable, ['-c', 'import sys; raise SystemExit(0 if sys.version_info.major == 3 else 1)'], {
        stdio: 'ignore', windowsHide: true, timeout: 5000,
      });
    } catch (error) {
      return {status: null, signal: null, error: {code: error.code}};
    }
  };
  const usable = result => !result.error && !result.signal && result.status === 0;
  if (process.env.DEMO_PYTHON) {
    const result = probe(process.env.DEMO_PYTHON);
    if (!usable(result)) throw new Error('DEMO_PYTHON is not a usable Python 3 executable: ' + safeSpawnDiagnostic(result));
    return process.env.DEMO_PYTHON;
  }
  const venvPython = path.join(root, '.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python');
  const candidates = [
    ...(fs.existsSync(venvPython) ? [{name: 'virtualenv', executable: venvPython}] : []),
    ...(process.platform === 'win32' ? ['python', 'python3'] : ['python3', 'python']).map(executable => ({name: executable, executable})),
  ];
  const failures = [];
  for (const candidate of candidates) {
    const result = probe(candidate.executable);
    if (usable(result)) return candidate.executable;
    failures.push(candidate.name + ': ' + safeSpawnDiagnostic(result));
  }
  throw new Error('No usable Python 3 executable: ' + failures.join('; '));
}

function createSyntheticPdf() {
  const content = 'BT /F1 12 Tf 72 720 Td (Synthetic CSP browser fixture.) Tj ET\n';
  const objects = [
    '<< /Type /Catalog /Pages 2 0 R >>',
    '<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
    '<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>',
    '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
    '<< /Length ' + Buffer.byteLength(content, 'ascii') + ' >>\nstream\n' + content + 'endstream',
  ];
  let pdf = '%PDF-1.4\n';
  const offsets = [0];
  for (const [index, object] of objects.entries()) {
    offsets.push(Buffer.byteLength(pdf, 'ascii'));
    pdf += (index + 1) + ' 0 obj\n' + object + '\nendobj\n';
  }
  const xrefOffset = Buffer.byteLength(pdf, 'ascii');
  pdf += 'xref\n0 ' + (objects.length + 1) + '\n0000000000 65535 f \n';
  for (const offset of offsets.slice(1)) pdf += String(offset).padStart(10, '0') + ' 00000 n \n';
  pdf += 'trailer\n<< /Size ' + (objects.length + 1) + ' /Root 1 0 R >>\nstartxref\n' + xrefOffset + '\n%%EOF\n';
  return Buffer.from(pdf, 'ascii');
}

const python = selectPython();
const generated=cp.spawnSync(python,['-c',`import json\nfrom urllib.parse import urlsplit\nfrom scripts.verify_review_artifact import yaml_parse\nfrom policy_assistant.app import _s3\nfrom pathlib import Path\nt=yaml_parse(Path('template.yaml').read_text(encoding='utf-8'))\nr=next(v for v in t['Resources'].values() if v['Type']=='AWS::CloudFront::ResponseHeadersPolicy')\nc=r['Properties']['ResponseHeadersPolicyConfig']['SecurityHeadersConfig']['ContentSecurityPolicy']['ContentSecurityPolicy']['Fn::Sub'].replace('\u0024{AWS::Region}','ap-southeast-1').replace('\u0024{AWS::URLSuffix}','amazonaws.com')\ns=_s3()\np=s.generate_presigned_post(Bucket='fcaj-local-fixture',Key='uploads/doc-csp-fixture/document')\ng=s.generate_presigned_url('get_object',Params={'Bucket':'fcaj-local-fixture','Key':'uploads/doc-csp-fixture/document','VersionId':'fixture-version'})\nprint(json.dumps({'csp':c,'post_host':urlsplit(p['url']).hostname,'get_host':urlsplit(g).hostname}))`],{cwd:root,encoding:'utf8',env:{...process.env,AWS_ACCESS_KEY_ID:'LOCALFIXTURE',AWS_SECRET_ACCESS_KEY:'LOCALFIXTURE',AWS_SESSION_TOKEN:'LOCALFIXTURE',AWS_REGION:'ap-southeast-1',AWS_DEFAULT_REGION:'ap-southeast-1',AWS_EC2_METADATA_DISABLED:'true'}});
if (generated.error || generated.signal || generated.status !== 0) {
  throw new Error('Local CSP/signer fixture export failed: ' + safeSpawnDiagnostic(generated));
}
const fixture=JSON.parse(generated.stdout);const PDF=createSyntheticPdf();const SHA=crypto.createHash('sha256').update(PDF).digest('hex');
const evidence={scope:'LOCAL Edge + mocked API/S3; CSP from source IaC, no AWS requests/credentials',csp:fixture.csp,actual_helper_post_host:fixture.post_host,actual_helper_get_host:fixture.get_host,cases:{}};
for(const scenario of ['legacy-global','actual-helper']){
 test('CSP regional contract: '+scenario,async()=>{
  const postHost=scenario==='legacy-global'?'fcaj-local-fixture.s3.amazonaws.com':fixture.post_host;const getHost=scenario==='legacy-global'?'fcaj-local-fixture.s3.amazonaws.com':fixture.get_host;let browser,server;let posts=0,gets=0,unmocked=0;let record={status:'RUNNING',post_host:postHost,get_host:getHost};
  try{
   server=http.createServer((req,res)=>{const key=req.url.split('?')[0];const files={'/':'index.html','/app.js':'app.js','/styles.css':'styles.css'};if(key==='/config.json'){res.setHeader('Content-Type','application/json');res.end(JSON.stringify({mode:'aws',apiBase:'https://fixture-api.execute-api.ap-southeast-1.amazonaws.com/Prod',region:'ap-southeast-1',clientId:'fixtureclient'}));return;}if(!files[key]){res.writeHead(404);res.end();return;}res.setHeader('Content-Security-Policy',fixture.csp);res.setHeader('Content-Type',key.endsWith('.js')?'application/javascript':key.endsWith('.css')?'text/css':'text/html; charset=utf-8');res.end(fs.readFileSync(path.join(root,'frontend',files[key])));});await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));const origin='http://127.0.0.1:'+server.address().port;
   browser=await chromium.launch(process.platform==='win32'?{channel:'msedge',headless:true}:{headless:true});record.browser_version=browser.version();const context=await browser.newContext({acceptDownloads:true});const page=await context.newPage();
   await context.addInitScript(()=>{window.cspEvents=[];document.addEventListener('securitypolicyviolation',event=>{let blocked;try{blocked=new URL(event.blockedURI).hostname;}catch{blocked=event.blockedURI;}window.cspEvents.push({effective_directive:event.effectiveDirective,violated_directive:event.violatedDirective,blocked_host:blocked,disposition:event.disposition});});});
   await context.route('**/*',async route=>{const req=route.request();const url=new URL(req.url());if(url.hostname==='127.0.0.1')return route.continue();const headers={'access-control-allow-origin':origin,'access-control-allow-headers':'authorization,content-type','access-control-allow-methods':'GET,POST,OPTIONS'};if(url.hostname==='fixture-api.execute-api.ap-southeast-1.amazonaws.com'){if(req.method()==='OPTIONS')return route.fulfill({status:204,headers});let body;if(url.pathname.endsWith('/upload-session'))body={doc_id:'doc-csp-fixture',s3_key:'uploads/doc-csp-fixture/document',upload_url:'https://'+postHost+'/',upload_method:'POST',upload_fields:{key:'uploads/doc-csp-fixture/document','Content-Type':'application/pdf',success_action_status:'201'},max_bytes:10485760};else if(url.pathname.endsWith('/submit'))body={status:'pending'};else if(url.pathname.endsWith('/status'))body={doc_id:'doc-csp-fixture',status:'processed',sha256:SHA};else if(url.pathname.endsWith('/download'))body={download_url:'https://'+getHost+'/uploads/doc-csp-fixture/document',sha256:SHA};else body={policies:[],count:0,documents:[]};return route.fulfill({status:200,headers,contentType:'application/json',body:JSON.stringify(body)});}if([postHost,getHost].includes(url.hostname)){if(req.method()==='OPTIONS')return route.fulfill({status:204,headers});if(req.method()==='POST'){posts++;assert.equal(req.headers().authorization,undefined);assert.ok(req.postDataBuffer().includes(PDF));return route.fulfill({status:201,headers});}if(req.method()==='GET'){gets++;return route.fulfill({status:200,headers,contentType:'application/pdf',body:PDF});}}unmocked++;return route.abort();});
   await page.goto(origin);await page.locator('summary').click();await page.locator('#jwt-input').fill('fixture.token.only');await page.locator('#connect').click();assert.equal(await page.locator('#auth-status').getAttribute('data-state'),'ok');await page.locator('#file-input').setInputFiles({name:'synthetic.pdf',mimeType:'application/pdf',buffer:PDF});await page.locator('#upload').click();await page.waitForFunction(()=>['ok','error'].includes(document.getElementById('upload-result').dataset.state));await page.waitForTimeout(100);
   record.ui_state=await page.locator('#upload-result').getAttribute('data-state');record.ui_message=await page.locator('#upload-result').innerText();record.auth_state=await page.locator('#auth-status').getAttribute('data-state');record.api_base=await page.locator('#api-base').inputValue();record.csp_violations=await page.evaluate(()=>window.cspEvents);record.s3_post_requests=posts;record.s3_get_requests=gets;record.unmocked_external_requests=unmocked;
   if(scenario==='legacy-global'){assert.equal(record.ui_state,'error');assert.equal(posts,0);assert.ok(record.csp_violations.some(v=>v.effective_directive==='connect-src'&&v.blocked_host===postHost));}
   else{assert.equal(record.ui_state,'ok');assert.equal(posts,1);assert.equal(gets,1);assert.equal(record.csp_violations.length,0);assert.match(await page.locator('#upload-result').innerText(),new RegExp(SHA));assert.equal(postHost,'fcaj-local-fixture.s3.ap-southeast-1.amazonaws.com');assert.equal(getHost,postHost);}
   assert.equal(unmocked,0);record.status='PASS';
  }catch(error){record.status='FAIL';record.error_type=error.name;throw error;}
  finally{if(browser)await browser.close();if(server)await new Promise(resolve=>server.close(resolve));evidence.cases[scenario]=record;fs.mkdirSync(path.join(root,'docs/evidence'),{recursive:true});fs.writeFileSync(path.join(root,'docs/evidence/b5r-local-csp-browser.json'),JSON.stringify(evidence,null,2)+'\n');}
 });
}
