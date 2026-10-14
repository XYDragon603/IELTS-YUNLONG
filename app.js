import { localPracticeLinks } from './ui/import-catalog.js';
import { icon } from './ui/icons.js';
import { shell } from './ui/layout.js';
import { studioHome } from './ui/studio-home.js';
import { createStudy } from './features/study.js';
import { SECTIONS, createAttempt, secondsLeft, grade, wordCount, escapeHTML as esc, formatTime } from './core.js';
import { listeningScript, listeningQuestions, readingParagraphs, readingQuestions, writingPrompt, speakingPrompt } from './data.js';

const $ = selector => document.querySelector(selector);
let storageFailed = false;
function read(key, fallback) { try { return JSON.parse(localStorage.getItem(key)) ?? fallback; } catch { return fallback; } }
let attempt = read('ielts-attempt', null);
if (attempt && (!Array.isArray(attempt.sections) || !attempt.sections.every(id => SECTIONS.some(s => s.id === id)) || !attempt.sections[attempt.index] || !attempt.answers || !Array.isArray(attempt.flags))) attempt = null;
let history = read('ielts-history', []);
if (!Array.isArray(history)) history = [];
let target = read('ielts-target', 7);
let recorder = null, recording = false, acquiringMic = false, recordingStart = 0, chunks = [], stream = null, stopPromise = null;
let activeURL = null, speaking = false, audioToken = 0, advancing = false;
let route = '';
function save(key, value) {
  try { localStorage.setItem(key, JSON.stringify(value)); return true; }
  catch { if (!storageFailed) notify('浏览器无法保存进度，请保持此页面打开，并在完成后导出报告。'); storageFailed = true; return false; }
}
function saveAttempt() { save('ielts-attempt', attempt); }
function notify(message) {
  $('#notice').textContent = message; $('#notice').classList.add('show');
  clearTimeout(notify.timer); notify.timer = setTimeout(() => $('#notice').classList.remove('show'), 5500);
}
function modal(title, body, confirmText, action) {
  const dialog = $('#dialog');
  dialog.innerHTML = `<h2 id="dialog-title">${title}</h2>${body}<div class="dialog-actions"><button class="btn" id="cancel-modal">取消</button><button class="btn primary" id="confirm-modal">${confirmText}</button></div>`;
  $('#cancel-modal').onclick = () => dialog.close();
  $('#confirm-modal').onclick = async () => { dialog.close(); await action(); };
  dialog.showModal();
}
function section() { return SECTIONS.find(s => s.id === attempt?.sections[attempt.index]); }
function questions(id) { return id === 'listening' ? listeningQuestions : id === 'reading' ? readingQuestions : []; }
function answeredCount() { return questions(section()?.id).filter(q => String(attempt.answers[q.id] || '').trim()).length; }
function date(value, full = false) { return new Intl.DateTimeFormat('zh-CN', { month: 'long', day: 'numeric', ...(full ? { hour: '2-digit', minute: '2-digit' } : {}) }).format(new Date(value)); }
function elapsed(a) { return Math.round((a.elapsed + (!a.paused && !a.finished ? Date.now() - a.lastResumed : 0)) / 60000); }

