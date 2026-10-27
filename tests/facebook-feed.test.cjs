const {test}=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
const context=vm.createContext({URL,atob:value=>Buffer.from(value,'base64').toString('utf8')});
vm.runInContext(fs.readFileSync(path.join(__dirname,'../extension/chromium/facebook-feed.js'),'utf8'),context);
const fb=context.DownloadNowFacebook,story='UzpfSVNDOjE2NjE1MTM1MTU2NDUyOTg=';
function container({links=[],count=1,article=false,parent=null,id=null}={}){return {parentElement:parent,querySelectorAll:s=>s==='video'?Array(count).fill({}):links.map(href=>({href})),getAttribute:k=>k==='data-video-id'?id:null,matches:()=>article};}
function video(parent,src='blob:facebook/player'){return {parentElement:parent,currentSrc:src,src,closest:()=>null};}
const doc={querySelectorAll:()=>[]};
test('normalizes feed video and post links without tracking',()=>{
 assert.equal(fb.canonical('/watch/?v=123&tracking=x','https://www.facebook.com/'),'https://www.facebook.com/watch/?v=123');
 assert.equal(fb.canonical('https://www.facebook.com/user/videos/456/?x=y'),'https://www.facebook.com/watch/?v=456');
 assert.equal(fb.canonical('/user/posts/pfbidABC?comment_id=2','https://www.facebook.com/'),'https://www.facebook.com/user/posts/pfbidABC');
 assert.equal(fb.canonical('https://facebook.com.evil.test/watch/?v=123'),null);
});
test('resolves video only inside its own post',()=>{
 const parent=container({links:['https://www.facebook.com/user/videos/123/'],article:true,parent:container({links:['https://www.facebook.com/user/videos/999/']})});
 assert.equal(fb.resolve(video(parent),'https://www.facebook.com/',doc),'https://www.facebook.com/watch/?v=123');
});
test('never borrows permalink from neighbouring posts or guesses between videos',()=>{
 const outer=container({links:['https://www.facebook.com/user/videos/999/'],count:2}),article=container({article:true,parent:outer});
 assert.equal(fb.resolve(video(article),'https://www.facebook.com/',doc),null);
 const ambiguous=container({links:['https://www.facebook.com/watch/?v=123','https://www.facebook.com/watch/?v=456'],article:true});
 assert.equal(fb.resolve(video(ambiguous),'https://www.facebook.com/',doc),null);
});
test('supports an explicit video id or a single post permalink',()=>{
 assert.equal(fb.resolve(video(container({id:'123'})),'https://www.facebook.com/',doc),'https://www.facebook.com/watch/?v=123');
 assert.equal(fb.resolve(video(container({article:true,links:['https://www.facebook.com/u/posts/123']})),'https://www.facebook.com/',doc),'https://www.facebook.com/u/posts/123');
});
test('direct fallback only accepts signed Facebook MP4 sources',()=>{
 assert.equal(fb.direct('https://video.xx.fbcdn.net/file.mp4?sig=abc'),'https://video.xx.fbcdn.net/file.mp4?sig=abc');
 for(const u of ['blob:facebook/a','https://fbcdn.net.evil.test/file.mp4','https://video.xx.fbcdn.net/file.m3u8','https://user:pass@video.xx.fbcdn.net/file.mp4'])assert.equal(fb.direct(u),null);
});
test('stories use exactly the selected story, never a preloaded adjacent story',()=>{
 const data={stories:[{id:'other-story',video:{id:'video1',browser_native_hd_url:'https://v.fbcdn.net/other.mp4'}},{id:story,video:{id:'video2',browser_native_sd_url:'https://v.fbcdn.net/sd.mp4',browser_native_hd_url:'https://v.fbcdn.net/selected.mp4'}}]};
 assert.equal(fb.storyMedia(data,story),'https://v.fbcdn.net/selected.mp4');
 assert.equal(fb.storyMedia(data,'missing-story'),null);
 const page='https://www.facebook.com/stories/1959327764084753/'+story+'/';
 assert.equal(fb.resolve(video(null),page,{querySelectorAll:()=>[{textContent:JSON.stringify(data)}]}),'https://v.fbcdn.net/selected.mp4');
});
test('decoded numeric story identities are supported but multiple video attachments are rejected',()=>{
 assert.equal(fb.storyMedia({story_id:'1661513515645298',media:{id:'v1',playable_url:'https://v.fbcdn.net/selected.mp4'}},story),'https://v.fbcdn.net/selected.mp4');
 assert.equal(fb.storyMedia({id:story,attachments:[{id:'v1',playable_url:'https://v.fbcdn.net/a.mp4'},{id:'v2',playable_url:'https://v.fbcdn.net/b.mp4'}]},story),null);
});
test('stories without an accessible source are not sent as HTML or an unrelated post',()=>{
 const page='https://www.facebook.com/stories/1959327764084753/'+story+'/';
 assert.equal(fb.resolve(video(container({links:['https://www.facebook.com/u/videos/999']})),page,doc),null);
});

