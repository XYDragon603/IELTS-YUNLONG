import {personalBook} from './personal-words.js';
const object=v=>v!==null&&typeof v==='object'&&!Array.isArray(v);
const idPattern=/^[a-f0-9]{20}$/;
export function parseWordBackup(text){
 if(text.length>8*1024*1024)throw Error('文件过大，请选择本站导出的进度 JSON。');
 const data=JSON.parse(text);
 if(!object(data)||data.version!==1||!object(data.progress))throw Error('不是支持的词汇进度备份。');
 if(!Number.isInteger(data.limit)||data.limit<1||data.limit>1000||typeof data.random!=='boolean')throw Error('备份中的学习设置无效。');
 const progress={};
 for(const [id,p] of Object.entries(data.progress)){
  if(!idPattern.test(id)||!object(p))throw Error('备份含无效单词记录。');
  const clean={};
  for(const field of ['stage','due','reviews','lastReviewed','mistakes','lastMistake'])if(p[field]!==undefined){if(!Number.isSafeInteger(p[field])||p[field]<0||(field==='stage'&&p[field]>6))throw Error('备份含无效学习数值。');clean[field]=p[field];}
  for(const field of ['starred','needsPractice'])if(p[field]!==undefined){if(typeof p[field]!=='boolean')throw Error('备份含无效标记。');clean[field]=p[field];}
  if(p.rating!==undefined){if(!['again','hard','known'].includes(p.rating))throw Error('备份含无效评级。');clean.rating=p.rating;}
  progress[id]=clean;
 }
 let session=null;
 if(data.session!==null&&data.session!==undefined){
  const s=data.session;
  if(!object(s)||typeof s.book!=='string'||!(s.book==='personal'||/^ielts-[\w-]+$/.test(s.book))||!Array.isArray(s.ids)||s.ids.length>1000||!s.ids.every(id=>typeof id==='string'&&idPattern.test(id))||new Set(s.ids).size!==s.ids.length||!Number.isInteger(s.index)||s.index<0||s.index>s.ids.length)throw Error('备份中的学习队列无效。');
  if(s.mode!==undefined&&!['learn','spell','dictation'].includes(s.mode))throw Error('备份中的学习模式无效。');
  session={book:s.book,ids:s.ids,index:s.index,mode:s.mode||'learn',review:s.review===true,completed:s.completed===true};
 }
 return {version:1,progress,limit:data.limit,random:data.random,session};
}
export function replaceWordBackup(storage,key,next){
 const previous=storage.getItem(key);
 // Do not replace current data unless the rollback copy was saved successfully.
 if(previous!==null)storage.setItem(key+'-before-import',previous);
 storage.setItem(key,JSON.stringify(next));
}
export function downloadBackup(text,name){const url=URL.createObjectURL(new Blob([text],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
export async function chooseWordBackup({key,manifest,onImported,message}){
 const input=document.createElement('input');input.type='file';input.accept='.json,application/json';
 input.onchange=async()=>{try{
  const file=input.files[0];if(!file)return;if(file.size>8*1024*1024)throw Error('备份文件不能超过 8 MB。');
  const next=parseWordBackup(await file.text());
  if(next.session){const entry=manifest.books.find(b=>b.id===next.session.book);if(!entry)throw Error('备份队列的词书尚未安装。');const response=next.session.book==='personal'?{ok:true,json:async()=>personalBook()}:await fetch('/resources/words/'+entry.path);if(!response.ok)throw Error('无法核对备份词书。');const book=await response.json();const ids=new Set(book.words.map(w=>w.id));if(!next.session.ids.every(id=>ids.has(id)))throw Error('队列词条与当前词书不匹配，请保留原备份。');}
  const values=Object.values(next.progress),dialog=document.createElement('dialog');
  dialog.innerHTML='<h2>恢复学习进度</h2><p id="backup-summary"></p><p>将替换当前词汇进度、收藏和学习队列。当前记录会另存为导入前备份，不影响模考记录。</p><form method="dialog" class="word-actions"><button class="btn" value="cancel">取消</button><button class="btn primary" value="restore">备份当前并恢复</button></form>';
  dialog.querySelector('#backup-summary').textContent=`共 ${values.length} 条记录，${values.filter(p=>p.starred).length} 个收藏，${values.filter(p=>p.needsPractice).length} 个错词。`;
  document.body.append(dialog);dialog.showModal();dialog.addEventListener('close',async()=>{const restore=dialog.returnValue==='restore';dialog.remove();if(!restore)return;try{replaceWordBackup(localStorage,key,next);await onImported(next);message('进度已恢复。原记录可通过“导入前备份”下载。');}catch(e){message('恢复失败：'+e.message);}},{once:true});
 }catch(e){message('无法导入：'+e.message);}};input.click();
}
