const bridge = globalThis.browser || globalThis.chrome;
if(!globalThis.DownloadNowUpdates&&typeof importScripts==='function')importScripts('updates.js');
if(!globalThis.DownloadNowFacebookProbe&&typeof importScripts==='function')importScripts('facebook-probe.js');
const fallbackUrls = new Map();
const inFlight = new Map();
function localApplicationBase(value){
 try{
  const u=new URL(value),port=Number(u.port);
  if(u.protocol!=='http:'||!['127.0.0.1','localhost'].includes(u.hostname)||u.username||u.password||!Number.isInteger(port)||port<1024||port>65535)return null;
  return 'http://127.0.0.1:'+port;
 }catch(error){return null;}
}
async function probeApplication(base){
 if(!localApplicationBase(base))return false;
 try{
  const response=await fetch(base+'/api/discovery',{credentials:'omit',redirect:'error',signal:AbortSignal.timeout(900)});
  if(!response.ok)return false;
  const info=await response.json();
  return info.application==='DownloadNow'&&info.protocol===1&&info.port===Number(new URL(base).port)&&typeof info.version==='string';
 }catch(error){return false;}
}
let discoveryInFlight=null;
async function applicationBase(){
 if(discoveryInFlight)return discoveryInFlight;
 discoveryInFlight=(async()=>{
  const stored=await bridge.storage.local.get('appBase');
  const preferred=localApplicationBase(stored.appBase||'http://127.0.0.1:8765');
  if(preferred&&await probeApplication(preferred))return preferred;
  const candidates=Array.from({length:10},(_,i)=>'http://127.0.0.1:'+(8765+i)).filter(base=>base!==preferred);
  const results=await Promise.all(candidates.map(base=>probeApplication(base)));
  const base=candidates[results.indexOf(true)];
  if(!base)throw Error('Không tìm thấy Download Now. Hãy mở ứng dụng rồi thử lại.');
  await bridge.storage.local.set({appBase:base});return base;
 })().finally(()=>{discoveryInFlight=null;});
 return discoveryInFlight;
}
function videoPageURL(value){
 try{const u=new URL(value),host=u.hostname.replace(/^(www\.|m\.)/,'');
  return /^https?:$/.test(u.protocol)&&!u.username&&!u.password&&((host==='youtube.com'&&/^\/(shorts\/|watch|live\/)/.test(u.pathname))||host==='youtu.be'&&u.pathname.length>1||host==='instagram.com'&&/^\/(reels?\/|p\/)/.test(u.pathname)||['facebook.com','web.facebook.com'].includes(host)&&(/^\/(reels?\/|watch|share\/r\/|video\.php|story\.php|permalink\.php)/.test(u.pathname)||u.pathname.includes('/videos/')||u.pathname.includes('/posts/')));
 }catch(e){return false;}
}
const CONTENT_ID = 'download-now-links';
const origins = ['http://*/*', 'https://*/*'];
let interceptionSync=Promise.resolve();
let updateDownloadInFlight=null;
let extensionSyncInFlight=null;

async function reportExtension(){
 const {token}=await bridge.storage.local.get('token');
 if(!token)return;
 const marker=await managedExtension();
 const agent=globalThis.navigator?.userAgent||'';
 const browser=bridge.runtime.getBrowserInfo?'Firefox':/Edg\//.test(agent)?'Edge':/OPR\//.test(agent)?'Opera':'Chrome';
 const response=await fetch((await applicationBase())+'/api/extension/heartbeat',{
  method:'POST',headers:{Authorization:'Bearer '+token,'Content-Type':'application/json'},
  body:JSON.stringify({id:bridge.runtime.id,version:bridge.runtime.getManifest().version,managed:!!marker,browser}),signal:AbortSignal.timeout(5000)
 });
 if(!response.ok)throw Error('Cần ứng dụng mới để xác nhận đồng bộ tiện ích.');
 return response.json();
}
async function synchronizeExtension(){
 if(extensionSyncInFlight)return extensionSyncInFlight;
 extensionSyncInFlight=(async()=>{
  // Report the running version, never mistake updated files for loaded code.
  await reportExtension();
  return {reloading:await reloadManagedExtension()};
 })().finally(()=>{extensionSyncInFlight=null;});
 return extensionSyncInFlight;
}

