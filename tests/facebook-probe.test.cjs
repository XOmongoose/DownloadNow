const {test}=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
const script=fs.readFileSync(path.join(__dirname,'../extension/chromium/facebook-probe.js'),'utf8');
const story='UzpfSVNDOjE2NTQ2NDM1Njk2MzAyNDA=',page='https://www.facebook.com/stories/1399901183414478/'+story+'/';
function probe(data,expected=page,current=page){
 const video={parentElement:null,__reactFiber$test:{memoizedProps:data,return:null}};
 const c=vm.createContext({URL,location:{href:current},document:{querySelectorAll:()=>[video]},atob:v=>Buffer.from(v,'base64').toString()});
 vm.runInContext(script,c);return c.DownloadNowFacebookProbe(expected);
}
test('finds dynamically loaded progressive video for the supplied Story identity',()=>{
 const data={story:{id:'1654643569630240',video:{id:'v1',videoDeliveryResponseResult:{progressive_urls:[{progressive_url:'https://video.xx.fbcdn.net/selected.mp4?sig=test'}]}}}};
 assert.equal(probe(data).url,'https://video.xx.fbcdn.net/selected.mp4?sig=test');
});
test('never uses a neighbouring preloaded Story',()=>{
 assert.equal(probe({id:'other-story',video:{browser_native_hd_url:'https://v.fbcdn.net/wrong.mp4'}}).url,undefined);
});
test('rejects navigation to another Story before probing',()=>{
 assert.match(probe({},page,page.replace(story,'other')).error,/thay đổi/);
});
test('rejects several distinct videos under the same Story',()=>{
 assert.equal(probe({id:story,attachments:[{id:'v1',playable_url:'https://v.fbcdn.net/a.mp4'},{id:'v2',playable_url:'https://v.fbcdn.net/b.mp4'}]}).url,undefined);
});
test('handles component cycles and skips getters',()=>{
 const data={id:story,video:{id:'v1',playable_url:'https://v.fbcdn.net/a.mp4'}};data.loop=data;
 Object.defineProperty(data,'credentials',{enumerable:true,get(){throw Error('must not read getter');}});
 assert.equal(probe(data).url,'https://v.fbcdn.net/a.mp4');
});
test('does not accept an arbitrary URL or credentials in a media URL',()=>{
 for(const url of ['https://evil.test/file.mp4','https://u:p@v.fbcdn.net/file.mp4','blob:facebook/video'])assert.equal(probe({id:story,video:{playable_url:url}}).url,undefined);
});
test('returns only the selected media URL and Story identity, not component data',()=>{
 const result=probe({id:story,privateField:'not-returned',video:{id:'v1',playable_url:'https://v.fbcdn.net/a.mp4'}});
 assert.deepEqual(Object.keys(result).sort(),['story','url']);
});

test('rejects a different owner even when a Story suffix is reused',()=>{
 assert.match(probe({},page,page.replace('1399901183414478','another-owner')).error,/thay đổi/);
});

test('finds the supplied Story through React children while excluding a neighbour',()=>{
 const requested='UzpfSVNDOjE1OTIwMzc5MTIxNzM0ODY=',url='https://www.facebook.com/stories/1293026967448904/'+requested+'/';
 const data={children:[{props:{story:{id:'other',children:{playable_url:'https://v.fbcdn.net/wrong.mp4'}}}},{props:{story:{id:'1592037912173486',children:{props:{video:{id:'v1',browser_native_hd_url:'https://v.fbcdn.net/right.mp4'}}}}}}]};
 assert.equal(probe(data,url,url).url,'https://v.fbcdn.net/right.mp4');
});
test('walks cyclic React children without invoking accessors or entering DOM nodes',()=>{
 const data={id:story,children:{props:{video:{id:'v1',playable_url:'https://v.fbcdn.net/right.mp4'}}}};
 data.children.loop=data;data.dom={nodeType:1,id:story,playable_url:'https://v.fbcdn.net/wrong.mp4'};
 Object.defineProperty(data.children,'nodeType',{get(){throw Error('nodeType getter');}});
 Object.defineProperty(data.children,'secret',{enumerable:true,get(){throw Error('getter');}});
 assert.equal(probe(data).url,'https://v.fbcdn.net/right.mp4');
});
test('does not borrow media from a neighbouring child when requested Story has no video',()=>{
 assert.equal(probe({children:[{props:{id:story}},{props:{id:'other',playable_url:'https://v.fbcdn.net/wrong.mp4'}}]}).url,undefined);
});

function playerProbe(players,target){
 const c=vm.createContext({URL,location:{href:page,pathname:new URL(page).pathname},innerHeight:900,innerWidth:1200,document:{querySelectorAll:()=>players},atob:v=>Buffer.from(v,'base64').toString()});vm.runInContext(script,c);return c.DownloadNowFacebookProbe(page,target);
}
const marker='12345678-1234-1234-1234-123456789abc';
function player(url,marked=true,props={}){return {isConnected:true,currentSrc:url,src:'',parentElement:null,getAttribute:()=>marked?marker:null,getBoundingClientRect:()=>({left:400,right:800,top:50,bottom:750,width:400,height:700}),__reactProps$test:props};}
test('marked visible player wins over previous Story and unchanged address',()=>{
 const old=player('https://v.fbcdn.net/old.mp4',false),current=player('https://v.fbcdn.net/new.mp4');
 assert.equal(playerProbe([old,current],marker).url,'https://v.fbcdn.net/new.mp4');
});
test('recycled blob player reads current local properties rather than preloaded Stories',()=>{
 const v=player('blob:current',true,{video:{playable_url:'https://v.fbcdn.net/current.mp4'},children:{id:story,playable_url:'https://v.fbcdn.net/old.mp4'}});
 assert.equal(playerProbe([v],marker).url,'https://v.fbcdn.net/current.mp4');
 v.__reactProps$test.video.playable_url='https://v.fbcdn.net/next.mp4';assert.equal(playerProbe([v],marker).url,'https://v.fbcdn.net/next.mp4');
});
test('missing marked player never falls back to old Story metadata',()=>{
 assert.equal(playerProbe([player('https://v.fbcdn.net/old.mp4',false)],marker).url,undefined);
});
test('ambiguous local sources and hidden marked players are rejected',()=>{
 const v=player('blob:current',true,{a:{playable_url:'https://v.fbcdn.net/a.mp4'},b:{playable_url:'https://v.fbcdn.net/b.mp4'}});
 assert.equal(playerProbe([v],marker).url,undefined);v.isConnected=false;assert.equal(playerProbe([v],marker).url,undefined);
});

test('HD and SD alternatives of one player prefer HD',()=>{
 const v=player('blob:current',true,{video:{browser_native_hd_url:'https://v.fbcdn.net/hd.mp4',browser_native_sd_url:'https://v.fbcdn.net/sd.mp4'}});
 assert.equal(playerProbe([v],marker).url,'https://v.fbcdn.net/hd.mp4');
});
