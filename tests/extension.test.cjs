const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');
const path=require('node:path');
const background=fs.readFileSync(path.join(__dirname,'../extension/chromium/background.js'),'utf8');
const content=fs.readFileSync(path.join(__dirname,'../extension/chromium/content.js'),'utf8');
const event=()=>({listeners:[],addListener(fn){this.listeners.push(fn);}});
function harness({online=true,capture=true,token='test-token',state='in_progress',promptOutcome=null,exclusive=false,filenameGate=false}={}){
 const calls=[],settings={capture,token,intercept:true,downloadNowOnly:exclusive};
 const bridge={storage:{local:{async get(){return settings;},async set(data){Object.assign(settings,data);}},onChanged:event()},
  runtime:{onInstalled:event(),onStartup:event(),onMessage:event()},
  scripting:{async getRegisteredContentScripts(){return [];},async registerContentScripts(){},async unregisterContentScripts(){}},
  permissions:{async contains(){return true;}},contextMenus:{onClicked:event(),async removeAll(){},create(){}},
  action:{async setBadgeText(){},async setBadgeBackgroundColor(){}},
  downloads:{onCreated:event(),async pause(){calls.push('pause');},async search(){return [{url:'https://files.example/file.zip',filename:'C:\\Downloads\\file.zip',state}];},async cancel(){calls.push('cancel');},async resume(){calls.push('resume');}}};
 if(filenameGate)bridge.downloads.onDeterminingFilename=event();
 const context=vm.createContext({chrome:bridge,URL,crypto:require('node:crypto').webcrypto,AbortSignal,console,Map,Date,setTimeout:fn=>fn(),
  fetch:async(url,options)=>{if(url.endsWith('/api/info')){calls.push('verify-pair');if(!online)throw Error('offline');return {ok:true,json:async()=>({version:'1.9.0'})};}if(url.includes('/api/prompts/')){calls.push('poll');return {ok:true,json:async()=>({state:promptOutcome,id:'job-1'})};}calls.push('send');if(!online)throw Error('offline');assert.ok(url.endsWith('/api/capture'));assert.ok(JSON.parse(options.body).request_id);assert.equal(JSON.parse(options.body).ask_save,true);return {ok:true,json:async()=>promptOutcome?({prompt_id:'prompt-1'}):({id:'job-1'})};}});
 vm.runInContext(background,context);
 return {context,bridge,calls,settings};
}

