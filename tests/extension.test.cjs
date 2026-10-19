const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');
const path=require('node:path');
const background=fs.readFileSync(path.join(__dirname,'../extension/chromium/background.js'),'utf8');
const content=fs.readFileSync(path.join(__dirname,'../extension/chromium/content.js'),'utf8');
const event=()=>({listeners:[],addListener(fn){this.listeners.push(fn);}});
function harness({online=true,capture=true,token='test-token',state='in_progress',promptOutcome=null}={}){
 const calls=[],settings={capture,token,intercept:true};
 const bridge={storage:{local:{async get(){return settings;},async set(data){Object.assign(settings,data);}},onChanged:event()},
  runtime:{onInstalled:event(),onStartup:event(),onMessage:event()},
  scripting:{async getRegisteredContentScripts(){return [];},async registerContentScripts(){},async unregisterContentScripts(){}},
  permissions:{async contains(){return true;}},contextMenus:{onClicked:event(),async removeAll(){},create(){}},
  action:{async setBadgeText(){},async setBadgeBackgroundColor(){}},
  downloads:{onCreated:event(),async pause(){calls.push('pause');},async search(){return [{url:'https://files.example/file.zip',filename:'C:\\Downloads\\file.zip',state}];},async cancel(){calls.push('cancel');},async resume(){calls.push('resume');}}};
 const context=vm.createContext({chrome:bridge,crypto:require('node:crypto').webcrypto,AbortSignal,console,Map,Date,setTimeout:fn=>fn(),
  fetch:async(url,options)=>{if(url.includes('/api/prompts/')){calls.push('poll');return {ok:true,json:async()=>({state:promptOutcome,id:'job-1'})};}calls.push('send');if(!online)throw Error('offline');assert.ok(url.endsWith('/api/capture'));assert.ok(JSON.parse(options.body).request_id);assert.equal(JSON.parse(options.body).ask_save,true);return {ok:true,json:async()=>promptOutcome?({prompt_id:'prompt-1'}):({id:'job-1'})};}});
 vm.runInContext(background,context);
 return {context,bridge,calls,settings};
}
test('browser download pauses, sends, then cancels only after acceptance',async()=>{
 const h=harness();await h.context.captureDownload({id:1,url:'https://files.example/file.zip',state:'in_progress'});
 assert.deepEqual(h.calls,['pause','send','cancel']);
});
test('offline bridge resumes original browser download',async()=>{
 const h=harness({online:false});await h.context.captureDownload({id:1,url:'https://files.example/file.zip',state:'in_progress'});
 assert.deepEqual(h.calls,['pause','send','resume']);
});
test('disabled or unpaired capture leaves browser alone',async()=>{
 for(const options of [{capture:false},{token:''}]){const h=harness(options);await h.context.captureDownload({id:1,url:'https://files.example/file.zip'});assert.deepEqual(h.calls,[]);}
});
test('already completed downloads are not sent again',async()=>{
 const h=harness({state:'complete'});await h.context.captureDownload({id:1,url:'https://files.example/file.zip',state:'complete'});assert.deepEqual(h.calls,[]);
});
test('concurrent notifications for same URL share one handoff',async()=>{
 const h=harness();await Promise.all([h.context.automaticSend('https://files.example/file.zip','','request-1'),h.context.automaticSend('https://files.example/file.zip','','request-2')]);assert.deepEqual(h.calls,['send']);
});
test('browser waits for Save As selection before cancelling its download',async()=>{
 const h=harness({promptOutcome:'accepted'});await h.context.captureDownload({id:1,url:'https://files.example/file.zip',state:'in_progress'});assert.deepEqual(h.calls,['pause','send','poll','cancel']);
});
test('cancelling Save As cancels browser download without enqueueing or resuming',async()=>{
 const h=harness({promptOutcome:'cancelled'});await h.context.captureDownload({id:1,url:'https://files.example/file.zip',state:'in_progress'});assert.deepEqual(h.calls,['pause','send','poll','cancel']);
});
function pageHarness({ok=true,cancelled=false}={}){
 let listener,messages=[],fallbackClicks=0;
 const make=()=>({style:{},setAttribute(){},append(){},remove(){},attachShadow(){return {append(){}};},click(){fallbackClicks++;}});
 const bridge={storage:{local:{async get(){return {capture:true,intercept:true,token:'secret'};}},onChanged:event()},runtime:{async sendMessage(m){messages.push(m);return ok?{ok:true,cancelled}:{error:'offline'};}}};
 const document={createElement:make,body:{append(){}},addEventListener(name,fn){listener=fn;}};
 vm.runInNewContext(content,{chrome:bridge,document,URL,crypto:require('node:crypto').webcrypto,setTimeout(){}});
 const click=async(url,options={})=>{
  await Promise.resolve();
  const a={tagName:'A',href:url,target:'',rel:'',hasAttribute(){return false;},getAttribute(){return '';}};
  const e={isTrusted:true,defaultPrevented:false,button:0,composedPath:()=>[a],preventDefault(){this.defaultPrevented=true;},stopImmediatePropagation(){},...options};
  await listener(e);return e;
 };
 return {click,messages,fallbackClicks:()=>fallbackClicks};
}
test('direct file click is intercepted without exposing pairing token',async()=>{
 const h=pageHarness();const e=await h.click('https://files.example/report.zip');assert.equal(e.defaultPrevented,true);assert.equal(h.messages.length,1);assert.equal(h.messages[0].type,'capture-link');assert.equal(h.messages[0].token,undefined);
});
test('normal navigation and modified clicks are not intercepted',async()=>{
 const h=pageHarness();await h.click('https://files.example/article');await h.click('https://files.example/file.zip',{ctrlKey:true});assert.equal(h.messages.length,0);
});
test('failed direct link handoff restores the original browser action',async()=>{
 const h=pageHarness({ok:false});await h.click('https://files.example/file.zip');assert.equal(h.fallbackClicks(),1);
});
test('cancelling Save As does not trigger fallback link navigation',async()=>{
 const h=pageHarness({cancelled:true});await h.click('https://files.example/file.zip');assert.equal(h.fallbackClicks(),0);
});
