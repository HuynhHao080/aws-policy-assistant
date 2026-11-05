const {test}=require('node:test');
const {execFileSync}=require('node:child_process');
const path=require('node:path');
test('public frontend API and upload contracts',()=>{execFileSync(process.execPath,['--test',path.join(__dirname,'../../frontend/tests/api.test.mjs')],{stdio:'pipe'});});
