// Fetch package metadata only. No remote code is loaded or executed.
globalThis.DownloadNowUpdates=(()=>{
 const bridge=globalThis.browser||globalThis.chrome;
 const repository='XOmongoose/DownloadNow',base='https://github.com/'+repository;
 function version(value){if(!/^\d+\.\d+\.\d+$/.test(value))throw Error('Phiên bản tiện ích không hợp lệ.');return value.split('.').map(Number);}
 function newer(a,b){const x=version(a),y=version(b);for(let i=0;i<3;i++){if(x[i]!==y[i])return x[i]>y[i];}return false;}
 function select(release,browser,current){
  if(release.draft||release.prerelease)throw Error('Bỏ qua bản nháp hoặc bản thử nghiệm.');
  const tag=release.tag_name||'',latest=tag.replace(/^v/,'');version(latest);
  const expected='DownloadNow-'+browser+'-'+latest+(browser==='Firefox'?'-unsigned':'')+'.zip';
  const fallback='DownloadNow-Browser-Extensions-'+latest+'.zip';
  const assets=release.assets||[];
  const asset=assets.find(item=>item.name===expected)||assets.find(item=>item.name===fallback);
  if(!asset)throw Error('Release chưa có gói tiện ích phù hợp.');
  const url=base+'/releases/download/'+encodeURIComponent(tag)+'/'+asset.name;
  if(asset.browser_download_url!==url)throw Error('Đường dẫn gói cập nhật không thuộc kho chính thức.');
  return {current,version:latest,newer:newer(latest,current),url,filename:asset.name,page:base+'/releases/tag/'+encodeURIComponent(tag),browser};
 }
 async function browserName(){
  if(bridge.runtime.getBrowserInfo)return 'Firefox';
  const agent=globalThis.navigator?.userAgent||'';
  return /Edg\//.test(agent)?'Edge':/OPR\//.test(agent)?'Opera':'Chrome';
 }
 async function check(force=false){
  const current=bridge.runtime.getManifest().version,browser=await browserName();
  const stored=await bridge.storage.local.get(['extensionRelease','extensionCheckedAt']);
  let release=stored.extensionRelease;
  if(force||!release||Date.now()-(stored.extensionCheckedAt||0)>6*3600000){
   const response=await fetch('https://api.github.com/repos/'+repository+'/releases/latest',{headers:{Accept:'application/vnd.github+json'},signal:AbortSignal.timeout(12000)});
   if(!response.ok)throw Error('Chưa kiểm tra được bản tiện ích mới (GitHub '+response.status+').');
   release=await response.json();
   select(release,browser,current);
   await bridge.storage.local.set({extensionRelease:release,extensionCheckedAt:Date.now()});
  }
  return select(release,browser,current);
 }
 return {check,select,newer};
})();
