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
test('update progress is visible before approval at zero',()=>{
 for(const state of ['idle','available','up_to_date']){
  const $=render({state});assert.equal($('#update-progress-panel').hidden,false);
  assert.equal($('#update-progress').value,0);assert.equal($('#update-percent').textContent,'0%');
 }
});
test('download percentage is calculated from actual bytes',()=>{
 const $=render({state:'downloading',bytes:56,total_bytes:100,speed:8,eta:5.5});
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
