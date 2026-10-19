const token = document.querySelector('meta[name="bridge-token"]').content;
const $ = s => document.querySelector(s);
const iconPaths = {
 plus:['M12 5v14M5 12h14'],download:['M12 3v12m-5-5 5 5 5-5M5 16v5h14v-5'],
 pause:['M8 5v14M16 5v14'],play:['m8 5 11 7-11 7Z'],retry:['M20 7v5h-5','M19 12a7 7 0 1 0-2 5'],
 grid:['M3 3h7v7H3zM14 3h7v7h-7zM3 14h7v7H3zM14 14h7v7h-7z'],
 clock:['M12 8v4l3 2','M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0'],
 check:['m5 12 4 4L19 6'],alert:['m12 3 10 18H2Z','M12 9v4m0 4h.01'],
 calendar:['M4 5h16v16H4zM8 3v4m8-4v4M4 11h16M8 15h2m4 0h2'],
 puzzle:['M9 3H4v6a3 3 0 1 1 0 6v5h6a3 3 0 1 1 6 0h4v-6a3 3 0 1 0 0-6V3h-5a3 3 0 1 1-6 0Z'],
 search:['M16 16l5 5','M18 10a8 8 0 1 1-16 0 8 8 0 0 1 16 0'],
 bolt:['m13 2-9 12h7l-1 8 10-12h-7Z'],arrow:['M7 17 17 7M7 7h10v10'],
 copy:['M9 9h12v12H9zM5 15H3V3h12v2'],folder:['M3 7V5h6l2 2h10v13H3Z','M3 10h18'],close:['m6 6 12 12M6 18 18 6'],
 layers:['m12 3 10 5-10 5L2 8Z','m2 12 10 5 10-5M2 16l10 5 10-5']
};
function icon(name) {
 const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');
 for(const [key,value] of Object.entries({viewBox:'0 0 24 24',fill:'none',stroke:'currentColor','stroke-width':'1.8','stroke-linecap':'round','stroke-linejoin':'round','aria-hidden':'true',focusable:'false',class:'ui-icon'}))svg.setAttribute(key,value);
 for(const d of iconPaths[name]||iconPaths.download){const path=document.createElementNS(svg.namespaceURI,'path');path.setAttribute('d',d);svg.append(path);}
 return svg;
}
document.querySelectorAll('[data-icon]').forEach(element=>element.replaceChildren(icon(element.dataset.icon)));
const labels = {queued:'Trong hàng đợi', probing:'Đang kết nối', downloading:'Đang tải', pausing:'Đang dừng…', paused:'Tạm dừng', completed:'Hoàn tất', error:'Cần kiểm tra'};
let jobs = [], filter = 'all', noticeTimer;
const active = j => ['probing','downloading','pausing'].includes(j.status);
function bytes(n) {if (!n) return '0 B';const k=Math.min(4,Math.floor(Math.log(n)/Math.log(1024)));return `${(n/1024**k).toFixed(k?1:0)} ${['B','KB','MB','GB','TB'][k]}`;}
function notice(message) {$('#toast').textContent=message;$('#toast').hidden=false;clearTimeout(noticeTimer);noticeTimer=setTimeout(()=>$('#toast').hidden=true,5000);}
async function api(path, data) {const r=await fetch('/api/'+path,{method:data?'POST':'GET',headers:{Authorization:'Bearer '+token,'Content-Type':'application/json'},...(data?{body:JSON.stringify(data)}:{})});const value=await r.json();if(!r.ok) throw Error(value.error||'Không thể kết nối.');return value;}
async function waitSavePrompt(result){
 if(!result.prompt_id)return result;
 notice('Chọn nơi lưu trong hộp thoại Windows đang mở…');
 while(true){
  await new Promise(resolve=>setTimeout(resolve,800));
  const state=await api('prompts/'+result.prompt_id);
  if(state.state==='pending')continue;
  if(state.state==='error')throw Error(state.error);
  return state;
 }
}
function text(tag, value, className) {const e=document.createElement(tag);e.textContent=value;if(className)e.className=className;return e;}
function choose(value) {filter=value;document.querySelectorAll('[data-filter]').forEach(e=>e.classList.toggle('active',e.dataset.filter===value));document.querySelectorAll('[data-tab]').forEach(e=>e.classList.toggle('active',e.dataset.tab===value));render();}
function render() {
 const counts={all:jobs.length,active:jobs.filter(active).length,queued:jobs.filter(j=>j.status==='queued').length,completed:jobs.filter(j=>j.status==='completed').length};
 Object.entries(counts).forEach(([k,v])=>$('#count-'+k).textContent=v);
 $('#tab-count').textContent=jobs.length;$('#stat-active').replaceChildren(document.createTextNode(counts.active+' '),text('small','tệp'));$('#stat-completed').replaceChildren(document.createTextNode(counts.completed+' '),text('small','tệp'));
 $('#stat-speed').textContent=bytes(jobs.reduce((s,j)=>s+j.speed,0))+'/s';$('#stat-bytes').textContent=bytes(jobs.filter(j=>j.status==='completed').reduce((s,j)=>s+j.done,0))+' đã tải về';
 const search=$('#search').value.toLocaleLowerCase('vi');const visible=jobs.filter(j=>(filter==='all'||(filter==='active'?active(j):j.status===filter))&&j.name.toLocaleLowerCase('vi').includes(search)).reverse();
 $('#empty').hidden=visible.length>0;$('#empty h2').textContent=jobs.length?'Chưa có tệp phù hợp':'Sẵn sàng cho lượt tải đầu tiên';$('#empty p').textContent=jobs.length?'Thử bộ lọc khác hoặc thêm liên kết mới.':'Dán liên kết tệp để bắt đầu. Chúng tôi sẽ lo phần còn lại.';
 $('#list-summary').textContent=`${visible.length} / ${jobs.length} tệp trong không gian của bạn`;
 const rows=visible.map(j=>{
  const tr=document.createElement('tr'),td=document.createElement('td'),cell=text('div','','file-cell'),ext=j.name.includes('.')?j.name.split('.').pop().slice(0,4).toUpperCase():'FILE';
  cell.append(text('span',ext,'file-icon'));const info=text('div','');info.append(text('span',j.name,'file-name'));
  const pct=j.total?Math.min(100,j.done/j.total*100):(j.status==='completed'?100:0);
  let meta=`${bytes(j.done)} · ${pct.toFixed(0)}%`;
  if(j.status==='queued'&&j.start_at)meta='◷ '+new Date(j.start_at*1000).toLocaleString('vi-VN');
  if(j.status==='error')meta=j.error;
  if(j.status==='downloading'&&j.speed&&j.total)meta+=` · còn ${Math.ceil((j.total-j.done)/j.speed)} giây`;
  const subtitle=text('span',meta,'file-meta');subtitle.title=j.error||j.url;info.append(subtitle);
  if(j.status==='completed'&&j.file_path){const location=text('span',j.file_path,'file-meta file-location');location.title=j.file_path;info.append(location);}
  if(active(j)){const bar=text('div','','progress'),fill=text('div','','progress-fill');fill.style.width=pct+'%';bar.setAttribute('role','progressbar');bar.setAttribute('aria-valuenow',pct.toFixed(0));bar.setAttribute('aria-label',j.name);bar.setAttribute('aria-valuemin','0');bar.setAttribute('aria-valuemax','100');bar.append(fill);info.append(bar);}
  cell.append(info);td.append(cell);tr.append(td,text('td',j.total===null?'Chưa xác định':bytes(j.total)));
  const status=document.createElement('td');status.append(text('span',labels[j.status],`status ${j.status}`));tr.append(status,text('td',j.speed?bytes(j.speed)+'/s':'—'));
  const actions=document.createElement('td');if(j.status!=='completed'){const pause=active(j)||j.status==='queued',b=text('button','','row-action');b.append(icon(pause?'pause':j.status==='error'?'retry':'play'));b.title=pause?'Tạm dừng':'Tiếp tục';b.setAttribute('aria-label',b.title+' '+j.name);b.disabled=j.status==='pausing';b.onclick=async()=>{b.disabled=true;try{await api('action',{id:j.id,action:pause?'pause':'resume'});await refresh();}catch(e){notice(e.message);b.disabled=false;}};actions.append(b);}else {
   const group=text('div','','file-actions'),folder=text('button','','row-action');folder.append(icon('folder'),document.createTextNode('Thư mục'));folder.title='Mở thư mục chứa '+j.name;folder.setAttribute('aria-label',folder.title);folder.onclick=async()=>{folder.disabled=true;try{await api('open-folder',{id:j.id});}catch(e){notice(e.message);}finally{folder.disabled=false;}};
   const location=text('button','','row-action');location.append(icon('copy'));location.title='Xem và sao chép đường dẫn tệp';location.setAttribute('aria-label',location.title+' '+j.name);location.onclick=()=>{$('#file-location-path').value=j.file_path||'';$('#file-location-name').textContent=j.name;$('#file-location-dialog').showModal();};group.append(folder,location);actions.append(group);
  }tr.append(actions);return tr;
 });$('#job-list').replaceChildren(...rows);
}
async function refresh(){try{jobs=await api('jobs');$('#connection-state').textContent='Đã kết nối · sẵn sàng';render();}catch(e){$('#connection-state').textContent='Mất kết nối · đang thử lại';}}
function openAdd(schedule=false){$('#form-error').textContent='';if(schedule){const d=new Date(Date.now()+3600000);d.setMinutes(d.getMinutes()-d.getTimezoneOffset());$('#add-form').elements.start_at.value=d.toISOString().slice(0,16);}$('#add-dialog').showModal();}
$('#add-open').onclick=()=>openAdd();$('#empty-add').onclick=()=>openAdd();$('#schedule-nav').onclick=()=>openAdd(true);$('#schedule-card').onclick=()=>openAdd(true);
document.querySelectorAll('.close-dialog').forEach(e=>e.onclick=()=>e.closest('dialog').close());document.querySelectorAll('[data-filter]').forEach(e=>e.onclick=()=>choose(e.dataset.filter));document.querySelectorAll('[data-tab]').forEach(e=>e.onclick=()=>choose(e.dataset.tab));$('#search').oninput=render;
$('#add-form').onsubmit=async e=>{e.preventDefault();const form=e.currentTarget,b=form.querySelector('[type="submit"]');b.disabled=true;$('#form-error').textContent='';try{const data=Object.fromEntries(new FormData(form));data.ask_save=true;data.connections=Number(data.connections);for(const field of ['start_at','stop_at'])data[field]=data[field]?new Date(data[field]).toISOString():null;const result=await waitSavePrompt(await api('jobs',data));if(result.state==='cancelled'){notice('Đã hủy chọn nơi lưu. Chưa tạo lượt tải.');return;}form.reset();$('#add-dialog').close();choose('all');await refresh();notice('Đã thêm tệp vào hàng đợi.');}catch(ex){$('#form-error').textContent=ex.message;}finally{b.disabled=false;}};
$('#extension-nav').onclick=()=>{$('#pair-token').value=token;$('#extension-dialog').showModal();};$('#copy-token').onclick=async()=>{try{await navigator.clipboard.writeText(token);notice('Đã sao chép mã kết nối.');}catch(e){$('#pair-token').select();notice('Nhấn Ctrl+C để sao chép mã.');}};
$('#version-open').onclick=()=>$('#version-dialog').showModal();
$('#copy-file-path').onclick=async()=>{try{await navigator.clipboard.writeText($('#file-location-path').value);notice('Đã sao chép đường dẫn tệp.');}catch(e){$('#file-location-path').focus();$('#file-location-path').select();notice('Nhấn Ctrl+C để sao chép đường dẫn.');}};
api('storage').then(data=>{$('#storage-path').textContent='Lưu tại '+data.directory;$('#storage-path').title=data.directory;}).catch(()=>{});
let updateState={},installAfterDownload=false,installingUpdate=false;
const updateLabels={idle:'Sẵn sàng kiểm tra cập nhật.',unconfigured:'Chưa có nguồn cập nhật. Nhập URL hoặc chọn gói ZIP trên máy.',checking:'Đang kiểm tra phiên bản…',available:'Có phiên bản mới.',up_to_date:'Bạn đang dùng phiên bản mới nhất từ nguồn đã cấu hình.',downloading:'Đang tải và xác minh gói cập nhật…',importing:'Chọn gói ZIP trong hộp thoại Windows…',ready:'Gói đã được kiểm tra, sẵn sàng cài đặt.',installing:'Đang cập nhật. Ứng dụng sẽ tự mở lại.',error:'Không thể cập nhật.'};
async function readSettings(){const s=await api('settings');$('#update-feed').value=s.update_feed;$('#auto-check-updates').checked=s.auto_check_updates;$('#auto-install-updates').checked=s.auto_install_updates;$('#remember-save-folder').checked=s.remember_save_dir;$('#remembered-folder').value=s.last_save_dir;}
async function saveSettings(){await api('settings',{update_feed:$('#update-feed').value.trim(),auto_check_updates:$('#auto-check-updates').checked,auto_install_updates:$('#auto-install-updates').checked,remember_save_dir:$('#remember-save-folder').checked});}
async function installUpdate(){
 if(installingUpdate)return;
 try{await api('update/install',{});installingUpdate=true;$('#update-state').textContent=updateLabels.installing;notice('Đang cài bản mới, dữ liệu của bạn sẽ được giữ lại.');
  const reconnect=async()=>{try{const info=await api('info');if(info.version===updateState.version){location.reload();return;}}catch(e){}setTimeout(reconnect,2500);};setTimeout(reconnect,5000);
 }catch(e){notice(e.message);$('#update-state').textContent=e.message;}
}
async function readUpdateStatus(){
 if(installingUpdate)return;
 try{updateState=await api('update/status');const s=updateState;$('#update-current').textContent='Đang dùng v'+s.current_version;$('#update-state').textContent=(updateLabels[s.state]||s.state)+(s.version?' · v'+s.version:'')+(s.error?' '+s.error:'');$('#update-notes').textContent=s.notes||'';$('#update-label').textContent=['available','ready'].includes(s.state)?'Cập nhật ●':'Cập nhật';const busy=['checking','downloading','importing','installing'].includes(s.state);$('#update-check').disabled=busy;$('#update-import').disabled=busy;$('#update-download').disabled=s.state!=='available';$('#update-install').disabled=s.state!=='ready'||!s.can_install;
  if(s.state==='error')installAfterDownload=false;
  if(s.state==='ready'&&installAfterDownload){installAfterDownload=false;if(s.can_install)await installUpdate();else notice('Gói đã chuẩn bị. Cài tự động dùng trong bản EXE Windows.');}
 }catch(e){if($('#update-dialog').open)$('#update-state').textContent='Chưa kết nối được máy chủ ứng dụng.';}
}
$('#update-open').onclick=async()=>{$('#update-dialog').showModal();try{await readSettings();await readUpdateStatus();}catch(e){notice(e.message);}};
$('#settings-form').onsubmit=async e=>{e.preventDefault();try{await saveSettings();notice('Đã lưu tùy chọn.');await readSettings();}catch(error){notice(error.message);}};
$('#update-check').onclick=async()=>{try{await saveSettings();await api('update/check',{});await readUpdateStatus();}catch(e){notice(e.message);}};
$('#update-download').onclick=async()=>{try{installAfterDownload=true;await api('update/download',{});await readUpdateStatus();}catch(e){installAfterDownload=false;notice(e.message);}};
$('#update-install').onclick=installUpdate;
$('#update-import').onclick=async()=>{try{installAfterDownload=false;await api('update/import',{});await readUpdateStatus();}catch(e){notice(e.message);}};
async function pollUpdates(){await readUpdateStatus();setTimeout(pollUpdates,$('#update-dialog').open?1500:10000);}pollUpdates();
async function poll(){await refresh();setTimeout(poll,1200);}poll();
