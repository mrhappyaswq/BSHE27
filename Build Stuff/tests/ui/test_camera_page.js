const path=require('node:path'),fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const html=fs.readFileSync(process.argv[2]||path.join(__dirname,'../../../Code/web/index.html'),'utf8'),script=html.match(/<script>([\s\S]*?)<\/script>/)[1];
const flush=async()=>{for(let i=0;i<6;i++)await new Promise(r=>setImmediate(r));};
function page(){
 let now=100000,seq=0,blob=0,offline=false,state={ready:true,quality:75,fps_limit:3,wifi_up:true,device_connected:true},hold=false,release;
 const timers=new Map(),calls=[],revoked=[],dom={};
 for(const id of ['feed','toggle','status','network','camera','error','placeholder','snapshot','pixhawk','flight','telemetry-detail','quality','fps','apply','settings','settings-message','indicator']){
  let src='';dom[id]={textContent:'',hidden:false,value:id==='quality'?'75':'3',setAttribute(){},removeAttribute(k){if(k==='src')src='';},set src(v){src=v;Promise.resolve().then(()=>{if(src===v&&this.onload)this.onload();});},get src(){return src;}};
 }
 const context=vm.createContext({document:{getElementById:id=>dom[id]},window:{addEventListener(){}},Date:{now:()=>now},AbortController,Uint8Array,Blob,
  URL:{createObjectURL:()=>`blob:${++blob}`,revokeObjectURL:u=>revoked.push(u)},setTimeout:(fn,ms)=>{const id=++seq;timers.set(id,{fn,due:now+ms});return id;},clearTimeout:id=>timers.delete(id),setInterval:()=>1,
  fetch:async(url,options={})=>{calls.push(url);if(offline)throw Error('offline');
   if(url.startsWith('/capture'))return {ok:true,arrayBuffer:async()=>{if(hold)await new Promise((resolve,reject)=>{release=resolve;options.signal.addEventListener('abort',()=>reject(Error('aborted')));});return Uint8Array.from([255,216,1,2,255,217]).buffer;}};
   if(url==='/settings')return {ok:true,json:async()=>JSON.parse(options.body)};
   return {ok:true,json:async()=>state};}
 });vm.runInContext(script,context);
 return {dom,calls,context,revoked,setState:s=>state=s,offline:v=>offline=v,hold:v=>hold=v,release:()=>release&&release(),
  advance:async ms=>{now+=ms;for(const [id,t] of [...timers])if(t.due<=now){timers.delete(id);t.fn();}await flush();},
  refresh:async()=>{await vm.runInContext('refresh()',context);await flush();}};
}
(async()=>{
 const p=page();await flush();await p.advance(60);assert.match(p.dom.feed.src,/^blob:/);assert.equal(p.dom.status.textContent,'Live view connected');
 assert.deepEqual(p.calls.map(u=>u.split('?')[0]),['/status','/capture']);
 await p.advance(1100);assert.deepEqual(p.calls.map(u=>u.split('?')[0]),['/status','/capture','/status','/capture']);
 p.hold(true);await p.advance(1100);const count=p.calls.length;await p.refresh();assert.equal(p.calls.length,count,'status must wait for JPEG transfer');
 p.dom.toggle.onclick();await flush();assert.equal(p.dom.status.textContent,'Live view paused');await p.advance(20000);await p.refresh();assert.equal(p.dom.status.textContent,'Live view paused');
 const q=page();await flush();await q.advance(60);q.dom.quality.value='35';q.dom.quality.oninput();await q.refresh();assert.equal(q.dom.quality.value,'35');
 await q.dom.settings.onsubmit({preventDefault(){}});assert.match(q.dom['settings-message'].textContent,/Applied/);
 q.offline(true);await q.refresh();assert.equal(q.dom.network.textContent,'Board unreachable');assert.match(q.dom.error.textContent,/offline/);
 const broken=page();await flush();await broken.advance(60);broken.setState({ready:true,pixhawk:{state:'connected',get error(){throw Error('render test');}}});await broken.refresh();assert.match(broken.dom.error.textContent,/Dashboard display error: render test/);assert.notEqual(broken.dom.network.textContent,'Board unreachable');
 console.log('PASS: complete JPEGs, sequential status/preview, cancellation, pause, settings and accurate errors');
})().catch(e=>{console.error(e);process.exitCode=1;});
