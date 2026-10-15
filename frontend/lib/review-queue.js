import {normalizeAnswer} from '../core.js';
import {exactReadingExcerpt} from './synonym-notes.js';

export const REVIEW_KEY='ielts-review-v1';
export const REVIEW_REASONS={vocabulary:'词汇 / 同义替换',misread:'审题',distractor:'干扰信息',time:'时间不够',careless:'疏忽',listening:'辨音'};
const DAY=86400000;

export function reviewId(book,test,skill,questionId){return `c${book}-t${test}-${skill}-${questionId}`;}

export function loadReviewQueue(storage=globalThis.localStorage){
  const raw=storage.getItem(REVIEW_KEY);
  if(!raw)return {version:1,items:[]};
  let value;
  try{value=JSON.parse(raw);}catch{throw Error('复盘记录无法读取，原数据未被覆盖。');}
  if(value?.version!==1||!Array.isArray(value.items))throw Error('复盘记录格式异常，原数据未被覆盖。');
  return value;
}

export function addReviewItem(item,storage=globalThis.localStorage,now=Date.now()){
  if(!/^c\d+-t[1-4]-(listening|reading)-q\d+$/.test(item?.id))throw Error('无效的复盘题目');
  const queue=loadReviewQueue(storage);
  const old=queue.items.find(entry=>entry.id===item.id);
  if(old)return {item:old,added:false};
  const entry={...item,status:'new',reason:'',createdAt:now,dueAt:now,attempts:[]};
  storage.setItem(REVIEW_KEY,JSON.stringify({...queue,items:[entry,...queue.items]}));
  return {item:entry,added:true};
}

export function updateReviewItem(id,change,storage=globalThis.localStorage){
  const queue=loadReviewQueue(storage),index=queue.items.findIndex(item=>item.id===id);
  if(index<0)throw Error('未找到这道复盘题');
  const next=change(queue.items[index]);
  if(next.id!==id)throw Error('复盘题号不能修改');
  queue.items[index]=next;
  storage.setItem(REVIEW_KEY,JSON.stringify(queue));
  return next;
}

export function retryReviewItem(id,answer,storage=globalThis.localStorage,now=Date.now()){
  return updateReviewItem(id,item=>{
    const given=String(answer||'').trim();
    if(!given)throw Error('先填写复做答案');
    const accepted=Array.isArray(item.accepted)?item.accepted:[];
    const match=item.sourceVerified&&accepted.length>0?(item.multiple?
      (()=>{const keys=accepted.map(normalizeAnswer).sort(),values=given.split(/[,，、;；\s]+/).filter(Boolean).map(normalizeAnswer).sort();return keys.length===values.length&&keys.every((key,index)=>key===values[index]);})():
      accepted.some(value=>normalizeAnswer(value)===normalizeAnswer(given))):null;
    return {...item,status:match===true?'mastered':'reviewing',dueAt:now+(match===true?7*DAY:DAY),attempts:[...(item.attempts||[]),{given,at:now,match}]};
  },storage);
}

export function setReviewStatus(id,status,storage=globalThis.localStorage,now=Date.now()){
  if(!['new','reviewing','mastered'].includes(status))throw Error('无效的复盘状态');
  return updateReviewItem(id,item=>({...item,status,dueAt:now+(status==='mastered'?7*DAY:status==='reviewing'?DAY:0)}),storage);
}

export function createReadingReviewItem(data,q,group,passage,given=''){
  const synonyms=q.explanation?.paraphraseSources||[];
  const evidence=synonyms.map(item=>exactReadingExcerpt(passage?.blocks,item.paraphrase)).filter(Boolean).map(hit=>({text:hit.text,sourcePdfPage:hit.source?.pdfPage||null}));
  const rawPrompt=q.prompt||null,rawContext=group.context||group.instruction||null;
  const noisy=text=>Boolean(text&&(text.length>180||/[©@]|\.{5,}/.test(text)));
  return {id:reviewId(data.book,data.test,'reading',q.id),book:data.book,test:data.test,skill:'reading',questionId:q.id,number:q.number,prompt:noisy(rawPrompt)?'题干 OCR 待核对，请对照原卷题页':rawPrompt,rawPrompt:noisy(rawPrompt)?rawPrompt:null,groupContext:noisy(rawContext)?null:rawContext,rawGroupContext:noisy(rawContext)?rawContext:null,options:q.options||group.options||[],accepted:q.answer?.accepted||data.answerKey?.[q.number]?.accepted||null,multiple:q.type==='multiple'||(q.numbers?.length||0)>1,sourceVerified:data.verified===true,paperPath:data.sources?.paper?.path||null,sourcePdfPage:q.source?.pdfPage||null,evidence,synonymNotes:synonyms,latestGiven:given};
}

export function createListeningReviewItem(data,q,part,given=''){
  return {id:reviewId(data.book,data.test,'listening',q.id),book:data.book,test:data.test,skill:'listening',questionId:q.id,number:q.numbers?.join('–')||q.number,prompt:q.prompt||null,groupContext:part.instruction||null,options:q.options||[],accepted:q.accepted||null,multiple:q.type==='multiple'||(q.numbers?.length||0)>1,sourceVerified:data.verified===true,paperPath:data.sources?.paper?.path||null,sourcePdfPage:q.source?.pdfPage||null,audioPath:data.audio?.[part.number]?.path||null,evidence:(q.evidence||[]).map(s=>({text:s.text,sourcePdfPage:s.sourcePdfPage})),synonymNotes:q.explanation?.paraphraseSources||[],latestGiven:Array.isArray(given)?given.join(', '):given};
}
