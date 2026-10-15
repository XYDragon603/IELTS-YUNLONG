import { icon } from './icons.js';
import { escapeHTML as esc } from '../core.js';

const skills=[['listening','headphones','听力'],['reading','book','阅读'],['writing','pen','写作'],['speaking','mic','口语']];

// Fills the practice header: breadcrumb, skill tabs and the exit link. Answers autosave, so exit is "save and exit".
export function mountExamHeader({book,test,skill,mockRunId=null,showSkills=true}){
  const header=document.querySelector('.practice-header');if(!header)return;
  const mock=mockRunId?`&mockRun=${encodeURIComponent(mockRunId)}`:'';
  const href=id=>id==='listening'?`/import-preview.html?book=${book}&test=${test}${mock}`:`/practice.html?book=${book}&test=${test}&skill=${id}${mock}`;
  const label=Object.fromEntries(skills.map(([id,,name])=>[id,name]));
  const brand=header.querySelector('.brand');
  if(brand&&!header.querySelector('.exam-crumbs')){
    brand.insertAdjacentHTML('afterend',`<nav class="exam-crumbs" aria-label="当前位置"><a href="/#library/${book}">Cambridge ${book}</a><span aria-hidden="true">/</span><a href="/#library/${book}/${test}">Test ${test}</a><span aria-hidden="true">/</span><span aria-current="page">${label[skill]}</span></nav>`);
  }
  const links=header.querySelector('#skill-links');
  if(links)links.innerHTML=showSkills?skills.map(([id,graphic,name])=>`<a href="${esc(href(id))}" ${id===skill?'aria-current="page"':''}>${icon(graphic)}<span>${name}</span></a>`).join(''):'';
  const exit=header.querySelector('#back-link');
  if(exit){exit.href=mockRunId?'/mock.html':`/#library/${book}/${test}`;exit.className='exam-exit';exit.innerHTML=`${icon('exit')}<span>${mockRunId?'保存并返回整套':'保存并退出'}</span>`;}
}