async function managedExtension(){
 try{
  const response=await fetch(bridge.runtime.getURL('managed.json'),{cache:'no-store'});
  if(!response.ok)return null;
  const marker=await response.json();
  return marker.managed===true&&/^\d+\.\d+\.\d+$/.test(marker.version)?marker:null;
 }catch(e){return null;}
}
async function reloadManagedExtension(){
 const marker=await managedExtension();
 if(!marker||inFlight.size)return false;
 // Read the installed files, not the running manifest cached by the browser.
 const response=await fetch(bridge.runtime.getURL('manifest.json'),{cache:'no-store'});
 if(!response.ok)return false;
 const manifest=await response.json(),current=bridge.runtime.getManifest().version;
 if(manifest.version!==marker.version)return false;
 const {token}=await bridge.storage.local.get('token');
 if(!token)return false;
 const app=await fetch((await applicationBase())+'/api/info',{headers:{Authorization:'Bearer '+token},signal:AbortSignal.timeout(5000)});
 if(!app.ok||(await app.json()).version!==marker.version)return false;
 const newer=manifest.version.split('.').map(Number).some((part,i,parts)=>parts.slice(0,i).every((v,j)=>v===Number(current.split('.')[j]))&&part>Number(current.split('.')[i]));
 if(newer){bridge.runtime.reload();return true;}
 return false;
}
async function downloadExtensionUpdate(){
 if(updateDownloadInFlight)return updateDownloadInFlight;
 updateDownloadInFlight=(async()=>{
  const info=await globalThis.DownloadNowUpdates.check();
  if(!info.newer)return {upToDate:true};
  // Never transfer the extension's own update ZIP back into the downloader.
  fallbackUrls.set(info.url,Date.now()+60000);
  const id=await bridge.downloads.download({url:info.url,filename:'DownloadNow/'+info.filename,saveAs:false});
  await bridge.storage.local.set({extensionDownloadedVersion:info.version,extensionUpdateDownloadId:id});
  return {id,version:info.version};
 })().finally(()=>{updateDownloadInFlight=null;});
 return updateDownloadInFlight;
}
async function checkExtensionUpdate(force=false){
 const info=await globalThis.DownloadNowUpdates.check(force);
 const values=await bridge.storage.local.get(['extensionAutoDownload','extensionDownloadedVersion']);
 if(info.newer){
  await bridge.action.setBadgeText({text:'NEW'});
  // Updates now require approval in the application; never download ZIPs silently.
 }
 return info;
}
if(bridge.alarms){
 bridge.alarms.get('managed-extension-reload').then(alarm=>{if(!alarm)bridge.alarms.create('managed-extension-reload',{periodInMinutes:1});}).catch(()=>{});
 bridge.alarms.onAlarm.addListener(alarm=>{if(alarm.name==='managed-extension-reload')synchronizeExtension().catch(()=>{});});
 bridge.alarms.get('extension-update-check').then(alarm=>{if(!alarm)bridge.alarms.create('extension-update-check',{periodInMinutes:360});}).catch(()=>{});
 bridge.alarms.onAlarm.addListener(alarm=>{if(alarm.name==='extension-update-check')checkExtensionUpdate().catch(e=>bridge.storage.local.set({extensionUpdateError:e.message}));});
}
if(bridge.downloads.onChanged)bridge.downloads.onChanged.addListener(async change=>{
 if(change.state?.current!=='interrupted'&&!change.error)return;
 const values=await bridge.storage.local.get('extensionUpdateDownloadId');
 if(values.extensionUpdateDownloadId===change.id)await bridge.storage.local.set({extensionDownloadedVersion:'',extensionUpdateDownloadId:null,extensionUpdateError:'Gói tiện ích tải lỗi. Nhấn Tải gói mới để thử lại.'});
});

