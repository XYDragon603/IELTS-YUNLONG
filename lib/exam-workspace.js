import { escapeHTML as esc } from '../core.js';

export function mountExamWorkspace({skill,book,test,state,items,onNavigate}){
  document.body.classList.add('exam-workspace');
  document.body.classList.toggle('exam-submitted',Boolean(state.submitted));
  const main=document.querySelector('#practice-main');
  const intro=main.querySelector('.practice-intro');
  intro.querySelector('h1').textContent=`Cambridge IELTS ${book} · Test ${test}`;
  intro.querySelector('.eyebrow').textContent={reading:'READING · 阅读练习',writing:'WRITING · 写作练习',speaking:'SPEAKING · 口语练习'}[skill];
  const actions=document.createElement('div');actions.className='exam-top-actions';
  const submit=main.querySelector('#submit-practice');
  actions.append(submit);intro.append(actions);
  const warnings=[...main.querySelectorAll(':scope > .practice-warning')];
  if(warnings.length){const details=document.createElement('details');details.className='exam-data-note';const summary=document.createElement('summary');const unverified=warnings.some(w=>w.hasAttribute('data-unverified'));details.classList.toggle('unverified',unverified);summary.textContent=unverified?'资料待核对 · 题干可能有识别错误':'练习资料说明';details.append(summary,...warnings);intro.after(details);}
  const history=main.querySelector('.practice-history');
  if(history){const details=document.createElement('details');details.className='exam-history';const summary=document.createElement('summary');summary.textContent='练习历史';details.append(summary,history);main.append(details);}
  const toolbar=main.querySelector('.reading-tools');
  if(toolbar){
    const tabs=toolbar.querySelector('.reading-mobile-tabs');
    const details=document.createElement('details');details.className='exam-reading-options';
    const summary=document.createElement('summary');summary.textContent='阅读工具 · 字号 / 高亮';
    const panel=document.createElement('div');panel.className='exam-tools-panel';
    [...toolbar.children].filter(el=>el!==tabs).forEach(el=>panel.append(el));details.append(summary,panel);toolbar.append(details);
    const sectionBar=document.createElement('div');sectionBar.className='exam-section-bar';
    const sections=main.querySelector('.practice-tabs');sections.before(sectionBar);sectionBar.append(sections,toolbar);
  }
  if(skill!=='reading')return;
  const all=items.flatMap((passage,index)=>(passage.groups||[]).flatMap(g=>(g.questions||[]).map(q=>({...q,passageIndex:index}))));
  const unique=[...new Map(all.map(q=>[q.id,q])).values()];
  const button=document.createElement('button');button.className='btn';button.id='answer-card-toggle';button.type='button';button.setAttribute('aria-haspopup','dialog');
  actions.prepend(button);
  const update=()=>{button.textContent=`答题卡 ${unique.filter(q=>String(state.answers[q.id]||'').trim()).length} / ${unique.length}`;};update();
  const dialog=document.createElement('dialog');dialog.className='exam-answer-card';dialog.setAttribute('aria-label','阅读答题卡');
  dialog.innerHTML=`<form method="dialog"><h2>答题卡</h2><button class="btn" aria-label="关闭答题卡">关闭</button></form><p>选择题号，跳转至对应文章。标记的题目显示 ☆。</p>${items.map((p,i)=>`<section><h3>Passage ${p.number||i+1}</h3><div class="exam-answer-grid">${unique.filter(q=>q.passageIndex===i).map(q=>`<button class="btn" type="button" data-question-jump="${esc(q.id)}" data-passage-index="${i}">${q.number}</button>`).join('')}</div></section>`).join('')}`;
  main.append(dialog);
  button.onclick=()=>{
    dialog.querySelectorAll('[data-question-jump]').forEach(b=>{const id=b.dataset.questionJump;const q=unique.find(q=>q.id===id);const answered=Boolean(String(state.answers[id]||'').trim());const flagged=state.flags.includes(id);b.classList.toggle('answered',answered);b.textContent=q.number+(flagged?' ☆':'');b.setAttribute('aria-label',`第 ${q.number} 题，${answered?'已作答':'未作答'}${flagged?'，已标记':''}`);});
    dialog.showModal();
  };
  dialog.addEventListener('click',async e=>{const b=e.target.closest('[data-question-jump]');if(!b)return;dialog.close();await onNavigate(Number(b.dataset.passageIndex));document.querySelector('[data-reading-panel="questions"]')?.click();const input=document.getElementById('answer-'+b.dataset.questionJump);input?.focus({preventScroll:true});input?.closest('.practice-q')?.scrollIntoView({block:'center'});});
  main.addEventListener('input',update,{signal:workspaceSignal(main)});
}

function workspaceSignal(main){main._workspaceController?.abort();main._workspaceController=new AbortController();return main._workspaceController.signal;}