function subjectCards() {
  return `<div class="subjects">${SECTIONS.map((s,i)=>`<article class="subject"><span class="subject-icon ${s.color}">${icon(s.icon)}</span><h3>${s.name}<span>${s.english}</span></h3><p>${s.detail} · 示例练习</p><div class="subject-bottom"><span>${s.duration/60} 分钟 / 单项练习</span><button class="round-button" data-start="${s.id}" aria-label="开始${s.name}练习">${icon('arrow')}</button></div></article>`).join('')}</div>`;
}
function resumeBanner() {
  return attempt ? `<div class="resume-banner"><div>你有一场尚未完成的练习<small>${attempt.sections.length===4?'全科模考':'单项练习'} · 当前科目：${section().name} · ${attempt.paused?'已暂停':'计时中'}</small></div><a class="btn primary small" href="#exam">继续练习 ${icon('arrow')}</a></div>` : '';
}
function historyRows(items) {
  if (!items.length) return `<div class="empty"><span class="empty-icon">${icon('chart')}</span><div><h3>你的第一份练习记录，从这里开始</h3><p>完成一次模考，查看答题结果与复盘建议。</p><button class="text-btn" data-start="all">开始第一次模考 ${icon('arrow')}</button></div></div>`;
  return items.map(a=>`<div class="history-row">${icon(a.sections.length===4?'book':SECTIONS.find(s=>s.id===a.sections[0]).icon)}<div class="history-text"><h3>${a.sections.length===4?'全科模考':SECTIONS.find(s=>s.id===a.sections[0]).name+'单项练习'} · 示例卷 01</h3><p>${date(a.finished,true)} · 练习 ${elapsed(a)} 分钟</p></div><a class="btn small" href="#report/${a.id}">查看复盘 ${icon('arrow')}</a></div>`).join('');
}
function home() {
  shell(studioHome());
}
function practice() {
  shell(`<div class="intro"><div><div class="eyebrow">BUILD YOUR SKILLS</div><h1>把专注，留给这一科。</h1><p>选择你想练习的科目，按自己的节奏开始。</p></div></div>${resumeBanner()}${subjectCards()}<section class="panel practice-info"><h2>关于这套示例练习</h2><p class="hint">当前提供一套原创学术类缩减题目，用于体验四科流程，题量与时长均不等同于正式考试。听力使用浏览器合成英文语音，可重复播放；阅读支持标记待检查题目。</p><p class="hint">写作与口语提供字数统计、录音及自查清单，暂未接入人工或 AI 评分。听读结果仅展示正确率，不换算雅思分数。</p><button class="btn primary" data-start="all">体验完整流程 ${icon('arrow')}</button></section>`, 'practice');
}
function historyPage() {
  shell(`<div class="intro"><div><div class="eyebrow">YOUR LEARNING JOURNEY</div><h1>每一次投入，都有回响。</h1><p>已完成 ${history.length} 次练习 · 累计 ${history.reduce((sum,a)=>sum+elapsed(a),0)} 分钟。记录仅保存在当前浏览器。</p></div></div>${localPracticeLinks()}${study.historyView()}${resumeBanner()}<section class="panel">${historyRows(history)}</section>`, 'history');
}
function start(id) {
  const begin = () => { attempt = createAttempt(id==='all'?null:id); saveAttempt(); if(location.hash==='#exam') render(); else location.hash='exam'; };
  if (attempt) modal('开始新的练习？','<p>这会替换当前未完成的练习，包括已填写的答案。你也可以取消后继续原来的练习。</p>','开始新练习',begin);
  else modal(id==='all'?'准备好开始全科模考了吗？':'开始单项练习',`<p>${id==='all'?'按听力、阅读、写作、口语的顺序完成，示例总计 26 分钟。':'该科目使用缩减示例题与练习计时。'}你可以随时暂停；计时结束会提交当前科目。</p><p>听力需要开启声音，口语录音需要麦克风权限。文字答案会自动保存到此浏览器。</p>`,'开始练习',begin);
}
function listeningPanel() {
  return `<div class="exam-panel"><span class="eyebrow">PART 1 · FORM COMPLETION</span><h2>A photography course</h2><p class="english">Listen to the announcement about a photography course at a community centre.</p><div class="audio-card"><div class="wave" id="wave" aria-hidden="true">${Array.from({length:32},(_,i)=>`<i style="--h:${12+((i*19)%45)}px;--delay:${i*.035}s"></i>`).join('')}</div><div class="audio-controls"><button class="btn primary" data-action="listen" id="listen-btn">${icon('play')} 播放示例音频</button><button class="btn" data-action="stop-audio">停止</button></div><p class="audio-status" id="audio-status" role="status">浏览器合成语音 · 英文 · 可重播</p></div><p class="hint">先阅读题目，留意日期、数字和拼写。填写不超过两个单词和／或一个数字。</p><details><summary class="text-btn">无法播放？查看文字稿</summary><p class="english">${listeningScript}</p><p class="hint">使用文字稿后，本次听力仅作流程体验。</p></details></div>`;
}
function questionPanel(id) {
  return `<div class="exam-panel"><span class="eyebrow">QUESTIONS 1–5</span><h2>${id==='listening'?'Complete the notes':'True, False or Not Given?'}</h2><p class="hint">${id==='listening'?'填写答案，点击旗帜可标记稍后检查。':'TRUE：与原文相符；FALSE：与原文矛盾；NOT GIVEN：文中未提供。'}</p>${questions(id).map((q,i)=>`<div class="question" id="q-${q.id}"><div class="question-top"><span class="q-num">${i+1}</span><label ${id==='listening'?`for="answer-${q.id}"`:`id="label-${q.id}"`}>${q.prompt}</label><button class="flag ${attempt.flags.includes(q.id)?'selected':''}" data-flag="${q.id}" aria-label="标记第 ${i+1} 题" aria-pressed="${attempt.flags.includes(q.id)}">${icon('flag')}</button></div>${id==='listening'?`<input type="text" id="answer-${q.id}" data-answer="${q.id}" value="${esc(attempt.answers[q.id] || '')}" autocomplete="off" spellcheck="false" placeholder="输入英文答案">`:`<div class="choices" role="radiogroup" aria-labelledby="label-${q.id}">${['TRUE','FALSE','NOT GIVEN'].map(option=>`<label class="choice"><input type="radio" name="${q.id}" data-answer="${q.id}" value="${option}" ${attempt.answers[q.id]===option?'checked':''}>${option}</label>`).join('')}</div>`}</div>`).join('')}</div>`;
}
function readingPanel() {
  return `<article class="exam-panel"><span class="eyebrow">READING PASSAGE · ORIGINAL SAMPLE</span><h2>The growth of community gardens</h2>${readingParagraphs.map(p=>`<p class="english">${p}</p>`).join('')}</article>`;
}
function writingPanels() {
  return `<section class="exam-panel"><span class="eyebrow">WRITING · TASK 2 SAMPLE</span><h2>Public libraries in a digital world</h2><p class="english">${writingPrompt}</p><p class="english">Give reasons for your answer and include any relevant examples from your own knowledge or experience.</p><div class="note-box">示例练习时间为 10 分钟。可以先完成提纲或一段正文，目标字数为 250 词。</div><h3>动笔前想一想</h3><ul class="hint"><li>两种观点分别有哪些理由？</li><li>你的立场是什么？</li><li>用什么具体例子来支持论点？</li></ul></section><section class="exam-panel"><label for="essay"><h2>你的作文</h2></label><textarea id="essay" data-answer="essay" lang="en" spellcheck="true" placeholder="Start writing your response here…">${esc(attempt.answers.essay||'')}</textarea><div class="writing-meta"><span><strong id="word-count">${wordCount(attempt.answers.essay)}</strong> words / 250 词目标</span><span id="essay-save">已保存到本地</span></div><p class="hint">本版仅提供字数统计和自查建议，未接入作文评分。</p></section>`;
}
function speakingPanels() {
  return `<section class="exam-panel"><span class="eyebrow">SPEAKING · CUE CARD</span><h2>Describe a skill you would like to learn.</h2><p class="english">You should say:</p><ul class="english">${speakingPrompt.map(p=>`<li>${p}</li>`).join('')}</ul><div class="note-box">建议准备 1 分钟，再连续讲述 1–2 分钟。你可以先写关键词，然后开始录音。</div><label for="notes" class="hint">准备笔记（英文关键词）</label><textarea id="notes" data-answer="notes" style="min-height:120px" placeholder="A few keywords to guide your response…">${esc(attempt.answers.notes||'')}</textarea></section><section class="exam-panel"><span class="eyebrow">YOUR VOICE, YOUR PROGRESS</span><h2>自信开口，从这一次开始。</h2><div class="record-circle" id="record-circle">${icon('mic')}</div><div class="record-actions"><button class="btn primary" data-action="record" id="record-btn">${icon('mic')} ${attempt.hasRecording?'重新录音':'开始录音'}</button><button class="btn" data-action="stop-record" id="stop-record-btn" disabled>结束录音</button></div><p class="record-status" id="record-status" role="status">${attempt.hasRecording?'已保存录音，可回放或重新录制':'点击开始后，允许浏览器使用麦克风'}</p><div id="record-player"></div><p class="hint">录音只保存在当前浏览器，提交后可在复盘页面回放与下载。重新录制会替换上一段录音。</p><p class="hint">如果无法使用麦克风，可以填写准备笔记并继续；未录音会在报告中如实标记。</p></section>`;
}
function exam() {
  if (!attempt) { location.hash='home'; return; }
  const s = section();
  shell(`<div class="exam-header"><div><span class="eyebrow">ACADEMIC · SAMPLE TEST 01</span><h1>${s.name} <span style="font-weight:400">/ ${s.english}</span></h1><span class="hint">缩减示例卷 · ${s.duration/60} 分钟</span></div><div class="timer-block"><span class="timer" id="timer" aria-label="剩余时间">${formatTime(secondsLeft(attempt))}</span><button class="btn small" data-action="pause">${icon(attempt.paused?'play':'pause')}${attempt.paused?'继续':'暂停'}</button></div></div><div class="stepper" aria-label="模考进度">${attempt.sections.map((id,i)=>`<div class="step ${i===attempt.index?'active':''}" ${i===attempt.index?'aria-current="step"':''}><span class="step-number">${i<attempt.index?'✓':i+1}</span>${SECTIONS.find(s=>s.id===id).name}<span>${i<attempt.index?'已提交':''}</span></div>`).join('')}</div>${attempt.paused?`<div class="panel pause-panel">${icon('pause')}<h2>休息一下，再继续。</h2><p>计时已暂停，答案已保存。<br>准备好后，回到你的练习节奏。</p><button class="btn primary" data-action="pause">继续练习 ${icon('arrow')}</button></div>`:`<div class="exam-layout">${s.id==='listening'?listeningPanel()+questionPanel('listening'):s.id==='reading'?readingPanel()+questionPanel('reading'):s.id==='writing'?writingPanels():speakingPanels()}</div><div class="exam-footer"><div>${questions(s.id).length?`<div class="question-nav" aria-label="题号导航">${questions(s.id).map((q,i)=>`<button class="q-jump ${attempt.answers[q.id]?'answered':''} ${attempt.flags.includes(q.id)?'flagged':''}" data-jump="${q.id}" aria-label="跳转第 ${i+1} 题">${i+1}</button>`).join('')}</div>`:`<span class="hint">${s.id==='writing'?'提交后可在复盘中查看作文。':'提交前请结束录音。'}</span>`}<div class="save-state" id="save-state">${questions(s.id).length?`已作答 ${answeredCount()} / 5 · `:''}答案自动保存在本地</div></div><button class="btn primary" data-action="next" id="next-btn">${attempt.index===attempt.sections.length-1?'提交并查看复盘':'提交并进入下一科'} ${icon('arrow')}</button></div>`}`, 'exam');
  if(s.id==='speaking'&&!attempt.paused) loadRecording(attempt.id);
}
function stopAudio() {
  audioToken++; speaking=false;
  if('speechSynthesis' in window) speechSynthesis.cancel();
  if($('#wave')) $('#wave').classList.remove('playing');
  if($('#listen-btn')) $('#listen-btn').disabled=false;
  if($('#audio-status')) $('#audio-status').textContent='已停止，可重新播放';
}
function listen() {
  if(!('speechSynthesis' in window)) { notify('当前浏览器不支持合成语音，请展开文字稿体验流程。'); return; }
  stopAudio();
  const token=audioToken;
  const utterance=new SpeechSynthesisUtterance(listeningScript);
  utterance.lang='en-GB'; utterance.rate=.88;
  const voice=speechSynthesis.getVoices().find(v=>v.lang==='en-GB') || speechSynthesis.getVoices().find(v=>v.lang.startsWith('en'));
  if(voice) utterance.voice=voice;
  speaking=true;
  $('#listen-btn').disabled=true; $('#wave').classList.add('playing'); $('#audio-status').textContent='正在播放 · 请填写右侧答案';
  utterance.onend=()=>{if(token!==audioToken)return;stopAudio();if($('#audio-status'))$('#audio-status').textContent='播放完成，可以重播检查';};
  utterance.onerror=()=>{if(token!==audioToken)return;stopAudio();notify('语音播放失败，请检查设备声音，或展开文字稿继续。');};
  speechSynthesis.speak(utterance);
}
function pauseTimer() {
  if (!attempt || attempt.paused) return;
  attempt.remaining=secondsLeft(attempt); attempt.elapsed+=Date.now()-attempt.lastResumed; attempt.paused=true;saveAttempt();
}
async function togglePause() {
  if(attempt.paused){attempt.deadline=Date.now()+attempt.remaining*1000;attempt.lastResumed=Date.now();attempt.paused=false;saveAttempt();}
  else {pauseTimer();stopAudio();await stopRecording();}
  exam();
}
function requestNext() {
  if(recording||acquiringMic){notify('请先结束录音，保存后再提交。');return;}
  const qs=questions(section().id),missing=qs.length-answeredCount();
  const missingText=qs.length&&missing?`还有 ${missing} 道题未作答，未作答的题目会记为错误。`:section().id==='writing'&&!wordCount(attempt.answers.essay)?'你还没有输入作文。':section().id==='speaking'&&!attempt.hasRecording?'本次没有录音，报告中会显示未录音。':'请确认已经检查好本部分的作答。';
  modal('提交当前科目？',`<p>${missingText}</p><p>提交后将无法修改本部分答案。</p>`,'确认提交',()=>advance());
}
async function advance(timedOut=false) {
  if(advancing||!attempt)return;
  advancing=true;
  try {
    $('#dialog').close(); stopAudio(); pauseTimer(); await stopRecording();
    attempt.completed.push(section().id);
    if(attempt.index===attempt.sections.length-1){
      const finished={...attempt,finished:Date.now(),paused:true};
      history.unshift(finished);save('ielts-history',history);attempt=null;saveAttempt();location.hash=`report/${finished.id}`;
    } else {
      attempt.index++;attempt.remaining=section().duration;attempt.paused=true;saveAttempt();exam();
    }
    if(timedOut)notify('本部分计时结束，已自动提交。');
  } finally {advancing=false;}
}

