import { icon } from './icons.js';
import { escapeHTML as esc } from '../core.js';
import { localPracticeEntries } from './import-catalog.js';
import { REVIEW_KEY } from '../lib/review-queue.js';

const skillNames={listening:'听力',reading:'阅读',writing:'写作',speaking:'口语'};
const skillIcons={listening:'headphones',reading:'book',writing:'pen',speaking:'mic'};
const QUESTIONS={listening:40,reading:40}; // Cambridge listening and reading papers have 40 items
const DAY=86400000;

function readJSON(key){try{return JSON.parse(localStorage.getItem(key));}catch{return null;}}

function quickStart(drafts,history){
  const draft=drafts[0],last=history[0];
  if(draft){
    const total=QUESTIONS[draft.skill];
    return {book:draft.book,test:draft.test,eyebrow:'CONTINUE PRACTICE',title:`继续上次的${skillNames[draft.skill]}练习`,
      progress:total?{value:Math.min(draft.answered,total),total}:null,
      text:total?`已作答 ${Math.min(draft.answered,total)} / ${total}`:`已完成 ${draft.answered} 项 · 草稿保存在本机`,href:draft.href,action:'继续练习'};
  }
  if(last)return {book:last.book,test:last.test,eyebrow:'LAST PRACTICE',title:`上次完成：${skillNames[last.skill]}`,text:'回看这套试卷的其他科目，或从题库选择下一套。',href:`#library/${last.book}/${last.test}`,action:'查看这套试卷'};
  return {book:18,test:1,eyebrow:'QUICK START',title:'从一套真题开始',text:'选一个科目作为今天的起点，进度会自动保存在本机。',href:'#library/18/1',action:'选择科目'};
}

function studyStats(history,now=Date.now()){
  const progress=readJSON('ielts-vocabulary-v1')?.progress;
  const words=progress&&typeof progress==='object'?Object.values(progress):[];
  const review=readJSON(REVIEW_KEY);
  const items=Array.isArray(review?.items)?review.items:[];
  const week=history.filter(h=>now-new Date(h.date).getTime()<7*DAY);
  return {
    wordsDue:words.filter(p=>Number(p?.due)<=now).length,
    wordsLearned:words.filter(p=>p?.reviews).length,
    reviewDue:items.filter(item=>item.dueAt<=now).length,
    weekSubmitted:week.length,
    weekSkills:[...new Set(week.map(h=>skillNames[h.skill]))]
  };
}

const when=date=>{const d=new Date(date);return Number.isNaN(d.getTime())?'':`${d.getFullYear()}/${d.getMonth()+1}/${d.getDate()} ${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`;};

export function studioHome(){
  const {drafts,history}=localPracticeEntries();
  const q=quickStart(drafts,history),s=studyStats(history);
  const tiles=[
    ['/words.html','book',s.wordsDue,'待复习单词',s.wordsLearned?`已学 ${s.wordsLearned} 词中需要复习`:'还没有开始背词'],
    ['/review.html','bookmark',s.reviewDue,'待复做错题',s.reviewDue?'来自交卷后收藏的错题':'交卷后可收藏错题'],
    ['#history','bars',s.weekSubmitted,'近 7 天练习',s.weekSkills.length?s.weekSkills.join(' · '):'提交后会记录在这里']
  ];
  const skills=[['listening','听力','听原音，完成作答，再回看证据。'],['reading','阅读','左文右题，专注理解每一篇文章。'],['writing','写作','对照题目与图表，完成两篇作文。'],['speaking','口语','准备、录音、回听，练习完整表达。']];
  const skillHref=id=>id==='listening'?`/import-preview.html?book=${q.book}&test=${q.test}`:`/practice.html?book=${q.book}&test=${q.test}&skill=${id}`;
  const recent=history.slice(0,4);
  return `<section class="studio-hero home-dash">
    <div class="home-head"><span class="eyebrow">Your next chapter</span><h1>今天，<em>练一点就好。</em></h1><p>从一套真题开始，按自己的节奏前进。</p></div>
    <div class="home-continue"><a class="studio-cover" href="${esc(q.href)}" tabindex="-1" aria-hidden="true"><small>CAMBRIDGE</small><span>${q.book}</span><small>ACADEMIC</small></a>
      <div class="home-continue-body"><span class="eyebrow">${q.eyebrow}</span><h2>${esc(q.title)}</h2><p class="home-continue-paper">Cambridge ${q.book} · Test ${q.test}</p>
        ${q.progress?`<div class="home-progress" role="progressbar" aria-label="作答进度" aria-valuemin="0" aria-valuemax="${q.progress.total}" aria-valuenow="${q.progress.value}"><i style="width:${Math.max(3,q.progress.value/q.progress.total*100)}%"></i></div>`:''}
        <p class="home-continue-meta">${esc(q.text)}</p>
        <div class="home-continue-actions"><a class="btn primary" href="${esc(q.href)}">${q.action} ${icon('arrow')}</a><a class="text-btn" href="#library/${q.book}/${q.test}">查看试卷 ${icon('arrow')}</a></div></div></div>
    <div class="home-stats">${tiles.map(([href,ico,value,label,hint])=>`<a class="home-stat" href="${href}"><span class="home-stat-icon">${icon(ico)}</span><strong>${value}</strong><span>${label}<small>${esc(hint)}</small></span>${icon('chevron')}</a>`).join('')}</div></section>
  <section class="studio-skills"><div class="section-heading"><h2>单项练习</h2><a class="text-btn" href="#library">全部题库 ${icon('arrow')}</a></div><div class="studio-skill-grid">${skills.map(([id,name,description])=>`<a class="studio-skill" href="${skillHref(id)}"><span class="studio-skill-icon">${icon(skillIcons[id])}</span><h3>${name}<small>${id.toUpperCase()}</small></h3><p>${description}</p><span class="studio-skill-link">Cambridge ${q.book} · Test ${q.test} ${icon('arrow')}</span></a>`).join('')}</div></section>
  <section class="studio-recent"><div class="section-heading"><h2>最近练习</h2><a class="text-btn" href="#history">查看全部记录 ${icon('arrow')}</a></div>${recent.length?`<ul class="recent-list">${recent.map(h=>`<li><span class="recent-icon">${icon(skillIcons[h.skill])}</span><span class="recent-paper">Cambridge ${h.book} · Test ${h.test}</span><span class="recent-skill">${skillNames[h.skill]}</span><time datetime="${esc(h.date)}">${when(h.date)}</time><a class="text-btn" href="${esc(h.href)}">查看记录 ${icon('arrow')}</a></li>`).join('')}</ul>`:'<p class="recent-empty">还没有提交过练习。交卷后，阅读、写作、口语记录会显示在这里。</p>'}</section>`;
}
