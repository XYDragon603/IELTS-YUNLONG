import { normalizeAnswer } from '../core.js';

export const MISTAKE_TYPES = { vocabulary:'Vocabulary · 词汇', misread:'Misread Question · 审题', distractor:'Distractor · 干扰项', time:'Time Pressure · 时间', careless:'Careless · 疏忽', listening:'Sound Recognition · 辨音' };
export const REVIEW_STATES = { new:'New · 待复习', reviewing:'Reviewing · 复习中', mastered:'Mastered · 已掌握' };
export function questionScore(question, given) {
  if (!question.accepted?.length) return null;
  if(question.type==='multiple') {
    const values = Array.isArray(given) ? [...new Set(given.map(normalizeAnswer))] : [];
    const keys = question.accepted.map(normalizeAnswer);
    return values.slice(0,question.maxChoices||keys.length).filter(v=>keys.includes(v)).length;
  }
  return question.accepted.some(a=>normalizeAnswer(a)===normalizeAnswer(given))?1:0;
}
export const questionWeight = q => q.numbers?.length || 1;
export const isAnswered = value => Array.isArray(value)?value.length>0:Boolean(String(value||'').trim());
export const answeredWeight = (q,value) => Array.isArray(value)?Math.min(value.length,questionWeight(q)):isAnswered(value)?questionWeight(q):0;
export const displayAnswer = value => Array.isArray(value)?value.join(', '):String(value||'未作答');
export function resultsFor(test,session) {
  const questions=test.parts.flatMap(p=>p.questions);
  return questions.map(q=>({...q,given:session.answers[q.id],score:test.verified===true?questionScore(q,session.answers[q.id]):null,weight:questionWeight(q)}));
}
export function newSession(test,mode='study',now=Date.now()) {
  return {id:`${now}-${Math.random().toString(36).slice(2,7)}`,testId:test.id,book:test.book,test:test.number,skill:'listening',mode,part:1,answers:{},flags:[],audio:{},remaining:30*60,deadline:null,started:now,updated:now,finished:null,elapsed:0,lastResumed:null};
}
export function addReview(items,question,session,reason='',now=Date.now()) {
  const key=`${session.testId}:${question.id}`;
  const existing=items.find(item=>item.key===key);
  if(existing) return items.map(item=>item.key===key?{...item,reason:reason||item.reason,lastAnswer:session.answers[question.id],sessionId:session.id,updated:now}:item);
  return [...items,{key,testId:session.testId,questionId:question.id,sessionId:session.id,skill:'listening',book:session.book,test:session.test,lastAnswer:session.answers[question.id],reason,status:'new',count:0,lastReviewed:null,created:now,updated:now}];
}
export function applyRetry(item,question,answer,now=Date.now()) {
  const score=questionScore(question,answer);
  return {...item,lastRetry:answer,retryScore:score,count:item.count+1,lastReviewed:now,updated:now,status:score===questionWeight(question)?'mastered':'reviewing'};
}
export function saveStudyState(state,storage=globalThis.localStorage) { storage.setItem('ielts-study-v1',JSON.stringify(state)); }
export function loadStudyState(storage=globalThis.localStorage) {
  try {
    const s=JSON.parse(storage.getItem('ielts-study-v1'));
    if(s?.version===1&&Array.isArray(s.sessions)&&Array.isArray(s.review))return {...s,saved:s.saved||[],diagnoses:s.diagnoses||{},recent:s.recent||[]};
  }catch{}
  return {version:1,sessions:[],review:[],saved:[],diagnoses:{},recent:[]};
}