let dbPromise;
function database(){
  if(!dbPromise) dbPromise=new Promise((resolve,reject)=>{
    const req=indexedDB.open('ielts-studio-audio',1);
    req.onupgradeneeded=()=>req.result.createObjectStore('recordings');
    req.onsuccess=()=>resolve(req.result);req.onerror=()=>reject(req.error);
  });
  return dbPromise;
}
async function putRecording(id,blob){
  const db=await database();
  await new Promise((resolve,reject)=>{const tx=db.transaction('recordings','readwrite');tx.objectStore('recordings').put(blob,id);tx.oncomplete=resolve;tx.onerror=()=>reject(tx.error);tx.onabort=()=>reject(tx.error);});
}
async function getRecording(id){
  const db=await database();
  return new Promise((resolve,reject)=>{const req=db.transaction('recordings').objectStore('recordings').get(id);req.onsuccess=()=>resolve(req.result);req.onerror=()=>reject(req.error);});
}
async function loadRecording(id){
  try{
    const blob=await getRecording(id);
    if(!$('#record-player')||!route.includes(id)&&!(route==='exam'&&attempt?.id===id))return;
    if(!blob){
      if(route.startsWith('report/'))$('#record-player').innerHTML='<p class="hint">未找到本地录音，音频可能已被浏览器清理。</p>';
      return;
    }
    if(activeURL)URL.revokeObjectURL(activeURL);activeURL=URL.createObjectURL(blob);
    $('#record-player').innerHTML=`<audio controls src="${activeURL}" aria-label="口语录音回放"></audio><a class="text-btn" href="${activeURL}" download="ielts-speaking-${id}.${blob.type.includes('mp4')?'m4a':blob.type.includes('ogg')?'ogg':'webm'}">${icon('download')} 下载录音</a>`;
  }catch{if($('#record-status'))$('#record-status').textContent='无法读取本地录音，请检查浏览器存储权限。';if(route.startsWith('report/')&&$('#record-player'))$('#record-player').innerHTML='<p class="hint">无法读取本地录音，请检查浏览器存储权限。</p>';}
}
async function startRecording(){
  if(recording||acquiringMic)return;
  if(!navigator.mediaDevices?.getUserMedia||!window.MediaRecorder){notify('此浏览器不支持录音。请使用 localhost 或 HTTPS 上的新版浏览器，或填写笔记后继续。');return;}
  const id=attempt.id;
  acquiringMic=true;$('#record-btn').disabled=true;$('#record-status').textContent='正在等待麦克风授权…';
  try{
    const incoming=await navigator.mediaDevices.getUserMedia({audio:true});
    if(!attempt||attempt.id!==id||route!=='exam'||attempt.paused||section().id!=='speaking'){incoming.getTracks().forEach(t=>t.stop());return;}
    stream=incoming;chunks=[];recorder=new MediaRecorder(stream);
    recorder.ondataavailable=e=>{if(e.data.size)chunks.push(e.data);};
    recorder.onerror=()=>{notify('录音发生错误，请重试。');stopRecording();};
    stopPromise=new Promise(resolve=>{
      recorder.onstop=async()=>{
        stream?.getTracks().forEach(t=>t.stop());stream=null;recording=false;
        try{
          const blob=new Blob(chunks,{type:recorder.mimeType||'audio/webm'});
          if(!blob.size)throw new Error('Empty recording');
          await putRecording(id,blob);
          if(attempt?.id===id){attempt.hasRecording=true;attempt.recordingSeconds=Math.round((Date.now()-recordingStart)/1000);saveAttempt();}
          if($('#record-status'))$('#record-status').textContent='录音已保存，可以回放或重新录制';
          await loadRecording(id);
        }catch{notify('录音未能保存，请检查浏览器存储空间后重试。');}
        finally{recordingUI(false);resolve();}
      };
    });
    recorder.start();recording=true;recordingStart=Date.now();recordingUI(true);
  }catch(error){stream?.getTracks().forEach(t=>t.stop());stream=null;notify(error.name==='NotAllowedError'?'麦克风权限被拒绝。请在浏览器地址栏允许麦克风后重试。':'无法访问麦克风，请检查设备连接后重试。');if($('#record-status'))$('#record-status').textContent='录音未开始，可重试或填写笔记继续';}
  finally{acquiringMic=false;if($('#record-btn')&&!recording)$('#record-btn').disabled=false;}
}
function recordingUI(on){
  if($('#record-btn')){$('#record-btn').disabled=on;$('#record-btn').innerHTML=`${icon('mic')} ${attempt?.hasRecording?'重新录音':'开始录音'}`;}
  if($('#stop-record-btn'))$('#stop-record-btn').disabled=!on;
  if($('#record-circle'))$('#record-circle').classList.toggle('recording',on);
}
async function stopRecording(){
  if(recorder&&recorder.state!=='inactive') {recorder.stop();recording=false; if($('#record-status'))$('#record-status').textContent='正在保存录音…';}
  if(stopPromise)await stopPromise;
}