function pair(h,url='http://127.0.0.1:8765/',frameId=0){return new Promise(resolve=>h.bridge.runtime.onMessage.listeners[0]({type:'pair-app',token:'new-valid-connection-token-12345'},{tab:{id:1},url,frameId},resolve));}
test('local application pairs automatically only after verifying token',async()=>{
 const h=harness();const result=await pair(h);assert.equal(result.ok,true);assert.equal(h.settings.token,'new-valid-connection-token-12345');assert.deepEqual(h.calls,['verify-pair']);
});
test('external pages and child frames cannot replace connection token',async()=>{
 for(const [url,frame] of [['https://evil.example',0],['http://127.0.0.1:8765.evil.example',0],['http://127.0.0.1:8765/',1]]){const h=harness();assert.ok((await pair(h,url,frame)).error);assert.equal(h.settings.token,'test-token');assert.deepEqual(h.calls,[]);}
});
test('failed verification preserves previous connection',async()=>{
 const h=harness({online:false});assert.ok((await pair(h)).error);assert.equal(h.settings.token,'test-token');
});
test('invalid token is not stored during automatic pairing',async()=>{
 const h=harness();h.context.fetch=async()=>({ok:false});assert.ok((await pair(h)).error);assert.equal(h.settings.token,'test-token');
});
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
function pageHarness({ok=true,cancelled=false,exclusive=false}={}){
 let listener,messages=[],fallbackClicks=0;
 const make=()=>({style:{},setAttribute(){},append(){},remove(){},attachShadow(){return {append(){}};},click(){fallbackClicks++;}});
 const bridge={storage:{local:{async get(){return {capture:true,intercept:true,token:'secret',downloadNowOnly:exclusive};}},onChanged:event()},runtime:{async sendMessage(m){messages.push(m);return ok?{ok:true,cancelled}:{error:'offline'};}}};
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
const updateSource=fs.readFileSync(path.join(__dirname,'../extension/chromium/updates.js'),'utf8');
function releaseFixture(browser='Chrome',version='2.0.0'){
 const name=`DownloadNow-${browser}-${version}${browser==='Firefox'?'-unsigned':''}.zip`;
 return {tag_name:'v'+version,draft:false,prerelease:false,assets:[{name,browser_download_url:'https://github.com/XOmongoose/DownloadNow/releases/download/v'+version+'/'+name}]};
}
function updateHarness({agent='',firefox=false}={}){
 const settings={};let requests=0;
 const context=vm.createContext({chrome:{runtime:{getManifest:()=>({version:'1.9.1'}),...(firefox?{getBrowserInfo:async()=>({name:'Firefox'})}:{})},storage:{local:{async get(){return settings;},async set(value){Object.assign(settings,value);}}}},navigator:{userAgent:agent},AbortSignal,Date,fetch:async()=>{requests++;return {ok:true,json:async()=>releaseFixture(firefox?'Firefox':agent.includes('Edg/')?'Edge':agent.includes('OPR/')?'Opera':'Chrome')};}});
 vm.runInContext(updateSource,context);return {client:context.DownloadNowUpdates,settings,requests:()=>requests};
}
test('extension updates choose the exact package for every supported browser',()=>{
 const h=updateHarness();for(const browser of ['Chrome','Edge','Opera','Firefox']){const info=h.client.select(releaseFixture(browser),browser,'1.9.1');assert.equal(info.newer,true);assert.match(info.filename,new RegExp(browser));}
});
test('extension updates fall back to full browser bundle for older releases',()=>{
 const h=updateHarness(),r=releaseFixture();r.assets[0].name='DownloadNow-Browser-Extensions-2.0.0.zip';r.assets[0].browser_download_url='https://github.com/XOmongoose/DownloadNow/releases/download/v2.0.0/'+r.assets[0].name;
 assert.match(h.client.select(r,'Chrome','1.9.1').filename,/Browser-Extensions/);
});
test('extension updater rejects a package redirected outside the official repository',()=>{
 const h=updateHarness(),r=releaseFixture();r.assets[0].browser_download_url='https://evil.example/update.zip';assert.throws(()=>h.client.select(r,'Chrome','1.9.1'));
});
test('extension updater ignores prereleases and invalid versions',()=>{
 const h=updateHarness();for(const change of [{draft:true},{prerelease:true},{tag_name:'v2.0.0-beta'}])assert.throws(()=>h.client.select({...releaseFixture(),...change},'Chrome','1.9.1'));
});
test('extension update comparison uses numeric version components',()=>{
 const h=updateHarness();assert.equal(h.client.newer('1.10.0','1.9.9'),true);assert.equal(h.client.newer('1.9.1','1.9.1'),false);assert.equal(h.client.newer('1.8.0','1.9.1'),false);
});
test('extension update checks cache metadata and allow explicit refresh',async()=>{
 const h=updateHarness();await h.client.check();await h.client.check();assert.equal(h.requests(),1);await h.client.check(true);assert.equal(h.requests(),2);
});
test('extension update checks detect Firefox Edge and Opera',async()=>{
 for(const [options,browser] of [[{firefox:true},'Firefox'],[{agent:'Edg/130'},'Edge'],[{agent:'OPR/110'},'Opera'],[{},'Chrome']])assert.equal((await updateHarness(options).client.check()).browser,browser);
});
test('extension update ZIP bypasses capture and concurrent download requests share one download',async()=>{
 const h=harness();let downloaded=0;
 const url='https://github.com/XOmongoose/DownloadNow/releases/download/v2.0.0/DownloadNow-Chrome-2.0.0.zip';
 h.context.DownloadNowUpdates={check:async()=>({newer:true,url,filename:'DownloadNow-Chrome-2.0.0.zip',version:'2.0.0'})};
 h.bridge.downloads.download=async options=>{downloaded++;assert.equal(options.url,url);assert.equal(options.saveAs,false);return 42;};
 await Promise.all([h.context.downloadExtensionUpdate(),h.context.downloadExtensionUpdate()]);assert.equal(downloaded,1);
 await h.context.captureDownload({id:42,url,state:'in_progress'});assert.deepEqual(h.calls,[]);
});
test('downloads created by this extension are not intercepted',async()=>{
 const h=harness();h.bridge.runtime.id='our-extension';await h.context.captureDownload({id:42,url:'https://example.com/file.zip',byExtensionId:'our-extension',state:'in_progress'});assert.deepEqual(h.calls,[]);
});
function filenameItem(options={}){return {id:7,url:'https://files.example/file.zip',filename:'file.zip',state:'in_progress',...options};}
async function filenameGate(h,item=filenameItem()){
 let count=0;
 const completed=new Promise(resolve=>{const returned=h.bridge.downloads.onDeterminingFilename.listeners[0](item,()=>{count++;h.calls.push('suggest');resolve();});assert.equal(returned,true);});
 await completed;return count;
}
test('filename gate cancels browser before releasing Save As and does not register duplicate onCreated handler',async()=>{
 const h=harness({filenameGate:true,exclusive:true});let accept;
 h.context.automaticSend=()=>{h.calls.push('send');return new Promise(resolve=>{accept=resolve;});};
 const completed=filenameGate(h);
 await new Promise(setImmediate);
 assert.deepEqual(h.calls,['pause','send']);assert.equal(h.bridge.downloads.onCreated.listeners.length,0);
 accept({id:'job'});assert.equal(await completed,1);assert.deepEqual(h.calls,['pause','send','cancel','suggest']);
});
test('strict filename gate cancels instead of opening browser Save As when application is offline',async()=>{
 const h=harness({filenameGate:true,exclusive:true,online:false});assert.equal(await filenameGate(h),1);assert.deepEqual(h.calls,['pause','send','cancel','suggest']);
});
test('filename gate permits browser fallback only when explicitly enabled',async()=>{
 const h=harness({filenameGate:true,exclusive:false,online:false});await filenameGate(h);assert.deepEqual(h.calls,['pause','send','resume','suggest']);
});
test('disabled capture releases filename determination exactly once',async()=>{
 const h=harness({filenameGate:true,capture:false});assert.equal(await filenameGate(h),1);assert.deepEqual(h.calls,['suggest']);
});
test('extension own update releases filename determination without opening application dialog',async()=>{
 const h=harness({filenameGate:true});h.bridge.runtime.id='self';await filenameGate(h,filenameItem({byExtensionId:'self'}));assert.deepEqual(h.calls,['suggest']);
});
test('cancelling application dialog cancels browser before Save As is released',async()=>{
 const h=harness({filenameGate:true,exclusive:true,promptOutcome:'cancelled'});await filenameGate(h);assert.deepEqual(h.calls,['pause','send','poll','cancel','suggest']);
});
test('strict click interception never starts browser fallback on handoff failure',async()=>{
 const h=pageHarness({ok:false,exclusive:true});const click=await h.click('https://files.example/file.zip');assert.equal(click.defaultPrevented,true);assert.equal(h.fallbackClicks(),0);
});
test('Google Drive generic download endpoints are intercepted before navigation',async()=>{
 for(const url of ['https://drive.usercontent.google.com/download?id=file-123&export=download','https://drive.google.com/uc?id=file-123&export=download']){const h=pageHarness();const click=await h.click(url);assert.equal(click.defaultPrevented,true);assert.equal(h.messages.length,1);}
 const h=pageHarness();const click=await h.click('https://drive.google.com.evil.example/download?id=file-123');assert.equal(click.defaultPrevented,false);
});
test('strict legacy download capture cancels instead of resuming on failure',async()=>{
 const h=harness({exclusive:true,online:false});await h.context.captureDownload(filenameItem());assert.deepEqual(h.calls,['pause','send','cancel']);
});
test('filename determination is released even if settings cannot be read',async()=>{
 const h=harness({filenameGate:true});h.bridge.storage.local.get=async()=>{throw Error('storage unavailable');};assert.equal(await filenameGate(h),1);assert.deepEqual(h.calls,['suggest']);
});
test('strict handoff failure never bypasses the filename gate on a later download attempt',async()=>{
 const h=harness({filenameGate:true,exclusive:true,online:false});
 const url='https://files.example/file.zip';
 const result=await new Promise(resolve=>h.bridge.runtime.onMessage.listeners[0]({type:'capture-link',url,requestId:'retry-001'},{tab:{id:1}},resolve));
 assert.ok(result.error);await filenameGate(h);assert.deepEqual(h.calls,['send','pause','send','cancel','suggest']);
});
test('strict mode without a connection token cancels instead of opening browser Save As',async()=>{
 const h=harness({filenameGate:true,exclusive:true,token:''});await filenameGate(h);assert.deepEqual(h.calls,['cancel','suggest']);
});

test('managed extension reloads only matching completed newer files and waits for handoff',async()=>{
 const h=harness();let reloads=0,version='2.0.0',manifestVersion='2.0.0',managed=true;
 h.context.chrome.runtime.getURL=name=>'chrome-extension://test/'+name;
 h.context.chrome.runtime.getManifest=()=>({version:'1.9.5'});
 h.context.chrome.runtime.reload=()=>reloads++;
 h.context.fetch=async url=>({ok:true,json:async()=>url.endsWith('managed.json')?{managed,version}:url.endsWith('/api/info')?{version}:{version:manifestVersion}});
 managed=false;assert.equal(await h.context.reloadManagedExtension(),false);
 managed=true;manifestVersion='1.9.5';assert.equal(await h.context.reloadManagedExtension(),false);
 manifestVersion='2.0.0';vm.runInContext("inFlight.set('pending',{})",h.context);assert.equal(await h.context.reloadManagedExtension(),false);
 vm.runInContext('inFlight.clear()',h.context);assert.equal(await h.context.reloadManagedExtension(),true);assert.equal(reloads,1);
 version=manifestVersion='1.8.0';assert.equal(await h.context.reloadManagedExtension(),false);assert.equal(reloads,1);
});

test('current video action sends the active Shorts page, not its blob stream',async()=>{
 const h=harness();const url='https://www.youtube.com/shorts/VTueQm5ER9I?feature=share';
 h.context.chrome.tabs={query:async()=>[{url}]};const sent=[];h.context.send=async value=>{sent.push(value);return {};};
 const result=await new Promise(resolve=>h.context.chrome.runtime.onMessage.listeners[0]({type:'send-current-video'},{},resolve));
 assert.equal(result.ok,true);assert.deepEqual(sent,[url]);
});

test('current video action rejects ordinary and spoofed pages',async()=>{
 for(const url of ['https://www.youtube.com/','https://youtube.com.evil.test/shorts/x','https://example.com/reel/x']){
  const h=harness();h.context.chrome.tabs={query:async()=>[{url}]};h.context.send=async()=>{throw Error('must not send');};
  const result=await new Promise(resolve=>h.context.chrome.runtime.onMessage.listeners[0]({type:'send-current-video'},{},resolve));
  assert.match(result.error,/Hãy mở video/);
 }
});

test('filename gate keeps stable release URL instead of signed UUID redirect',async()=>{
 const h=harness({filenameGate:true});const urls=[];h.context.automaticSend=async url=>{urls.push(url);return {};};
 const original='https://github.com/XOmongoose/DownloadNow/releases/download/v1.10.0/DownloadNow-Browser-Extensions-1.10.0.zip';
 await h.context.captureBeforeSaveAs({id:99,url:original,finalUrl:'https://release-assets.githubusercontent.com/asset/random-uuid',state:'in_progress'},()=>{});
 assert.deepEqual(urls,[original]);assert.deepEqual(h.calls,['pause','cancel']);
});

test('legacy capture also retains original URL across redirects',async()=>{
 const h=harness();const original='https://github.com/owner/repo/releases/download/v1/file.zip',urls=[];
 h.bridge.downloads.search=async()=>[{url:original,finalUrl:'https://cdn.example/uuid',state:'in_progress',filename:'C:\\Downloads\\file.zip'}];
 h.context.automaticSend=async url=>{urls.push(url);return {};};
 await h.context.captureDownload({id:99,url:original,finalUrl:'https://cdn.example/uuid',state:'in_progress'});
 assert.deepEqual(urls,[original]);
});