async function record(text, error=false) {
 await bridge.storage.local.set({lastStatus:text, lastError:error?text:''});
 await bridge.action.setBadgeBackgroundColor({color:error?'#bd694f':'#F1AF00'});
 await bridge.action.setBadgeText({text:error?'!':'ON'});
}
function syncInterception() {
 interceptionSync=interceptionSync.catch(()=>{}).then(applyInterception);
 return interceptionSync;
}
async function applyInterception() {
 const {intercept}=await bridge.storage.local.get('intercept');
 const registered=await bridge.scripting.getRegisteredContentScripts({ids:[CONTENT_ID]});
 const permitted=await bridge.permissions.contains({origins});
 const scripts=['facebook-feed.js','content.js'];
 if(intercept&&permitted&&registered.length&&JSON.stringify(registered[0].js)!==JSON.stringify(scripts)){
  await bridge.scripting.unregisterContentScripts({ids:[CONTENT_ID]});registered.length=0;
 }
 if(intercept && permitted && !registered.length)await bridge.scripting.registerContentScripts([{
  id:CONTENT_ID,js:scripts,matches:origins,
  excludeMatches:['http://127.0.0.1/*','http://localhost/*'],runAt:'document_start',allFrames:true
 }]);
 if((!intercept || !permitted) && registered.length)await bridge.scripting.unregisterContentScripts({ids:[CONTENT_ID]});
 if(intercept&&permitted)await attachFacebookTabs();
}
async function attachFacebookTabs(){
 if(!bridge.tabs?.query||!bridge.scripting?.executeScript)return;
 const tabs=await bridge.tabs.query({url:['*://facebook.com/*','*://www.facebook.com/*','*://m.facebook.com/*','*://web.facebook.com/*']});
 for(const tab of tabs){
  try{
   const u=new URL(tab.url);
   if(!/^https?:$/.test(u.protocol)||!['facebook.com','www.facebook.com','m.facebook.com','web.facebook.com'].includes(u.hostname))continue;
   await bridge.scripting.executeScript({target:{tabId:tab.id},files:['facebook-feed.js','content.js']});
  }catch(e){/* A tab may close or navigate while the extension is updating. */}
 }
}
async function refreshApplicationTabs(){
 if(!bridge.tabs?.query||!bridge.tabs?.reload)return;
 const stored=await bridge.storage.local.get('appBase');
 const base=localApplicationBase(stored.appBase||'http://127.0.0.1:8765');
 const tabs=await bridge.tabs.query({url:['http://127.0.0.1/*','http://localhost/*']});
 for(const tab of tabs){
  try{if(localApplicationBase(tab.url)===base)await bridge.tabs.reload(tab.id);}
  catch(e){/* A tab may have closed during application restart. */}
 }
}
bridge.runtime.onInstalled.addListener(async(details={})=>{
 try{
  await bridge.contextMenus.removeAll();
  bridge.contextMenus.create({id:'download-now',title:'Tải bằng Download Now',contexts:['link','video','audio']});
  const values=await bridge.storage.local.get(['capture','intercept']);
  if(values.capture===undefined)await bridge.storage.local.set({capture:true});
  if(values.intercept===undefined)await bridge.storage.local.set({intercept:false});
  await syncInterception();
  if(details.reason==='update')await refreshApplicationTabs();
  else if(details.reason==='install'&&bridge.tabs)await bridge.tabs.create({url:(await applicationBase())+'/'});
  if(globalThis.DownloadNowUpdates)await checkExtensionUpdate().catch(e=>bridge.storage.local.set({extensionUpdateError:e.message}));
 }catch(e){await record(e.message,true);}
});
bridge.runtime.onStartup.addListener(()=>{syncInterception().catch(e=>record(e.message,true));if(globalThis.DownloadNowUpdates)checkExtensionUpdate().catch(e=>bridge.storage.local.set({extensionUpdateError:e.message}));});
bridge.storage.onChanged.addListener((changes,area)=>{
 if(area==='local' && changes.intercept)syncInterception().catch(e=>record(e.message,true));
});

