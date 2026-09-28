function database(){return new Promise((resolve,reject)=>{const request=indexedDB.open('ielts-practice-recordings-v1',1);request.onupgradeneeded=()=>request.result.createObjectStore('recordings');request.onsuccess=()=>resolve(request.result);request.onerror=()=>reject(request.error);});}
export async function recordingStore(key,value){
  const db=await database();
  try{return await new Promise((resolve,reject)=>{const tx=db.transaction('recordings',value===undefined?'readonly':'readwrite');const store=tx.objectStore('recordings');const request=value===undefined?store.get(key):store.put(value,key);tx.oncomplete=()=>resolve(request.result);tx.onerror=()=>reject(tx.error);tx.onabort=()=>reject(tx.error||new Error('Recording save aborted'));});}finally{db.close();}
}
