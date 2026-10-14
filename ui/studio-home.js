import { icon } from './icons.js';
import { escapeHTML as esc } from '../core.js';
import { localPracticeEntries } from './import-catalog.js';

const skillNames={listening:'听力',reading:'阅读',writing:'写作',speaking:'口语'};

function quickStart(){
  const {drafts,history}=localPracticeEntries();
  const draft=drafts[0],last=history[0];
  if(draft)return {book:draft.book,test:draft.test,eyebrow:'CONTINUE',title:'继续上次练习',text:`${skillNames[draft.skill]} · 已作答 ${draft.answered} 项，进度保存在本机。`,href:draft.href,action:'继续练习'};
  if(last)return {book:last.book,test:last.test,eyebrow:'LAST PRACTICE',title:`上次完成：${skillNames[last.skill]}`,text:'回看这套试卷的其他科目，或从题库选择下一套。',href:`#library/${last.book}/${last.test}`,action:'查看这套试卷'};
  return {book:18,test:1,eyebrow:'QUICK START',title:'今天，专注一项能力',text:'从四科练习中选择你的起点。',href:'#library/18/1',action:'选择科目'};
}

export function studioHome(){
  const q=quickStart();
  const skills=[['listening','headphones','听力','听原音，完成作答，再回看证据。'],['reading','book','阅读','左文右题，专注理解每一篇文章。'],['writing','pen','写作','对照题目与图表，完成两篇作文。'],['speaking','mic','口语','准备、录音、回听，练习完整表达。']];
  return `<section class="studio-hero"><div><span class="studio-badge">IELTS ACADEMIC · 本地学习空间</span><h1>专注备考，<br><em>从一套真题开始。</em></h1><p>选择试卷，进入练习。把时间留给阅读、思考与作答，<br>让每一次练习都有可以回看的记录。</p><a class="btn primary" href="#library">进入我的题库 ${icon('arrow')}</a><a class="text-btn" href="#history">查看练习记录</a></div><aside class="studio-start"><span class="eyebrow">${q.eyebrow}</span><div class="studio-cover">CAMBRIDGE<span>${q.book}</span><small>ACADEMIC · TEST ${q.test}</small></div><h2>${esc(q.title)}</h2><p>${esc(q.text)}</p><a class="btn primary" href="${esc(q.href)}">${q.action} ${icon('arrow')}</a><small>全部试卷见题库</small></aside></section><section class="studio-skills"><div class="section-heading"><h2>你的备考工作台</h2><a class="text-btn" href="#library">全部试卷 ${icon('arrow')}</a></div><div class="studio-skill-grid">${skills.map(([id,ico,name,description])=>`<a class="studio-skill" href="${id==='listening'?`#library/${q.book}/${q.test}`:`/practice.html?book=${q.book}&test=${q.test}&skill=${id}`}"><span class="studio-skill-icon">${icon(ico)}</span><h3>${name}<small>${id.toUpperCase()}</small></h3><p>${description}</p><span class="studio-skill-link">${id==='listening'?'选择听力试卷':`Cambridge ${q.book} · Test ${q.test}`} ${icon('arrow')}</span></a>`).join('')}</div></section>`;
}
