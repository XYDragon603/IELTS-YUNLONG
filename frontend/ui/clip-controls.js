import {saveClip} from '../lib/listening-clips.js';
import {validLoop} from '../lib/listening-tools.js';
export function mountClipControls(root,audio,precision,context,notify,signal){
  if(!context||!root.querySelector('#listening-rate'))return;
  const section=document.createElement('details');section.className='clip-save';
  section.innerHTML=`<summary>收藏当前精听片段</summary><p class="hint">先设 A、B，再保存。区间由你手动标记，不代表官方逐题定位。</p><label>关联题号（可选）<input name="clip-question" type="number" min="${(context.part-1)*10+1}" max="${context.part*10}" placeholder="${(context.part-1)*10+1}–${context.part*10}"></label><label>复习笔记<textarea name="clip-note" maxlength="1000" rows="2" placeholder="例如：没听出转折，再听一遍"></textarea></label><div class="player-tools"><button class="btn small" type="button" data-save-clip>保存片段</button><a href="/listening-clips.html" class="text-btn">我的精听收藏 ↗</a></div><p role="status" data-clip-message></p>`;
  root.append(section);
  section.querySelector('[data-save-clip]').addEventListener('click',()=>{
    try{
      const {loop,rate}=precision.snapshot();
      if(!validLoop(loop,audio.duration))throw Error('请先设置有效的 A–B 循环区间。');
      saveClip({...context,loop:{...loop},rate,question:section.querySelector('input').value,note:section.querySelector('textarea').value});
      section.querySelector('[data-clip-message]').textContent='已保存，可在「我的精听收藏」回听。';
    }catch(error){section.querySelector('[data-clip-message]').textContent=error.message;notify(error.message);}
  },{signal});
}
