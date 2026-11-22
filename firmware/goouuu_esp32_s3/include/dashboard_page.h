#pragma once
#include <Arduino.h>
static const char CAMERA_PAGE[] PROGMEM=R"BSC_HTML(<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>BSHE27 · Camera speed</title>
<style>
:root{color-scheme:dark;font-family:system-ui,sans-serif;background:#10171e;color:#e9f2fa}*{box-sizing:border-box}[hidden]{display:none!important}body{max-width:1180px;margin:auto;padding:24px}h1{font-size:clamp(25px,4vw,38px);margin:6px 0}h2{font-size:21px}p{color:#afc1cf;line-height:1.55}small{color:#afc1cf}.eyebrow{color:#83dfca;letter-spacing:.14em;font-size:12px}.metrics,.views{display:grid;gap:14px}.metrics{grid-template-columns:repeat(auto-fit,minmax(150px,1fr));margin:24px 0}.card,.panel{background:#19232d;border:1px solid #30414e;border-radius:14px;padding:18px}.metric{display:block;font-size:30px;font-variant-numeric:tabular-nums;margin:8px 0}.views{grid-template-columns:1fr 1fr}.panel{min-width:0}canvas{display:block;width:100%;aspect-ratio:4/3;object-fit:contain;background:#080d12;border-radius:8px}button,a.button{display:inline-block;border:0;border-radius:7px;padding:11px 15px;margin:12px 5px 0 0;background:#a2e6d7;color:#13251f;font:inherit;text-decoration:none;cursor:pointer}button:disabled{opacity:.45;cursor:default}button:focus-visible,a:focus-visible{outline:3px solid white;outline-offset:3px}.state{min-height:3em;margin-bottom:0}.details{display:grid;grid-template-columns:1fr auto;gap:9px;margin-top:16px;font-size:14px}.details span:nth-child(even){font-variant-numeric:tabular-nums}pre{white-space:pre-wrap;overflow-wrap:anywhere;color:#bdd1df;font-size:13px}.muted{font-size:13px}details{margin-top:18px}summary{cursor:pointer}.offline{color:#ffce8b}@media(max-width:760px){body{padding:16px}.views{grid-template-columns:1fr}}
</style>
</head>
<body>
<div class="eyebrow">BSHE27 / GOOUUU ESP32-S3</div><h1>Camera speed, from board to screen.</h1>
<p>Compare the frames processed onboard with the distinct frames your browser displays over Wi-Fi or a native USB cable. Both viewers share the same encoded frames.</p>
<div class="metrics">
<div class="card"><small>Board processed</small><strong class="metric" id="board-fps">—</strong><small>FPS · sensor JPEG capture</small></div>
<div class="card"><small>ESP32 JPEG encoding</small><strong class="metric" id="jpeg-ms">—</strong><small>ms · bypassed with sensor JPEG</small></div>
<div class="card"><small>JPEG size</small><strong class="metric" id="jpeg-size">—</strong><small>KiB per received frame</small></div>
<div class="card"><small>Capture wait</small><strong class="metric" id="capture-ms">—</strong><small>milliseconds waiting for driver</small></div>
</div>
<div class="views">
<section class="panel" id="wifi-panel"><h2>Wi-Fi</h2><canvas id="wifi-image" width="320" height="240" aria-label="Wi-Fi camera feed"></canvas>
<button id="wifi-toggle">Start Wi-Fi</button><a class="button" id="snapshot" href="/capture" target="_blank" rel="noopener">JPEG snapshot</a>
<div class="details"><span>Browser displayed</span><span id="wifi-fps">0.0 FPS</span><span>Request → decoded image</span><span id="wifi-ms">—</span><span>Received JPEG data</span><span id="wifi-kbps">0 kB/s</span><span>Frame age when sent</span><span id="wifi-age">—</span></div>
<p class="state" id="wifi-state" role="status">Ready</p></section>
<section class="panel"><h2>USB-C live camera</h2>
<button id="usb-toggle">Connect USB</button><button id="usb-save" disabled>Save JPEG</button><button id="usb-fullscreen">Full screen</button>
<canvas id="usb-image" width="320" height="240" style="max-height:65vh" aria-label="USB camera feed"></canvas>
<div class="details"><span>Browser displayed</span><span id="usb-fps">0.0 FPS</span><span>Request → decoded image</span><span id="usb-ms">—</span><span>Received JPEG data</span><span id="usb-kbps">0 kB/s</span><span>Frame age when sent</span><span id="usb-age">—</span><span>Automatic recoveries</span><span id="usb-recoveries">0</span></div>
<p class="state" id="usb-state" role="status">Use the board's native USB-C port, not the TTL/CH340 port.</p></section>
</div>
<button id="compare-toggle" hidden>Show Wi-Fi comparison</button>
<p class="muted" id="usb-session" role="status">No USB frames received yet.</p>
<p class="muted">Board FPS measures completed sensor JPEG frames, not the sensor's theoretical maximum. Browser FPS counts distinct decoded frames, averaged over two seconds. Request time includes waiting for the next frame, transfer and JPEG decoding. Frame age is measured on the board before sending; it is not synchronized end-to-end latency. JPEG compression runs inside the camera sensor; 0 ms of ESP32 encoding does not mean zero sensor processing time. Image recognition is not installed. Multiple viewers share bandwidth.</p>
<section class="panel" style="margin:16px 0"><h2>Exposure and gain</h2>
<fieldset id="camera-controls" disabled style="border:0;padding:0"><label>Exposure (ms) <input id="exposure-ms" type="number" min="0.1" max="20" step="0.1" value="1" style="width:85px;padding:8px"></label>
<label>Gain (×) <input id="gain-x" type="number" min="1" max="15.5" step="0.5" value="4" style="width:85px;padding:8px"></label>
<button id="manual-apply">Apply manual</button><button id="auto-exposure">Restore auto</button><br>
<button id="preset-half">0.5 ms</button><button id="preset-one">1 ms</button><button id="preset-two">2 ms</button></fieldset>
<p id="exposure-state" role="status">Connect USB to read the sensor settings.</p>
<p class="muted">Short exposure reduces motion blur but can darken the image. More gain brightens it and adds noise. Presets apply manual exposure with the gain shown above. Auto restores automatic exposure and gain; night-mode frame extension stays off. Values are calculated from sensor register readback, not an optical shutter measurement. Settings reset to Auto on reboot.</p></section>
<details open><summary>Connect a wired laptop</summary><p>Use a data-capable cable in the board's native USB-C socket (the one connected to the ESP32-S3, often marked USB). The TTL/CH340 socket remains available for uploading and the console. Open the offline viewer in desktop Edge or Chrome, click Connect USB, and choose <strong>USB JTAG/serial debug unit</strong> / the Espressif device. Wi-Fi is not needed for USB viewing. This is a browser viewer, not a Windows webcam device.</p><a class="button" id="download" href="/viewer" download="BSHE27-USB-viewer.html">Download offline USB viewer</a><p class="muted" id="usb-help">If USB permission is unavailable on this Wi-Fi page, download the viewer and open that saved HTML file in Edge or Chrome. The USB interface supports video and camera exposure/gain only; it cannot start a flight mission. Video delivery pauses during missions.</p></details>
<details><summary>Pixhawk and board status</summary><pre id="status">Waiting for board status…</pre></details>
<script>
'use strict';
const $=id=>document.getElementById(id);
const standalone=location.protocol==='file:'||['localhost','127.0.0.1'].includes(location.hostname);
const wifiOrigin=standalone?'http://192.168.4.1':location.origin;
const videoOrigin=new URL(wifiOrigin);videoOrigin.port='81';
const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms));
const trackers={wifi:{samples:[],lastId:null,blob:null},usb:{samples:[],lastId:null,blob:null,total:0,started:0,lastAt:0}};
let wifiSession=0,wifiPlaying=false,wifiAbort=null,usbPlaying=false,port=null,reader=null,writer=null,serialBuffer=new Uint8Array();
let pendingSettings=null,lastSettingsAt=0,controlsBusy=false;
function setState(kind,text){$(kind+'-state').textContent=text;}
function metrics(m){$('board-fps').textContent=m.boardFps.toFixed(1);$('jpeg-ms').textContent=(m.jpegUs/1000).toFixed(1);$('jpeg-size').textContent=m.length?(m.length/1024).toFixed(1):'—';$('capture-ms').textContent=(m.captureUs/1000).toFixed(1);}
function parseHeader(bytes){
 if(bytes.length!==48||String.fromCharCode(...bytes.slice(0,4))!=='BSC1')throw new Error('Unexpected camera protocol. Upload the latest firmware.');
 const d=new DataView(bytes.buffer,bytes.byteOffset,bytes.byteLength);
 const m={length:d.getUint32(4,true),id:d.getUint32(8,true),captureUs:d.getUint32(20,true),jpegUs:d.getUint32(24,true),boardFps:d.getFloat32(32,true),age:d.getUint32(40,true),flags:d.getUint32(44,true)};
 if(m.length>524288||!Number.isFinite(m.boardFps)||d.getUint16(36,true)!==320||d.getUint16(38,true)!==240)throw new Error('Invalid camera frame header.');
 return m;
}
async function draw(kind,m,bytes,started){
 if(m.flags)throw new Error(m.flags&1?'Video paused during flight mission.':'Camera frame unavailable. Check board status.');
 if(m.length!==bytes.length||!m.length)throw new Error('Incomplete camera image.');
 const blob=new Blob([bytes],{type:'image/jpeg'}),bitmap=await createImageBitmap(blob);
 if((kind==='usb'&&!usbPlaying)||(kind==='wifi'&&!wifiPlaying)){bitmap.close();return;}
 const ctx=$(kind+'-image').getContext('2d');ctx.drawImage(bitmap,0,0,320,240);bitmap.close();
 const t=trackers[kind];t.blob=blob;
 if(kind==='usb'){if(t.lastId!==m.id)++t.total;t.lastAt=performance.now();}
 if(t.lastId!==m.id){t.samples.push({at:performance.now(),bytes:bytes.length});t.lastId=m.id;}
 metrics(m);$(kind+'-ms').textContent=(performance.now()-started).toFixed(0)+' ms';$(kind+'-age').textContent=m.age+' ms';
 setState(kind,'Connected · frame '+m.id+' · '+(bytes.length/1024).toFixed(1)+' KiB');
 if(kind==='usb')$('usb-save').disabled=false;
}
setInterval(()=>{const now=performance.now();for(const kind of ['wifi','usb']){const t=trackers[kind];t.samples=t.samples.filter(s=>now-s.at<2000);$(kind+'-fps').textContent=(t.samples.length/2).toFixed(1)+' FPS';$(kind+'-kbps').textContent=(t.samples.reduce((a,s)=>a+s.bytes,0)/2000).toFixed(1)+' kB/s';}
 const t=trackers.usb;if(t.started){const age=t.lastAt?now-t.lastAt:now-t.started;$('usb-session').textContent=t.total+' frames displayed · '+Math.floor((now-t.started)/1000)+' seconds since connection'+(usbPlaying&&age>2000?' · Waiting for fresh video; the displayed picture is stale.':!usbPlaying?' · Disconnected; showing last picture.':' · Live');}
},500);
function stopWifi(){++wifiSession;wifiPlaying=false;if(wifiAbort)wifiAbort.abort();$('wifi-toggle').textContent='Start Wi-Fi';setState('wifi','Stopped');}
async function wifiLoop(session){
 while(wifiPlaying&&session===wifiSession){
  const started=performance.now();const controller=new AbortController();wifiAbort=controller;const timeout=setTimeout(()=>controller.abort(),5000);
  try{
   const response=await fetch(videoOrigin.origin+'/frame?after='+(trackers.wifi.lastId||0),{cache:'no-store',signal:controller.signal});
   if(!response.ok)throw new Error(response.status===503?'Camera unavailable or mission running.':'HTTP '+response.status);
   const bytes=new Uint8Array(await response.arrayBuffer());
   if(!wifiPlaying||session!==wifiSession)break;
   if(bytes.length<48)throw new Error('Incomplete camera frame.');
   await draw('wifi',parseHeader(bytes.slice(0,48)),bytes.slice(48),started);
  }catch(error){if(!wifiPlaying||session!==wifiSession)break;setState('wifi',error.name==='AbortError'?'Wi-Fi request timed out. Reconnecting…':error.message+' Reconnecting…');await sleep(1000);}
  finally{clearTimeout(timeout);if(wifiAbort===controller)wifiAbort=null;}
 }
}
$('wifi-toggle').onclick=()=>{if(wifiPlaying)stopWifi();else{wifiPlaying=true;$('wifi-toggle').textContent='Stop Wi-Fi';wifiLoop(++wifiSession);}};
async function readExact(count){
 while(serialBuffer.length<count){const r=await reader.read();if(r.done)throw new Error('USB disconnected.');const joined=new Uint8Array(serialBuffer.length+r.value.length);joined.set(serialBuffer);joined.set(r.value,serialBuffer.length);serialBuffer=joined;if(serialBuffer.length>600000)throw new Error('USB buffer overflow. Reconnect.');}
 const bytes=serialBuffer.slice(0,count);serialBuffer=serialBuffer.slice(count);return bytes;
}
async function readPacket(){
 let magic=await readExact(4),skipped=0;
 while(String.fromCharCode(...magic)!=='BSC1'){if(++skipped>524288)throw new Error('USB protocol out of sync. Reconnect.');const next=await readExact(1);magic=new Uint8Array([magic[1],magic[2],magic[3],next[0]]);}
 const h=new Uint8Array(48);h.set(magic);h.set(await readExact(44),4);const m=parseHeader(h);return {m,bytes:await readExact(m.length)};
}
function showSettings(s,ack=false){
 if(ack)controlsBusy=false;
 $('camera-controls').disabled=controlsBusy;
 if(!s.ok){$('exposure-state').textContent=s.error||'Camera settings unavailable.';return;}
 $('exposure-state').textContent=(s.manual?'Manual':'Auto')+' · exposure '+s.exposure_ms.toFixed(3)+' ms · gain '+s.gain.toFixed(2)+'× · frame period '+s.frame_period_ms.toFixed(2)+' ms · night mode '+(s.night_mode?'on':'off');
 $('exposure-ms').max=String(Math.min(20,s.max_exposure_ms));
}
function controlBody(manual){
 const us=Math.round(Number($('exposure-ms').value)*1000),gain=Math.round(Number($('gain-x').value)*16);
 if(manual&&(!Number.isFinite(us)||us<100||us>20000||!Number.isFinite(gain)||gain<16||gain>248))throw new Error('Use exposure 0.1–20 ms and gain 1–15.5×.');
 const body=new Uint8Array(7);body[0]=manual?1:0;const d=new DataView(body.buffer);d.setUint32(1,manual?us:0,true);d.setUint16(5,manual?gain:0,true);return body;
}
async function applySettings(manual){
 try{const body=controlBody(manual);controlsBusy=true;$('camera-controls').disabled=true;$('exposure-state').textContent='Applying camera settings…';
 if(usbPlaying){pendingSettings=body;return;}
 if(standalone)throw new Error('Connect USB first.');
 const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),5000);try{const response=await fetch('/camera-control',{method:'POST',body,signal:controller.signal});if(!response.ok)throw new Error('Camera control HTTP '+response.status);showSettings(await response.json(),true);}finally{clearTimeout(timer);}
 }catch(error){controlsBusy=false;$('camera-controls').disabled=!usbPlaying&&standalone;$('exposure-state').textContent=error.message;}
}
$('manual-apply').onclick=()=>applySettings(true);$('auto-exposure').onclick=()=>applySettings(false);
for(const [id,value] of [['preset-half',0.5],['preset-one',1],['preset-two',2]])$(id).onclick=()=>{$('exposure-ms').value=value;applySettings(true);};
async function readSettings(){
 const h=await readExact(8);if(String.fromCharCode(...h.slice(0,4))!=='BSS1')throw new Error('Camera controls require the latest firmware.');
 const length=new DataView(h.buffer,h.byteOffset,h.byteLength).getUint32(4,true);if(!length||length>4096)throw new Error('Invalid camera settings response.');
 return JSON.parse(new TextDecoder().decode(await readExact(length)));
}
async function timedPacket(request,settings=false){
 let timer;const pending=(async()=>{await writer.write(request);return settings?readSettings():readPacket();})();
 try{return await Promise.race([pending,new Promise((_,reject)=>{timer=setTimeout(()=>reject(new Error('USB frame transfer stalled.')),5000);})]);}
 catch(error){
  // Settle the old reader before reopening. Otherwise an abandoned readPacket
  // can steal bytes from the next session after Promise.race has timed out.
  if(reader)try{await reader.cancel();}catch{}
  if(writer)try{await writer.abort();}catch{}
  await pending.catch(()=>{});throw error;
 }finally{clearTimeout(timer);}
}
async function releaseUsb(){
 if(reader){try{await reader.cancel();}catch{}try{reader.releaseLock();}catch{}reader=null;}
 if(writer){try{writer.releaseLock();}catch{}writer=null;}
 if(port){try{await port.close();}catch{}}
 serialBuffer=new Uint8Array();
}
async function closeUsb(){
 usbPlaying=false;pendingSettings=null;controlsBusy=false;$('camera-controls').disabled=standalone;await releaseUsb();port=null;$('usb-toggle').textContent='Connect USB';
}
async function openUsb(){
 await port.open({baudRate:115200,bufferSize:65536});
 await port.setSignals({dataTerminalReady:true,requestToSend:false});
 reader=port.readable.getReader();writer=port.writable.getWriter();serialBuffer=new Uint8Array();lastSettingsAt=0;
}
async function connectUsb(){
 if(!navigator.serial){setState('usb','Open the downloaded viewer in desktop Edge or Chrome to use USB.');return;}
 $('usb-toggle').disabled=true;
 try{
  port=await navigator.serial.requestPort({filters:[{usbVendorId:0x303a,usbProductId:0x1001}]});
  Object.assign(trackers.usb,{samples:[],lastId:null,blob:null,total:0,started:performance.now(),lastAt:0});$('usb-save').disabled=true;$('usb-recoveries').textContent='0';
  usbPlaying=true;let failures=0,recoveries=0;
  $('usb-toggle').textContent='Disconnect USB';$('usb-toggle').disabled=false;
  while(usbPlaying){
   try{
    if(!reader)await openUsb();
    if(!usbPlaying)break;
    if(pendingSettings || !lastSettingsAt || performance.now()-lastSettingsAt>1000){
     const body=pendingSettings;pendingSettings=null;const command=body?new Uint8Array([67,...body]):new Uint8Array([83]);
     showSettings(await timedPacket(command,true),!!body);lastSettingsAt=performance.now();
    }
    const started=performance.now(),request=new Uint8Array(5);request[0]=70;new DataView(request.buffer).setUint32(1,trackers.usb.lastId||0,true);
    const packet=await timedPacket(request);
    if(!usbPlaying)break;
    if(packet.m.flags){failures=0;setState('usb',packet.m.flags&1?'Video paused during flight mission.':'Camera frame unavailable.');await sleep(500);continue;}
    await draw('usb',packet.m,packet.bytes,started);failures=0;
   }catch(error){
    if(!usbPlaying)break;
    await releaseUsb();
    if(++failures>3)throw new Error('USB could not recover. Check the cable, then click Connect USB.');
    ++recoveries;$('usb-recoveries').textContent=String(recoveries);
    setState('usb',error.message+' Reconnecting automatically ('+failures+'/3)…');
    // Reuse the already authorized port; never ask the user to choose it again.
    await sleep(500*failures);
   }
  }
 }catch(error){if(usbPlaying||!reader)setState('usb',error.name==='NotFoundError'?'No USB device selected.':error.message);}
 finally{await closeUsb();$('usb-toggle').disabled=false;}
}
$('usb-toggle').onclick=async()=>{if(usbPlaying){usbPlaying=false;$('usb-toggle').disabled=true;setState('usb','Disconnected');if(reader)try{await reader.cancel();}catch{}}else connectUsb();};
$('usb-save').onclick=()=>{const blob=trackers.usb.blob;if(!blob)return;const a=document.createElement('a'),url=URL.createObjectURL(blob);a.href=url;a.download='BSHE27-'+Date.now()+'.jpg';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
$('usb-fullscreen').onclick=async()=>{try{await $('usb-image').requestFullscreen();}catch(error){setState('usb','Full screen unavailable: '+error.message);}};
$('compare-toggle').onclick=()=>{const panel=$('wifi-panel');panel.hidden=!panel.hidden;document.querySelector('.views').style.gridTemplateColumns=panel.hidden?'1fr':'';$('compare-toggle').textContent=panel.hidden?'Show Wi-Fi comparison':'Hide Wi-Fi comparison';};
async function poll(){
 if(standalone)return;
 const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),5000);
 try{const r=await fetch('/status',{cache:'no-store',signal:controller.signal});if(!r.ok)throw new Error('HTTP '+r.status);const s=await r.json();if(!usbPlaying&&!controlsBusy){try{const c=await fetch('/camera-control',{cache:'no-store',signal:controller.signal});if(c.ok)showSettings(await c.json());}catch{}}$('status').textContent=JSON.stringify(s,null,2);if(s.camera&&!usbPlaying&&!wifiPlaying)metrics({boardFps:s.camera.board_fps,captureUs:s.camera.capture_wait_ms*1000,jpegUs:s.camera.jpeg_ms*1000,length:s.camera.jpeg_bytes});if(s.mission_active&&wifiPlaying){stopWifi();setState('wifi','Video paused during flight mission.');}if(s.camera_error)setState('wifi','Camera: '+s.camera_error);}
 catch(error){$('status').textContent='Board unreachable. Join BSHE27-Camera to read Wi-Fi status.';}
 finally{clearTimeout(timeout);setTimeout(poll,1000);}
}
$('snapshot').href=wifiOrigin+'/capture';
if(standalone){document.title='BSHE27 · USB-C live camera';document.querySelector('h1').textContent='Live camera over USB-C.';document.querySelector('h1+p').textContent='Connect the board’s OTG USB-C socket, click Connect USB, and select the Espressif USB serial device. Video continues until you disconnect. No Wi-Fi or internet is required.';$('wifi-panel').hidden=true;document.querySelector('.views').style.gridTemplateColumns='1fr';$('compare-toggle').hidden=false;$('download').hidden=true;$('snapshot').hidden=true;$('status').textContent='USB viewer works without Wi-Fi. Pixhawk status remains on the board dashboard.';setState('wifi','Optional: join BSHE27-Camera, then start Wi-Fi to compare.');}
else{$('camera-controls').disabled=false;fetch('/camera-control',{cache:'no-store'}).then(r=>r.json()).then(showSettings).catch(e=>{$('exposure-state').textContent=e.message;});$('wifi-toggle').click();poll();}
if(!navigator.serial)setState('usb','Download the offline USB viewer, then open it in desktop Edge or Chrome.');
window.addEventListener('pagehide',()=>{stopWifi();closeUsb();});
</script>
</body></html>
)BSC_HTML";
