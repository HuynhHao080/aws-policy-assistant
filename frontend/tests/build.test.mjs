import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFile,access} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
test('production HTML references fingerprinted assets and never ships local QA authentication',async()=>{
  const html=await readFile(path.join(root,'dist/index.html'),'utf8');
  const assets=[...html.matchAll(/(?:src|href)="\.\/(assets\/[^" ]+\.(?:js|css))"/g)].map(match=>match[1]);
  assert.equal(assets.length,2);
  for(const name of assets){assert.match(name,/^assets\/app-[A-Z0-9]{8}\.(?:js|css)$/);await access(path.join(root,'dist',name));}
  for(const page of ['privacy.html','terms.html']){const text=await readFile(path.join(root,'dist',page),'utf8');const css=text.match(/href="\.\/(assets\/app-[A-Z0-9]{8}\.css)"/);assert.ok(css);await access(path.join(root,'dist',css[1]));}
  const js=await readFile(path.join(root,'dist',assets.find(name=>name.endsWith('.js'))),'utf8');
  assert.equal(js.includes('unit-fixture-not-a-jwt'),false);assert.equal(js.includes('local-fixture-not-a-jwt'),false);assert.equal(js.includes('admin@local-fixture.invalid'),false);
});
