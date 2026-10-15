import {requireMockStage} from '../lib/mock-run.js';
import {listeningSummary} from '../lib/listening-summary.js';
import { mountCatalog } from '../ui/import-catalog.js';
import { escapeHTML as esc,formatTime } from '../core.js';
import { icon } from '../ui/icons.js';
import { getListeningTest,getTestResources,findQuestion } from '../lib/cambridge.js';
import { loadStudyState,saveStudyState,newSession,resultsFor,addReview,applyRetry,questionScore,questionWeight,answeredWeight,isAnswered,REVIEW_STATES } from '../lib/study-model.js';
import { libraryView,testDetailView } from '../ui/library.js';
import { questionRenderer,questionNavigator,explanationPanel,reviewItem,mistakeSelect } from '../ui/components.js';
import { audioPlayer,mountAudioPlayer } from '../ui/audio-player.js';

export function createStudy({shell,notify,modal}) {
  let state=loadStudyState(),route='',player=null,current=null,explanationSession=null,retryItem=null,retryAnswer=null,retrySubmitted=false,submitting=false;
  const $=s=>document.querySelector(s);
  const commit=()=>{try{saveStudyState(state);return true;}catch{notify('本地存储空间不足，当前更改尚未保存。请导出报告并保留此页面。');return false;}};
  const sessionById=id=>state.sessions.find(s=>s.id===id);
  const keyFor=(s,q)=>`${s.testId}:${q.id}`;
  function disposePlayer(){const old=player;player=null;old?.destroy();}
  function remaining(s){return s.deadline?Math.max(0,Math.ceil((s.deadline-Date.now())/1000)):s.remaining;}
  function pause(s){if(!s?.deadline)return;s.remaining=remaining(s);s.elapsed+=(Date.now()-s.lastResumed);s.deadline=null;s.lastResumed=null;s.updated=Date.now();commit();}
  function resume(s){s.deadline=Date.now()+s.remaining*1000;s.lastResumed=Date.now();s.updated=Date.now();commit();}
  function renderFocus(s){
    disposePlayer();current=s;explanationSession=null;retryItem=null;
    const test=getListeningTest(s.testId),part=test.parts.find(p=>p.number===s.part);
    const completed=test.parts.flatMap(p=>p.questions).reduce((n,q)=>n+answeredWeight(q,s.answers[q.id]),0);
    const paused=!s.deadline;
    $('#app').innerHTML=`<div class="focus-workspace"><header class="focus-header"><a href="#home" class="brand"><span class="brand-mark">i.</span><span>IELTS Studio<small>YOUR NEXT CHAPTER</small></span></a><div class="focus-source"><strong>Cambridge ${s.book} · Test ${s.test} · Listening</strong><span>Part ${s.part} / ${s.mode==='mock'?'模考练习 · 限制快进回退':'学习模式'}</span></div><div class="focus-header-actions"><span class="timer" id="study-timer" aria-label="剩余时间">${formatTime(remaining(s))}</span><button class="btn small" data-study="pause">${icon(paused?'play':'pause')}${paused?'继续':'暂停'}</button><a class="text-btn" href="#home">保存并退出 ${icon('arrow')}</a></div></header><main id="main" class="focus-main" tabindex="-1"><div class="focus-part-heading"><div><span class="eyebrow">LISTENING / PART ${s.part}</span><h1>${esc(part.title)}</h1></div><span class="study-save" id="study-save" role="status">进度已保存</span></div>${paused?`<section class="focus-paused"><span class="eyebrow">TAKE YOUR TIME</span><h2>停一停，也没关系。</h2><p>答案与播放位置已经保存。继续后开始计时。</p><button class="btn primary" data-study="pause">继续练习 ${icon('play')}</button></section>`:`<div class="focus-grid"><div class="focus-paper">${audioPlayer(test.resources.audio[s.part]?.url,s.mode)}<div class="paper-heading"><span class="eyebrow">QUESTIONS ${(s.part-1)*10+1}–${s.part*10}</span><p>${esc(part.instruction)}</p>${part.context?`<p class="paper-context">${esc(part.context)}</p>`:''}${test.documentURL?`<a href="${test.documentURL}${test.partPages?'#page='+test.partPages[s.part-1]:''}" target="_blank" rel="noopener" class="text-btn">对照本地原卷 ↗</a>`:''}</div><div id="study-questions">${part.questions.map(q=>questionRenderer(q,s.answers,s.flags)).join('')}</div></div><aside class="focus-navigator"><div class="navigator-title"><strong>Question navigator</strong><span id="study-progress">${completed} / 40</span></div><div id="question-map">${questionNavigator(test,s,s.part)}</div><div class="navigator-note"><span class="eyebrow">A SMALL REMINDER</span><p>先读题，再听音频。<br>遇到不确定的答案，标记后继续。</p></div>${!test.verified?'<p class="source-note">本次不自动评分；可结合原卷答案页自查。音频按 Part 加载。</p>':''}</aside></div>`}</main><footer class="focus-footer"><div class="part-controls"><button class="btn" data-study="part" data-part="${s.part-1}" ${s.part===1||paused?'disabled':''}>← Previous</button><span>Part ${s.part} / 4</span><button class="btn" data-study="part" data-part="${s.part+1}" ${s.part===4||paused?'disabled':''}>Next →</button></div><button class="btn primary" data-study="submit" ${paused?'disabled':''}>提交整套听力 ${icon('arrow')}</button></footer></div>`;
    if(!paused){const id=s.id,partNumber=s.part;player=mountAudioPlayer({clipContext:{testId:s.testId,part:partNumber},saved:s.audio[partNumber],onSave:value=>{const target=sessionById(id);if(target&&!target.finished){target.audio[partNumber]=value;target.updated=Date.now();commit();}},notify});}
  }
  function start(testId,mockRun=null){
    const test=getListeningTest(testId);if(!test)return;
    const existing=state.sessions.find(s=>s.testId===testId&&!s.finished&&(mockRun?s.mockRun===mockRun.id:!s.mockRun));
    if(existing){location.hash=`listening/${existing.id}`;return;}
    modal(`Cambridge ${test.book} · Test ${test.number}`,`<p>${test.verified?'40 道听力题，已对照本地原卷与答案页核验。':'原卷配套练习：请打开原始 PDF 对照题号作答，提交后自行核对，不自动评分。'}</p><label for="study-mode">练习模式</label><select id="study-mode"><option value="study">学习模式 · 可暂停、回听与定位</option><option value="mock">模考练习 · 关闭快进和回退</option></select><p class="hint">整套练习计时 30 分钟，四段音频分别播放。退出会暂停，刷新保留计时与答案。</p>`,'开始练习',()=>{
      const mode=$('#study-mode').value;
      const s=newSession(test,mode);if(mockRun)s.mockRun=mockRun.id;state.sessions.push(s);resume(s);commit();location.hash=`listening/${s.id}`;
    });
  }
  function submit(timedOut=false){
    if(!current||current.finished||submitting)return;
    const s=current,test=getListeningTest(s.testId);
    const missing=40-test.parts.flatMap(p=>p.questions).reduce((n,q)=>n+answeredWeight(q,s.answers[q.id]),0);
    const finish=()=>{
      if(s.finished)return;submitting=true;
      disposePlayer();pause(s);s.finished=Date.now();s.updated=s.finished;if(!commit()){s.finished=null;submitting=false;$('#dialog').close();renderFocus(s);return;}$('#dialog').close();location.hash=`explanation/${s.id}`;submitting=false;
      if(timedOut)notify('练习计时结束，已保存并提交全部答案。');
    };
    if(timedOut)finish();else {
      const summary=listeningSummary(test,s);
      modal('交卷前检查',`<p>${missing?`还有 ${missing} 个计分点未完成。`:'全部题目已填写。'}提交后答案将不能修改。</p><div class="submit-parts">${summary.map(p=>`<div class="submit-part"><div><strong>Part ${p.part} · ${p.answered} / ${p.total}</strong><small>待填 ${p.missing} · 标记 ${p.flagged} 题组</small></div>${p.firstMissing?`<button class="btn" data-check-part="${p.part}" data-check-question="${esc(p.firstMissing)}">去检查</button>`:''}</div>`).join('')}</div><p class="hint">${test.verified?'根据录入答案核对，不换算 Band。':'资料未核验，交卷后保留作答，不自动评分。'}</p>`,'确认交卷',finish);
      $('#dialog').querySelectorAll('[data-check-part]').forEach(button=>button.onclick=()=>{$('#dialog').close();s.part=Number(button.dataset.checkPart);commit();renderFocus(s);const target=document.getElementById('study-q-'+button.dataset.checkQuestion);target?.scrollIntoView({block:'center'});target?.querySelector('input,select')?.focus({preventScroll:true});});
    }
  }
  function renderExplanation(s,qid){
    const test=getListeningTest(s.testId),results=resultsFor(test,s);
    const q=results.find(q=>q.id===qid)||results[0];explanationSession=s;current=null;retryItem=null;
    const correct=results.reduce((n,q)=>n+(q.score||0),0);const index=results.indexOf(q);
    const reason=state.diagnoses[`${s.id}:${q.id}`]||state.review.find(r=>r.key===keyFor(s,q))?.reason||'';
    const existing=state.review.some(r=>r.key===keyFor(s,q));
    shell(`${s.mockRun?'<p><a class="btn primary" href="/mock.html">返回整套进度 / 继续下一科</a></p>':''}<div class="intro journal-intro"><div><span class="eyebrow">PRACTICE → EXPLANATION → DIAGNOSE → REVIEW</span><h1>把答案，变成理解。</h1><p>Cambridge IELTS ${s.book} · Test ${s.test} · Listening</p></div><button class="btn" data-study="export" data-id="${s.id}">${icon('download')} 导出本次报告</button></div><div class="report-summary"><div><span>${test.verified?'答对题数':'核对状态'}</span><strong>${test.verified?`${correct}<small> / 40</small>`:'待核对'}</strong></div><div><span>练习用时</span><strong>${Math.ceil(s.elapsed/60000)}<small> 分钟</small></strong></div><div><span>下一步</span><a class="text-btn" href="#review">复习错题 ${icon('arrow')}</a></div><p>${test.verified?'依据本地答案判分；此页不推算 Band。':'本套答案尚未完成核验，请结合原卷与精讲核对。'}</p></div><div class="explanation-layout"><aside class="explanation-sidebar"><span class="eyebrow">QUESTION INDEX</span><div class="report-filter"><button class="btn" data-result-filter="all" aria-pressed="true">全部</button><button class="btn" data-result-filter="incorrect" aria-pressed="false">需复盘</button><button class="btn" data-result-filter="unknown" aria-pressed="false">待核对</button></div><div class="result-map">${results.map(item=>`<a href="#explanation/${s.id}/${item.id}" class="${item.score===null?'unknown':item.score===item.weight?'correct':'incorrect'} ${item.id===q.id?'selected':''}" aria-label="第 ${item.numbers?.join('、')||item.number} 题，${item.score===null?'待核对':item.score===item.weight?'正确':'需复习'}" ${item.id===q.id?'aria-current="true"':''}>${item.numbers?.join('–')||item.number}<small>${item.score===null?'—':item.score===item.weight?'✓':'×'}</small></a>`).join('')}</div><p class="hint">✓ 正确　× 错误 / 部分正确<br>— 尚未核对</p><a href="#library/${s.book}/${s.test}" class="text-btn">回到本套试卷</a></aside><div>${explanationPanel(q,q.given,q.score,q.weight,{documentURL:test.documentURL,reason,saved:state.saved.some(v=>v.key===keyFor(s,q)),inReview:existing,sourceURL:test.resources.explanations[0]?.url})}<div class="explanation-pagination">${index>0?`<a class="btn" href="#explanation/${s.id}/${results[index-1].id}">← 上一题</a>`:'<span></span>'}${index<results.length-1?`<a class="btn primary" href="#explanation/${s.id}/${results[index+1].id}">下一题 ${icon('arrow')}</a>`:'<a class="btn primary" href="#review">去复习错题 →</a>'}</div></div></div>`,'explanation');
  }
  function renderReview(filter='all'){
    current=null;explanationSession=null;retryItem=null;
    const list=filter==='saved'?state.saved:state.review.filter(r=>filter==='all'||r.status===filter);
    shell(`<div class="intro journal-intro"><div><span class="eyebrow">YOUR REVIEW JOURNAL</span><h1>把薄弱处，变成下一步。</h1><p>理解错因，然后给自己一次不看答案的机会。</p></div><span class="review-count">${state.review.filter(r=>r.status!=='mastered').length}<small>题待复习</small></span></div><div class="review-tabs" role="navigation" aria-label="复习状态">${[['all','全部错题'],['new','待复习'],['reviewing','复习中'],['mastered','已掌握'],['saved','收藏解析']].map(([id,label])=>`<a href="#review${id==='all'?'':'/'+id}" class="${filter===id?'active':''}" ${filter===id?'aria-current="page"':''}>${label} <span>${id==='saved'?state.saved.length:id==='all'?state.review.length:state.review.filter(r=>r.status===id).length}</span></a>`).join('')}</div><p><a class="btn" href="/listening-clips.html">我的精听收藏 ↗</a></p><div class="review-filter-line"><label for="review-skill">科目 <select id="review-skill"><option value="all">全部科目</option><option value="listening">Listening</option><option value="reading">Reading</option><option value="writing">Writing</option><option value="speaking">Speaking</option></select></label><span class="hint">本阶段先接通听力复习，其他科目保留扩展入口。</span></div><div id="review-list">${list.map(item=>{const test=getListeningTest(item.testId),q=findQuestion(test,item.questionId);if(!q)return '';return `<div data-review-skill="${item.skill||'listening'}">${filter==='saved'?`<article class="review-row"><div><span class="eyebrow">CAMBRIDGE ${test.book} · TEST ${test.number}</span><h3>Question ${q.numbers?.join('–')||q.number}</h3><p>${esc(q.prompt)}</p></div><a class="btn" href="#explanation/${item.sessionId}/${q.id}">阅读解析 ${icon('arrow')}</a></article>`:reviewItem(item,q)}</div>`;}).join('')}</div><div id="review-empty" class="review-empty" ${list.length?'hidden':''}>${icon('leaf')}<h2>${filter==='saved'?'把值得再读的解析，留在这里。':'这里，留给值得再做一次的题。'}</h2><p>${filter==='saved'?'在答案解析页点击「收藏解析」。':'完成练习后，在解析页标注错因并加入错题本。'}</p><a class="btn primary" href="#library/18/1">从一套听力开始 ${icon('arrow')}</a></div>`,'review');
  }
  function renderRetry(key){
    const item=state.review.find(r=>r.key===key);if(!item){shell('<h1>没有找到这道复习题</h1><a class="btn" href="#review">返回错题本</a>','review');return;}
    const test=getListeningTest(item.testId),q=findQuestion(test,item.questionId),part=test.parts.find(p=>p.questions.some(v=>v.id===q.id));
    retryItem=item;retryAnswer=q.type==='multiple'?[]:'';retrySubmitted=false;current=null;explanationSession=null;
    shell(`<a class="text-btn" href="#review">← 返回错题本</a><div class="intro journal-intro"><div><span class="eyebrow">RETRY WITHOUT LOOKING</span><h1>再试一次，把理解留住。</h1><p>Cambridge ${test.book} · Test ${test.number} · Listening Part ${part.number} · 第 ${item.count+1} 次复习</p></div></div><div class="retry-layout">${audioPlayer(test.resources.audio[part.number]?.url,'study')}<div class="note-box">重新听原音频并作答，提交后再看参考答案。此页未显示上次答案。</div><div id="retry-question">${questionRenderer(q,{},[],true)}</div><button class="btn primary" data-study="retry-submit">检查答案 ${icon('arrow')}</button><div id="retry-feedback" aria-live="polite"></div></div>`,'review');
    player=mountAudioPlayer({clipContext:{testId:test.id,part:part.number},onSave:()=>{},notify});
  }
  function historyView(){
    const sessions=state.sessions.filter(s=>s.finished).sort((a,b)=>b.finished-a.finished);
    if(!sessions.length)return '';
    return `<section class="cambridge-history"><div class="section-heading"><h2>Cambridge 练习记录 <span>${sessions.length} 次</span></h2></div>${sessions.map(s=>`<a class="activity-row" href="#explanation/${s.id}"><span class="activity-date">${new Date(s.finished).toLocaleDateString('zh-CN')}</span><div><strong>Cambridge ${s.book} · Test ${s.test} · Listening</strong><small>${getListeningTest(s.testId)?.verified?'已完成 · 可查看解析':'已提交 · 待自行核对'}</small></div>${icon('arrow')}</a>`).join('')}</section>`;
  }
  function render(next){
    route=next;current=null;retryItem=null;explanationSession=null;
    if(next.startsWith('mock-listening/')){try{const run=requireMockStage(next.slice(15),'listening');shell('<h1>开始整套听力练习</h1><a class="btn" href="/mock.html">返回整套进度</a>','library');start(`c${run.book}-t${run.test}-listening`,run);}catch(e){shell(`<p>${esc(e.message)}</p><a href="/mock.html">返回整套进度</a>`,'library');}return true;}
    if(next==='library'){shell(libraryView(state),'library');mountCatalog();return true;}
    const detail=next.match(/^library\/(\d+)\/([1-4])$/);
    if(detail){const book=Number(detail[1]),test=Number(detail[2]);if(getTestResources(book,test)){state.recent=[{book,test},...state.recent.filter(v=>v.book!==book||v.test!==test)].slice(0,6);commit();}shell(testDetailView(book,test,state),'library');mountCatalog();return true;}
    if(next.startsWith('listening/')){const s=sessionById(next.slice(10));if(!s){shell('<h1>未找到本地练习</h1><a href="#library" class="btn">回到题库</a>','library');}else if(s.finished){location.hash=`explanation/${s.id}`;}else renderFocus(s);return true;}
    if(next.startsWith('explanation/')){const [,id,qid]=next.split('/'),s=sessionById(id);if(s?.finished)renderExplanation(s,qid);else shell('<h1>未找到已提交的练习</h1><a href="#library" class="btn">回到题库</a>','explanation');return true;}
    if(next==='review'||next.startsWith('review/')){renderReview(next.split('/')[1]||'all');return true;}
    if(next.startsWith('retry/')){renderRetry(decodeURIComponent(next.slice(6)));return true;}
    return false;
  }
  function updateProgress(){
    if(!current)return;
    const test=getListeningTest(current.testId);
    $('#question-map').innerHTML=questionNavigator(test,current,current.part);
    $('#study-progress').textContent=test.parts.flatMap(p=>p.questions).reduce((n,q)=>n+answeredWeight(q,current.answers[q.id]),0)+' / 40';
  }
  document.addEventListener('input',e=>{
    const el=e.target;
    if(el.id==='book-filter'){
      const value=el.value.trim().toLowerCase().replace(/cambridge|ielts|剑雅?|\s/g,'');let visible=0;
      document.querySelectorAll('[data-book]').forEach(row=>{row.hidden=Boolean(value&&!row.dataset.book.includes(value));if(!row.hidden)visible++;});$('#book-empty').hidden=visible>0;return;
    }
    if(el.dataset.response){
      const test=getListeningTest(current?.testId||retryItem?.testId);if(!test)return;
      const q=findQuestion(test,el.dataset.response);if(!q||(!current&&!retryItem)||current&&!current.deadline||retrySubmitted)return;
      let value=el.value;
      if(q.type==='multiple'){
        const previous=current?.answers[q.id]||retryAnswer||[];value=Array.isArray(previous)?[...previous]:[];
        if(el.checked){if(value.length>=q.maxChoices){el.checked=false;notify(`本题最多选择 ${q.maxChoices} 项。`);return;}value.push(el.value);}else value=value.filter(v=>v!==el.value);
      }
      if(current){current.answers[q.id]=value;current.updated=Date.now();const saved=commit();$('#study-save').textContent=saved?'已自动保存':'保存失败，请勿关闭页面';updateProgress();}else retryAnswer=value;
    }
  });
  document.addEventListener('change',e=>{
    const el=e.target;
    if(el.dataset.diagnose&&explanationSession){state.diagnoses[`${explanationSession.id}:${el.dataset.diagnose}`]=el.value;commit();}
    if(el.id==='review-skill'){let visible=0;document.querySelectorAll('[data-review-skill]').forEach(row=>{row.hidden=el.value!=='all'&&row.dataset.reviewSkill!==el.value;if(!row.hidden)visible++;});$('#review-empty').hidden=visible>0;}
  });
  document.addEventListener('click',e=>{
    const filter=e.target.closest('[data-result-filter]');if(filter){document.querySelectorAll('[data-result-filter]').forEach(b=>b.setAttribute('aria-pressed',String(b===filter)));document.querySelectorAll('.result-map a').forEach(a=>a.hidden=filter.dataset.resultFilter!=='all'&&!a.classList.contains(filter.dataset.resultFilter));return;}

    const el=e.target.closest('[data-study]');if(!el)return;
    const action=el.dataset.study;
    if(action==='start'){start(el.dataset.test);return;}
    if(action==='pause'&&current){if(current.deadline){player?.pause();pause(current);}else resume(current);renderFocus(current);return;}
    if((action==='part'||action==='jump')&&current&&current.deadline){
      const part=Number(el.dataset.part);if(part<1||part>4)return;
      if(part!==current.part){disposePlayer();current.part=part;current.updated=Date.now();commit();renderFocus(current);window.scrollTo(0,0);}
      if(el.dataset.q){const q=$(`#study-q-${el.dataset.q}`);q?.scrollIntoView({block:'center'});q?.querySelector('input,select')?.focus({preventScroll:true});}return;
    }
    if(action==='flag'&&current){const q=el.dataset.q;current.flags=current.flags.includes(q)?current.flags.filter(v=>v!==q):[...current.flags,q];commit();el.classList.toggle('selected',current.flags.includes(q));el.setAttribute('aria-pressed',current.flags.includes(q));updateProgress();return;}
    if(action==='submit'){submit();return;}
    if(action==='add-review'&&explanationSession){
      const q=findQuestion(getListeningTest(explanationSession.testId),el.dataset.q),reason=$('[data-diagnose]').value;
      state.review=addReview(state.review,q,explanationSession,reason);if(commit()){el.innerHTML=`已在错题本 · 更新错因 ${icon('check')}`;notify('已加入错题本，可以不看答案重新练习。');}return;
    }
    if(action==='save-explanation'&&explanationSession){
      const key=`${explanationSession.testId}:${el.dataset.q}`;
      if(state.saved.some(v=>v.key===key)){state.saved=state.saved.filter(v=>v.key!==key);el.textContent='收藏解析';}
      else{state.saved.push({key,testId:explanationSession.testId,questionId:el.dataset.q,sessionId:explanationSession.id,skill:'listening'});el.textContent='已收藏 · 取消';}commit();return;
    }
    if(action==='master'){
      const item=state.review.find(v=>v.key===el.dataset.key);if(!item)return;
      item.status=item.status==='mastered'?'reviewing':'mastered';item.updated=Date.now();commit();renderReview(route.split('/')[1]||'all');return;
    }
    if(action==='retry-submit'&&retryItem&&!retrySubmitted){
      const q=findQuestion(getListeningTest(retryItem.testId),retryItem.questionId);if(!isAnswered(retryAnswer)){notify('先填写答案，再检查。');return;}
      if(!getListeningTest(retryItem.testId).verified){
        retrySubmitted=true;el.disabled=true;
        $('#retry-feedback').textContent='答案待核验，本次不自动判分或标记掌握。请对照原卷核对。';
        retryItem.lastRetry=retryAnswer;retryItem.updated=Date.now();commit();return;
      }
      const updated=applyRetry(retryItem,q,retryAnswer);state.review=state.review.map(v=>v.key===updated.key?updated:v);commit();retrySubmitted=true;el.disabled=true;
      document.querySelectorAll('[data-response]').forEach(input=>input.disabled=true);
      $('#retry-feedback').innerHTML=`<div class="retry-result"><h2>${updated.status==='mastered'?'这一次，答对了。':'再看一次证据，找到差距。'}</h2><p>本题答对 ${updated.retryScore} / ${questionWeight(q)} · 参考答案：${esc(q.accepted.join(' + '))}</p><p>${esc(q.explanation?.why||'请对照原始答案核对。')}</p><p>复习次数：${updated.count} · 状态：${REVIEW_STATES[updated.status]}</p><a class="btn primary" href="#review">返回错题本 ${icon('arrow')}</a> <a class="text-btn" href="#explanation/${updated.sessionId}/${q.id}">查看完整解析</a></div>`;return;
    }
    if(action==='export'){
      const s=sessionById(el.dataset.id);if(!s)return;const test=getListeningTest(s.testId);
      const result={title:test.title,mode:s.mode,finished:new Date(s.finished).toISOString(),scored:test.verified,results:resultsFor(test,s).map(q=>({number:q.numbers||q.number,prompt:q.prompt,given:q.given||'',correct:q.accepted,score:q.score,weight:q.weight,explanation:q.explanation||null,mistakeType:state.diagnoses[`${s.id}:${q.id}`]||''}))};
      const url=URL.createObjectURL(new Blob([JSON.stringify(result,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download=`${test.id}-${s.id}.json`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
    }
  });
  setInterval(()=>{if(current?.deadline&&!current.finished){const left=remaining(current);if($('#study-timer')){$('#study-timer').textContent=formatTime(left);$('#study-timer').classList.toggle('urgent',left<=60);}if(!left)submit(true);}},500);
  window.addEventListener('beforeunload',()=>{disposePlayer();commit();});
  return {render,getState:()=>state,historyView,leave(){disposePlayer();pause(current);current=null;retryItem=null;explanationSession=null;}};
}
