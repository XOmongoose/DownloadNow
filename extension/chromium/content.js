(() => {
 const bridge=globalThis.browser||globalThis.chrome;
 let enabled=false,exclusive=true;
 const types=/\.(?:zip|rar|7z|tar|gz|bz2|xz|zst|exe|msi|iso|dmg|pkg|apk|pdf|epub|docx?|xlsx?|pptx?|csv|txt|mp4|mkv|webm|mov|avi|mp3|wav|flac|ogg|m4a)$/i;
 const refresh=()=>bridge.storage.local.get(['capture','intercept','token','downloadNowOnly']).then(s=>{enabled=!!(s.capture&&s.intercept&&s.token);exclusive=s.downloadNowOnly!==false;});
 refresh();
 bridge.storage.onChanged.addListener((changes,area)=>{if(area==='local'&&(changes.capture||changes.intercept||changes.token||changes.downloadNowOnly))refresh();});
 if(globalThis.DownloadNowFacebook&&typeof window!=='undefined'&&globalThis.DownloadNowFacebook.facebook(window.location.href))globalThis.DownloadNowFacebook.attach({doc:document,bridge,enabled:()=>enabled,notice:showNotice});
 function videoPage(value){
  try{const u=new URL(value),host=u.hostname.replace(/^(www\.|m\.)/,'');
   return /^https?:$/.test(u.protocol)&&((host==='youtube.com'&&/^\/(shorts\/|watch)/.test(u.pathname))||host==='youtu.be'||host==='instagram.com'&&/^\/(reels?\/|p\/)/.test(u.pathname)||['facebook.com','web.facebook.com'].includes(host)&&(/^\/(reels?\/|watch|share\/r\/)/.test(u.pathname)||u.pathname.includes('/videos/')));
  }catch(e){return false;}
 }
 // These pages navigate without a document reload. Resolve the current URL at
 // click time instead of capturing the first reel visited in a feed.
 if(typeof window!=='undefined'&&typeof setInterval==='function'){
  let host,button,busy=false;
  const mount=()=>{
   const visible=enabled&&videoPage(window.location.href)&&!(globalThis.DownloadNowFacebook&&globalThis.DownloadNowFacebook.facebook(window.location.href));
   if(!visible){if(host)host.hidden=true;return;}
   if(!host){
    host=document.createElement('div');const shadow=host.attachShadow({mode:'closed'});button=document.createElement('button');
    button.textContent='↓ Tải video này';button.setAttribute('type','button');
    button.style.cssText='position:fixed;right:24px;bottom:92px;z-index:2147483647;border:1px solid #d99e00;border-radius:24px;padding:13px 20px;background:#F1AF00;color:#302600;font:600 14px system-ui;cursor:pointer;box-shadow:0 4px 18px #0003';
    shadow.append(button);(document.body||document.documentElement).append(host);
    button.onclick=async()=>{
     const url=window.location.href;if(busy||!enabled||!videoPage(url))return;
     busy=true;button.disabled=true;button.textContent='Đang phân tích video…';
     try{const result=await bridge.runtime.sendMessage({type:'capture-link',url,requestId:crypto.randomUUID()});if(!result?.ok)throw Error(result?.error||'Không kết nối được ứng dụng.');showNotice(result.cancelled?'Đã hủy tải video.':'Đã thêm video vào Download Now.');}
     catch(e){showNotice(e.message);}finally{busy=false;button.disabled=false;button.textContent='↓ Tải video này';}
    };
   }
   host.hidden=false;
  };
  setInterval(mount,1200);
 }
 function isDownload(anchor,url) {
  if(anchor.hasAttribute('download'))return true;
  if(['drive.usercontent.google.com','drive.google.com','docs.google.com'].includes(url.hostname)&&url.searchParams.has('id')&&(url.pathname==='/download'||url.pathname==='/uc'&&url.searchParams.get('export')==='download'))return true;
  if(types.test(decodeURIComponent(url.pathname)))return true;
  for(const key of ['filename','file_name','download_filename','file','name'])if(types.test(url.searchParams.get(key)||''))return true;
  return false;
 }
 function showNotice(text) {
  const host=document.createElement('div');
  const shadow=host.attachShadow({mode:'closed'}),box=document.createElement('div');
  box.textContent=text;box.setAttribute('role','status');
  box.style.cssText='position:fixed;bottom:24px;right:24px;z-index:2147483647;max-width:360px;padding:14px 18px;background:#302600;color:#fff5d6;border-left:4px solid #F1AF00;border-radius:9px;font:13px/1.6 system-ui;box-shadow:0 5px 24px #0003';
  shadow.append(box);(document.body||document.documentElement).append(host);setTimeout(()=>host.remove(),5000);
 }
 document.addEventListener('click',async event=>{
  if(!enabled || !event.isTrusted || event.defaultPrevented || event.button!==0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey)return;
  const anchor=event.composedPath().find(node=>node?.tagName==='A'&&node.href);
  if(!anchor)return;
  let url;
  try{url=new URL(anchor.href);if(!/^https?:$/.test(url.protocol)||!isDownload(anchor,url))return;}catch(e){return;}
  event.preventDefault();event.stopImmediatePropagation();
  const fallback=document.createElement('a');fallback.href=url.href;fallback.target=anchor.target;fallback.rel=anchor.rel;
  if(anchor.hasAttribute('download'))fallback.setAttribute('download',anchor.getAttribute('download'));
  try{
   showNotice('Đang chuyển liên kết sang Download Now…');
   const result=await bridge.runtime.sendMessage({type:'capture-link',url:url.href,name:anchor.getAttribute('download')||'',requestId:crypto.randomUUID()});
   if(!result?.ok)throw Error(result?.error||'Không kết nối được ứng dụng.');
   if(result.cancelled){showNotice('Đã hủy tải.');return;}
   showNotice('Đã thêm vào Download Now.');
  }catch(e){
   if(exclusive){showNotice('Không chuyển được sang Download Now. Hãy mở ứng dụng và thử lại; không tự tải bằng trình duyệt.');return;}
   showNotice('Không chuyển được. Tiếp tục bằng trình duyệt.');
   fallback.hidden=true;(document.body||document.documentElement).append(fallback);fallback.click();fallback.remove();
  }
 },true);
})();
