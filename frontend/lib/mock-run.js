export const MOCK_SKILLS=['listening','reading','writing','speaking'];
export const MOCK_KEY='ielts-mock-runs-v1';
export function mockRuns(storage=localStorage){const raw=storage.getItem(MOCK_KEY);if(!raw)return [];const rows=JSON.parse(raw);if(!Array.isArray(rows))throw Error('整套记录无法读取，原数据未覆盖。');return rows;}
export function mockPaperOptions(entries){
 const papers=new Map();
 for(const entry of entries){const key=`${entry.book}-${entry.test}`;if(!papers.has(key))papers.set(key,{book:entry.book,test:entry.test,skills:{}});papers.get(key).skills[entry.skill]=entry;}
 return [...papers.values()].map(paper=>({...paper,available:MOCK_SKILLS.every(skill=>paper.skills[skill]?.available),verified:MOCK_SKILLS.every(skill=>paper.skills[skill]?.status==='ready')})).sort((a,b)=>b.book-a.book||a.test-b.test);
}
export function createMockRun(storage=localStorage,selection={book:18,test:1}){const {book,test}=selection;if(!Number.isInteger(book)||!Number.isInteger(test)||book<4||book>20||test<1||test>4)throw Error('试卷编号无效');const run={id:crypto.randomUUID(),book,test,source:'imported',created:new Date().toISOString()};storage.setItem(MOCK_KEY,JSON.stringify([run,...mockRuns(storage)]));return run;}
export function listeningRunKey(run){return `ielts-c${run.book}-t${run.test}-import-preview-v1-mock-${run.id}`;}
export function practiceRunKey(run,skill){return `ielts-practice-v1-c${run.book}-t${run.test}-${skill}-mock-${run.id}`;}
export function mockProgress(run,storage=localStorage){
 const study=run.source==='imported'?null:JSON.parse(storage.getItem('ielts-study-v1')||'{"sessions":[]}');
 return MOCK_SKILLS.map(skill=>{
  const s=skill==='listening'?(run.source==='imported'?JSON.parse(storage.getItem(listeningRunKey(run))||'null'):(study.sessions||[]).find(s=>s.mockRun===run.id)):JSON.parse(storage.getItem(practiceRunKey(run,skill))||'null');
  const listeningHref=run.source==='imported'?`/import-preview.html?book=${run.book}&test=${run.test}&mockRun=${run.id}`:(s?`/#${s.finished?'explanation':'listening'}/${s.id}`:`/#mock-listening/${run.id}`);
  return {skill,started:Boolean(s),finished:Boolean(s?.finished||s?.submitted),href:skill==='listening'?listeningHref:`/practice.html?book=${run.book}&test=${run.test}&skill=${skill}&mockRun=${run.id}`};
 });
}
export function requireMockStage(id,skill,storage=localStorage){const run=mockRuns(storage).find(r=>r.id===id);if(!run)throw Error('未找到整套练习记录');const index=MOCK_SKILLS.indexOf(skill);if(index<0||mockProgress(run,storage).slice(0,index).some(p=>!p.finished))throw Error('请先完成上一科，再进入下一科。');return run;}
