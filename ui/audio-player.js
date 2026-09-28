import {precisionTools,mountPrecision} from '../lib/listening-tools.js';
import { formatTime } from '../core.js';
import { icon } from './icons.js';
import {mountClipControls} from './clip-controls.js';
export function audioPlayer(src,mode){
  if(!src)return '<div class="audio-unavailable"><strong>本 Part 音频尚未就绪</strong><p>可以对照原卷继续作答，或返回题库选择有音频的练习。未完成下载的文件不会被播放。</p></div>';
  return `<section class="study-audio" aria-label="听力播放器"><audio id="study-audio" preload="metadata" src="${src}"></audio><div class="audio-topline"><span class="eyebrow">LISTEN CLOSELY</span><span id="media-status" role="status">正在读取音频…</span></div><div class="player-main"><button class="audio-play" data-player="play" aria-label="播放音频">${icon('play')}</button><div class="audio-timeline"><label class="sr-only" for="audio-seek">播放进度</label><input type="range" id="audio-seek" min="0" max="100" step=".1" value="0" ${mode==='mock'?'disabled':''}><div><span id="audio-time">00:00</span><span id="audio-duration">--:--</span></div></div></div><div class="player-tools"><div><button class="btn small" data-player="back" ${mode==='mock'?'disabled':''}>−10 秒</button><button class="btn small" data-player="forward" ${mode==='mock'?'disabled':''}>+10 秒</button></div><label>音量 <input id="audio-volume" type="range" min="0" max="1" step=".05" value="1" aria-label="音量"></label><span class="hint">${mode==='mock'?'模考练习 · 快进回退已关闭':'学习模式 · 支持回听'}</span></div>${mode==='mock'?'':precisionTools()}</section>`;
}
export function mountAudioPlayer({saved={},onSave,notify,clipContext}){
  const audio=document.querySelector('#study-audio');if(!audio)return {destroy(){},pause(){}};
  const root=audio.closest('.study-audio'),$=s=>root.querySelector(s);
  const controller=new AbortController(),options={signal:controller.signal};
  const listen=(target,event,fn)=>target.addEventListener(event,fn,options);
  let lastSave=0,precision=null,restored=false,destroyed=false;
  const persist=()=>{if(!restored||destroyed)return;onSave({time:Number.isFinite(audio.currentTime)?audio.currentTime:0,volume:audio.volume,...(precision?.snapshot()||{})});};
  precision=mountPrecision(audio,saved,persist,notify);
  mountClipControls(root,audio,precision,clipContext,notify,controller.signal);
  const update=()=>{
    if(!$('#audio-time'))return;
    $('#audio-time').textContent=formatTime(Math.floor(audio.currentTime||0));
    $('#audio-duration').textContent=Number.isFinite(audio.duration)?formatTime(Math.floor(audio.duration)):'--:--';
    $('#audio-seek').value=Number.isFinite(audio.duration)&&audio.duration>0?audio.currentTime/audio.duration*100:0;
    if(Date.now()-lastSave>1500){persist();lastSave=Date.now();}
  };
  const loaded=()=>{
    if(!restored&&Number.isFinite(audio.duration)&&audio.duration>0){
      audio.volume=Number.isFinite(saved.volume)?Math.max(0,Math.min(1,saved.volume)):1;
      $('#audio-volume').value=audio.volume;
      if(Number.isFinite(saved.time)&&saved.time>0)audio.currentTime=Math.min(saved.time,audio.duration);
      restored=true;$('#media-status').textContent=saved.time?'已恢复播放位置':'音频就绪';
    }
    update();
  };
  listen(audio,'loadedmetadata',loaded);listen(audio,'durationchange',loaded);if(audio.readyState>=1)loaded();
  listen(audio,'timeupdate',update);listen(audio,'seeked',persist);
  listen(audio,'play',()=>{$('[data-player="play"]').innerHTML=icon('pause');$('[data-player="play"]').setAttribute('aria-label','暂停音频');$('#media-status').textContent='正在播放';});
  listen(audio,'pause',()=>{$('[data-player="play"]').innerHTML=icon('play');$('[data-player="play"]').setAttribute('aria-label','播放音频');$('#media-status').textContent=audio.ended?'本段播放完毕':'已暂停';persist();});
  listen(audio,'error',()=>{$('#media-status').textContent='音频读取失败，请检查文件是否已下载完整';notify('音频无法播放，答案仍会保存。请重新扫描资源后重试。');});
  listen($('[data-player="play"]'),'click',async()=>{if(audio.paused){try{await audio.play();}catch{if(!destroyed)notify('无法播放音频，请确认音频文件可用后重试。');}}else audio.pause();});
  listen($('[data-player="back"]'),'click',()=>{if(Number.isFinite(audio.duration))audio.currentTime=Math.max(0,audio.currentTime-10);persist();});
  listen($('[data-player="forward"]'),'click',()=>{if(Number.isFinite(audio.duration))audio.currentTime=Math.min(audio.duration,audio.currentTime+10);persist();});
  listen($('#audio-seek'),'input',e=>{if(!e.target.disabled&&Number.isFinite(audio.duration)){audio.currentTime=Number(e.target.value)/100*audio.duration;persist();}});
  listen($('#audio-volume'),'input',e=>{audio.volume=Number(e.target.value);persist();});
  listen(window,'pagehide',persist);
  return {pause(){audio.pause();persist();},destroy(){if(destroyed)return;persist();destroyed=true;controller.abort();precision?.destroy();audio.pause();audio.removeAttribute('src');audio.load();}};
}
