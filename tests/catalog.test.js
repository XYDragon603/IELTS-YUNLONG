import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, mkdir, writeFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { buildCatalog } from '../lib/catalog-server.js';
test('catalog discovers new imports and refuses missing assets and invalid JSON',async()=>{
 const root=await mkdtemp(path.join(tmpdir(),'ielts-catalog-'));
 try{
  const dir=path.join(root,'resources/cambridge/c18/test-2');await mkdir(dir,{recursive:true});
  const find=c=>c.entries.find(e=>e.book===18&&e.test===2&&e.skill==='writing');
  assert.equal(find(await buildCatalog(root)).status,'not-imported');
  const data={schemaVersion:1,book:18,test:2,skill:'writing',verified:true,status:'ready',tasks:[{number:1,prompt:'Write',assets:[]}],needsReview:[]};
  await writeFile(path.join(dir,'writing.json'),JSON.stringify(data));
  assert.equal(find(await buildCatalog(root)).available,true);
  data.needsReview=[{type:'unconfirmed'}];await writeFile(path.join(dir,'writing.json'),JSON.stringify(data));
  assert.equal(find(await buildCatalog(root)).status,'needs-review');
  data.tasks[0].assets=[{asset:'./assets/missing.png'}];await writeFile(path.join(dir,'writing.json'),JSON.stringify(data));
  assert.equal(find(await buildCatalog(root)).status,'missing-resource');
  assert.equal(find(await buildCatalog(root)).available,false);
  await writeFile(path.join(dir,'writing.json'),'{partial');
  assert.equal(find(await buildCatalog(root)).available,false);
 }finally{const relative=path.relative(path.resolve(tmpdir()),path.resolve(root));assert.ok(relative&&!relative.startsWith('..')&&!path.isAbsolute(relative));await rm(root,{recursive:true,force:true});}
});

test('catalog refuses reading with empty blocks or short text and listening with invalid transcript pages',async()=>{
 const root=await mkdtemp(path.join(tmpdir(),'ielts-catalog-guards-'));
 try{
  const dir=path.join(root,'resources/cambridge/c18/test-1');await mkdir(dir,{recursive:true});
  const findR=c=>c.entries.find(e=>e.book===18&&e.test===1&&e.skill==='reading');
  const findL=c=>c.entries.find(e=>e.book===18&&e.test===1&&e.skill==='listening');

  const validQs=Array.from({length:40},(_,i)=>({id:`q${i+1}`,number:i+1,type:'text',prompt:`Question ${i+1}`}));
  const rData={
    schemaVersion:1,book:18,test:1,skill:'reading',verified:false,status:'needs-review',
    passages:[
      {title:'P1',blocks:[{text:'Valid long text '.repeat(30)}],groups:[{questions:validQs.slice(0,14)}]},
      {title:'P2',blocks:[],groups:[{questions:validQs.slice(14,27)}]},
      {title:'P3',blocks:[{text:'Valid long text '.repeat(30)}],groups:[{questions:validQs.slice(27,40)}]}
    ],
    needsReview:[]
  };
  await writeFile(path.join(dir,'reading.json'),JSON.stringify(rData));
  const catR1=findR(await buildCatalog(root));
  assert.equal(catR1.available,false);
  assert.ok(catR1.issues.some(i=>i.includes('正文缺失或不完整')));

  rData.passages[1].blocks=[{text:'Too short only five words'}];
  await writeFile(path.join(dir,'reading.json'),JSON.stringify(rData));
  const catR2=findR(await buildCatalog(root));
  assert.equal(catR2.available,false);
  assert.ok(catR2.issues.some(i=>i.includes('正文缺失或不完整')));

  rData.passages[1].blocks=[{text:'Valid passage text '.repeat(50)}];
  rData.passages[1].groups[0].questions[0].prompt=null;
  await writeFile(path.join(dir,'reading.json'),JSON.stringify(rData));
  const catR3=findR(await buildCatalog(root));
  assert.equal(catR3.available,false);
  assert.ok(catR3.issues.some(i=>i.includes('缺少题干及题组上下文')));

  const lQs=Array.from({length:40},(_,i)=>({
    id:`q${i+1}`,number:i+1,type:'text',
    transcriptEvidence:{segmentIds:['s1'],sourcePdfPage:999}
  }));
  const lData={
    schemaVersion:1,book:18,test:1,skill:'listening',verified:false,status:'needs-review',
    parts:[
      {part:1,questions:lQs.slice(0,10)},
      {part:2,questions:lQs.slice(10,20)},
      {part:3,questions:lQs.slice(20,30)},
      {part:4,questions:lQs.slice(30,40)}
    ],
    sources:{transcriptPdfPages:[103,104,105,106,107]},
    needsReview:[]
  };
  await writeFile(path.join(dir,'listening.json'),JSON.stringify(lData));
  const catL=findL(await buildCatalog(root));
  assert.equal(catL.available,false);
  assert.ok(catL.issues.some(i=>i.includes('超出录音稿范围')));
 }finally{await rm(root,{recursive:true,force:true});}
});
