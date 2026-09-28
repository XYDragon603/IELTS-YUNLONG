export const AUDIO_RATES=[0.75,0.85,1,1.15,1.25];
export function validLoop(loop,duration){return loop&&Number.isFinite(loop.a)&&Number.isFinite(loop.b)&&loop.a>=0&&loop.b-loop.a>=0.5&&loop.b<=duration;}
export function precisionTools(){return '<div class="player-tools precision-tools"><label>速度 <select id="listening-rate"><option>0.75</option><option>0.85</option><option selected>1</option><option>1.15</option><option>1.25</option></select> ×</label><button class="btn small" id="loop-a">设 A 起点</button><button class="btn small" id="loop-b">设 B 并循环</button><button class="btn small" id="loop-clear">清除循环</button><span id="loop-status" role="status">未设置循环</span></div>';}
export function mountPrecision(audio,saved,onChange,notify){
 const rate=document.querySelector('#listening-rate');if(!rate)return {snapshot:()=>({}),destroy(){}};
 const controller=new AbortController(),options={signal:controller.signal};let loop=null,a=null,restored=false;
 const status=document.querySelector('#loop-status');
 const show=()=>{status.textContent=loop?`循环 ${loop.a.toFixed(1)}–${loop.b.toFixed(1)} 秒`:a!==null?`起点 ${a.toFixed(1)} 秒，请设置 B`:'未设置循环';};
 const restore=()=>{if(restored||!Number.isFinite(audio.duration))return;restored=true;audio.playbackRate=AUDIO_RATES.includes(saved.rate)?saved.rate:1;rate.value=String(audio.playbackRate);loop=validLoop(saved.loop,audio.duration)?saved.loop:null;a=loop?.a??null;show();};
 audio.addEventListener('loadedmetadata',restore,options);audio.addEventListener('durationchange',restore,options);if(audio.readyState>=1)restore();
 rate.addEventListener('change',()=>{audio.playbackRate=Number(rate.value);onChange();},options);
 document.querySelector('#loop-a').addEventListener('click',()=>{if(!Number.isFinite(audio.duration)){notify('音频尚未加载完成。');return;}a=audio.currentTime;loop=null;show();onChange();},options);
 document.querySelector('#loop-b').addEventListener('click',()=>{const next={a,b:audio.currentTime};if(a===null||!validLoop(next,audio.duration)){notify('请先设 A，再在至少 0.5 秒之后设置 B。');return;}loop=next;audio.currentTime=a;show();onChange();},options);
 document.querySelector('#loop-clear').addEventListener('click',()=>{loop=null;a=null;show();onChange();},options);
 const repeat=()=>{if(loop&&(audio.currentTime>=loop.b||audio.currentTime<loop.a)){const ended=audio.ended;audio.currentTime=loop.a;if(ended)audio.play().catch(()=>notify('请点击播放以继续循环。'));}};
 audio.addEventListener('timeupdate',repeat,options);audio.addEventListener('ended',repeat,options);
 return {snapshot:()=>({rate:audio.playbackRate,loop}),destroy:()=>controller.abort()};
}
