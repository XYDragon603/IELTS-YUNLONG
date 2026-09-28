import { loadPractice, readingReport } from './practice-model.js';

export const attemptId = () => globalThis.crypto.randomUUID();
export function identifyPractice(state,key){
  if(state.attemptId)return state;
  return {...state,attemptId:attemptId(),started:new Date().toISOString(),recordingNamespace:key,legacySnapshot:Boolean(state.submitted)};
}
export function newPractice(skill,key){
  const id=attemptId();
  return {...loadPractice(key,skill,{getItem:()=>null}),attemptId:id,started:new Date().toISOString(),recordingNamespace:`${key}-${id}`};
}
export function historyEntries(key,storage=localStorage){
  const raw=storage.getItem(`${key}-history`);
  if(!raw)return [];
  const value=JSON.parse(raw);
  if(!Array.isArray(value))throw new Error('练习历史格式损坏，未覆盖原记录。');
  return value;
}
export function archivePractice(key,state,data,storage=localStorage){
  if(!state.submitted||!state.attemptId)throw new Error('只能归档已提交的练习');
  const entries=historyEntries(key,storage);
  if(entries.some(e=>e.id===state.attemptId))return;
  const entry={id:state.attemptId,submitted:state.submitted,snapshotCaptured:new Date().toISOString(),legacySnapshot:Boolean(state.legacySnapshot),session:structuredClone(state),paper:structuredClone(data),
    readingResults:data.skill==='reading'?readingReport(data,state.answers):null};
  storage.setItem(`${key}-history`,JSON.stringify([entry,...entries]));
}
