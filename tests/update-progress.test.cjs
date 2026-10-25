const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');
function render(state){
 const nodes=new Map();
 const $=id=>{if(!nodes.has(id))nodes.set(id,{hidden:true,value:0,textContent:'',removeAttribute(key){delete this[key];}});return nodes.get(id);};
 const source=fs.readFileSync('web/app.js','utf8');
 const start=source.indexOf('function renderUpdateProgress(');
 const end=source.indexOf('const updateLabels=',start);
 const context={$,bytes:n=>n+' B',document:{querySelectorAll:()=>[]}};
 vm.createContext(context);vm.runInContext(source.slice(start,end),context);
 context.renderUpdateProgress(state);
 return $;
}
test('update progress stays hidden before download approval',()=>{
 for(const state of ['idle','unconfigured','checking','available','up_to_date']){
  const $=render({state});assert.equal($('#update-progress-panel').hidden,true);
 }
});
test('download percentage is calculated from actual bytes',()=>{
 const $=render({state:'downloading',bytes:56,total_bytes:100,speed:8,eta:5.5});
 assert.equal($('#update-progress-panel').hidden,false);
 assert.ok(Math.abs($('#update-progress').value-56)<1e-9);assert.equal($('#update-percent').textContent,'56%');
 assert.match($('#update-transfer').textContent,/56 B \/ 100 B.*8 B\/s.*6 giây/);
});
test('unknown length animates without a fabricated percentage',()=>{
 const $=render({state:'downloading',bytes:56,total_bytes:null});
 assert.equal($('#update-progress').value,undefined);assert.match($('#update-transfer').textContent,/chưa cung cấp/);
});
test('verification and ready show 100 percent',()=>{
 for(const state of ['verifying','ready']){
  const $=render({state,bytes:100,total_bytes:100});
  assert.equal($('#update-progress').value,100);assert.match($('#update-percent').textContent,/100%/);
 }
});
function apiHarness(fetch){
 const source=fs.readFileSync('web/app.js','utf8');
 const start=source.indexOf('async function api('),end=source.indexOf('async function waitSavePrompt(',start);
 const context={fetch,token:'test-token',AbortSignal, setTimeout:fn=>{fn();}};
 vm.createContext(context);vm.runInContext(source.slice(start,end),context);return context.api;
}
test('pause recovers a lost response without changing the command',async()=>{
 const calls=[];
 const api=apiHarness(async(path,options)=>{calls.push(JSON.parse(options.body));if(calls.length===1)throw TypeError('Failed to fetch');return {ok:true,json:async()=>({ok:true})};});
 await api('action',{id:'job',action:'pause'});
 assert.deepEqual(calls,[{id:'job',action:'pause'},{id:'job',action:'pause'}]);
});
test('failed add and resume are never resent',async()=>{
 for(const [path,data] of [['jobs',{url:'https://example.com/file'}],['action',{id:'job',action:'resume'}]]){
  let calls=0;const api=apiHarness(async()=>{calls++;throw TypeError('Failed to fetch');});
  await assert.rejects(api(path,data),/Chưa xác nhận/);assert.equal(calls,1);
 }
});
test('application errors are not retried',async()=>{
 let calls=0;const api=apiHarness(async()=>{calls++;return {ok:false,json:async()=>({error:'Lượt tải đã hủy'})};});
 await assert.rejects(api('action',{id:'job',action:'pause'}),/Lượt tải đã hủy/);assert.equal(calls,1);
});
test('status reconnects but repeated failures are bounded',async()=>{
 let calls=0;const api=apiHarness(async()=>{calls++;throw TypeError('Failed to fetch');});
 await assert.rejects(api('jobs'),/Tạm mất kết nối/);assert.equal(calls,3);
});
