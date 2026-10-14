import { icon } from './icons.js';
import { escapeHTML as esc } from '../core.js';
import { localPracticeEntries } from './import-catalog.js';
import { REVIEW_KEY } from '../lib/review-queue.js';

const skillNames={listening:'听力',reading:'阅读',writing:'写作',speaking:'口语'};
const DAY=86400000;

function readJSON(key){try{return JSON.parse(localStorage.getItem(key));}catch{return null;}}

function quickStart(drafts,history){
  const draft=drafts[0],last=history[0];
  if(draft)return {book:draft.book,test:draft.test,eyebrow:'CONTINUE',title:'继续上次练习',text:`${skillNames[draft.skill]} · 已作答 ${draft.answered} 项，进度保存在本机。`,href:draft.href,action:'继续练习'};
  if(last)return {book:last.book,test:last.test,eyebrow:'LAST PRACTICE',title:`上次完成：${skillNames[last.skill]}`,text:'回看这套试卷的其他科目，或从题库选择下一套。',href:`#library/${last.book}/${last.test}`,action:'查看这套试卷'};
  return {book:18,test:1,eyebrow:'QUICK START',title:'从一套真题开始',text:'选一个科目作为今天的起点，进度会自动保存在本机。',href:'#library/18/1',action:'选择科目'};
}

function studyStats(history,now=Date.now()){
  const progress=readJSON('ielts-vocabulary-v1')?.progress;
  const words=progress&&typeof progress==='object'?Object.values(progress):[];
  const review=readJSON(REVIEW_KEY);
  const items=Array.isArray(review?.items)?review.items:[];
  return {
    wordsDue:words.filter(p=>Number(p?.due)<=now).length,
    wordsLearned:words.filter(p=>p?.reviews).length,
    reviewDue:items.filter(item=>item.dueAt<=now).length,
    weekSubmitted:history.filter(h=>now-new Date(h.date).getTime()<7*DAY).length
  };
}

export function studioHome(){
  const {drafts,history}=localPracticeEntries();
  const q=quickStart(drafts,history),s=studyStats(history);
  const today=new Date().toLocaleDateString('zh-CN',{month:'long',day:'numeric',weekday:'long'});
  const tiles=[
    ['/words.html','cards',s.wordsDue,'待复习单词',s.wordsLearned?`已学 ${s.wordsLearned} 词`:'还没有开始背词'],
    ['/review.html','flag',s.reviewDue,'待复做错题','交卷后可收藏错题'],
    ['#history','chart',s.weekSubmitted,'近 7 天提交','阅读 · 写作 · 口语'],
    ['/mock.html','clock',null,'整套模考','听说读写依次完成']
  ];
  const skills=[['listening','headphones','听力','听原音，完成作答，再回看证据。'],['reading','book','阅读','左文右题，专注理解每一篇文章。'],['writing','pen','写作','对照题目与图表，完成两篇作文。'],['speaking','mic','口语','准备、录音、回听，练习完整表达。']];
  const skillHref=id=>id==='listening'?`/import-preview.html?book=${q.book}&test=${q.test}`:`/practice.html?book=${q.book}&test=${q.test}&skill=${id}`;
  return `<section class="studio-hero home-dash"><div class="home-head"><span class="eyebrow">${esc(today)}</span><h1>今天，<em>练一点就好。</em></h1></div>
    <a class="home-continue" href="${esc(q.href)}"><div class="studio-cover">CAMBRIDGE<span>${q.book}</span><small>ACADEMIC · TEST ${q.test}</small></div><div class="home-continue-body"><span class="eyebrow">${q.eyebrow}</span><h2>${esc(q.title)}</h2><p>${esc(q.text)}</p><span class="btn primary">${q.action} ${icon('arrow')}</span></div></a>
    <div class="home-stats">${tiles.map(([href,ico,value,label,hint])=>`<a class="home-stat" href="${href}"><span class="home-stat-icon">${icon(ico)}</span><strong>${value===null?icon('arrow'):value}</strong><span>${label}</span><small>${hint}</small></a>`).join('')}</div></section>
  <section class="studio-skills"><div class="section-heading"><h2>单项练习</h2><a class="text-btn" href="#library">全部试卷 ${icon('arrow')}</a></div><div class="studio-skill-grid">${skills.map(([id,ico,name,description])=>`<a class="studio-skill" href="${skillHref(id)}"><span class="studio-skill-icon">${icon(ico)}</span><h3>${name}<small>${id.toUpperCase()}</small></h3><p>${description}</p><span class="studio-skill-link">Cambridge ${q.book} · Test ${q.test} ${icon('arrow')}</span></a>`).join('')}</div></section>`;
}