function report(id){
  const a=history.find(a=>a.id===id);
  if(!a){shell('<div class="panel"><h1>未找到这份练习记录</h1><p class="hint">记录只保存在完成练习的浏览器中。</p><a class="btn" href="#history">返回练习记录</a></div>','report');return;}
  const autoSections=a.sections.filter(id=>questions(id).length);
  const total=autoSections.flatMap(id=>grade(questions(id),a.answers));
  shell(`<div class="intro"><div><span class="eyebrow">WELL DONE. KEEP GOING.</span><h1>又向前走了一步。</h1><p>${date(a.finished,true)} · ${a.sections.length===4?'全科模考':'单项练习'} · 示例卷 01</p></div><button class="btn" data-export="${a.id}">${icon('download')} 导出报告</button></div><div class="note-box">本报告来自缩减示例题。听力与阅读仅展示答题正确率，不换算雅思 Band；写作与口语尚未评分。</div><div class="results-overview">${autoSections.map(id=>`<div class="result-stat"><p>${SECTIONS.find(s=>s.id===id).name} · 答对题数</p><strong>${grade(questions(id),a.answers).filter(q=>q.correct).length}<span class="hint"> / 5</span></strong><small>原创示例题</small></div>`).join('')}${a.sections.includes('writing')?`<div class="result-stat"><p>写作 · 英文词数</p><strong>${wordCount(a.answers.essay)}</strong><small>目标 250 词 · 待评估</small></div>`:''}${a.sections.includes('speaking')?`<div class="result-stat"><p>口语 · 录音时长</p><strong>${a.hasRecording?formatTime(a.recordingSeconds||0):'未录音'}</strong><small>自查练习 · 待评估</small></div>`:''}</div>${autoSections.map(id=>`<section class="panel review-section"><h2>${SECTIONS.find(s=>s.id===id).name}答案与解析</h2>${grade(questions(id),a.answers).map((q,i)=>`<div class="review-item"><h3><span class="status-tag ${q.correct?'':'wrong'}">${q.correct?'正确':q.given?'错误':'未作答'}</span>${i+1}. ${q.prompt}</h3><p>你的答案：<strong>${esc(q.given)||'未填写'}</strong> · 参考答案：<strong>${q.accepted[0]}</strong></p><p>${q.explanation}</p></div>`).join('')}<details><summary class="text-btn">查看${id==='listening'?'听力文字稿':'阅读原文'}</summary>${(id==='listening'?[listeningScript]:readingParagraphs).map(p=>`<p class="hint">${p}</p>`).join('')}</details></section>`).join('')}${a.sections.includes('writing')?`<section class="panel review-section"><h2>写作复盘</h2><p class="hint">${writingPrompt}</p><div class="submitted-text">${esc(a.answers.essay)||'本次未提交作文。'}</div><div class="note-box">${wordCount(a.answers.essay)<250?'目前少于 250 词，下一步可以补充论证与例子。':'已达到 250 词目标，下一步请检查论证与表达。'}<br>自查：是否讨论了双方观点？立场是否清晰？每段是否围绕一个主旨？例子是否支持论点？</div><p class="hint">以上是通用自查清单，不代表对这篇作文的质量评分。</p></section>`:''}${a.sections.includes('speaking')?`<section class="panel review-section"><h2>口语复盘</h2><p class="hint">Describe a skill you would like to learn.</p><div id="record-player">${a.hasRecording?'<p class="hint">正在读取本地录音…</p>':'<p class="hint">本次未录音，可以在下次练习中允许麦克风权限。</p>'}</div><h3>准备笔记</h3><div class="submitted-text">${esc(a.answers.notes)||'未填写笔记。'}</div><div class="note-box">自查：有没有覆盖话题卡的全部要点？是否用了具体细节？能否减少过长停顿？回听时挑选一句表达，再尝试说得更清晰。</div></section>`:''}<a class="btn primary" href="#home">回到学习概览 ${icon('arrow')}</a>`, 'report');
  if(a.hasRecording)loadRecording(a.id);
}
function exportReport(id){
  const a=history.find(a=>a.id===id);if(!a)return;
  const text=['IELTS Studio · 示例练习报告',date(a.finished,true),'缩减原创题目，不代表官方雅思分数。',...a.sections.flatMap(id=>questions(id).length?[`\n${SECTIONS.find(s=>s.id===id).name}`,...grade(questions(id),a.answers).map((q,i)=>`${i+1}. ${q.prompt}\n你的答案：${q.given||'未作答'} | 参考答案：${q.accepted[0]} | ${q.correct?'正确':'错误'}\n${q.explanation}`)]:id==='writing'?[`\n写作（未评分）：${wordCount(a.answers.essay)} 词\n题目：${writingPrompt}\n${a.answers.essay||'未填写'}`]:[`\n口语（未评分）：${a.hasRecording?'已录音，请在报告页单独下载音频':'未录音'}\n笔记：${a.answers.notes||'未填写'}`])].join('\n');
  const url=URL.createObjectURL(new Blob(['\uFEFF'+text],{type:'text/plain;charset=utf-8'}));
  const link=document.createElement('a');link.href=url;link.download=`IELTS-report-${id}.txt`;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
function updateAnswerUI(){
  if($('#word-count'))$('#word-count').textContent=wordCount(attempt.answers.essay);
  if($('#essay-save'))$('#essay-save').textContent=storageFailed?'本地保存失败':'已保存到本地';
  if($('#save-state'))$('#save-state').textContent=(questions(section().id).length?`已作答 ${answeredCount()} / 5 · `:'')+(storageFailed?'保存失败，请勿关闭页面':'已自动保存到本地');
  document.querySelectorAll('[data-jump]').forEach(el=>{el.classList.toggle('answered',Boolean(String(attempt.answers[el.dataset.jump]||'').trim()));el.classList.toggle('flagged',attempt.flags.includes(el.dataset.jump));});
}
document.addEventListener('input',e=>{
  if(e.target.dataset.answer&&attempt&&!attempt.paused){attempt.answers[e.target.dataset.answer]=e.target.value;saveAttempt();updateAnswerUI();}
});
document.addEventListener('click',async e=>{
  const el=e.target.closest('button,a');if(!el)return;
  if(el.dataset.start){start(el.dataset.start);return;}
  if(el.dataset.export){exportReport(el.dataset.export);return;}
  if(el.dataset.jump){const q=$(`#q-${el.dataset.jump}`);q.scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth',block:'center'});q.querySelector('input')?.focus({preventScroll:true});return;}
  if(el.dataset.flag){const id=el.dataset.flag;attempt.flags=attempt.flags.includes(id)?attempt.flags.filter(x=>x!==id):[...attempt.flags,id];saveAttempt();el.classList.toggle('selected',attempt.flags.includes(id));el.setAttribute('aria-pressed',attempt.flags.includes(id));updateAnswerUI();return;}
  switch(el.dataset.action){
    case 'goal': modal('设定你的目标','<p>这是你的个人目标，不是当前水平评估。</p><label for="target-band">目标 Band</label><select id="target-band">'+[4,4.5,5,5.5,6,6.5,7,7.5,8,8.5,9].map(n=>`<option value="${n}" ${n===Number(target)?'selected':''}>${n.toFixed(1)}</option>`).join('')+'</select>','保存目标',()=>{target=Number($('#target-band').value);save('ielts-target',target);home();notify('目标已更新，按自己的节奏前进。');});break;
    case 'pause':await togglePause();break;
    case 'listen':listen();break;
    case 'stop-audio':stopAudio();break;
    case 'next':requestNext();break;
    case 'record':if(attempt.hasRecording)modal('重新录制？','<p>新录音保存成功后将替换上一段。你可以先下载现有录音。</p>','重新录音',startRecording);else await startRecording();break;
    case 'stop-record':await stopRecording();break;
  }
});
function render(){
  route=location.hash.slice(1)||'home';
  if(study.render(route))return;
  if(route==='home')home();else if(route==='practice')practice();else if(route==='history')historyPage();else if(route==='exam')exam();else if(route.startsWith('report/'))report(route.slice(7));else {location.hash='home';return;}
}
window.addEventListener('hashchange',async()=>{
  const next=location.hash.slice(1)||'home';
  study.leave();
  if(route==='exam'&&next!=='exam'){pauseTimer();stopAudio();await stopRecording();}
  if(activeURL){URL.revokeObjectURL(activeURL);activeURL=null;}
  render();window.scrollTo(0,0);$('#main')?.focus({preventScroll:true});
});
window.addEventListener('beforeunload',e=>{
  if(recording||acquiringMic){e.preventDefault();e.returnValue='';}
  saveAttempt();
});
setInterval(()=>{
  if(attempt&&!attempt.paused&&route==='exam'&&!advancing){
    const left=secondsLeft(attempt);
    if($('#timer')){$('#timer').textContent=formatTime(left);$('#timer').classList.toggle('urgent',left<=60);}
    if(left===0)advance(true);
  }
  if(recording&&$('#record-status'))$('#record-status').textContent=`正在录音 ${formatTime(Math.floor((Date.now()-recordingStart)/1000))} · 完成后点击结束录音`;
},500);
const study=createStudy({shell,notify,modal});
if(attempt&&!attempt.paused&&location.hash!=='#exam')pauseTimer();
render();
