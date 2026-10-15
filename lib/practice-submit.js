import {wordCount,escapeHTML as esc} from '../core.js';
export function submissionRows(skill,paper,state){
 if(skill==='reading')return (paper.passages||[]).map((p,index)=>{
  const questions=[...new Map((p.groups||[]).flatMap(g=>g.questions||[]).map(q=>[q.id,q])).values()];
  const missing=questions.filter(q=>!String(state.answers[q.id]||'').trim());
  const flags=questions.filter(q=>(state.flags||[]).includes(q.id));
  return {index,title:`Passage ${p.number||index+1}`,detail:`已答 ${questions.length-missing.length} / ${questions.length} · 待填 ${missing.length} · 标记 ${flags.length}`,target:(missing[0]||flags[0])?.id};
 });
 if(skill==='writing')return (paper.tasks||[]).map((task,index)=>{const count=wordCount(state.answers[task.id]);const min=Number(task.minimumWords)||0;return {index,title:`Task ${task.number||index+1}`,detail:`${count} 词${min?` / 要求至少 ${min} 词`:''} · ${!count?'尚未作答':min&&count<min?'字数不足':'已填写'}`};});
 return (paper.parts||[]).map((p,index)=>({index,title:`Part ${p.part}`,detail:'正在检查本机录音…',part:p.part}));
}
export async function openSubmissionCheck({skill,paper,state,recordingStore,onNavigate}){
 const dialog=document.querySelector('#practice-submit');
 dialog.returnValue='';
 const rows=submissionRows(skill,paper,state);
 const missing=skill==='reading'?(paper.passages||[]).flatMap(p=>(p.groups||[]).flatMap(g=>g.questions||[])).filter((q,i,all)=>all.findIndex(x=>x.id===q.id)===i&&!String(state.answers[q.id]||'').trim()).length:null;
 dialog.innerHTML=`<span class="submit-alert" aria-hidden="true">!</span><h2>确认交卷？</h2><p>${missing?`还有 <strong>${missing}</strong> 题未作答。`:''}检查下列内容后确认提交。未完成也可交卷，提交后本次答案只读。</p><div class="submission-checks">${rows.map(r=>`<section class="submission-check"><div><strong>${esc(r.title)}</strong><p data-check-status="${r.index}">${esc(r.detail)}</p></div><button class="btn" type="button" data-check-index="${r.index}">返回检查</button></section>`).join('')}</div>${paper.verified?'':'<p class="practice-muted">本次练习结果仅供个人复习，不作为正式成绩。</p>'}${skill==='reading'?'':'<p class="practice-muted">本次仅保存作答与本机录音，不提供写作或口语评分。</p>'}<form method="dialog" class="practice-actions"><button class="btn" value="cancel">继续练习</button><button class="btn primary" value="submit">确认提交</button></form>`;
 dialog.querySelectorAll('[data-check-index]').forEach(b=>b.onclick=async()=>{const row=rows[Number(b.dataset.checkIndex)];dialog.close('cancel');await onNavigate(row.index,row.target);});
 dialog.showModal();
 if(skill==='speaking'){
  await Promise.all(rows.map(async r=>{const target=dialog.querySelector(`[data-check-status="${r.index}"]`);try{const blob=await recordingStore(`${state.recordingNamespace}-part-${r.part}`);target.textContent=blob?.size?'已保存录音 · 可返回回听确认':'未找到已保存录音';}catch{target.textContent='录音读取失败，状态未知；请返回回听并下载备份。';}}));
 }
}
