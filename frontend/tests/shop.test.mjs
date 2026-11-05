import{test}from'node:test';
import assert from'node:assert/strict';
import{ShopEditor,shopDraft}from'../src/shop-editor.js';
const fields={shop_name:'DEMO',support_email:'',support_phone:'',support_hours:'',returns_instructions:'',support_message:'',mode:'demo'};
const blank={revision:null,current:null,draft:null};

test('shop draft shares only supported fields and rejects invalid lengths/modes',()=>{
 assert.deepEqual(shopDraft({...fields,shop_name:' DEMO ',document_ids:['private']}),fields);
 assert.throws(()=>shopDraft({...fields,shop_name:'x'.repeat(101)}));assert.throws(()=>shopDraft({...fields,mode:'unknown'}));
});
test('shop creation loads the shared revision and saves only a draft',async()=>{
 const calls=[];const editor=new ShopEditor(async(path,options)=>{calls.push({path,options});return options?{...blank,revision:'v1',draft:fields}:blank;});
 assert.throws(()=>editor.save(fields));await editor.load();editor.markDirty();await editor.save(fields);
 assert.equal(calls[1].path,'/admin/shop');assert.equal(calls[1].options.body.action,'save_draft');assert.equal(calls[1].options.body.expected_revision,null);assert.equal(editor.dirty,false);
});
test('shop publication needs a saved draft, no dirty edits and exact confirmation',async()=>{
 const calls=[];const editor=new ShopEditor(async(path,options)=>{calls.push(options);return{revision:'v1',current:null,draft:fields};});await editor.load();
 assert.throws(()=>editor.act('publish'));editor.markDirty();assert.throws(()=>editor.act('publish',true));await editor.save(fields);await editor.act('publish',true);
 assert.deepEqual(calls.at(-1).body,{action:'publish',expected_revision:'v1',confirmed:true});
});
test('shop conflicts retain the unsent draft and opened revision',async()=>{
 let fail=false;const editor=new ShopEditor(async()=>{if(fail)throw Object.assign(new Error('Conflict'),{status:409});return{revision:'v1',current:null,draft:fields};});await editor.load();editor.markDirty();fail=true;await assert.rejects(editor.save({...fields,shop_name:'Unsent'}));assert.equal(editor.dirty,true);assert.equal(editor.record.revision,'v1');
});
test('shop clear prevents a late response restoring administrator data',async()=>{
 let finish;const editor=new ShopEditor(()=>new Promise(resolve=>finish=resolve));const pending=editor.load();editor.clear();finish({revision:'v1',current:null,draft:fields});await assert.rejects(pending);assert.equal(editor.loaded,false);assert.equal(editor.record,null);
});
