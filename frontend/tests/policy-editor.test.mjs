import {test} from 'node:test';
import assert from 'node:assert/strict';
import {PolicyEditor,draftPayload} from '../src/policy-editor.js';
const fields={title:'Refund',category:'Support',content:'DEMO only',keywords:['refund']};
const record=(overrides={})=>({policy_id:'POL-1',revision:'revision-1',publication_state:'published',current:fields,draft:null,...overrides});

test('draft payload only contains supported fields, trims text and parses keywords',()=>{
  assert.deepEqual(draftPayload({...fields,title:' Refund ',keywords:' refund, , warranty ',action:'publish'}),{...fields,keywords:['refund','warranty']});
  for(const raw of [{...fields,content:''},{...fields,title:'x'.repeat(181)},{...fields,keywords:Array(31).fill('x')},{...fields,keywords:['x'.repeat(81)]}])assert.throws(()=>draftPayload(raw));
});

test('new policy saves only a draft with an explicit absent revision',async()=>{
  const calls=[];const editor=new PolicyEditor(async(path,options)=>{calls.push({path,options});return record({publication_state:'draft',current:null,draft:fields});});
  await editor.save('POL-1',fields);
  assert.equal(calls[0].options.method,'PATCH');assert.equal(calls[0].options.body.action,'save_draft');assert.equal(calls[0].options.body.expected_revision,null);
  assert.equal(editor.record.publication_state,'draft');assert.equal(editor.dirty,false);
});

test('editing preserves the loaded revision and never publishes automatically',async()=>{
  const calls=[];const editor=new PolicyEditor(async(path,options)=>{calls.push({path,options});return record(options?{revision:'revision-2',draft:fields}:{});});
  await editor.open('POL-1');editor.markDirty();await editor.save('POL-1',fields);
  assert.equal(calls[1].options.body.expected_revision,'revision-1');assert.equal(calls[1].options.body.action,'save_draft');assert.equal(editor.record.revision,'revision-2');
  assert.throws(()=>editor.save('OTHER',fields));
});

test('publication, archive and discard require saved edits and use the loaded revision',async()=>{
  const calls=[];const editor=new PolicyEditor(async(path,options)=>{calls.push({path,options});return record({draft:fields});});
  await editor.open('POL-1');editor.markDirty();assert.throws(()=>editor.transition('publish'));assert.equal(calls.length,1);
  await editor.save('POL-1',fields);await editor.transition('publish');
  assert.deepEqual(calls[2].options.body,{action:'publish',expected_revision:'revision-1'});
  assert.throws(()=>editor.transition('delete_account'));
});

test('a conflict retains the opened revision and unsaved editor state',async()=>{
  let writes=false;const conflict=Object.assign(new Error('Conflict'),{status:409});
  const editor=new PolicyEditor(async()=>{if(writes)throw conflict;return record();});
  await editor.open('POL-1');editor.markDirty();writes=true;
  await assert.rejects(editor.save('POL-1',fields),error=>error.status===409);
  assert.equal(editor.record.revision,'revision-1');assert.equal(editor.dirty,true);assert.equal(editor.busy,false);
});

test('clearing a session prevents a late response from restoring administrator data',async()=>{
  let finish;const editor=new PolicyEditor(()=>new Promise(resolve=>{finish=resolve;}));
  const pending=editor.open('POL-1');assert.equal(editor.busy,true);editor.clear();finish(record({draft:fields}));
  await assert.rejects(pending);assert.equal(editor.record,null);assert.equal(editor.busy,false);assert.equal(editor.dirty,false);
});

test('in-flight save cannot be replaced by another selection or reset',async()=>{
  let finish;const editor=new PolicyEditor(()=>new Promise(resolve=>{finish=resolve;}));
  const pending=editor.open('POL-1');assert.throws(()=>editor.newPolicy());await assert.rejects(editor.open('POL-2'));
  finish(record());await pending;assert.equal(editor.record.policy_id,'POL-1');
});

test('malformed readback never replaces the editor snapshot',async()=>{
  const editor=new PolicyEditor(async()=>({policy_id:'OTHER',revision:'unexpected'}));
  await assert.rejects(editor.open('POL-1'));assert.equal(editor.record,null);assert.equal(editor.busy,false);
});
