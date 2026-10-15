import { readFile, writeFile, mkdir } from 'node:fs/promises';
import path from 'node:path';

const root=path.resolve(import.meta.dirname,'..','..');
const rows=[];
const documents=[];
const skills=['listening','reading','writing','speaking'];
const read=async relative=>JSON.parse(await readFile(path.join(root,relative),'utf8'));

function walk(node,location,meta){
 if(!node||typeof node!=='object')return;
 if(Array.isArray(node.needsReview))for(let index=0;index<node.needsReview.length;index++){
  const item=node.needsReview[index];
  rows.push({...meta,location:`${location}/needsReview/${index}`,question:item?.question??node.number??node.numbers?.join('-')??'',type:typeof item==='string'?item:item?.type??'',message:typeof item==='string'?item:item?.message??'',pdfPage:item?.sourcePdfPage??node.source?.pdfPage??'',detail:JSON.stringify(item)});
 }
 for(const [key,value] of Object.entries(node))if(key!=='needsReview'&&value&&typeof value==='object'){
  if(Array.isArray(value))value.forEach((child,index)=>walk(child,`${location}/${key}/${index}`,meta));
  else walk(value,`${location}/${key}`,meta);
 }
}

for(let book=4;book<=20;book++)for(let test=1;test<=4;test++)for(const skill of skills){
 const file=`resources/cambridge/c${book}/test-${test}/${skill}.json`;
 let data;try{data=await read(file);}catch(error){if(error.code==='ENOENT')continue;throw error;}
 const before=rows.length;
 walk(data,'',{book,test,skill,file});
 documents.push({book,test,skill,file,status:data.status??'',verified:data.verified===true,reviewItems:rows.length-before});
}
for(let book=4;book<=20;book++){
 const file=`resources/page-maps/cambridge-${String(book).padStart(2,'0')}.json`;
 try{walk(await read(file),'',{book,test:'',skill:'page-map',file});}catch(error){if(error.code!=='ENOENT')throw error;}
}
const synonymFile='resources/synonyms/review-queue.json';
try{
 const data=await read(synonymFile);
 for(const [index,item] of (data.items??[]).entries())walk(item,`/items/${index}`,{book:'',test:'',skill:'vocabulary',file:synonymFile,word:item.word??''});
}catch(error){if(error.code!=='ENOENT')throw error;}

const output=path.join(root,'artifacts');await mkdir(output,{recursive:true});
const columns=['book','test','skill','file','location','question','word','type','message','pdfPage','detail'];
const quote=value=>`"${String(value??'').replaceAll('"','""').replaceAll(/\r?\n/g,' ')}"`;
const csv='\uFEFF'+[columns.join(','),...rows.map(row=>columns.map(column=>quote(row[column])).join(','))].join('\r\n')+'\r\n';
await writeFile(path.join(output,'pending-review-items.csv'),csv,'utf8');
const summary={generatedAt:new Date().toISOString(),reviewItems:rows.length,documents:documents.length,documentsPending:documents.filter(item=>!item.verified).length,bySkill:Object.fromEntries([...new Set(rows.map(row=>row.skill))].map(skill=>[skill,rows.filter(row=>row.skill===skill).length])),documentsByBook:documents.reduce((acc,item)=>{const key=`C${item.book}`;acc[key]??={files:0,reviewItems:0};acc[key].files++;acc[key].reviewItems+=item.reviewItems;return acc;},{})};
await writeFile(path.join(output,'pending-review-summary.json'),JSON.stringify(summary,null,2)+'\n','utf8');
console.log(JSON.stringify({csv:'artifacts/pending-review-items.csv',summary:'artifacts/pending-review-summary.json',reviewItems:summary.reviewItems,documentsPending:summary.documentsPending,bySkill:summary.bySkill}));
