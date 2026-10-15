import { SECTIONS,escapeHTML as esc,grade } from '../core.js';
import { listeningQuestions,readingQuestions } from '../data.js';
import { icon } from './icons.js';
import { getListeningTest } from '../lib/cambridge.js';
import { resultsFor,answeredWeight } from '../lib/study-model.js';
import { progressBar } from './components.js';
import { loadReviewQueue } from '../lib/review-queue.js';

function continuePractice(session,legacy){
  if(session){
    const test=getListeningTest(session.testId),part=test.parts.find(p=>p.number===session.part);
    const done=test.parts.flatMap(p=>p.questions).reduce((n,q)=>n+answeredWeight(q,session.answers[q.id]),0);
    return `<section class="continue-practice"><div class="eyebrow">CONTINUE PRACTICE · 接着上次的节奏</div><h2>Cambridge IELTS <em>${session.book}</em></h2><p>Test ${session.test} <span>/</span> Listening <span>/</span> Part ${session.part}</p><div class="continue-detail">${esc(part.title)} · Questions ${(session.part-1)*10+1}–${session.part*10}</div><div class="continue-progress"><span>已作答 ${done} / 40 题</span><strong>${Math.round(done/40*100)}%</strong></div>${progressBar(Math.round(done/40*100))}<div class="continue-bottom"><span>${session.mode==='mock'?'模考练习':'学习模式'} · 进度与音频位置已保存</span><a href="#listening/${session.id}" class="btn lime">继续练习 ${icon('arrow')}</a></div></section>`;
  }
  if(legacy){
    const section=SECTIONS.find(s=>s.id===legacy.sections[legacy.index]);
    const count=Object.values(legacy.answers).filter(v=>String(v).trim()).length;
    return `<section class="continue-practice"><div class="eyebrow">CONTINUE PRACTICE · 继续示例练习</div><h2>Sample Test <em>01</em></h2><p>${section.english} <span>/</span> 第 ${legacy.index+1} 科，共 ${legacy.sections.length} 科</p><div class="continue-detail">${section.detail} · 已保存 ${count} 项作答</div><div class="continue-bottom"><span>原有练习进度完整保留</span><a href="#exam" class="btn lime">继续练习 ${icon('arrow')}</a></div></section>`;
  }
  return `<section class="continue-practice"><div class="eyebrow">YOUR NEXT PRACTICE · 今天，从这里开始</div><h2>A focused start.<br><em>A little progress.</em></h2><p>Cambridge IELTS 18 <span>/</span> Test 1 · Listening</p><div class="continue-detail">40 道真实题目 · 本地音频 · 逐题解析</div><div class="continue-bottom"><a class="quiet-link" href="#library">浏览我的题库 ↗</a><button class="btn lime" data-study="start" data-test="c18-t1-listening">开始练习 ${icon('arrow')}</button></div></section>`;
}
function bandProgress(state,history,target){
  const completed=state.sessions.filter(s=>s.finished&&getListeningTest(s.testId)?.verified);
  const scores=completed.slice(-4).map(s=>Math.round(resultsFor(getListeningTest(s.testId),s).reduce((n,q)=>n+q.score,0)/40*100));
  return `<section class="progress-section"><div class="section-heading"><h2>My progress <span>把每一次进步，留在这里</span></h2><button class="text-btn" data-action="goal">目标 Band ${Number(target).toFixed(1)} · 调整 ${icon('arrow')}</button></div><div class="skill-progress">${SECTIONS.map(s=>{
    let value='—',caption='完成一次练习后记录';
    if(s.id==='listening'&&scores.length){value=scores.at(-1)+'%';caption='最近完整听力正确率';}
    else if(['listening','reading'].includes(s.id)){const last=history.find(h=>h.sections.includes(s.id));if(last){const qs=s.id==='listening'?listeningQuestions:readingQuestions;value=grade(qs,last.answers).filter(q=>q.correct).length+'/'+qs.length;caption='最近示例练习答对题数';}}
    else if(history.some(h=>h.sections.includes(s.id))){value='待评估';caption='已练习 · 尚未评分';}
    return `<div><span>${s.english}</span><strong>${value}</strong><small>${caption}</small></div>`;
  }).join('')}</div><div class="progress-caption">${scores.length?`听力正确率趋势 <span>${scores.join(' → ')}%</span>`:'你的学习记录将从第一次提交开始。'}<span>正确率不等同于 IELTS Band</span></div></section>`;
}
function skillCards(){
  return `<div class="skill-rows">${SECTIONS.map((s,i)=>`<a class="skill-tile" href="${s.id==='listening'?'#library/18/1':'#practice'}"><span class="skill-number">0${i+1}</span><span class="subject-icon ${s.color}">${icon(s.icon)}</span><h3>${s.english}<small>${s.name}</small></h3><span>${s.id==='listening'?'真题听力与音频':'专项示例练习'}</span>${icon('arrow')}</a>`).join('')}</div>`;
}
export function dashboardView({state,legacyAttempt,history,target}){
  const session=state.sessions.filter(s=>!s.finished).sort((a,b)=>b.updated-a.updated)[0];
  let importedDue=0;try{importedDue=loadReviewQueue().items.filter(item=>item.dueAt<=Date.now()).length;}catch{}
  const due=state.review.filter(r=>r.status!=='mastered').length+importedDue;
  const completed=state.sessions.filter(s=>s.finished).sort((a,b)=>b.finished-a.finished);
  const recent=state.recent.slice(0,2);
  const previews=recent.length?recent:[{book:18,test:1}];
  const activity=[...completed.map(s=>({time:s.finished,title:`Cambridge ${s.book} · Test ${s.test}`,sub:'Listening · '+(getListeningTest(s.testId)?.verified?'已完成，开始复盘':'原卷练习，待自行核对'),url:`#explanation/${s.id}`})),...history.map(h=>({time:h.finished,title:'示例卷 01 · '+(h.sections.length===4?'全科模考':SECTIONS.find(s=>s.id===h.sections[0]).name),sub:'原有练习记录',url:`#report/${h.id}`}))].sort((a,b)=>b.time-a.time).slice(0,3);
  return `<div class="intro journal-intro"><div><div class="eyebrow">${new Date().toLocaleDateString('en-GB',{day:'numeric',month:'long',year:'numeric'}).toUpperCase()} / YOUR STUDY JOURNAL</div><h1>为下一章，留一点专注。</h1><p>${session||legacyAttempt?'上次的练习已经为你保存，继续自己的节奏。':'今天的进步，从认真完成一道题开始。'}</p></div><span class="journal-target">TARGET BAND <strong class="goal-display"><strong>${Number(target).toFixed(1)}</strong></strong></span></div><div class="study-overview">${continuePractice(session,legacyAttempt)}<aside class="today-plan"><span class="eyebrow">TODAY’S FOCUS</span><h2>练习之后，<br>让理解再深一点。</h2><a href="/review.html" class="focus-stat"><span>待复习的题目</span><strong>${due} ${icon('arrow')}</strong></a><a href="#review/saved" class="focus-stat"><span>收藏的解析</span><strong>${state.saved.length} ${icon('arrow')}</strong></a><p>不急着做更多题。<br>先弄懂上一次为什么错。</p></aside></div>${bandProgress(state,history,target)}<section><div class="section-heading"><h2>Practice by skill <span>一次，专注一项能力</span></h2><a href="#practice" class="text-btn">专项练习 ${icon('arrow')}</a></div>${skillCards()}</section><section class="library-preview"><div class="section-heading"><h2>Your Cambridge shelf <span>${recent.length?'最近浏览':'推荐起点'}</span></h2><a href="#library" class="text-btn">浏览 Cambridge 4–20 ${icon('arrow')}</a></div>${previews.map(v=>`<a href="#library/${v.book}/${v.test}" class="shelf-row"><span class="book-spine">${v.book}</span><div><strong>Cambridge IELTS ${v.book}</strong><small>Test ${v.test} · Academic</small></div><span>${v.book===18&&v.test===1?'40 题在线听力已就绪':'本地原卷与听力音频'}</span>${icon('arrow')}</a>`).join('')}</section><section><div class="section-heading"><h2>Recent activity <span>最近完成</span></h2><a class="text-btn" href="#history">全部记录 ${icon('arrow')}</a></div><div class="activity-list">${activity.length?activity.map(a=>`<a href="${a.url}" class="activity-row"><span class="activity-date">${new Date(a.time).toLocaleDateString('zh-CN',{month:'2-digit',day:'2-digit'})}</span><div><strong>${esc(a.title)}</strong><small>${esc(a.sub)}</small></div><span>查看复盘 ${icon('arrow')}</span></a>`).join(''):'<p class="empty-journal">还没有完成的练习。开始一次听力，留下你的第一条学习记录。</p>'}</div></section><div class="study-note-inline">${icon('leaf')} <span>STUDY NOTE</span> 做完题，也别忘了问一句：这次我真正弄懂了什么？</div><div class="legacy-entry"><button class="text-btn" data-start="all">体验四科缩减示例卷 ${icon('arrow')}</button></div>`;
}
