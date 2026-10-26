const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
function harness(){
 const nodes=new Map();const $=id=>{if(!nodes.has(id))nodes.set(id,{textContent:'',title:'',classList:{toggle(){}},setAttribute(k,v){this[k]=v;}});return nodes.get(id);};
 const source=fs.readFileSync('web/app.js','utf8');
 const context={$,document:{querySelectorAll:()=>[]},jobs:[{id:'a',name:'First.img',speed:10,status:'downloading'},{id:'b',name:'Second.zip',speed:20,status:'downloading'}],selectedSpeedId:null,filter:'all',bytes:n=>String(n),Date,Object};
 vm.createContext(context);
 vm.runInContext(source.slice(source.indexOf('const speedSamples=[];'),source.indexOf('async function refresh()')),context);
 vm.runInContext(source.slice(source.indexOf('function choose(value)'),source.indexOf('const pendingActions=')),context);
 context.render=()=>context.renderSpeed();return {context,$};
}
test('unselected chart shows aggregate speed',()=>{
 const {context:c,$}=harness();c.sampleSpeed();c.renderSpeed();assert.equal($('#stat-speed').textContent,'30/s');assert.match($('#speed-description').textContent,/Tổng tốc độ/);
});
test('selecting a file shows only its speed and peak',()=>{
 const {context:c,$}=harness();c.sampleSpeed();c.selectSpeedFile('a');assert.equal($('#stat-speed').textContent,'10/s');assert.equal($('#speed-peak').textContent,'Đỉnh 10/s');assert.equal($('#speed-description').textContent,'Tệp: First.img');
});
test('selection survives new polling samples',()=>{
 const {context:c,$}=harness();c.sampleSpeed();c.selectSpeedFile('b');c.jobs[1].speed=25;c.sampleSpeed();c.renderSpeed();assert.equal(c.selectedSpeedId,'b');assert.equal($('#stat-speed').textContent,'25/s');
});
test('switching a stat filter clears file selection and restores total',()=>{
 for(const filter of ['active','queued','completed']){
  const {context:c,$}=harness();c.sampleSpeed();c.selectSpeedFile('a');c.choose(filter);assert.equal(c.filter,filter);assert.equal(c.selectedSpeedId,null);assert.equal($('#stat-speed').textContent,'30/s');
 }
});
test('deleted selection falls back to aggregate without stale data',()=>{
 const {context:c,$}=harness();c.sampleSpeed();c.selectSpeedFile('a');c.jobs=c.jobs.filter(j=>j.id!=='a');c.sampleSpeed();c.renderSpeed();assert.equal(c.selectedSpeedId,null);assert.equal($('#stat-speed').textContent,'20/s');
});
