const bridge = globalThis.browser || globalThis.chrome;
if(!globalThis.DownloadNowUpdates&&typeof importScripts==='function')importScripts('updates.js');
const fallbackUrls = new Map();
const inFlight = new Map();
const CONTENT_ID = 'download-now-links';
const origins = ['http://*/*', 'https://*/*'];
let interceptionSync=Promise.resolve();
let updateDownloadInFlight=null;

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
  if(values.extensionAutoDownload&&values.extensionDownloadedVersion!==info.version)await downloadExtensionUpdate();
 }
 return info;
}
if(bridge.alarms){
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
 if(intercept && permitted && !registered.length)await bridge.scripting.registerContentScripts([{
  id:CONTENT_ID,js:['content.js'],matches:origins,
  excludeMatches:['http://127.0.0.1/*','http://localhost/*'],runAt:'document_start',allFrames:true
 }]);
 if((!intercept || !permitted) && registered.length)await bridge.scripting.unregisterContentScripts({ids:[CONTENT_ID]});
}
bridge.runtime.onInstalled.addListener(async()=>{
 try{
  await bridge.contextMenus.removeAll();
  bridge.contextMenus.create({id:'download-now',title:'Tải bằng Download Now',contexts:['link','video','audio']});
  const values=await bridge.storage.local.get(['capture','intercept']);
  if(values.capture===undefined)await bridge.storage.local.set({capture:true});
  if(values.intercept===undefined)await bridge.storage.local.set({intercept:false});
  await syncInterception();
  if(bridge.tabs)await bridge.tabs.create({url:'http://127.0.0.1:8765/'});
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
 const response=await fetch('http://127.0.0.1:8765/api/'+(automatic?'capture':'jobs'),{
  method:'POST',headers:{'Content-Type':'application/json',Authorization:'Bearer '+token},
  body:JSON.stringify({url,ask_save:true,...(name?{name}:{}),...(automatic?{request_id:requestId}:{})}),signal:AbortSignal.timeout(12000)
 });
 let data=await response.json();
 if(!response.ok)throw Error(response.status===404?'Cần nâng cấp ứng dụng lên v1.5.0 để chọn nơi lưu.':data.error||'Không thể gửi liên kết.');
 if(data.prompt_id){
  const prompt=data.prompt_id;
  await record('Đang chờ bạn chọn nơi lưu trong hộp thoại Windows.');
  do{
   await new Promise(resolve=>setTimeout(resolve,800));
   const status=await fetch('http://127.0.0.1:8765/api/prompts/'+prompt,{headers:{Authorization:'Bearer '+token},signal:AbortSignal.timeout(12000)});
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
 if(info.menuItemId==='download-now')send(info.linkUrl||info.srcUrl).catch(e=>record(e.message,true));
});

async function captureDownload(item) {
 let pausedByUs=false;
 try{
  if(item.byExtensionId&&item.byExtensionId===bridge.runtime.id)return;
  const {capture,token}=await bridge.storage.local.get(['capture','token']);
  const original=item.finalUrl||item.url;
  if(!capture || !token || !/^https?:\/\//i.test(original) || item.state==='complete' || item.paused || item.danger && item.danger!=='safe')return;
  const bypassUntil=fallbackUrls.get(original)||fallbackUrls.get(item.url)||0;
  if(bypassUntil>Date.now()){fallbackUrls.delete(original);fallbackUrls.delete(item.url);return;}
  try{await bridge.downloads.pause(item.id);pausedByUs=true;}catch(e){/* A download may already have completed. */}
  const [current]=await bridge.downloads.search({id:item.id});
  if(!current || current.state!=='in_progress')return;
  const url=current.finalUrl||current.url||original;
  const name=(current.filename||'').split(/[\\/]/).pop();
  const result=await automaticSend(url,name,crypto.randomUUID());
  if(result.cancelled){await bridge.downloads.cancel(item.id);return;}
  try{await bridge.downloads.cancel(item.id);}catch(e){
   if(pausedByUs){try{await bridge.downloads.resume(item.id);}catch(ignore){}}
   await record('Đã chuyển sang ứng dụng; kiểm tra danh sách tải vì trình duyệt có thể còn một bản.');
  }
 }catch(e){
  if(pausedByUs){try{await bridge.downloads.resume(item.id);}catch(resumeError){await record('Chuyển tải thất bại. Mở danh sách tải của trình duyệt để tiếp tục: '+e.message,true);return;}}
  await record('Trình duyệt tiếp tục tải. '+e.message,true);
 }
}
bridge.downloads.onCreated.addListener(item=>{captureDownload(item).catch(e=>record(e.message,true));});

bridge.runtime.onMessage.addListener((message,sender,reply)=>{
 const fromPage=!!sender.tab;
 if(message.type==='pair-app'){
  (async()=>{
   const address=new URL(sender.url||'');
   if(!fromPage || sender.frameId!==0 || !['http://127.0.0.1:8765','http://localhost:8765'].includes(address.origin) || !/^[A-Za-z0-9_-]{20,200}$/.test(message.token||''))throw Error('Trang ghép nối không hợp lệ.');
   const response=await fetch('http://127.0.0.1:8765/api/info',{headers:{Authorization:'Bearer '+message.token},signal:AbortSignal.timeout(5000)});
   if(!response.ok)throw Error('Không xác minh được ứng dụng.');
   const info=await response.json();
   if(typeof info.version!=='string')throw Error('Phản hồi ứng dụng không hợp lệ.');
   await bridge.storage.local.set({token:message.token,lastError:'',lastStatus:'Đã tự kết nối ứng dụng v'+info.version});
   await record('Đã tự kết nối ứng dụng v'+info.version);
   return {ok:true,version:info.version};
  })().then(reply).catch(e=>reply({error:e.message}));return true;
 }
 if(message.type==='capture-link'){
  (async()=>{
   const {capture,intercept,token}=await bridge.storage.local.get(['capture','intercept','token']);
   if(!capture || !intercept || !token)return {error:'Bắt link đang tắt hoặc chưa ghép nối.'};
   try{const result=await automaticSend(message.url,message.name||'',message.requestId);return {ok:true,cancelled:!!result.cancelled};}
   catch(e){fallbackUrls.set(message.url,Date.now()+20000);await record(e.message,true);return {error:e.message};}
  })().then(reply).catch(e=>reply({error:e.message}));return true;
 }
 if(fromPage)return;
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
