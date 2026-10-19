// Only injected into the local application's top-level page by the manifest.
if(window.top===window && ['http://127.0.0.1:8765','http://localhost:8765'].includes(location.origin)){
 const token=document.querySelector('meta[name="bridge-token"]')?.content;
 if(token){
  const bridge=globalThis.browser||globalThis.chrome;
  bridge.runtime.sendMessage({type:'pair-app',token}).then(result=>{
   const status=document.querySelector('#extension-connection');
   if(status)status.textContent=result?.ok?'Tiện ích đã tự kết nối với ứng dụng.':result?.error||'Chưa kết nối được tiện ích.';
  }).catch(()=>{});
 }
}
