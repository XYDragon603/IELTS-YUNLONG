import {icon} from './icons.js';

const items=[
 ['home','home','学习概览','/#home'],
 ['library','book','Cambridge 题库','/#library'],
 ['review','flag','错题复习','/review.html'],
 ['history','chart','练习记录','/#history'],
 ['mock',null,'整套练习','/mock.html'],
 ['words',null,'记单词','/words.html']
];

export function siteNav(page='home'){
 const active=page==='explanation'?'library':page;
 return `<header class="studio-nav"><a href="/#home" class="brand" aria-label="IELTS Studio"><span class="brand-mark">i.</span><span>IELTS Studio</span></a><nav aria-label="主要导航">${items.map(([id,graphic,label,href])=>`<a href="${href}" ${id===active?'aria-current="page"':''}>${graphic?icon(graphic):''}${label}</a>`).join('')}</nav><span class="yunlong-signature" aria-label="Yunlong.">Yunlong.</span></header>`;
}

export function mountSiteNav(){
 for(const placeholder of document.querySelectorAll('[data-site-nav]'))placeholder.outerHTML=siteNav(placeholder.dataset.siteNav);
}
