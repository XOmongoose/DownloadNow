const bridge=globalThis.browser||globalThis.chrome;
const status=document.querySelector('#status');
const capture=document.querySelector('#capture'),intercept=document.querySelector('#intercept');
document.querySelector('#connect').onclick=async()=>{
 await bridge.tabs.create({url:'http://127.0.0.1:8765/'});
 status.textContent='Trang ứng dụng sẽ tự ghép nối. Nếu chưa mở được trang, hãy chạy DownloadNow.exe.';
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
 try{const r=await fetch('http://127.0.0.1:8765/api/info',{headers:{Authorization:'Bearer '+document.querySelector('#token').value.trim()},signal:AbortSignal.timeout(4000)});if(!r.ok)throw Error(r.status===401?'Mã kết nối sai. Hãy sao chép lại từ ứng dụng.':r.status===404?'Cần mở ứng dụng v1.5.0 trở lên.':'Không thể kết nối.');const info=await r.json();status.textContent='Đã kết nối ứng dụng v'+info.version+'. Lưu mã trước khi bắt tải.';}
 catch(e){status.textContent='Chưa kết nối: '+e.message;}
};
document.querySelector('#send').onclick=async()=>{const button=document.querySelector('#send');button.disabled=true;status.textContent='Chọn nơi lưu trong hộp thoại Windows…';try{const r=await bridge.runtime.sendMessage({type:'send',url:document.querySelector('#url').value.trim()});status.textContent=r.error||(r.cancelled?'Đã hủy tải.':'Đã thêm vào hàng đợi.');}catch(e){status.textContent=e.message;}finally{button.disabled=false;}};
