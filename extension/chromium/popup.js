const bridge=globalThis.browser||globalThis.chrome;
const status=document.querySelector('#status');
const capture=document.querySelector('#capture'),intercept=document.querySelector('#intercept');
bridge.storage.local.get('downloadNowOnly').then(data=>{document.querySelector('#download-now-only').checked=data.downloadNowOnly!==false;});
document.querySelector('#download-now-only').onchange=event=>bridge.storage.local.set({downloadNowOnly:event.target.checked});
async function readExtensionUpdate(force=false){
 const label=document.querySelector('#extension-update-status'),button=document.querySelector('#extension-update-download');
 label.textContent='Đang tìm bản tiện ích mới…';
 try{
  const result=await bridge.runtime.sendMessage({type:'extension-update-check',force});
  if(result.error)throw Error(result.error);
  const info=result.info;label.textContent=info.newer?'Có v'+info.version+' cho '+info.browser:'Tiện ích đang ở bản mới nhất: v'+info.current;
  button.disabled=false;
  const link=document.querySelector('#extension-latest-link');link.href=info.page;link.textContent='Mở bản phát hành v'+info.version;
 }catch(e){label.textContent=e.message;button.disabled=false;}
}

document.querySelector('#extension-update-download').onclick=async()=>{
 const button=document.querySelector('#extension-update-download');button.disabled=true;
 try{
  const result=await bridge.runtime.sendMessage({type:'extension-update-apply'});if(result.error)throw Error(result.error);
  document.querySelector('#extension-update-status').textContent='Đã mở cập nhật chung. Đồng ý một lần trong ứng dụng để cập nhật cả hai; tiện ích tự nạp lại sau đó.';
 }catch(e){document.querySelector('#extension-update-status').textContent=e.message;}finally{button.disabled=false;}
};
readExtensionUpdate();
document.querySelector('#connect').onclick=async()=>{
 try{
  const result=await bridge.runtime.sendMessage({type:'application-open'});
  if(result.error)throw Error(result.error);
  status.textContent=result.native?'Đã mở cửa sổ Download Now.':'Đã mở trang ghép nối tiện ích. Sau khi ghép nối, ứng dụng dùng cửa sổ riêng.';
 }catch(error){status.textContent=error.message;}
};
function state(){document.querySelector('#capture-state').textContent=capture.checked?'● Tự bắt tải: BẬT':'○ Tự bắt tải: TẮT';}
bridge.storage.local.get(['token','capture','intercept','lastError','lastStatus']).then(data=>{document.querySelector('#token').value=data.token||'';capture.checked=data.capture!==false;intercept.checked=!!data.intercept;status.textContent=data.lastError||data.lastStatus||'Ghép nối để bắt đầu bắt tải.';state();});
document.querySelector('#save').onclick=async()=>{await bridge.storage.local.set({token:document.querySelector('#token').value.trim(),capture:capture.checked,lastError:''});status.textContent='Đã lưu kết nối. Bật bắt link khi bấm nếu muốn chuyển trước khi trình duyệt tải.';state();};
capture.onchange=async()=>{await bridge.storage.local.set({capture:capture.checked});state();status.textContent=capture.checked?'Đã bật tự bắt lượt tải.':'Đã tắt tự bắt lượt tải.';};
intercept.onchange=async()=>{
 try{
  // Permission prompts only originate from this explicit user gesture.
  if(intercept.checked && !await bridge.permissions.request({origins:['http://*/*','https://*/*']})){intercept.checked=false;throw Error('Chưa được cấp quyền bắt link trên trang.');}
  await bridge.storage.local.set({intercept:intercept.checked});
  const result=await bridge.runtime.sendMessage({type:'sync-interception'});
  if(result?.error)throw Error(result.error);
  status.textContent=intercept.checked?'Đã bật bắt link. Tải lại trang chứa liên kết để áp dụng.':'Đã tắt bắt link khi bấm.';
 }catch(e){status.textContent=e.message;}
};
document.querySelector('#check').onclick=async()=>{
 try{const result=await bridge.runtime.sendMessage({type:'application-info',token:document.querySelector('#token').value.trim()});if(result.error)throw Error(result.error);status.textContent='Đã kết nối ứng dụng v'+result.info.version+' · '+result.base+'. Lưu mã trước khi bắt tải.';}
 catch(e){status.textContent='Chưa kết nối: '+e.message;}
};
document.querySelector('#send').onclick=async()=>{const button=document.querySelector('#send');button.disabled=true;status.textContent='Chọn nơi lưu trong hộp thoại Windows…';try{const r=await bridge.runtime.sendMessage({type:'send',url:document.querySelector('#url').value.trim()});status.textContent=r.error||(r.cancelled?'Đã hủy tải.':'Đã thêm vào hàng đợi.');}catch(e){status.textContent=e.message;}finally{button.disabled=false;}};

document.querySelector('#send-current-video').onclick=async()=>{
 const button=document.querySelector('#send-current-video');button.disabled=true;status.textContent='Đang phân tích video và chọn nơi lưu…';
 try{const result=await bridge.runtime.sendMessage({type:'send-current-video'});if(result.error)throw Error(result.error);status.textContent=result.cancelled?'Đã hủy tải.':'Đã thêm video vào hàng đợi.';}catch(e){status.textContent=e.message;}finally{button.disabled=false;}
};

const extensionEnabled=document.querySelector('#extension-enabled');
bridge.storage.local.get('extensionEnabled').then(s=>extensionEnabled.checked=s.extensionEnabled!==false);
extensionEnabled.onchange=async()=>{await bridge.storage.local.set({extensionEnabled:extensionEnabled.checked});status.textContent=extensionEnabled.checked?'Đã bật tiện ích.':'Đã tắt bắt link và gửi tải; lượt tải trong ứng dụng tiếp tục.';};
