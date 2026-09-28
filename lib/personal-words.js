export const PERSONAL_KEY='ielts-personal-words-v1';
export function personalBook(storage=localStorage){const raw=storage.getItem(PERSONAL_KEY);const words=raw?JSON.parse(raw):[];if(!Array.isArray(words))throw Error('生词本无法读取，原记录未覆盖。');return {id:'personal',title:'我的阅读生词',words};}
export async function savePersonalWord({word,meaning,context,source},storage=localStorage){
 word=word.trim().replace(/\s+/g,' ');
 if(!/^[A-Za-z][A-Za-z '\-]*$/.test(word)||word.length>80||word.split(' ').length>8)throw Error('请选择一个英文单词或不超过 8 个词的短语。');
 const hash=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(word.toLowerCase()));
 const id=Array.from(new Uint8Array(hash),b=>b.toString(16).padStart(2,'0')).join('').slice(0,20);
 const book=personalBook(storage),old=book.words.find(w=>w.id===id);
 const entry={id,word,meaning:meaning?.trim()||old?.meaning||'释义待补充',context,source,added:old?.added||new Date().toISOString()};
 storage.setItem(PERSONAL_KEY,JSON.stringify([entry,...book.words.filter(w=>w.id!==id)]));return entry;
}
