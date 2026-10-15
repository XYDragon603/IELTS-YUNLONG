import { normalizeAnswer } from '../core.js';
export function practiceRemaining(state,now=Date.now()){return state.deadline ? Math.max(0,Math.ceil((state.deadline-now)/1000)) : state.remaining;}
export function pausePractice(state,now=Date.now()){state.remaining=practiceRemaining(state,now);state.deadline=null;return state;}
export function readingItems(data){return (data.passages||[]).flatMap(p=>(p.groups||[]).flatMap(g=>g.questions||[]));}
export function readingReport(data,answers){
  const seen=new Set();
  return readingItems(data).filter(q=>{if(seen.has(q.id))return false;seen.add(q.id);return true;}).map(q=>{
    const accepted=q.answer?.accepted || data.answerKey?.[q.number]?.accepted;
    return {id:q.id,number:q.number,given:answers[q.id]||'',accepted:accepted||null,
      correct:Array.isArray(accepted)&&accepted.length ? accepted.some(a=>normalizeAnswer(a)===normalizeAnswer(answers[q.id])) : null};
  });
}
export function loadPractice(key,skill,storage=localStorage){
  const initial={version:1,skill,index:0,answers:{},flags:[],remaining:skill==='speaking'?120:3600,deadline:null,submitted:null};
  try{const s=JSON.parse(storage.getItem(key));if(s?.version===1&&s.skill===skill&&s.answers&&typeof s.answers==='object'&&Array.isArray(s.flags)&&Number.isFinite(s.remaining)&&s.remaining>=0)return {...initial,...s};}catch{}
  return initial;
}
export function assetURL(base,path){
  if(typeof path!=='string'||!/^\.\/assets\/[\w.-]+$/.test(path))throw new Error('Invalid asset path');
  return base+path.slice(2);
}
