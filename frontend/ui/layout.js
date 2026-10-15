import { siteNav } from './site-nav.js';
export function shell(content,page='home') {
  document.querySelector('#app').innerHTML=`${siteNav(page)}<div class="studio-workspace"><main id="main" class="main" tabindex="-1">${content}<footer class="footer"><span>IELTS Studio</span><a href="#practice">四科示例体验</a><span>本地学习空间 · 非官方考试产品</span></footer></main></div>`;
}
