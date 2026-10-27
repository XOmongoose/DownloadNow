// Runs only on explicit Story action, in the page's MAIN world. Returns one
// validated media URL, never page data, cookies, credentials or browser storage.
globalThis.DownloadNowFacebookProbe=function(expected){
 function identity(value){try{const u=new URL(value);return u.protocol==='https:'&&!u.username&&!u.password&&['facebook.com','www.facebook.com','m.facebook.com','web.facebook.com'].includes(u.hostname)&&u.pathname.startsWith('/stories/')?decodeURIComponent(u.pathname.split('/')[3]||''):null;}catch(e){return null;}}
 const story=identity(expected);if(!story||(identity(location.href)!==story||new URL(location.href).pathname!==new URL(expected).pathname))return {error:'Tin đã thay đổi. Bấm tải lại trên đúng Tin.'};
 const aliases=new Set([story]);try{const id=atob(story).match(/:(\d+)$/)?.[1];if(id)aliases.add(id);}catch(e){}
 function direct(value){try{const u=new URL(value);return u.protocol==='https:'&&!u.username&&!u.password&&u.hostname.endsWith('.fbcdn.net')&&/\.mp4$/i.test(u.pathname)?u.href:null;}catch(e){return null;}}
 const skip=new Set(['return','child','sibling','stateNode','_owner','alternate','ref','children']);
 function entries(node){try{return Object.entries(Object.getOwnPropertyDescriptors(node)).filter(([k,d])=>!skip.has(k)&&'value' in d).map(([k,d])=>[k,d.value]);}catch(e){return [];}}
 const roots=[];
 // Limit inspection to media elements and their component ancestors. Do not
 // search window, the Relay store, request history, or unrelated page state.
 for(const video of [...document.querySelectorAll('video')].slice(0,20)){
  let element=video;
  for(let depth=0;element&&depth<8;depth++,element=element.parentElement){
   for(const key of Object.keys(element).filter(k=>/^__react(?:Props|Fiber|InternalInstance)\$/.test(k))){
    let node=element[key];if(key.startsWith('__reactProps'))roots.push(node);
    else for(let hop=0;node&&hop<35;hop++,node=node.return){if(node.memoizedProps)roots.push(node.memoizedProps);if(node.pendingProps)roots.push(node.pendingProps);}
   }
  }
 }
 const matches=[],seen=new WeakSet(),stack=roots.slice();let budget=60000;
 while(stack.length&&budget-->0){
  const node=stack.pop();if(!node||typeof node!=='object'||seen.has(node))continue;seen.add(node);
  const values=entries(node);
  if(values.some(([k,v])=>['id','story_id','story_fbid','storyID','storyId'].includes(k)&&aliases.has(String(v))))matches.push(node);
  for(const [,v] of values)if(v&&typeof v==='object')stack.push(v);
 }
 const media=new Map();
 for(const match of matches){
  const pending=[[match,'story']],visited=new WeakSet();let remaining=15000;
  while(pending.length&&remaining-->0){
   const [node,parentId]=pending.pop();if(!node||typeof node!=='object'||visited.has(node))continue;visited.add(node);
   const values=entries(node),id=values.find(([k,v])=>['id','video_id','videoID'].includes(k)&&typeof v!=='object')?.[1]||parentId;
   const fields=['browser_native_hd_url','playable_url_quality_hd','browser_native_sd_url','playable_url','progressive_url'];
   const url=fields.map(key=>direct(values.find(([k])=>k===key)?.[1])).find(Boolean);
   if(url&&!media.has(String(id)))media.set(String(id),url);
   for(const [,v] of values)if(v&&typeof v==='object')pending.push([v,id]);
  }
 }
 if((identity(location.href)!==story||new URL(location.href).pathname!==new URL(expected).pathname))return {error:'Tin đã thay đổi. Bấm tải lại trên đúng Tin.'};
 return media.size===1?{url:[...media.values()][0],story}:{error:media.size>1?'Tin có nhiều nguồn video, chưa xác định được tệp cần tải.':'Video đang phát nhưng chưa tìm được nguồn MP4 phù hợp của đúng Tin này.'};
};
