// Resolve only the selected Facebook video. Never guess from unrelated posts
// or preload/network history; no cookies or login credentials are read.
globalThis.DownloadNowFacebook=(()=>{
 function facebook(value){try{const u=new URL(value);return /^https?:$/.test(u.protocol)&&!u.username&&!u.password&&['facebook.com','www.facebook.com','m.facebook.com','web.facebook.com'].includes(u.hostname);}catch(e){return false;}}
 function canonical(value,base){
  try{const u=new URL(value,base);if(!facebook(u.href))return null;
   const id=u.searchParams.get('v')||u.searchParams.get('video_id');
   if(/^\d+$/.test(id||'')&&/^\/(watch\/?|video\.php|video\/video\.php|video\/embed)$/.test(u.pathname))return 'https://www.facebook.com/watch/?v='+id;
   const video=u.pathname.match(/\/(?:videos|reel)\/(?:[^/]+\/)?(\d+)\/?$/);
   if(video)return 'https://www.facebook.com/watch/?v='+video[1];
   if(/^\/[^/]+\/posts\/(?:pfbid[A-Za-z0-9]+|\d+)\/?$/.test(u.pathname)||/^\/groups\/[^/]+\/(?:posts|permalink)\/\d+\/?$/.test(u.pathname))return 'https://www.facebook.com'+u.pathname.replace(/\/$/,'');
   if(/^\/(story|permalink)\.php$/.test(u.pathname)&&/^(?:\d+|pfbid[A-Za-z0-9]+)$/.test(u.searchParams.get('story_fbid')||''))return 'https://www.facebook.com'+u.pathname+'?story_fbid='+encodeURIComponent(u.searchParams.get('story_fbid'))+(u.searchParams.has('id')?'&id='+encodeURIComponent(u.searchParams.get('id')):'');
  }catch(e){}return null;
 }
 function direct(value){try{const u=new URL(value);return u.protocol==='https:'&&!u.username&&!u.password&&(u.hostname==='fbcdn.net'||u.hostname.endsWith('.fbcdn.net'))&&/\.mp4$/i.test(u.pathname)?u.href:null;}catch(e){return null;}}
 function storyIdentity(value){
  try{const u=new URL(value);if(!facebook(value)||!u.pathname.startsWith('/stories/'))return null;const id=decodeURIComponent(u.pathname.split('/')[3]||'');return id||null;}catch(e){return null;}
 }
 function storyMedia(data,identity){
  const aliases=new Set([identity]);
  try{const decoded=atob(identity);const match=decoded.match(/:(\d+)$/);if(match)aliases.add(match[1]);}catch(e){}
  let budget=80000;const matches=[];
  const stack=[data];
  while(stack.length&&budget-->0){const node=stack.pop();if(!node||typeof node!=='object')continue;
   if(['id','story_id','story_fbid'].some(key=>aliases.has(String(node[key]||''))))matches.push(node);
   for(const value of Object.values(node))if(value&&typeof value==='object')stack.push(value);
  }
  const videos=new Map();
  for(const match of matches){const pending=[[match,'story']];let remaining=20000;
   while(pending.length&&remaining-->0){const [node,parentId]=pending.pop();if(!node||typeof node!=='object')continue;
    const id=String(node.id||node.video_id||parentId);
    const fields=['browser_native_hd_url','playable_url_quality_hd','browser_native_sd_url','playable_url','progressive_url'];
    const url=fields.map(k=>direct(node[k])).find(Boolean);
    if(url&&!videos.has(id))videos.set(id,url);
    for(const value of Object.values(node))if(value&&typeof value==='object')pending.push([value,id]);
   }
  }
  return videos.size===1?[...videos.values()][0]:null;
 }
 function resolve(video,page,doc){
  if(!facebook(page))return null;
  const story=storyIdentity(page);
  if(story||new URL(page).pathname.startsWith('/stories/')){
   let numeric='';try{numeric=atob(story).match(/:(\d+)$/)?.[1]||'';}catch(e){}
   // Match the current story exactly: adjacent stories may already be preloaded.
   let budget=12000000;
   for(const script of [...doc.querySelectorAll('script[type="application/json"]')].slice(0,60)){
    const raw=script.textContent||'';budget-=raw.length;if(budget<0)break;if(!story||raw.length>4000000||!raw.includes(story)&&!(numeric&&raw.includes(numeric)))continue;
    try{const url=storyMedia(JSON.parse(raw),story);if(url)return url;}catch(e){}
   }
   return null;
  }
  if(!video)return null;
  const enclosing=video.closest('a[href]');const own=enclosing&&canonical(enclosing.href,page);if(own)return own;
  let node=video.parentElement,post=null;
  for(let depth=0;node&&depth<10;depth++,node=node.parentElement){
   if(node.querySelectorAll('video').length>1)break;
   const id=node.getAttribute('data-video-id');if(/^\d+$/.test(id||''))return 'https://www.facebook.com/watch/?v='+id;
   const urls=[...new Set([...node.querySelectorAll('a[href]')].map(a=>canonical(a.href,page)).filter(Boolean))];
   const videos=urls.filter(u=>u.includes('/watch/?v='));if(videos.length>1)return null;if(videos.length===1)return videos[0];
   const posts=urls.filter(u=>!u.includes('/watch/?v='));if(posts.length===1)post=posts[0];else if(posts.length>1)post=null;
   if(node.matches('[role="article"],article'))break;
  }
  return post||direct(video.currentSrc)||direct(video.src);
 }
 function visible(video){
  const r=video.getBoundingClientRect();if(!video.isConnected||r.width<120||r.height<80||r.bottom<=0||r.top>=window.innerHeight||r.right<=0||r.left>=window.innerWidth)return false;
  const top=video.ownerDocument.elementFromPoint(Math.max(0,r.left+Math.min(20,r.width/4)),Math.max(0,Math.min(window.innerHeight-1,(Math.max(0,r.top)+Math.min(window.innerHeight,r.bottom))/2)));
  return !top||top===video||video.parentElement?.contains(top)||top.hasAttribute('data-downloadnow-feed');
 }
 function selected(doc){const videos=[...doc.querySelectorAll('video')].filter(visible),playing=videos.filter(v=>!v.paused&&!v.ended);return playing.length===1?playing[0]:videos.length===1?videos[0]:null;}
 function attach({doc,bridge,enabled,notice,page=()=>window.location.href}){
  const buttons=new Map();let scheduled=false,storyButton=null;
  // Old extension contexts can leave DOM behind after runtime.reload().
  for(const host of doc.querySelectorAll('[data-downloadnow-feed],[data-downloadnow-story]'))host.remove();
  async function source(video){
   const initial=page();let url;
   if(new URL(initial).pathname.startsWith('/stories/')){
    if(!video)throw Error('Chưa xác định được video Tin đang hiển thị. Đợi video hiện rồi thử lại.');
    const target=crypto.randomUUID(),src=video.currentSrc||video.src||'';
    video.setAttribute('data-downloadnow-target',target);
    let result;
    try{result=await bridge.runtime.sendMessage({type:'resolve-facebook-story-source',page:initial,target});}
    finally{if(video.getAttribute('data-downloadnow-target')===target)video.removeAttribute('data-downloadnow-target');}
    if(new URL(page()).pathname!==new URL(initial).pathname||selected(doc)!==video||(video.currentSrc||video.src||'')!==src)throw Error('Tin đã thay đổi. Bấm tải lại trên đúng Tin.');
    if(!result?.url)throw Error(result?.error||'Chưa tìm được nguồn MP4 phù hợp của Tin đang mở.');
    url=direct(result.url);if(!url)throw Error('Nguồn video Facebook không hợp lệ.');
   }else url=resolve(video,initial,doc);
   return url;
  }
  async function send(video,button){
   if(button.disabled)return;
   if(!enabled()){notice('Mở tiện ích Download Now, bật Bắt tự động và Bắt link tệp ngay khi bấm, rồi mở ứng dụng để kết nối.');return;}
   const label=button.textContent;
   button.disabled=true;button.textContent='Đang tìm nguồn video…';
   try{const url=await source(video);if(!url)throw Error('Chưa tìm được nguồn video của mục đang mở.');
    button.textContent='Đang chọn nơi lưu…';
    let result=await bridge.runtime.sendMessage({type:'capture-link',url,name:'Facebook video.mp4',requestId:crypto.randomUUID()});
    const fallback=new URL(page()).pathname.startsWith('/stories/')?null:direct(video?.currentSrc)||direct(video?.src);
    if(!result?.ok&&fallback&&fallback!==url)result=await bridge.runtime.sendMessage({type:'capture-link',url:fallback,name:'Facebook video.mp4',requestId:crypto.randomUUID()});
    if(!result?.ok)throw Error(result?.error||'Không kết nối được ứng dụng.');notice(result.cancelled?'Đã hủy tải.':'Đã thêm video vào Download Now.');}
   catch(e){notice(e.message);}finally{button.disabled=false;button.textContent=label;}
  }
  function update(){
   scheduled=false;
   const story=facebook(page())&&new URL(page()).pathname.startsWith('/stories/');
   if(storyButton)storyButton.host.hidden=!enabled();
   if(story&&enabled()&&!storyButton){
    const host=doc.createElement('div'),shadow=host.attachShadow({mode:'closed'}),button=doc.createElement('button');
    host.setAttribute('data-downloadnow-story','');
    host.style.cssText='position:fixed;right:24px;bottom:88px;z-index:2147483647;';
    button.type='button';button.textContent='↓ Tải Tin Facebook';button.setAttribute('aria-label','Download Now: tải Tin Facebook đang mở');
    button.style.cssText='background:#F1AF00;color:#302600;border:1px solid #d99e00;border-radius:24px;padding:13px 18px;font:600 14px system-ui;cursor:pointer;box-shadow:0 4px 18px #0005';
    button.onclick=async e=>{e.preventDefault();e.stopPropagation();await send(selected(doc),button);};
    shadow.append(button);(doc.body||doc.documentElement).append(host);storyButton={host,button};
   }
   if(!story&&storyButton){storyButton.host.remove();storyButton=null;}
   const videos=!story&&enabled()&&facebook(page())?[...doc.querySelectorAll('video')].filter(visible).slice(0,12):[];
   for(const [video,item] of buttons)if(!videos.includes(video)){item.host.remove();buttons.delete(video);}
   for(const video of videos){
    let item=buttons.get(video);
    if(!item){const host=doc.createElement('div'),shadow=host.attachShadow({mode:'closed'}),button=doc.createElement('button');host.setAttribute('data-downloadnow-feed','');button.type='button';button.textContent='↓ Tải video / Tin';button.setAttribute('aria-label','Download Now: tải đúng video hoặc Tin này');
     button.style.cssText='background:#F1AF00;color:#302600;border:1px solid #d99e00;border-radius:18px;padding:9px 13px;font:600 12px system-ui;cursor:pointer;box-shadow:0 3px 12px #0003';
     button.onclick=async e=>{e.preventDefault();e.stopPropagation();await send(video,button);};shadow.append(button);(doc.body||doc.documentElement).append(host);item={host,button};buttons.set(video,item);
    }
    const r=video.getBoundingClientRect();item.host.style.cssText='position:fixed;z-index:2147483646;top:'+Math.max(8,r.top+10)+'px;left:'+Math.max(8,Math.min(window.innerWidth-175,r.right-170))+'px;';
   }
  }
  function schedule(){if(!scheduled){scheduled=true;requestAnimationFrame(update);}}
  window.addEventListener('scroll',schedule,true);window.addEventListener('resize',schedule);setInterval(update,1200);
  bridge.runtime.onMessage.addListener((message,sender,reply)=>{
   if(message.type!=='resolve-facebook-video')return;
   if(!enabled()){reply({error:'Bật Bắt link tệp ngay khi bấm và tải lại Facebook trước.'});return;}
   const video=selected(doc);
   source(video).then(url=>reply(url?{url}:{error:'Dùng nút Tải video / Tin trên đúng video bạn muốn tải; không chọn tự động khi có nhiều video hoặc chưa lấy được nguồn.'})).catch(e=>reply({error:e.message}));return true;
  });
  update();
 }
 return {facebook,canonical,direct,storyIdentity,storyMedia,resolve,attach};
})();
