import {validLoop,AUDIO_RATES} from './listening-tools.js';
export const CLIPS_KEY='ielts-listening-clips-v1';
export function validateClip(c){
  if(!c||!/^c(?:[4-9]|1\d|20)-t[1-4]-listening$/.test(c.testId)||!Number.isInteger(c.part)||c.part<1||c.part>4||!validLoop(c.loop,86400)||!AUDIO_RATES.includes(c.rate)||typeof c.note!=='string'||c.note.length>1000||typeof c.question!=='string'||!/^$|^(?:[1-9]|[1-3]\d|40)$/.test(c.question))throw Error('精听片段格式不正确。');
  if(c.question&&Math.ceil(Number(c.question)/10)!==c.part)throw Error('题号必须属于当前 Part。');
  return c;
}
export function loadClips(storage=localStorage){
  const raw=storage.getItem(CLIPS_KEY);if(!raw)return [];
  let data;try{data=JSON.parse(raw);if(!Array.isArray(data)||data.some(c=>typeof c.id!=='string'||!Number.isFinite(c.created)))throw Error();data.forEach(validateClip);}catch{throw Error('精听收藏无法读取，原记录未覆盖。');}
  return data;
}
export function saveClip(input,storage=localStorage){
  const clip=validateClip({...input,note:(input.note||'').trim(),question:(input.question||'').trim()});
  const items=loadClips(storage);
  const old=items.find(c=>c.testId===clip.testId&&c.part===clip.part&&c.loop.a===clip.loop.a&&c.loop.b===clip.loop.b);
  const entry={...clip,id:old?.id||crypto.randomUUID(),created:old?.created||Date.now()};
  storage.setItem(CLIPS_KEY,JSON.stringify([entry,...items.filter(c=>c.id!==entry.id)]));return entry;
}
export function deleteClip(id,storage=localStorage){storage.setItem(CLIPS_KEY,JSON.stringify(loadClips(storage).filter(c=>c.id!==id)));}
