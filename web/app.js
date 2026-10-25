const token = document.querySelector('meta[name="bridge-token"]').content;
const $ = s => document.querySelector(s);
const iconPaths = {
 trash:['M3 6h18M9 6V3h6v3M5 6l1 15h12l1-15M10 10v7m4-7v7'],stop:['M5 5h14v14H5z'],
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
// Keep widths on columns so periodic row rendering cannot reset a resize.
(() => {
 const table=document.querySelector('.table-scroll table');
 const headings=[...table.querySelectorAll('thead th')];
 const key='downloadnow.column-widths.v1';
 const defaults=[36,Math.max(320,table.parentElement.clientWidth-670),140,140,120,234];
 const minimums=[36,200,110,115,100,200];
 let widths=[...defaults];
 try{
  const saved=JSON.parse(localStorage.getItem(key));
  if(Array.isArray(saved)&&saved.length===6&&saved.every((n,i)=>Number.isFinite(n)&&n>=minimums[i]&&n<=2000))widths=saved;
 }catch(error){/* Storage may be unavailable in private browser profiles. */}
 const group=document.createElement('colgroup');
 const columns=widths.map(()=>{const col=document.createElement('col');group.append(col);return col;});
 table.prepend(group);table.classList.add('resizable-table');
 const handles=[];
 function apply(){
  // The last column fills remaining space: its right edge cannot leave a
  // blank strip inside the list when columns are narrowed or the frame grows.
  const last=widths.length-1;
  const preceding=widths.slice(0,last).reduce((sum,n)=>sum+n,0);
  widths[last]=Math.max(minimums[last],table.parentElement.clientWidth-preceding);
  columns.forEach((col,i)=>col.style.width=widths[i]+'px');
  table.style.width=widths.reduce((sum,n)=>sum+n,0)+'px';
  handles.forEach(({handle,i})=>handle.setAttribute('aria-valuenow',Math.round(widths[i])));
 }
 function save(){try{localStorage.setItem(key,JSON.stringify(widths));}catch(error){}}
 headings.forEach((heading,i)=>{
  if(!i||i===headings.length-1)return;
  const handle=document.createElement('span');handle.className='column-resizer';handle.tabIndex=0;
  handle.setAttribute('role','separator');handle.setAttribute('aria-orientation','vertical');
  handle.setAttribute('aria-label','Đổi độ rộng cột '+heading.textContent.trim());
  handle.setAttribute('aria-valuemin',minimums[i]);handle.setAttribute('aria-valuemax','2000');
  handle.title='Kéo để đổi độ rộng · Nhấp đúp để đặt lại';
  let drag=null;
  handle.addEventListener('pointerdown',event=>{
   if(event.button!==0)return;
   event.preventDefault();drag={x:event.clientX,width:widths[i]};
   handle.setPointerCapture(event.pointerId);document.body.classList.add('resizing-columns');
  });
  handle.addEventListener('pointermove',event=>{
   if(!drag)return;
   widths[i]=Math.max(minimums[i],Math.min(2000,drag.width+event.clientX-drag.x));apply();
  });
  function finish(){if(!drag)return;drag=null;document.body.classList.remove('resizing-columns');save();}
  handle.addEventListener('pointerup',finish);handle.addEventListener('pointercancel',finish);handle.addEventListener('lostpointercapture',finish);
  handle.addEventListener('dblclick',()=>{widths[i]=defaults[i];apply();save();});
  handle.addEventListener('keydown',event=>{
   if(!['ArrowLeft','ArrowRight','Home'].includes(event.key))return;
   event.preventDefault();widths[i]=event.key==='Home'?defaults[i]:Math.max(minimums[i],Math.min(2000,widths[i]+(event.key==='ArrowRight'?1:-1)*(event.shiftKey?50:10)));apply();save();
  });
  heading.append(handle);handles.push({handle,i});
 });
 apply();
 new ResizeObserver(()=>apply()).observe(table.parentElement);
})();
const labels = {queued:'Trong hàng đợi', probing:'Đang kết nối', downloading:'Đang tải', pausing:'Đang dừng…', paused:'Đã dừng', cancelling:'Đang hủy…', cancelled:'Đã hủy', completed:'Hoàn tất', error:'Cần kiểm tra'};
let jobs = [], filter = 'all', noticeTimer;
const active = j => ['probing','downloading','pausing','cancelling'].includes(j.status);
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
function actionButton(job,label,symbol,operation,disabled=false){
 const button=text('button',label,'row-action labeled-action');button.prepend(icon(symbol));button.title=label+' · '+job.name;button.setAttribute('aria-label',button.title);button.disabled=disabled;
 button.onclick=async()=>{button.disabled=true;try{await api('action',{id:job.id,action:operation});await refresh();}catch(e){notice(e.message);button.disabled=false;}};
 return button;
}
let historyIds=[];
let historyTarget=null;
let historyCandidates={selected:[],all:[]};
const selectedHistory=new Set();
const canClearHistory=j=>['completed','cancelled'].includes(j.status);
function updateHistorySummary(){
 const eligible=new Set(jobs.filter(canClearHistory).map(j=>j.id));
 const selected=historyCandidates.selected.filter(id=>eligible.has(id)),all=historyCandidates.all.filter(id=>eligible.has(id));
 $('#history-scope-selected-count').textContent=selected.length;$('#history-scope-all-count').textContent=all.length;
 $('#history-scope-selected').disabled=!selected.length;
 historyIds=historyTarget?selected:$('#history-scope-selected').checked?selected:all;
 $('#history-message').textContent='Sẽ xóa '+historyIds.length+' mục lịch sử. Các lượt đang tải, đã dừng và bị lỗi vẫn được giữ để tiếp tục.';
 $('#history-confirm').disabled=!historyIds.length;
 $('#history-confirm').textContent='Xóa '+historyIds.length+' mục'+($('#history-delete-files').checked?' và tệp':'');
}
function openHistory(ident=null){
 historyTarget=ident;
 $('#history-dialog .history-scope').hidden=!!ident;
 $('#history-title').textContent=ident?'Xóa mục tải này':'Xóa lịch sử tải';
 historyCandidates={selected:ident?[ident]:[...selectedHistory],all:jobs.filter(canClearHistory).map(j=>j.id)};
 if(!historyCandidates.all.length)return;
 $('#history-scope-selected').checked=historyCandidates.selected.length>0;$('#history-scope-all').checked=!historyCandidates.selected.length;
 $('#history-delete-files').checked=false;updateHistorySummary();$('#history-dialog').showModal();
}
function render() {
 $('#history-clear').disabled=!jobs.some(j=>['completed','cancelled'].includes(j.status));
 const eligibleIds=new Set(jobs.filter(canClearHistory).map(j=>j.id));
 for(const id of selectedHistory)if(!eligibleIds.has(id))selectedHistory.delete(id);
 if($('#history-dialog').open)updateHistorySummary();
 const counts={all:jobs.length,active:jobs.filter(active).length,queued:jobs.filter(j=>j.status==='queued').length,completed:jobs.filter(j=>j.status==='completed').length};
 Object.entries(counts).forEach(([k,v])=>$('#count-'+k).textContent=v);
 $('#tab-count').textContent=jobs.length;$('#stat-active').replaceChildren(document.createTextNode(counts.active+' '),text('small','tệp'));$('#stat-completed').replaceChildren(document.createTextNode(counts.completed+' '),text('small','tệp'));
 $('#stat-speed').textContent=bytes(jobs.reduce((s,j)=>s+j.speed,0))+'/s';$('#stat-bytes').textContent=bytes(jobs.filter(j=>j.status==='completed').reduce((s,j)=>s+j.done,0))+' đã tải về';
 const search=$('#search').value.toLocaleLowerCase('vi');const visible=jobs.filter(j=>(filter==='all'||(filter==='active'?active(j):j.status===filter))&&j.name.toLocaleLowerCase('vi').includes(search)).reverse();
 const selectable=visible.filter(canClearHistory),selectAll=$('#history-select-all');
 selectAll.disabled=!selectable.length;selectAll.checked=selectable.length>0&&selectable.every(j=>selectedHistory.has(j.id));selectAll.indeterminate=selectable.some(j=>selectedHistory.has(j.id))&&!selectAll.checked;
 selectAll.onchange=()=>{for(const j of selectable){if(selectAll.checked)selectedHistory.add(j.id);else selectedHistory.delete(j.id);}render();};
 $('#empty').hidden=visible.length>0;$('#empty h2').textContent=jobs.length?'Chưa có tệp phù hợp':'Sẵn sàng cho lượt tải đầu tiên';$('#empty p').textContent=jobs.length?'Thử bộ lọc khác hoặc thêm liên kết mới.':'Dán liên kết tệp để bắt đầu. Chúng tôi sẽ lo phần còn lại.';
 $('#list-summary').textContent=`${visible.length} / ${jobs.length} tệp trong không gian của bạn`;
 const rows=visible.map(j=>{
  const tr=document.createElement('tr'),td=document.createElement('td'),cell=text('div','','file-cell'),ext=j.name.includes('.')?j.name.split('.').pop().slice(0,4).toUpperCase():'FILE';
  const selectCell=text('td','','history-select-cell'),checkbox=document.createElement('input');checkbox.type='checkbox';checkbox.disabled=!canClearHistory(j);checkbox.checked=selectedHistory.has(j.id);checkbox.setAttribute('aria-label','Chọn lịch sử '+j.name);checkbox.onchange=()=>{if(checkbox.checked)selectedHistory.add(j.id);else selectedHistory.delete(j.id);render();};selectCell.append(checkbox);tr.append(selectCell);
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
  const actions=document.createElement('td');actions.className='download-actions';if(!['completed','cancelled'].includes(j.status)){
   const group=text('div','','file-actions'),stopping=['pausing','cancelling'].includes(j.status),pause=active(j)||j.status==='queued';
   group.append(actionButton(j,pause?'Dừng':'Tiếp tục',pause?'pause':'play',pause?'pause':'resume',stopping),actionButton(j,'Hủy','close','cancel',j.status==='cancelling'));
   actions.append(group);
  }else if(j.status==='completed') {
   const group=text('div','','file-actions'),folder=text('button','','row-action');folder.append(icon('folder'),document.createTextNode('Thư mục'));folder.title='Mở thư mục chứa '+j.name;folder.setAttribute('aria-label',folder.title);folder.onclick=async()=>{folder.disabled=true;try{await api('open-folder',{id:j.id});}catch(e){notice(e.message);}finally{folder.disabled=false;}};
   const open=text('button','Mở tệp','row-action labeled-action');open.prepend(icon('play'));open.title='Mở tệp '+j.name;open.setAttribute('aria-label',open.title);open.onclick=async()=>{open.disabled=true;try{await api('open-file',{id:j.id});}catch(e){notice(e.message);}finally{open.disabled=false;}};group.append(open);
   const location=text('button','','row-action');location.append(icon('copy'));location.title='Xem và sao chép đường dẫn tệp';location.setAttribute('aria-label',location.title+' '+j.name);location.onclick=()=>{$('#file-location-path').value=j.file_path||'';$('#file-location-name').textContent=j.name;$('#file-location-dialog').showModal();};group.append(folder,location);actions.append(group);
  }
  if(['completed','cancelled'].includes(j.status)){
   const again=text('button','Tải lại','row-action labeled-action');again.prepend(icon('retry'));again.setAttribute('aria-label','Tải lại '+j.name);again.onclick=async()=>{again.disabled=true;try{await api('redownload',{id:j.id});await refresh();notice('Đã tạo lượt tải mới trong thư mục cũ. Tệp đã tải được giữ nguyên.');}catch(e){notice(e.message);again.disabled=false;}};
   const remove=text('button','','row-action delete-action');remove.append(icon('trash'));remove.title='Xóa lịch sử '+j.name;remove.setAttribute('aria-label',remove.title);remove.onclick=()=>openHistory(j.id);const group=text('div','','file-actions history-row-actions');group.append(again,remove);actions.append(group);
  }
  tr.append(actions);return tr;
 });$('#job-list').replaceChildren(...rows);
}
const speedSamples=[];
function sampleSpeed(){
 const now=Date.now(),speed=jobs.reduce((sum,j)=>sum+(Number.isFinite(j.speed)?Math.max(0,j.speed):0),0);
 speedSamples.push({at:now,value:speed});while(speedSamples.length&&speedSamples[0].at<now-60000)speedSamples.shift();
 const actualPeak=Math.max(0,...speedSamples.map(s=>s.value)),peak=Math.max(1,actualPeak);
 const points=speedSamples.map(s=>[Math.max(0,320*(1-(now-s.at)/60000)),72-60*s.value/peak]);
 const line=points.map((p,i)=>(i?'L':'M')+p.map(x=>x.toFixed(2)).join(' ')).join(' ');
 $('#speed-line').setAttribute('d',line||'M0 72H320');
 $('#speed-area').setAttribute('d',points.length?'M'+points[0][0].toFixed(2)+' 72 '+line.replace(/^M/,'L')+' L320 72Z':'M0 72H320Z');
 $('#speed-peak').textContent='Đỉnh '+bytes(actualPeak)+'/s';
 $('#speed-live').textContent=jobs.some(j=>j.status==='downloading')?'● Trực tiếp':'Đang chờ tải';
 $('#speed-live').classList.toggle('is-live',jobs.some(j=>j.status==='downloading'));
 $('#speed-chart').setAttribute('aria-label','Tốc độ hiện tại '+bytes(speed)+'/s, đỉnh '+bytes(actualPeak)+'/s trong 60 giây gần nhất');
}
async function refresh(){try{jobs=await api('jobs');$('#connection-state').textContent='Đã kết nối · cổng '+location.port;sampleSpeed();render();}catch(e){$('#connection-state').textContent='Mất kết nối · đang thử lại';$('#speed-live').textContent='Mất kết nối';}}
function openAdd(schedule=false){$('#form-error').textContent='';if(schedule){const d=new Date(Date.now()+3600000);d.setMinutes(d.getMinutes()-d.getTimezoneOffset());$('#add-form').elements.start_at.value=d.toISOString().slice(0,16);}$('#add-dialog').showModal();}
$('#add-open').onclick=()=>openAdd();$('#empty-add').onclick=()=>openAdd();$('#schedule-nav').onclick=()=>openAdd(true);$('#schedule-card').onclick=()=>openAdd(true);
$('#history-clear').onclick=()=>openHistory();
$('#history-scope-selected').onchange=updateHistorySummary;
$('#history-scope-all').onchange=updateHistorySummary;
$('#history-delete-files').onchange=updateHistorySummary;
$('#history-confirm').onclick=async()=>{const button=$('#history-confirm'),deleteFiles=$('#history-delete-files').checked;button.disabled=true;try{const result=await api('history/clear',{ids:historyIds,delete_files:deleteFiles});$('#history-dialog').close();await refresh();notice('Đã xóa '+result.removed+' mục.'+(deleteFiles?' Đã xóa tệp tương ứng trên máy.':' Tệp trên máy được giữ lại.'));}catch(e){$('#history-dialog').close();await refresh();notice(e.message);}finally{button.disabled=false;}};
document.querySelectorAll('.close-dialog').forEach(e=>e.onclick=()=>e.closest('dialog').close());document.querySelectorAll('[data-filter]').forEach(e=>e.onclick=()=>choose(e.dataset.filter));document.querySelectorAll('[data-tab]').forEach(e=>e.onclick=()=>choose(e.dataset.tab));$('#search').oninput=render;
$('#add-form').onsubmit=async e=>{e.preventDefault();const form=e.currentTarget,b=form.querySelector('[type="submit"]');b.disabled=true;$('#form-error').textContent='';try{const data=Object.fromEntries(new FormData(form));data.ask_save=true;data.connections=Number(data.connections);for(const field of ['start_at','stop_at'])data[field]=data[field]?new Date(data[field]).toISOString():null;const result=await waitSavePrompt(await api('jobs',data));if(result.state==='cancelled'){notice('Đã hủy chọn nơi lưu. Chưa tạo lượt tải.');return;}form.reset();$('#add-dialog').close();choose('all');await refresh();notice('Đã thêm tệp vào hàng đợi.');}catch(ex){$('#form-error').textContent=ex.message;}finally{b.disabled=false;}};
$('#extension-nav').onclick=()=>{$('#pair-token').value=token;$('#extension-dialog').showModal();};$('#copy-token').onclick=async()=>{try{await navigator.clipboard.writeText(token);notice('Đã sao chép mã kết nối.');}catch(e){$('#pair-token').select();notice('Nhấn Ctrl+C để sao chép mã.');}};
$('#version-open').onclick=()=>$('#version-dialog').showModal();
$('#copy-file-path').onclick=async()=>{try{await navigator.clipboard.writeText($('#file-location-path').value);notice('Đã sao chép đường dẫn tệp.');}catch(e){$('#file-location-path').focus();$('#file-location-path').select();notice('Nhấn Ctrl+C để sao chép đường dẫn.');}};
api('storage').then(data=>{$('#storage-path').textContent='Lưu tại '+data.directory;$('#storage-path').title=data.directory;}).catch(()=>{});
let updateState={},updateOpening=false,serverVersion=null;
function renderUpdateProgress(s){
 const panel=$('#update-progress-panel'),bar=$('#update-progress');
 panel.hidden=false;
 const known=Number.isFinite(s.total_bytes)&&s.total_bytes>0;
 const amount=Math.max(0,Number(s.bytes)||0);
 const percentage=known?Math.min(100,amount/s.total_bytes*100):null;
 const waiting=['idle','unconfigured','available','up_to_date'].includes(s.state);
 if(waiting){bar.value=0;$('#update-percent').textContent='0%';}
 else if(s.state==='downloading'&&percentage!==null){bar.value=percentage;$('#update-percent').textContent=Math.floor(percentage)+'%';}
 else if(['verifying','ready'].includes(s.state)){bar.value=100;$('#update-percent').textContent='100% · Đã tải xong';}
 else if(s.state==='error'){bar.value=percentage||0;$('#update-percent').textContent='Tải bị gián đoạn';}
 else{bar.removeAttribute('value');$('#update-percent').textContent=s.state==='installing'?'Đang cài…':s.state==='checking'?'Đang kiểm tra…':'Đang tải…';}
 const phase=s.state==='downloading'?'download':s.state==='installing'?'install':'verify';
 $('#update-phase').textContent=waiting?'Chưa bắt đầu tải':s.state==='checking'?'Đang tìm phiên bản mới':s.state==='downloading'?'Tải ứng dụng và tiện ích':s.state==='installing'?'Chờ ứng dụng mở lại':s.state==='ready'?'Gói đã xác minh, chờ cài đặt':s.state==='error'?'Chưa hoàn tất':`Đang xác minh${s.total_files?' · '+(s.verified_files||0)+'/'+s.total_files+' tệp':''}`;
 $('#update-transfer').textContent=waiting?'Thanh tiến độ sẽ chạy sau khi bạn đồng ý tải bản cập nhật.':amount?bytes(amount)+(known?' / '+bytes(s.total_bytes):' · Máy chủ chưa cung cấp tổng dung lượng')+(s.state==='downloading'&&s.speed>0?' · '+bytes(s.speed)+'/s':'')+(s.state==='downloading'&&Number.isFinite(s.eta)&&s.eta>0?' · Còn khoảng '+Math.ceil(s.eta)+' giây':''):s.state==='downloading'?'Đang kết nối với máy chủ cập nhật…':'';
 document.querySelectorAll('[data-update-step]').forEach(element=>{
  const stages=['download','verify','install'],index=stages.indexOf(element.dataset.updateStep),current=stages.indexOf(phase);
  element.classList.toggle('step-current',!waiting&&s.state!=='checking'&&index===current);element.classList.toggle('step-done',!waiting&&s.state!=='checking'&&(index<current||s.state==='ready'&&index<2));
 });
}
const updateLabels={idle:'Sẵn sàng kiểm tra cập nhật.',unconfigured:'Chưa cấu hình nguồn cập nhật trong tùy chọn nâng cao.',checking:'Đang kiểm tra phiên bản…',available:'Có phiên bản mới. Bạn có muốn cập nhật không?',up_to_date:'Bạn đang dùng phiên bản mới nhất.',downloading:'Đang tải gói cập nhật…',verifying:'Đang xác minh gói cập nhật…',importing:'Đang chuẩn bị gói…',ready:'Đã xác minh gói cập nhật.',installing:'Đang cài cập nhật. Ứng dụng sẽ tự mở lại.',error:'Không thể cập nhật.'};
async function readSettings(){const s=await api('settings');$('#update-feed').value=s.update_feed;$('#auto-check-updates').checked=s.auto_check_updates;$('#remember-save-folder').checked=s.remember_save_dir;$('#remembered-folder').value=s.last_save_dir;}
async function saveSettings(){await api('settings',{update_feed:$('#update-feed').value.trim(),auto_check_updates:$('#auto-check-updates').checked,auto_install_updates:false,remember_save_dir:$('#remember-save-folder').checked});}
function renderExtensionSync(sync){
 const label=$('#update-sync');
 if(!sync||!sync.clients.length){label.textContent='Gói cập nhật chứa cả ứng dụng và tiện ích cùng phiên bản. Chưa nhận xác nhận từ trình duyệt; mở ứng dụng trong trình duyệt có tiện ích để kiểm tra.';return;}
 const versions=sync.clients.map(c=>c.browser+' v'+c.version).join(', ');
 label.textContent=sync.state==='synced'?'✓ Đã đồng bộ: ứng dụng v'+sync.version+' · '+versions:sync.clients.some(c=>!c.managed)?'Ứng dụng v'+sync.version+' · '+versions+'. Tiện ích đang dùng thư mục riêng hoặc bản cửa hàng; xem Tiện ích trình duyệt để thiết lập cập nhật cùng ứng dụng.':'Đang chờ tiện ích tự nạp lại: '+versions+' → v'+sync.version+'.';
}
async function readUpdateStatus(){
 try{const s=updateState=await api('update/status');renderExtensionSync(s.extension_sync);renderUpdateProgress(s);if(serverVersion&&serverVersion!==s.current_version){location.reload();return;}serverVersion=s.current_version;$('#update-current').textContent='Đang dùng v'+s.current_version;$('#update-state').textContent=(updateLabels[s.state]||s.state)+(s.version?' · v'+s.version:'')+(s.error?' '+s.error:'');$('#update-notes').textContent=s.notes||'';$('#update-label').textContent=['available','ready'].includes(s.state)?'Cập nhật ●':'Cập nhật';$('#update-confirm').hidden=!['available','ready'].includes(s.state)||s.install_requested;$('#update-question').textContent=s.install_requested?'Đã đồng ý cập nhật cả hai. Ứng dụng sẽ tự cài khi hàng đợi đã dừng, thay tiện ích cùng phiên bản và chờ tiện ích tự nạp lại.':'Một lần đồng ý để tải và cài cả ứng dụng lẫn tiện ích. Ứng dụng mở lại, tiện ích tự nạp lại; dữ liệu và kết nối được giữ nguyên.';
 }catch(e){if($('#update-dialog').open)$('#update-state').textContent='Đang chờ ứng dụng kết nối lại…';}
}
$('#update-open').onclick=async()=>{if(updateOpening)return;updateOpening=true;$('#update-dialog').showModal();$('#update-confirm').hidden=true;try{await readSettings();await readUpdateStatus();if(!['checking','downloading','verifying','importing','installing'].includes(updateState.state)&&!updateState.install_requested){await api('update/check',{});await readUpdateStatus();}}catch(e){notice(e.message);}finally{updateOpening=false;}};
$('#settings-form').onsubmit=async e=>{e.preventDefault();try{await saveSettings();notice('Đã lưu tùy chọn.');}catch(error){notice(error.message);}};
$('#update-confirm').onclick=async()=>{const button=$('#update-confirm');button.disabled=true;try{await api('update/accept',{version:updateState.version});await readUpdateStatus();}catch(e){notice(e.message);}finally{button.disabled=false;}};
$('#extension-folder').onclick=async()=>{try{const result=await api('extension/open-folder',{});$('#extension-folder-status').textContent='Nạp thư mục này một lần trong trình duyệt: '+result.path;}catch(e){notice(e.message);}};
// A fixed tick notices an opened dialog immediately, even if the previous
// background poll scheduled a ten-second delay. Never overlap status requests.
let updatePollBusy=false,updatePolledAt=0;
async function pollUpdates(){
 if(updatePollBusy||!$('#update-dialog').open&&Date.now()-updatePolledAt<10000)return;
 updatePollBusy=true;
 try{await readUpdateStatus();}finally{updatePolledAt=Date.now();updatePollBusy=false;}
}
setInterval(pollUpdates,750);pollUpdates();
async function poll(){await refresh();setTimeout(poll,1200);}poll();

if(new URLSearchParams(location.search).has("update"))$("#update-open").click();
if(new URLSearchParams(location.search).has("extensions"))$("#extension-nav").click();
