import {icon} from './icons.js';

const items=[
 ['home','house','学习概览','/#home'],
 ['library','book','Cambridge 题库','/#library'],
 ['mock','doc','整套模考','/mock.html'],
 ['words','bars','记单词','/words.html'],
 ['review','bookmark','错题复习','/review.html'],
 ['history','clock','练习记录','/#history']
];

const today=()=>new Date().toLocaleDateString('zh-CN',{month:'long',day:'numeric',weekday:'long'}).replace(/日(?=星期)/,'日 · ');

// Desktop: fixed left sidebar plus a slim top bar in the content column. Narrow screens: top bar with a scrollable link row.
export function siteNav(page='home'){
 const active=page==='explanation'?'library':page;
 return `<header class="studio-nav"><a href="/#home" class="brand" aria-label="IELTS Studio 首页"><span class="brand-mark">i.</span><span>IELTS Studio</span></a><nav aria-label="主要导航">${items.map(([id,graphic,label,href])=>`<a href="${href}" ${id===active?'aria-current="page"':''}>${icon(graphic)}<span>${label}</span></a>`).join('')}</nav><div class="studio-nav-foot"><button type="button" class="theme-switch" data-theme-toggle role="switch" aria-label="深色模式">${icon('moon')}<span>深色模式</span><i aria-hidden="true"></i></button><p class="nav-local">${icon('folder')}<span>本地学习空间<small>进度只保存在这台设备</small></span></p></div></header><div class="studio-topbar"><span class="studio-date">${today()}</span><span class="studio-user" aria-label="Yunlong">Yunlong</span></div>`;
}

export function mountSiteNav(){
 for(const placeholder of document.querySelectorAll('[data-site-nav]'))placeholder.outerHTML=siteNav(placeholder.dataset.siteNav);
}
