export const DAY=86400000;
export function spellingMatches(given,expected){return String(given).trim().replace(/\s+/g,' ').toLowerCase()===String(expected).trim().replace(/\s+/g,' ').toLowerCase();}
export function recordWordError(previous={},now=Date.now()){return {...previous,needsPractice:true,mistakes:(previous.mistakes||0)+1,lastMistake:now};}
export const WORD_LIMITS=[10,20,30,50,100,200,300,500];
export function normalizeWordLimit(value){const n=Number(value);return Number.isFinite(n)?Math.max(1,Math.min(1000,Math.floor(n)||20)):20;}
export function rateWord(previous={},rating,now=Date.now()){
  if(!['again','hard','known'].includes(rating))throw new Error('Invalid rating');
  const stage=rating==='again'?0:rating==='hard'?Math.max(0,(previous.stage||0)-1):Math.min(6,(previous.stage||0)+1);
  const delay=rating==='again'?10*60000:rating==='hard'?DAY:[0,1,3,7,14,30,60][stage]*DAY;
  return {...previous,stage,due:now+delay,reviews:(previous.reviews||0)+1,lastReviewed:now,rating};
}
export function studyQueue(words,progress,{review=false,limit=20,random=false,now=Date.now()}={}){
  const selected=words.filter(w=>review?progress[w.id]?.due<=now:!progress[w.id]?.reviews);
  if(random)for(let i=selected.length-1;i>0;i--){const j=Math.floor(Math.random()*(i+1));[selected[i],selected[j]]=[selected[j],selected[i]];}
  else if(review)selected.sort((a,b)=>progress[a.id].due-progress[b.id].due);
  return selected.slice(0,normalizeWordLimit(limit)).map(w=>w.id);
}
