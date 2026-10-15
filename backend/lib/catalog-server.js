import { readFile, stat } from 'node:fs/promises';
import path from 'node:path';
const skills=['listening','reading','writing','speaking'];
export async function buildCatalog(root){
  const entries=[];
  const exists=async file=>{try{const rel=path.relative(root,file);if(rel.startsWith('..')||path.isAbsolute(rel))return false;const s=await stat(file);return s.isFile()&&s.size>0;}catch{return false;}};
  for(let book=4;book<=20;book++)for(let test=1;test<=4;test++){
    await Promise.all(skills.map(async skill=>{
      const directory=path.join(root,`resources/cambridge/c${book}/test-${test}`);
      const entry={book,test,skill,status:'not-imported',available:false,issues:[]};
      if(book===12){entry.status='missing-resource';entry.issues.push('按要求暂留空，等待可靠原卷');entries.push(entry);return;}
      let data;
      try{data=JSON.parse(await readFile(path.join(directory,skill+'.json'),'utf8'));}
      catch(error){if(error.code!=='ENOENT'){entry.status='needs-review';entry.issues.push('文件正在写入或 JSON 格式无效');}entries.push(entry);return;}
      try{
        if(data.schemaVersion!==1||data.book!==book||data.test!==test||data.skill!==skill)throw new Error('数据身份或版本不匹配');
        const sections=skill==='reading'?data.passages:skill==='writing'?data.tasks:data.parts;
        if(!Array.isArray(sections)||!sections.length)throw new Error('缺少可展示的题目内容');
        let reviews=0,missing=false;
        const visit=async node=>{
          if(!node||typeof node!=='object')return;
          if(Array.isArray(node.needsReview))reviews+=node.needsReview.length;
          if(typeof node.asset==='string'){
            if(!/^\.\/assets\/[\w.-]+$/.test(node.asset)||!await exists(path.resolve(directory,node.asset))){missing=true;entry.issues.push('题目图片缺失');}
          }
          for(const value of Object.values(node))if(value&&typeof value==='object')await visit(value);
        };
        await visit(data);
        const incomplete=(message)=>{reviews++;entry.issues.push(message);};
        if(skill==='reading'){
          const qs=sections.flatMap(p=>(p.groups||[]).flatMap(g=>g.questions||[]));
          if(sections.length!==3||qs.length!==40||new Set(qs.map(q=>q.number)).size!==40)throw new Error('阅读文章或题号尚不完整');
          for(const passage of sections)for(const group of passage.groups||[]){
            if((group.questions||[]).some(q=>!q.prompt)&&!(group.context||group.instruction||group.asset))
              throw new Error('阅读题目缺少题干及题组上下文');
          }
          for(let i=0;i<sections.length;i++){
            const p=sections[i];
            const blocks=Array.isArray(p?.blocks)?p.blocks:[];
            const text=blocks.map(b=>b.text||'').join(' ').trim();
            const words=text?text.split(/\s+/).filter(Boolean).length:0;
            if(blocks.length===0||words<100)throw new Error(`阅读第 ${i+1} 篇正文缺失或不完整`);
          }
        }
        if(skill==='writing'&&(!sections.some(p=>p.number===1)||!sections.some(p=>p.number===2)))incomplete('写作任务尚不完整');
        if(skill==='speaking'&&[1,2,3].some(n=>!sections.some(p=>p.part===n)))incomplete('口语 Part 尚不完整');
        if(skill==='listening'){
          const numbers=new Set(sections.flatMap(p=>(p.questions||[]).flatMap(q=>q.numbers||[q.number])));
          if(numbers.size!==40||Array.from({length:40},(_,i)=>i+1).some(n=>!numbers.has(n)))throw new Error('听力计分点尚不完整');
          for(let part=1;part<=4;part++){
            const file=data.audio?.[part]?.path;
            if(!file||!file.startsWith('IELTS/')||!await exists(path.resolve(root,file))){missing=true;entry.issues.push(`Part ${part} 音频缺失`);}
          }
          try{const transcript=JSON.parse(await readFile(path.join(directory,'audioscript.json'),'utf8'));if(!Array.isArray(transcript.parts))throw new Error();}
          catch{missing=true;entry.issues.push('听力稿缺失或无法读取');}
          const transcriptPages=new Set(Array.isArray(data.sources?.transcriptPdfPages)?data.sources.transcriptPdfPages:[]);
          const qs=sections.flatMap(p=>p.questions||[]);
          for(const q of qs){
            const te=q.transcriptEvidence;
            if(te&&te.sourcePdfPage!=null){
              if(typeof te.sourcePdfPage!=='number'||te.sourcePdfPage<1||(transcriptPages.size>0&&!transcriptPages.has(te.sourcePdfPage))){
                throw new Error(`听力题 Q${q.number} 证据页码 ${te.sourcePdfPage} 超出录音稿范围`);
              }
            }
          }
        }
        entry.reviewCount=reviews;
        entry.status=missing||data.status==='missing-resource'?'missing-resource':data.verified===true&&reviews===0&&data.status!=='needs-review'?'ready':'needs-review';
        entry.available=entry.status!=='missing-resource';
        entry.href=skill==='listening'?`/import-preview.html?book=${book}&test=${test}`:`/practice.html?book=${book}&test=${test}&skill=${skill}`;
      }catch(error){entry.status='needs-review';entry.available=false;entry.issues.push(error.message);}
      entries.push(entry);
    }));
  }
  return {schemaVersion:1,generatedAt:new Date().toISOString(),entries:entries.sort((a,b)=>b.book-a.book||a.test-b.test||skills.indexOf(a.skill)-skills.indexOf(b.skill))};
}
