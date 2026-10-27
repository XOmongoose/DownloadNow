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
