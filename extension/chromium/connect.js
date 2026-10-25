// Only injected into the local application's top-level page by the manifest.
if(window.top===window && location.protocol==='http:' && ['127.0.0.1','localhost'].includes(location.hostname) && Number(location.port)>=1024 && document.querySelector('meta[name="download-now-app"]')?.content==='1'){
 const token=document.querySelector('meta[name="bridge-token"]')?.content;
 if(token){
  const bridge=globalThis.browser||globalThis.chrome;
  bridge.runtime.sendMessage({type:'pair-app',token}).then(result=>{
   const status=document.querySelector('#extension-connection');
   if(status)status.textContent=result?.ok?'Tiện ích đã tự kết nối với ứng dụng.':result?.error||'Chưa kết nối được tiện ích.';
  }).catch(()=>{});
  // The page remains open throughout update/restart. Poll locally so both
  // running components converge without a second update button or ZIP.
  const syncTimer=setInterval(()=>{
   try{if(!document.hidden)bridge.runtime.sendMessage({type:'sync-app-update'}).catch(()=>{});}
   catch(e){clearInterval(syncTimer);}
  },2000);
 }
}