test('per-video button resolves a recycled feed element again at click time',async()=>{
 const messages=[],hosts=[],listeners=[];let timer;
 const parent=container({article:true,links:['https://www.facebook.com/u/videos/123/']});
 const doc={querySelectorAll:s=>s==='video'?[v]:[],body:{append:h=>hosts.push(h)},createElement:()=>({style:{},setAttribute(){},remove(){},attachShadow(){const shadow={children:[],append(x){this.children.push(x);}};this.shadow=shadow;return shadow;}})};
 const v=video(parent);Object.assign(v,{ownerDocument:doc,isConnected:true,paused:false,ended:false,getBoundingClientRect:()=>({left:100,right:500,top:100,bottom:360,width:400,height:260})});doc.elementFromPoint=()=>v;
 const bridge={runtime:{onMessage:{addListener:f=>listeners.push(f)},sendMessage:async m=>{messages.push(m);return {ok:true};}}};
 const c=vm.createContext({URL,atob:x=>Buffer.from(x,'base64').toString(),window:{location:{href:'https://www.facebook.com/'},innerHeight:900,innerWidth:1200,addEventListener(){}},setInterval:f=>{timer=f;},requestAnimationFrame:f=>f(),crypto:require('node:crypto').webcrypto});
 vm.runInContext(fs.readFileSync(path.join(__dirname,'../extension/chromium/facebook-feed.js'),'utf8'),c);
 c.DownloadNowFacebook.attach({doc,bridge,enabled:()=>true,notice(){}});assert.equal(hosts.length,1);
 const button=hosts[0].shadow.children[0];await button.onclick({preventDefault(){},stopPropagation(){}});
 parent.querySelectorAll=s=>s==='video'?[v]:[{href:'https://www.facebook.com/u/videos/456/'}];
 await button.onclick({preventDefault(){},stopPropagation(){}});
 assert.deepEqual(messages.map(m=>m.url),['https://www.facebook.com/watch/?v=123','https://www.facebook.com/watch/?v=456']);
 v.isConnected=false;timer();
});

function storyUI({enabled=true,data=null,probe=null}={}){
 const hosts=[],messages=[],notices=[];let timer,page='https://www.facebook.com/stories/1959327764084753/'+story+'/';
 const doc={querySelectorAll:s=>s==='script[type="application/json"]'&&data?[{textContent:JSON.stringify(data)}]:[],body:{append:h=>hosts.push(h)},createElement:()=>({style:{},setAttribute(){},remove(){this.removed=true;},attachShadow(){const shadow={children:[],append(x){this.children.push(x);}};this.shadow=shadow;return shadow;}})};
 const bridge={runtime:{onMessage:{addListener(){}},sendMessage:async m=>{messages.push(m);return m.type==='resolve-facebook-story-source'&&probe?probe():{ok:true};}}};
 const c=vm.createContext({URL,atob:x=>Buffer.from(x,'base64').toString(),window:{location:{href:page},innerHeight:900,innerWidth:1200,addEventListener(){}},setInterval:f=>{timer=f;},requestAnimationFrame:f=>f(),crypto:require('node:crypto').webcrypto});
 vm.runInContext(fs.readFileSync(path.join(__dirname,'../extension/chromium/facebook-feed.js'),'utf8'),c);
 c.DownloadNowFacebook.attach({doc,bridge,enabled:()=>enabled,notice:t=>notices.push(t),page:()=>page});
 return {hosts,messages,notices,click:()=>hosts.at(-1).shadow.children[0].onclick({preventDefault(){},stopPropagation(){}}),navigate:p=>{page=p;timer();}};
}

