import path from 'node:path';

const pages=new Set(['/','/index.html','/mock.html','/words.html','/review.html','/practice.html','/import-preview.html','/listening-clips.html']);
const rootFiles=new Set(['/favicon.svg','/app.js','/core.js','/data.js','/styles.css','/studio.css','/site-nav.css','/study.css','/words.css','/practice.css','/exam-workspace.css','/listening-workspace.css','/listening-clips.css','/review.css']);

export function publicPathAllowed(pathname){
 if(pages.has(pathname)||rootFiles.has(pathname))return true;
 const extension=path.extname(pathname).toLowerCase();
 if(/^\/(features|lib|ui)\/[^/]+(?:\/[^/]+)*$/.test(pathname))return extension==='.js'||extension==='.css';
 if(pathname.startsWith('/resources/'))return ['.js','.json','.png','.webp','.svg'].includes(extension);
 if(pathname.startsWith('/IELTS/'))return ['.pdf','.mp3','.m4a','.wav','.ogg','.mp4'].includes(extension);
 return false;
}
