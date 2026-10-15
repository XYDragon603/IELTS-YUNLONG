import { manifest } from '../data/manifest.js';
import { c18t1Listening } from '../data/c18-t1-listening.js';
import { resourceURL } from './resource-parser.js';

export { manifest };
export const getBook = number => manifest.books.find(b=>b.number===Number(number));
export const getTestResources = (book,test) => {
  const b=getBook(book);const t=b?.tests.find(t=>t.number===Number(test));
  if(!b||!t)return null;
  return {...t,book:b.number,documents:b.documents.filter(d=>!d.test||d.test===Number(test)),explanations:b.explanations,videos:b.videos.filter(v=>v.test===Number(test))};
};
export function getListeningTest(id) {
  const match=id?.match(/^c(\d+)-t([1-4])-listening$/);
  if(!match)return null;
  const resources=getTestResources(match[1],match[2]);
  if(!resources)return null;
  // The legacy fixture is independently curated: imported-data verification
  // cannot certify this copy. Keep it unscored until its own audit is complete.
  if(id===c18t1Listening.id)return {...c18t1Listening,verified:false,status:'needs-review',
    verification:{questions:'needs-review',answers:'needs-review',audio:'content-not-reviewed'},
    partPages:[12,13,15,17],resources,documentURL:resourceURL(c18t1Listening.source.path)};
  return {id,book:resources.book,number:resources.number,title:`Cambridge IELTS ${resources.book} · Test ${resources.number}`,verified:false,resources,documentURL:resources.documents[0]?.url,
    parts:Array.from({length:4},(_,i)=>({number:i+1,title:`Part ${i+1} · 原卷配套练习`,type:'Original paper',instruction:'请打开本地原卷，对照对应题号作答。本套题尚未转录，答案将保存，提交后可对照原书自行核对，不会自动判分。',questions:Array.from({length:10},(_,j)=>({id:`q${i*10+j+1}`,number:i*10+j+1,type:'text',prompt:`原卷第 ${i*10+j+1} 题`,accepted:[]}))}))};
}
export function findQuestion(test,id){return test?.parts.flatMap(p=>p.questions).find(q=>q.id===id);}
