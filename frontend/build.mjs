import { build } from 'esbuild';
import { mkdir, copyFile, readFile, writeFile, rm, access } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const root=path.dirname(fileURLToPath(import.meta.url));
const assets=path.resolve(root,'dist/assets');
await mkdir(assets,{recursive:true});
// Never upload a changed fixed-name bundle over one referenced by the previous HTML.
// Remove only these two generated local files; old hosted assets remain available.
for(const name of ['app.js','app.css']){
  const target=path.resolve(assets,name);
  if(path.dirname(target)!==assets)throw new Error('Unexpected generated asset path');
  await rm(target,{force:true});
}
const result=await build({absWorkingDir:root,entryPoints:['src/main.js'],bundle:true,outdir:'dist/assets',entryNames:'app-[hash]',format:'esm',minify:true,sourcemap:false,metafile:true,target:['es2022'],legalComments:'eof',loader:{'.woff2':'file','.ttf':'file'}});
const entry=Object.entries(result.metafile.outputs).find(([name,meta])=>name.endsWith('.js')&&meta.entryPoint==='src/main.js');
if(!entry||!entry[1].cssBundle)throw new Error('Missing entry bundle or stylesheet');
const script=path.basename(entry[0]),style=path.basename(entry[1].cssBundle);
let html=await readFile(path.join(root,'index.html'),'utf8');
if(!html.includes('./assets/app.js')||!html.includes('./assets/app.css'))throw new Error('Unexpected source entry document');
html=html.replace('./assets/app.js','./assets/'+script).replace('./assets/app.css','./assets/'+style);
await writeFile(path.join(root,'dist/index.html'),html);
for(const file of ['privacy.html','terms.html']){const page=await readFile(path.join(root,file),'utf8');await writeFile(path.join(root,'dist',file),page.replace('./assets/app.css','./assets/'+style));}
await copyFile(path.join(root,'src/fonts/OFL.txt'),path.join(assets,'OFL.txt'));
await copyFile(path.join(root,'src/fonts/noto-sans-OFL.txt'),path.join(assets,'noto-sans-OFL.txt'));
try{await copyFile(path.join(root,'config.json'),path.join(root,'dist/config.json'));}
catch{await copyFile(path.join(root,'config.example.json'),path.join(root,'dist/config.json'));}
for(const name of [script,style])await access(path.join(assets,name));
const js=await readFile(path.join(assets,script),'utf8');
if(js.includes('local-fixture-not-a-jwt')||js.includes('admin@local-fixture.invalid'))throw new Error('Local QA authentication must never enter a production build');
console.log('Frontend build ready with content-fingerprinted assets:',script,style);
