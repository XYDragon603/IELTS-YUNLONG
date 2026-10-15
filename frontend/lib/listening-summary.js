import {answeredWeight,questionWeight} from './study-model.js';
export function listeningSummary(test,session){
 return test.parts.map(part=>{
  const total=part.questions.reduce((n,q)=>n+questionWeight(q),0);
  const answered=part.questions.reduce((n,q)=>n+answeredWeight(q,session.answers[q.id]),0);
  const missing=part.questions.filter(q=>answeredWeight(q,session.answers[q.id])<questionWeight(q));
  return {part:part.number,total,answered,missing:total-answered,flagged:part.questions.filter(q=>session.flags.includes(q.id)).length,firstMissing:missing[0]?.id};
 });
}