test('fixed Story button remains visible without a video element and downloads only its matching source',async()=>{
 const h=storyUI({data:{id:story,video:{id:'v1',browser_native_hd_url:'https://v.fbcdn.net/selected.mp4'}}});
 assert.equal(h.hosts.length,1);assert.equal(h.hosts[0].shadow.children[0].textContent,'↓ Tải Tin Facebook');
 assert.match(h.hosts[0].style.cssText,/right:24px;bottom:88px/);
 await h.click();assert.equal(h.messages[0].url,'https://v.fbcdn.net/selected.mp4');
 h.navigate('https://www.facebook.com/');assert.equal(h.hosts[0].removed,true);
});

test('unavailable Story tries dynamic source resolution without downloading HTML or calling it a photo',async()=>{
 const h=storyUI();await h.click();assert.equal(h.messages.filter(m=>m.type==='capture-link').length,0);assert.equal(h.messages[0].type,'resolve-facebook-story-source');assert.match(h.notices[0],/Chưa tìm được nguồn MP4/);assert.doesNotMatch(h.notices[0],/ảnh/);
});

test('unpaired Story action stays visible and explains how to connect',async()=>{
 const h=storyUI({enabled:false});assert.equal(h.hosts.length,1);await h.click();assert.equal(h.messages.length,0);assert.match(h.notices[0],/mở ứng dụng để kết nối/);
});

test('Story button sends a dynamically resolved MP4 through the normal download queue',async()=>{
 const h=storyUI({probe:()=>({url:'https://v.fbcdn.net/dynamic.mp4'})});await h.click();
 assert.deepEqual(h.messages.map(m=>m.type),['resolve-facebook-story-source','capture-link']);assert.equal(h.messages[1].url,'https://v.fbcdn.net/dynamic.mp4');
});

test('Story button refuses the result if navigation changes during async resolution',async()=>{
 let h;h=storyUI({probe:()=>{h.navigate('https://www.facebook.com/stories/owner/other/');return {url:'https://v.fbcdn.net/old.mp4'};}});await h.click();
 assert.equal(h.messages.filter(m=>m.type==='capture-link').length,0);assert.match(h.notices[0],/Tin đã thay đổi/);
});

test('initial Story JSON supports progressive delivery fields without mixing video identities',()=>{
 assert.equal(fb.storyMedia({id:story,video:{id:'v1',progressive_urls:[{progressive_url:'https://v.fbcdn.net/a.mp4'},{progressive_url:'https://v.fbcdn.net/b.mp4'}]}},story)?.endsWith('.mp4'),true);
});

test('Story never falls back to a recycled player URL from the previous owner',()=>{
 assert.equal(fb.resolve(video(null,'https://v.fbcdn.net/previous.mp4'),'https://www.facebook.com/stories/second/new/',doc),null);
});
test('same Story button resolves each successive owner from its current identity',async()=>{
 let current='https://v.fbcdn.net/first.mp4';const h=storyUI({probe:()=>({url:current})});
 await h.click();h.navigate('https://www.facebook.com/stories/second/new/');current='https://v.fbcdn.net/second.mp4';await h.click();
 assert.deepEqual(h.messages.filter(m=>m.type==='capture-link').map(m=>m.url),['https://v.fbcdn.net/first.mp4','https://v.fbcdn.net/second.mp4']);
});
