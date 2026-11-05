export class LatestTask{
  constructor(){this.sequence=0;this.active=new Map();}
  begin(key){const id=++this.sequence;this.active.set(key,id);return()=>this.active.get(key)===id;}
  clear(){this.active.clear();}
}
export async function pollDocument(api,id,{isCurrent=()=>true,onStatus=()=>{},pause=ms=>new Promise(resolve=>setTimeout(resolve,ms)),attempts=40,interval=2500}={}){
  let last=null;
  for(let i=0;i<attempts;i++){
    if(!isCurrent())return null;
    await pause(interval);if(!isCurrent())return null;
    try{last=await api(`/documents/${encodeURIComponent(id)}/status`);}catch(error){if(!isCurrent())return null;throw error;}
    if(!isCurrent())return null;
    onStatus(last);if(['processed','failed','deleted'].includes(last.status))return last;
  }
  return last;
}
