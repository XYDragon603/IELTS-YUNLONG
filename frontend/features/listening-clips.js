import {loadClips,deleteClip} from '../lib/listening-clips.js';
import {getListeningTest} from '../lib/cambridge.js';
import {audioPlayer,mountAudioPlayer} from '../ui/audio-player.js';
import {escapeHTML as esc,formatTime} from '../core.js';
import {savePersonalWord} from '../lib/personal-words.js';
let player=null;
const $=s=>document.querySelector(s),notify=text=>$('#clips-message').textContent=text;
const title=c=>{const t=getListeningTest(c.testId);return t?`Cambridge ${t.book} · Test ${t.number} · Part ${c.part}`:c.testId;};
const interval=c=>`${formatTime(Math.floor(c.loop.a))}–${formatTime(Math.floor(c.loop.b))}`;
function render(){
  player?.destroy();player=null;
  try{
    const clips=loadClips();
    $('#clips-list').innerHTML=clips.length?clips.map(c=>`<article class="clip-card" aria-current="${location.hash.slice(1)===c.id}"><strong>${esc(title(c))}</strong><p>${interval(c)}${c.question?` · Q${c.question}`:''} · ${c.rate}×</p><p>${esc(c.note||'暂无笔记')}</p><div class="clip-actions"><a class="btn small" href="#${esc(c.id)}">回听片段</a><button class="text-btn" data-delete="${esc(c.id)}">删除</button></div></article>`).join(''):'<div class="note-box"><h2>还没有精听片段</h2><p>在听力学习模式设 A、B，展开「收藏当前精听片段」。</p><a class="btn" href="/#library/18/1">去听力练习</a></div>';
    const c=clips.find(c=>c.id===location.hash.slice(1));
    if(!c){$('#clip-detail').innerHTML='<p class="note-box">选择一个片段开始复习。</p>';return;}
    const test=getListeningTest(c.testId),src=test?.resources.audio[c.part]?.url;
    $('#clip-detail').innerHTML=`<h2>${esc(title(c))}</h2><p>${interval(c)} · 手动标记，内容待听辨</p><p class="clip-note">${esc(c.note)}</p>${audioPlayer(src,'study')}<form class="clip-word"><h3>收藏相关生词</h3><label>单词或短语<input name="word" required maxlength="80" autocomplete="off"></label><label>释义（可选）<input name="meaning" maxlength="500"></label><button class="btn" type="submit">加入生词本</button> <a href="/words.html">去复习单词 ↗</a><p role="status" id="clip-word-message"></p></form>`;
    player=mountAudioPlayer({saved:{time:c.loop.a,loop:c.loop,rate:c.rate},onSave:()=>{},notify});
    $('#clip-detail form').onsubmit=async event=>{event.preventDefault();const form=event.currentTarget,button=form.querySelector('button');button.disabled=true;try{await savePersonalWord({word:form.elements.word.value,meaning:form.elements.meaning.value,context:`${title(c)} · ${interval(c)} ${c.note}`,source:{title:title(c),url:`/listening-clips.html#${c.id}`}});$('#clip-word-message').textContent='已加入生词本（我的阅读生词）。';form.reset();}catch(error){$('#clip-word-message').textContent=error.message;}finally{button.disabled=false;}};
  }catch(error){notify(error.message);}
}
$('#clips-list').onclick=event=>{const button=event.target.closest('[data-delete]');if(!button||!confirm('删除这个精听片段？音频文件不会删除。'))return;try{deleteClip(button.dataset.delete);render();notify('片段已删除。');}catch(error){notify(error.message);}};
window.addEventListener('hashchange',render);window.addEventListener('pagehide',()=>player?.destroy());render();