async function send(url,name='',requestId=crypto.randomUUID(),automatic=false) {
 if(!/^https?:\/\//i.test(url))throw Error('Chỉ hỗ trợ liên kết HTTP(S) trực tiếp.');
 const {token}=await bridge.storage.local.get('token');
 if(!token)throw Error('Chưa ghép nối: dán mã kết nối trong tiện ích rồi nhấn Lưu.');
 const base=await applicationBase();
 let response;
 const attempts=automatic&&requestId?3:1;
 for(let attempt=0;attempt<attempts;attempt++){
 try{response=await fetch(base+'/api/'+(automatic?'capture':'jobs'),{
  method:'POST',headers:{'Content-Type':'application/json',Authorization:'Bearer '+token},
  body:JSON.stringify({url,ask_save:true,...(name?{name}:{}),...(automatic?{request_id:requestId}:{})}),signal:AbortSignal.timeout(12000)
 });break;}catch(error){
  // The same capture request_id returns the existing save ticket/job.
  // Requests without that deduplication key must never be repeated.
  if(attempt+1<attempts){await new Promise(resolve=>setTimeout(resolve,300*(attempt+1)));continue;}
  throw Error('Không kết nối được Download Now. Hãy mở ứng dụng rồi thử lại.');
 }
 }
 let data=await response.json();
 if(!response.ok)throw Error(response.status===404?'Cần nâng cấp ứng dụng lên v1.5.0 để chọn nơi lưu.':data.error||'Không thể gửi liên kết.');
 if(data.prompt_id){
  const prompt=data.prompt_id;
  try{await record('Đang chờ bạn chọn nơi lưu trong hộp thoại Windows.');}catch(error){}
  let connectionFailures=0;
  data={state:'pending'};
  do{
   await new Promise(resolve=>setTimeout(resolve,800));
   let status;
   try{
    status=await fetch(base+'/api/prompts/'+prompt,{headers:{Authorization:'Bearer '+token},signal:AbortSignal.timeout(12000)});
   }catch(error){
    if(++connectionFailures<3)continue;
    throw Error('Mất kết nối với Download Now. Kiểm tra danh sách tải trong ứng dụng trước khi thử lại.');
   }
   connectionFailures=0;
   data=await status.json();
   if(!status.ok)throw Error(data.error||'Không thể kiểm tra hộp thoại lưu.');
  }while(data.state==='pending');
  if(data.state==='error')throw Error(data.error);
  if(data.state==='cancelled'){await record('Bạn đã hủy chọn nơi lưu.');return {cancelled:true};}
 }
 try{await record('Đã chuyển lượt tải sang Download Now.');}catch(e){/* Handoff is already accepted; badge failure must not trigger a duplicate. */}
 return data;
}
function automaticSend(url,name,requestId) {
 if(inFlight.has(url))return inFlight.get(url);
 const pending=send(url,name,requestId,true).finally(()=>inFlight.delete(url));
 inFlight.set(url,pending);return pending;
}
bridge.contextMenus.onClicked.addListener(info=>{
 if(info.menuItemId==='download-now'){
  const direct=info.linkUrl||info.srcUrl;
  if(direct?.startsWith('blob:')&&!videoPageURL(info.pageUrl)){record('Trang video này chưa được hỗ trợ.',true);return;}
  send(direct?.startsWith('blob:')?info.pageUrl:direct).catch(e=>record(e.message,true));
 }
});

async function captureDownload(item) {
 let pausedByUs=false,exclusive=true;
 try{
  if(item.byExtensionId&&item.byExtensionId===bridge.runtime.id)return;
  const {capture,token,downloadNowOnly}=await bridge.storage.local.get(['capture','token','downloadNowOnly']);
  exclusive=downloadNowOnly!==false;
  const original=item.finalUrl||item.url;
  if(!capture || !token || !/^https?:\/\//i.test(original) || item.state==='complete' || item.paused || item.danger && item.danger!=='safe')return;
  const bypassUntil=fallbackUrls.get(original)||fallbackUrls.get(item.url)||0;
  if(bypassUntil>Date.now()){fallbackUrls.delete(original);fallbackUrls.delete(item.url);return;}
  try{await bridge.downloads.pause(item.id);pausedByUs=true;}catch(e){/* A download may already have completed. */}
  const [current]=await bridge.downloads.search({id:item.id});
  if(!current || current.state!=='in_progress')return;
  // Keep the stable source URL: signed CDN redirects often end in a UUID.
  const url=current.url||item.url||current.finalUrl||original;
  const name=(current.filename||'').split(/[\\/]/).pop();
  const result=await automaticSend(url,name,crypto.randomUUID());
  if(result.cancelled){await bridge.downloads.cancel(item.id);return;}
  try{await bridge.downloads.cancel(item.id);}catch(e){
   if(pausedByUs){try{await bridge.downloads.resume(item.id);}catch(ignore){}}
   await record('Đã chuyển sang ứng dụng; kiểm tra danh sách tải vì trình duyệt có thể còn một bản.');
  }
 }catch(e){
  if(exclusive){
   try{await bridge.downloads.cancel(item.id);}catch(ignore){}
   await record('Không chuyển được sang Download Now. Lượt trình duyệt đã hủy; mở ứng dụng và thử lại. '+e.message,true);return;
  }
  if(pausedByUs){try{await bridge.downloads.resume(item.id);}catch(resumeError){await record('Chuyển tải thất bại. Mở danh sách tải của trình duyệt để tiếp tục: '+e.message,true);return;}}
  await record('Trình duyệt tiếp tục tải. '+e.message,true);
 }
}
async function captureBeforeSaveAs(item,suggest){
 try{
  const {capture,token,downloadNowOnly}=await bridge.storage.local.get(['capture','token','downloadNowOnly']);
  const url=item.url||item.finalUrl;
  if(!capture||!/^https?:\/\//i.test(url)||item.state==='complete'||item.danger&&item.danger!=='safe'||item.byExtensionId===bridge.runtime.id&&item.byExtensionId)return;
  if((fallbackUrls.get(url)||fallbackUrls.get(item.url)||0)>Date.now()){
   fallbackUrls.delete(url);fallbackUrls.delete(item.url);return;
  }
  if(!token){
   if(downloadNowOnly!==false){await bridge.downloads.cancel(item.id);await record('Chưa kết nối Download Now. Mở trang ứng dụng để tự ghép nối rồi thử lại; không mở Save As của trình duyệt.',true);}
   return;
  }
  let paused=false;
  try{
   try{await bridge.downloads.pause(item.id);paused=true;}catch(ignore){}
   const result=await automaticSend(url,(item.filename||'').split(/[\\/]/).pop(),crypto.randomUUID());
   // Finish the browser job before releasing filename determination. This
   // keeps its Save As prompt from competing with our native download dialog.
   await bridge.downloads.cancel(item.id);
   if(result.cancelled)await record('Đã hủy tải trong Download Now.');
  }catch(error){
   if(downloadNowOnly!==false){
    await bridge.downloads.cancel(item.id);
    await record('Không chuyển được sang Download Now. Lượt tải trình duyệt đã hủy để không hiện Save As. Mở ứng dụng rồi thử lại. '+error.message,true);
   }else{
    if(paused)await bridge.downloads.resume(item.id);
    await record('Trình duyệt tiếp tục tải. '+error.message,true);
   }
  }
 }finally{
  // Chrome requires every filename listener to answer exactly once, including
  // skipped and cancelled downloads. Never strand an ordinary browser download.
  try{suggest();}catch(ignore){}
 }
}
if(bridge.downloads.onDeterminingFilename){
 bridge.downloads.onDeterminingFilename.addListener((item,suggest)=>{
  captureBeforeSaveAs(item,suggest).catch(e=>record(e.message,true));
  return true;
 });
}else{
 bridge.downloads.onCreated.addListener(item=>{captureDownload(item).catch(e=>record(e.message,true));});
}

bridge.runtime.onMessage.addListener((message,sender,reply)=>{
 const fromPage=!!sender.tab;
 if(message.type==='application-info'){
  if(fromPage){reply({error:'Chỉ dùng trong tiện ích.'});return false;}
  (async()=>{
   const base=await applicationBase();
   if(message.token===undefined)return {base};
   const response=await fetch(base+'/api/info',{headers:{Authorization:'Bearer '+message.token},signal:AbortSignal.timeout(4000)});
   if(!response.ok)throw Error('Mã kết nối không hợp lệ. Mở trang ứng dụng để ghép nối lại.');
   return {base,info:await response.json()};
  })().then(reply).catch(error=>reply({error:error.message}));return true;
 }
 if(message.type==='resolve-facebook-story-source'){
  (async()=>{
   const page=new URL(sender.url||''),requested=new URL(message.page||'');
   const hosts=['facebook.com','www.facebook.com','m.facebook.com','web.facebook.com'];
   if(!fromPage||sender.frameId!==0||page.protocol!=='https:'||!hosts.includes(page.hostname)||requested.origin!==page.origin||!requested.pathname.startsWith('/stories/'))throw Error('Trang Tin không hợp lệ hoặc đã thay đổi.');
   const settings=await bridge.storage.local.get(['capture','intercept','token']);
   if(!settings.capture||!settings.intercept||!settings.token)throw Error('Bật bắt link và kết nối ứng dụng trước.');
   const results=await bridge.scripting.executeScript({target:{tabId:sender.tab.id,frameIds:[0]},world:'MAIN',func:globalThis.DownloadNowFacebookProbe,args:[requested.href,message.target]});
   const result=results.find(r=>r.frameId===0)?.result;
   if(!result?.url)throw Error(result?.error||'Chưa tìm được nguồn phát của Tin này.');
   const url=new URL(result.url);
   if(url.protocol!=='https:'||url.username||url.password||!url.hostname.endsWith('.fbcdn.net')||! /\.mp4$/i.test(url.pathname))throw Error('Nguồn phát không hợp lệ.');
   return {url:url.href};
  })().then(reply).catch(e=>reply({error:e.message}));return true;
 }
 if(message.type==='sync-app-update'){
  try{
   const origin=new URL(sender.url||'').origin;
   if(!fromPage||sender.frameId!==0||!localApplicationBase(origin))throw Error('Trang đồng bộ không hợp lệ.');
   synchronizeExtension().then(reply).catch(e=>reply({error:e.message}));
  }catch(e){reply({error:e.message});}
  return true;
 }
 if(message.type==='pair-app'){
  (async()=>{
   const address=new URL(sender.url||'');
   const base=localApplicationBase(address.origin);
   if(!fromPage || sender.frameId!==0 || !base || !/^[A-Za-z0-9_-]{20,200}$/.test(message.token||''))throw Error('Trang ghép nối không hợp lệ.');
   if(!await probeApplication(base))throw Error('Cổng này không phải Download Now.');
   const response=await fetch(base+'/api/info',{headers:{Authorization:'Bearer '+message.token},signal:AbortSignal.timeout(5000)});
   if(!response.ok)throw Error('Không xác minh được ứng dụng.');
   const info=await response.json();
   if(typeof info.version!=='string')throw Error('Phản hồi ứng dụng không hợp lệ.');
   await bridge.storage.local.set({token:message.token,appBase:base,lastError:'',lastStatus:'Đã tự kết nối ứng dụng v'+info.version+' · cổng '+address.port});
   if(bridge.runtime.getManifest&&bridge.runtime.getURL)synchronizeExtension().catch(()=>{});
   await record('Đã tự kết nối ứng dụng v'+info.version);
   return {ok:true,version:info.version};
  })().then(reply).catch(e=>reply({error:e.message}));return true;
 }
 if(message.type==='capture-link'){
  (async()=>{
   const {capture,intercept,token,downloadNowOnly}=await bridge.storage.local.get(['capture','intercept','token','downloadNowOnly']);
   if(!capture || !intercept || !token)return {error:'Bắt link đang tắt hoặc chưa ghép nối.'};
   try{const result=await automaticSend(message.url,message.name||'',message.requestId);return {ok:true,cancelled:!!result.cancelled};}
   catch(e){if(downloadNowOnly===false)fallbackUrls.set(message.url,Date.now()+20000);await record(e.message,true);return {error:e.message};}
  })().then(reply).catch(e=>reply({error:e.message}));return true;
 }
 if(fromPage)return;
 if(message.type==='send-current-video'){
  (async()=>{
   const [tab]=await bridge.tabs.query({active:true,currentWindow:true});
   if(!tab?.url)throw Error('Không đọc được trang hiện tại. Mở trang Reels/Shorts rồi bấm tiện ích.');
   const host=new URL(tab.url).hostname.replace(/^(www\.|m\.)/,'');
   if(['facebook.com','web.facebook.com'].includes(host)&&!videoPageURL(tab.url)){
    let result;try{result=await bridge.tabs.sendMessage(tab.id,{type:'resolve-facebook-video'});}catch(e){throw Error('Bật Bắt link tệp ngay khi bấm rồi tải lại Facebook để chọn video/Tin.');}
    if(!result?.url)throw Error(result?.error||'Hãy dùng nút trên đúng video/Tin cần tải.');
    const media=new URL(result.url);if(!videoPageURL(result.url)&&!(media.protocol==='https:'&&media.hostname.endsWith('.fbcdn.net')&&/\.mp4$/i.test(media.pathname)))throw Error('Nguồn video Facebook không hợp lệ.');
    return send(result.url,'Facebook video.mp4');
   }
   if(!videoPageURL(tab.url))throw Error('Hãy mở video YouTube Shorts, Facebook Reels hoặc Instagram Reels.');
   return send(tab.url);
  })().then(result=>reply({ok:true,cancelled:!!result.cancelled})).catch(e=>reply({error:e.message}));return true;
 }
 if(message.type==='extension-update-mode'){
  managedExtension().then(marker=>reply({managed:!!marker}));return true;
 }
 if(message.type==='extension-update-apply'){
  (async()=>{
   if(await reloadManagedExtension())return {reloading:true};
   // Ask the application to check; its own dialog obtains user approval.
   await bridge.tabs.create({url:(await applicationBase())+'/?update=1'});
   return {ok:true};
  })().then(reply).catch(e=>reply({error:e.message}));return true;
 }
 if(message.type==='extension-update-check'){
  checkExtensionUpdate(!!message.force).then(info=>reply({info})).catch(e=>reply({error:e.message}));return true;
 }
 if(message.type==='extension-update-download'){
  downloadExtensionUpdate().then(result=>reply(result)).catch(e=>reply({error:e.message}));return true;
 }
 if(message.type==='sync-interception'){
  syncInterception().then(()=>reply({ok:true})).catch(e=>reply({error:e.message}));return true;
 }
 if(message.type==='send'){
  send(message.url).then(result=>reply({ok:true,cancelled:!!result.cancelled})).catch(e=>reply({error:e.message}));return true;
 }
});
if(bridge.runtime.getManifest&&bridge.runtime.getURL)synchronizeExtension().catch(()=>{});
