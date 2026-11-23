#pragma once
#include <Arduino.h>
static const char CAMERA_PAGE[] PROGMEM=R"BSC_HTML(<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>BSHE27 · Wi-Fi telemetry tests</title>
<style>
:root{color-scheme:dark;font-family:system-ui,sans-serif;background:#10171e;color:#e9f2fa}*{box-sizing:border-box}[hidden]{display:none!important}body{max-width:1180px;margin:auto;padding:24px}h1{font-size:clamp(25px,4vw,38px);margin:6px 0}h2{font-size:21px}p{color:#afc1cf;line-height:1.55}small{color:#afc1cf}.eyebrow{color:#83dfca;letter-spacing:.14em;font-size:12px}.metrics,.views{display:grid;gap:14px}.metrics{grid-template-columns:repeat(auto-fit,minmax(150px,1fr));margin:24px 0}.card,.panel{background:#19232d;border:1px solid #30414e;border-radius:14px;padding:18px}.metric{display:block;font-size:30px;font-variant-numeric:tabular-nums;margin:8px 0}.views{grid-template-columns:1fr 1fr}.panel{min-width:0}canvas{display:block;width:100%;aspect-ratio:4/3;object-fit:contain;background:#080d12;border-radius:8px}button,a.button{display:inline-block;border:0;border-radius:7px;padding:11px 15px;margin:12px 5px 0 0;background:#a2e6d7;color:#13251f;font:inherit;text-decoration:none;cursor:pointer}button:disabled{opacity:.45;cursor:default}button:focus-visible,a:focus-visible{outline:3px solid white;outline-offset:3px}.state{min-height:3em;margin-bottom:0}.details{display:grid;grid-template-columns:1fr auto;gap:9px;margin-top:16px;font-size:14px}.details span:nth-child(even){font-variant-numeric:tabular-nums}pre{white-space:pre-wrap;overflow-wrap:anywhere;color:#bdd1df;font-size:13px}.muted{font-size:13px}details{margin-top:18px}summary{cursor:pointer}.offline{color:#ffce8b}@media(max-width:760px){body{padding:16px}.views{grid-template-columns:1fr}}
.telemetry-values{display:grid;grid-template-columns:repeat(auto-fit,minmax(165px,1fr));gap:12px;margin:16px 0}.value{display:block;font-size:22px;margin-top:6px;font-variant-numeric:tabular-nums}.table-wrap{overflow-x:auto}table{width:100%;border-collapse:collapse;font-size:14px}th,td{text-align:left;padding:12px 10px;border-bottom:1px solid #30414e;white-space:nowrap}th{color:#a2e6d7}.warning{color:#ffce8b}.good{color:#83dfca}select,input{font:inherit;max-width:100%}
.usb-live{display:grid;grid-template-columns:minmax(0,1.15fr) minmax(0,1fr);gap:14px;align-items:start}.usb-live .views{display:block}.usb-live #aruco-panel .telemetry-values{grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.usb-live #aruco-panel .value{font-size:18px}.usb-live #aruco-panel .muted{font-size:11px}.usb-live .panel{padding:14px}.usb-live canvas{max-height:50vh!important}@media(max-width:900px){.usb-live{grid-template-columns:1fr}}
</style>
</head>
<body>
<div class="eyebrow">BSHE27 / GOOUUU ESP32-S3</div><h1>Wi-Fi telemetry and camera tests.</h1>
<p>Start with small telemetry messages. Camera streaming and snapshots are optional, so you can measure the wireless link without downloading video.</p>
<section class="panel" id="telemetry-panel"><h2>Wireless telemetry · no JPEG</h2>
<button id="telemetry-toggle">Start telemetry test</button><label>Poll interval <select id="telemetry-interval"><option value="250">250 ms</option><option value="500" selected>500 ms</option><option value="1000">1 second</option><option value="2000">2 seconds</option></select></label>
<button id="reset-comparison">Reset measurements</button>
<p class="state" id="telemetry-state" role="status">Join BSHE27-Camera to test the wireless link.</p><p id="telemetry-error" class="warning" role="status"></p>
<div class="telemetry-values">
<div><small>Latest HTTP round-trip</small><strong class="value" id="telemetry-rtt">—</strong></div>
<div><small>Last ESP32 reply</small><strong class="value" id="esp-reply-age">—</strong></div>
<div><small>Flight controller link</small><strong class="value" id="fc-link">Unknown</strong></div>
<div><small>Last FC heartbeat</small><strong class="value" id="fc-heartbeat-age">Never seen</strong></div>
<div><small>Armed</small><strong class="value" id="fc-armed">—</strong></div>
<div><small>Flight mode (numeric)</small><strong class="value" id="fc-mode">—</strong></div>
<div><small>Relative altitude</small><strong class="value" id="fc-altitude">—</strong></div>
<div><small>Battery voltage</small><strong class="value" id="fc-battery">—</strong></div>
<div><small>GPS fix / satellites</small><strong class="value" id="fc-gps">—</strong></div>
<div><small>FC heartbeats received</small><strong class="value" id="fc-heartbeats">—</strong></div>
<div><small>UART bytes / bad CRC</small><strong class="value" id="fc-uart">—</strong></div>
<div><small>ESP32 uptime</small><strong class="value" id="esp-uptime">—</strong></div>
<div><small>ESP32 free heap</small><strong class="value" id="esp-heap">—</strong></div>
<div><small>ESP32 free PSRAM</small><strong class="value" id="esp-psram">—</strong></div>
</div><p class="muted">A fresh Wi-Fi reply proves laptop ↔ ESP32 communication. FC connection requires a fresh, valid ArduCopter heartbeat received by the ESP32. Missing or stale FC readings show —. This test only reads data; it does not arm the drone or request flight modes.</p></section>
<div class="metrics">
<div class="card"><small>Board processed</small><strong class="metric" id="board-fps">—</strong><small>FPS · published sensor JPEG frames</small></div>
<div class="card"><small>ESP32 JPEG encoding</small><strong class="metric" id="jpeg-ms">—</strong><small>ms · bypassed with sensor JPEG</small></div>
<div class="card"><small>JPEG size</small><strong class="metric" id="jpeg-size">—</strong><small>KiB per received frame</small></div>
<div class="card"><small>Capture wait</small><strong class="metric" id="capture-ms">—</strong><small>milliseconds waiting for driver</small></div>
</div>
<div class="views">
<section class="panel" id="wifi-panel"><h2>Optional Wi-Fi camera</h2><canvas hidden id="wifi-image" width="320" height="240" aria-label="Wi-Fi camera feed"></canvas>
<button id="wifi-toggle">Start video</button><button id="snapshot">Get latest snapshot</button>
<div class="details"><span>Browser displayed</span><span id="wifi-fps">0.0 FPS</span><span>Request → decoded image</span><span id="wifi-ms">—</span><span>Received JPEG data</span><span id="wifi-kbps">0 kB/s</span><span>Frame age when sent</span><span id="wifi-age">—</span></div>
<p class="state" id="wifi-state" role="status">Video off · no JPEG requests</p>
<details id="snapshot-panel" hidden open><summary>Latest snapshot · not live video</summary><canvas id="snapshot-image" width="320" height="240" aria-label="Latest Wi-Fi snapshot"></canvas><p id="snapshot-state" role="status">No snapshot requested.</p></details></section>
<section class="panel"><h2>USB-C live camera</h2>
<button id="usb-toggle">Connect USB</button><button id="usb-save" disabled>Save JPEG</button><button id="usb-fullscreen">Full screen</button>
<label><input type="checkbox" id="aruco-enabled" checked> ESP32 ArUco overlay</label>
<details open style="margin:8px 0"><summary>Simulated altitude → image detail and frame rate</summary>
<label><input type="checkbox" id="altitude-enabled"> Enable altitude simulation</label><br>
<label for="altitude-slider">Simulated height <strong id="altitude-value">1.0 m</strong></label>
<input type="range" id="altitude-slider" min="0" max="20" step="0.1" value="1" style="width:100%">
<p id="altitude-state" class="muted" role="status">Simulation off · original QVGA camera settings.</p>
<p id="profile-live" class="good">Waiting for frame settings.</p>
<details><summary>Profile bands and behavior</summary><p class="muted">0–2 m: 320×240, JPEG Q28, up to 20 FPS · 2–8 m: 640×480, Q20, 8 FPS · 8–20 m: 1024×768, Q10, 2 FPS. Smaller JPEG Q means higher quality. Rates are publishing targets; actual FPS is measured below. Moving the slider enables simulation and selects raw video so ArUco processing does not cap the visible frame rate. This uses no barometer or FC altitude.</p></details></details>
<canvas id="usb-image" width="320" height="240" style="max-height:65vh" aria-label="USB camera feed"></canvas>
<div class="details"><span>Browser displayed</span><span id="usb-fps">0.0 FPS</span><span>Request → decoded image</span><span id="usb-ms">—</span><span>Received JPEG data</span><span id="usb-kbps">0 kB/s</span><span>Frame age when sent</span><span id="usb-age">—</span><span>Automatic recoveries</span><span id="usb-recoveries">0</span></div>
<p class="state" id="usb-state" role="status">Use the board's native USB-C port, not the TTL/CH340 port.</p></section>
</div>
<button id="compare-toggle" hidden>Show Wi-Fi comparison</button>
<p class="muted" id="usb-session" role="status">No USB frames received yet.</p>
<section class="panel" id="aruco-panel"><h2>Onboard ArUco · command preview</h2>
<p id="aruco-state" class="warning" role="status">Connect USB to receive ESP32 detection results.</p>
<p id="aruco-config" class="warning">PLACEHOLDER calibration and marker size. Measurements and commands are illustrative. Nothing is sent to the flight controller.</p>
<div class="telemetry-values">
<div><small>Marker</small><strong class="value" id="aruco-id">—</strong></div>
<div><small>Camera → marker distance</small><strong class="value" id="aruco-distance">—</strong></div>
<div><small>Optical depth (camera Z)</small><strong class="value" id="aruco-depth">—</strong></div>
<div><small>Marker in camera X / Y / Z</small><strong class="value" id="aruco-position">—</strong></div>
<div><small>Camera in marker X / Y / Z</small><strong class="value" id="aruco-camera-position">—</strong></div>
<div><small>Marker roll / pitch / yaw</small><strong class="value" id="aruco-angles">—</strong></div>
<div><small>ESP32 processing / JPEG decode</small><strong class="value" id="aruco-ms">—</strong></div>
<div><small>Prepare / shapes / ID / pose</small><strong class="value" id="aruco-stages">&#8212;</strong></div>
<div><small>Analyzed frames / search</small><strong class="value" id="aruco-rate">&#8212;</strong></div>
<div><small>Vision internal / external RAM</small><strong class="value" id="aruco-ram">&#8212;</strong></div>
<div><small>Worker wall busy fraction · one core</small><strong class="value" id="aruco-busy">—</strong></div>
<div><small>Vision workspace / free PSRAM</small><strong class="value" id="aruco-memory">—</strong></div>
<div><small>Free heap / vision stack headroom</small><strong class="value" id="aruco-heap">—</strong></div>
<div><small>Result age when sent / corner fit</small><strong class="value" id="aruco-quality">—</strong></div>
</div><p><strong id="aruco-command">HOLD · no usable marker</strong></p><p id="aruco-velocity">Forward / right / down / yaw rate: —</p>
<p class="muted">Detects your photographed 7×7 marker ID 0 on the ESP32. The browser only draws results. Outline and values belong to the same analyzed JPEG. Camera axes: X right, Y down, Z forward, in the configured detector image. Angles describe marker orientation in that camera frame; they are not drone attitude. Preview assumes a downward camera with image top pointing drone-forward. No arming, MAVLink setpoints or landing command is sent. Wall busy fraction includes blocking/scheduling and is not measured CPU utilization. Uncheck the overlay for the original raw USB video.</p></section>
<section class="panel" style="margin:16px 0"><h2>Wi-Fi comparison</h2>
<p id="test-load">Current load: telemetry stopped; video off.</p>
<div class="table-wrap"><table><thead><tr><th>Wi-Fi request</th><th>OK / failed / timeout</th><th>Success</th><th>Mean RTT</th><th>95th percentile</th><th>Mean payload</th><th>Latency vs telemetry</th><th>Payload vs telemetry</th></tr></thead><tbody id="comparison-body"></tbody></table></div><div class="telemetry-values" id="comparison-summary"></div>
<p class="muted">RTT is the browser request → complete response-body time, before JSON parsing or JPEG decoding. It includes server waiting and transport, not one-way radio latency or full FC-to-screen delay. Percent change = (image − telemetry) ÷ telemetry × 100; multiplier = image ÷ telemetry. Counts cover completed requests since Reset; means and percentiles use the latest 100 successful requests per mode. Request failures (including timeouts or invalid responses) are not raw radio packet-loss measurements. Heartbeat age starts when the ESP32 receives it, not when the FC generates it. Historical results may include different loads: reset before each controlled test. Telemetry continues while video/snapshots run; the camera still captures onboard when video downloads are off.</p></section>
<p class="muted">Board FPS measures completed sensor JPEG frames, not the sensor's theoretical maximum. Browser FPS counts distinct decoded frames, averaged over two seconds. ArUco view is limited by onboard analysis, processing the latest frame without a fixed five-Hz limit. Altitude simulation caps published JPEG frames; it does not set optical exposure time or guarantee the sensor stops capturing between frames. Request time includes waiting for the next frame, transfer and JPEG decoding. JPEG compression runs inside the camera sensor; 0 ms of ESP32 encoding does not mean zero sensor processing time. Multiple viewers share bandwidth.</p>
<section class="panel" style="margin:16px 0"><h2>Exposure and gain</h2>
<fieldset id="camera-controls" disabled style="border:0;padding:0"><label>Exposure (ms) <input id="exposure-ms" type="number" min="0.1" max="20" step="0.1" value="1" style="width:85px;padding:8px"></label>
<label>Gain (×) <input id="gain-x" type="number" min="1" max="15.5" step="0.5" value="4" style="width:85px;padding:8px"></label>
<button id="manual-apply">Apply manual</button><button id="auto-exposure">Restore auto</button><br>
<button id="preset-half">0.5 ms</button><button id="preset-one">1 ms</button><button id="preset-two">2 ms</button></fieldset>
<button id="read-exposure">Read exposure over Wi-Fi</button><p id="exposure-state" role="status">Connect USB or read the settings over Wi-Fi.</p>
<p class="muted">Short exposure reduces motion blur but can darken the image. More gain brightens it and adds noise. Presets apply manual exposure with the gain shown above. Auto restores automatic exposure and gain; night-mode frame extension stays off. Values are calculated from sensor register readback, not an optical shutter measurement. Settings reset to Auto on reboot.</p></section>
<details open><summary>Connect a wired laptop</summary><p>Use a data-capable cable in the board's native USB-C socket (the one connected to the ESP32-S3, often marked USB). The TTL/CH340 socket remains available for uploading and the console. Open the offline viewer in desktop Edge or Chrome, click Connect USB, and choose <strong>USB JTAG/serial debug unit</strong> / the Espressif device. Wi-Fi is not needed for USB viewing. This is a browser viewer, not a Windows webcam device.</p><a class="button" id="download" href="/viewer" download="BSHE27-USB-viewer.html">Download offline USB viewer</a><p class="muted" id="usb-help">If USB permission is unavailable on this Wi-Fi page, download the viewer and open that saved HTML file in Edge or Chrome. The USB interface supports video, ArUco preview and camera exposure/gain; it cannot start a flight mission. Video delivery pauses during missions.</p></details>
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
let pendingProfile=null,profileTimer=null,profileInFlight=false,visionBeforeSimulation=false,simulationWasEnabled=false;
function profileBody(){const b=new Uint8Array(3);b[0]=$('altitude-enabled').checked?1:0;new DataView(b.buffer).setUint16(1,Math.round(Number($('altitude-slider').value)*100),true);return b;}
function showProfile(p){$('altitude-state').textContent=p.ok?(p.enabled?'Applied '+p.altitude_m.toFixed(1)+' m simulation · '+p.width+'×'+p.height+' · JPEG Q'+p.quality+' · target '+p.target_fps+' FPS.':'Simulation off · original camera settings restored.'):(p.error||'Camera profile failed.');}
async function wifiProfile(){if(profileInFlight)return;profileInFlight=true;try{while(pendingProfile&&!usbPlaying){const body=pendingProfile;pendingProfile=null;const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),5000);try{const r=await fetch(wifiOrigin+'/camera-profile',{method:'POST',body,signal:controller.signal});if(!r.ok)throw new Error('Camera profile HTTP '+r.status);showProfile(await r.json());}finally{clearTimeout(timer);}}}catch(e){$('altitude-state').textContent=e.message;}finally{profileInFlight=false;}}
function queueProfile(){
 clearTimeout(profileTimer);$('altitude-value').textContent=Number($('altitude-slider').value).toFixed(1)+' m';
 if($('altitude-enabled').checked){if(!simulationWasEnabled)visionBeforeSimulation=$('aruco-enabled').checked;$('aruco-enabled').checked=false;lastVisionAt=0;clearVision('Raw altitude preview · ArUco continues onboard.');}
 else if(simulationWasEnabled)$('aruco-enabled').checked=visionBeforeSimulation;
 simulationWasEnabled=$('altitude-enabled').checked;
 $('altitude-state').textContent=usbPlaying||!standalone?'Applying latest slider setting…':'Connect USB to apply the selected simulation.';
 profileTimer=setTimeout(()=>{pendingProfile=profileBody();if(!usbPlaying&&!standalone)wifiProfile();},200);
}
$('altitude-slider').oninput=()=>{$('altitude-enabled').checked=true;queueProfile();};$('altitude-enabled').onchange=queueProfile;
let lastVisionAt=0,visionExpiresAt=0;
function clearVision(reason,clearMetrics=true){for(const id of ['aruco-id','aruco-distance','aruco-depth','aruco-position','aruco-camera-position','aruco-angles'])$(id).textContent='—';if(clearMetrics)for(const id of ['aruco-ms','aruco-stages','aruco-rate','aruco-ram','aruco-busy','aruco-memory','aruco-heap','aruco-quality'])$(id).textContent='—';$('aruco-state').textContent=reason;$('aruco-command').textContent='HOLD · no usable marker';$('aruco-velocity').textContent='Forward / right / down / yaw rate: —';}
function showVision(v,ctx,requestMs=0){
 lastVisionAt=performance.now();const remaining=(v.max_age_ms||700)-v.age_ms-requestMs;visionExpiresAt=lastVisionAt+Math.max(0,remaining);
 $('aruco-config').textContent=(v.placeholder?'PLACEHOLDER calibration':'Calibrated intrinsics')+' · black square '+v.marker_side_m.toFixed(3)+' m · test height '+v.target_height_m.toFixed(2)+' m · '+(v.mount_verified?'mount verified':'MOUNT UNVERIFIED')+' · preview only, no commands transmitted.';
 $('aruco-ms').textContent=v.processing_ms.toFixed(1)+' / '+v.decode_ms.toFixed(1)+' ms';$('aruco-busy').textContent=v.worker_busy_percent.toFixed(1)+'%';$('aruco-memory').textContent=(v.workspace_bytes/1024).toFixed(0)+' KiB / '+(v.psram_free/1048576).toFixed(2)+' MiB';$('aruco-heap').textContent=(v.heap_free/1024).toFixed(0)+' KiB / '+v.stack_free_bytes+' B';$('aruco-quality').textContent=v.age_ms+' ms / '+v.reprojection_px.toFixed(2)+' px';
 const stageTimes=[v.prepare_ms,v.search_ms,v.identify_ms,v.pose_ms];
 $('aruco-stages').textContent=stageTimes.every(Number.isFinite)?stageTimes.map(n=>n.toFixed(1)).join(' / ')+' ms':'\u2014';
 $('aruco-rate').textContent=Number.isFinite(v.analysis_fps)?v.analysis_fps.toFixed(1)+' FPS / '+(v.tracked_search?'tracking':'full image'):'\u2014';
 $('aruco-ram').textContent=Number.isFinite(v.internal_workspace_bytes)&&Number.isFinite(v.external_workspace_bytes)?(v.internal_workspace_bytes/1024).toFixed(0)+' / '+(v.external_workspace_bytes/1024).toFixed(0)+' KiB':'\u2014';
 if(!v.fresh||remaining<=0||!v.detected){clearVision(v.error||(!v.fresh||remaining<=0?'ArUco result stale or unavailable.':'Searching for 7×7 ID 0.'),!v.fresh||remaining<=0);return;}
 $('aruco-id').textContent='7×7 · ID '+v.marker_id;
 if(ctx&&Array.isArray(v.corners)&&v.corners.length===4){ctx.strokeStyle='#83ffb1';ctx.lineWidth=2;ctx.beginPath();v.corners.forEach((p,i)=>i?ctx.lineTo(...p):ctx.moveTo(...p));ctx.closePath();ctx.stroke();ctx.fillStyle='#ffce8b';ctx.beginPath();ctx.arc(...v.corners[0],4,0,2*Math.PI);ctx.fill();ctx.font='12px sans-serif';ctx.fillText('ID '+v.marker_id,v.corners[0][0]+5,v.corners[0][1]-5);}
 if(!v.pose_valid){clearVision('Marker decoded; pose rejected by geometry check.',false);return;}
 $('aruco-state').textContent='ESP32 decoded ID '+v.marker_id+' · '+v.bit_errors+' corrected bit(s).';
 $('aruco-distance').textContent=v.distance_m.toFixed(3)+' m';$('aruco-depth').textContent=v.depth_m.toFixed(3)+' m';
 $('aruco-position').textContent=v.marker_in_camera_m.map(n=>n.toFixed(3)).join(' / ')+' m';$('aruco-camera-position').textContent=v.camera_in_marker_m.map(n=>n.toFixed(3)).join(' / ')+' m';$('aruco-angles').textContent=v.rpy_deg.map(n=>n.toFixed(1)).join(' / ')+'°';
 $('aruco-command').textContent='PREVIEW: '+v.command;$('aruco-velocity').textContent='Forward / right / down: '+v.body_velocity_mps.map(n=>n.toFixed(2)).join(' / ')+' m/s · yaw '+v.yaw_rate_deg_s.toFixed(1)+'°/s';
}
setInterval(()=>{if(lastVisionAt&&performance.now()>visionExpiresAt){clearVision('USB vision stale · displayed image may be old.');lastVisionAt=0;}},100);
let telemetryPlaying=false,telemetrySession=0,telemetryAbort=null,telemetryLast=null,telemetryError='',snapshotRunning=false;
let measurementResetAt=performance.now();
const measurements=Object.fromEntries(['telemetry','snapshot','video'].map(k=>[k,{ok:0,failed:0,timeouts:0,samples:[]} ]));
function recordMeasure(kind,ms,bytes,started=performance.now()){
 if(started<measurementResetAt)return;
 const m=measurements[kind];m.ok++;m.samples.push({ms,bytes});if(m.samples.length>100)m.samples.shift();renderComparison();
}
function recordFailure(kind,error,started=performance.now()){
 if(started<measurementResetAt)return;
 const m=measurements[kind];m.failed++;if(error.name==='AbortError')m.timeouts++;renderComparison();
}
function summary(kind){const m=measurements[kind],n=m.samples.length,sorted=m.samples.map(s=>s.ms).sort((a,b)=>a-b);return {...m,n,mean:n?m.samples.reduce((a,s)=>a+s.ms,0)/n:null,bytes:n?m.samples.reduce((a,s)=>a+s.bytes,0)/n:null,p95:n?sorted[Math.ceil(n*.95)-1]:null};}
function comparison(value,baseline,noun){if(!Number.isFinite(value)||!Number.isFinite(baseline)||baseline<=0)return '—';const ratio=value/baseline,pct=(ratio-1)*100;return Math.abs(pct).toFixed(1)+'% '+(pct>=0?'higher':'lower')+' · '+ratio.toFixed(2)+'× '+noun;}
function renderComparison(){
 const base=summary('telemetry');
 $('comparison-body').innerHTML=['telemetry','snapshot','video'].map((kind,i)=>{const m=summary(kind),completed=m.ok+m.failed;return '<tr><td>'+['Telemetry JSON','Latest snapshot','Streaming frames'][i]+'</td><td>'+m.ok+' / '+m.failed+' / '+m.timeouts+'</td><td>'+(completed?(100*m.ok/completed).toFixed(1)+'%':'—')+'</td><td>'+(m.n?m.mean.toFixed(1)+' ms':'—')+'</td><td>'+(m.n?m.p95.toFixed(1)+' ms':'—')+'</td><td>'+(m.n?m.bytes.toFixed(0)+' B':'—')+'</td><td>'+(i?comparison(m.mean,base.mean,'latency'):'Baseline')+'</td><td>'+(i?comparison(m.bytes,base.bytes,'payload'):'Baseline')+'</td></tr>';}).join('');
 $('comparison-summary').innerHTML=['snapshot','video'].map((kind,i)=>{const m=summary(kind);return '<div><strong>'+['Snapshot','Video frame'][i]+' vs telemetry</strong><p>'+(m.n&&base.n?comparison(m.mean,base.mean,'latency')+'<br>'+comparison(m.bytes,base.bytes,'payload'):'Collect telemetry and '+['snapshot','video'][i]+' samples to compare.')+'</p></div>';}).join('');
 $('test-load').textContent='Current load: '+(telemetryPlaying?'telemetry on':'telemetry stopped')+'; '+(wifiPlaying?'video on':'video off')+(snapshotRunning?'; snapshot in progress':'')+(usbPlaying?'; USB camera also active':'')+'.';
}
$('reset-comparison').onclick=()=>{measurementResetAt=performance.now();for(const m of Object.values(measurements)){m.ok=m.failed=m.timeouts=0;m.samples=[];}$('telemetry-rtt').textContent='—';renderComparison();};
function value(id,v,suffix=''){ $(id).textContent=Number.isFinite(v)?v.toFixed(suffix===' V'||suffix===' m'?2:0)+suffix:'—'; }
function renderHealth(){
 const now=performance.now(),last=telemetryLast,age=last?now-last.at:null;
 const interval=Number($('telemetry-interval').value),s=last?.data;
 const fresh=telemetryPlaying&&last&&age<Math.max(2000,interval*3)&&Number.isFinite(s.seq)&&s.sample_age_ms<1500;
 $('esp-reply-age').textContent=last?(age/1000).toFixed(1)+' s ago':'No reply yet';
 $('telemetry-state').textContent=!telemetryPlaying?'Telemetry test stopped.':!last?(telemetryError?'ESP32 unreachable · no usable reply yet.':'Waiting for an ESP32 reply…'):!fresh?'ESP32 telemetry stale / unreachable.':telemetryError?'Retrying · last ESP32 reply is still recent.':'ESP32 telemetry connected · fresh sample '+s.seq;
 $('telemetry-state').className='state '+(fresh&&!telemetryError?'good':'warning');
 $('telemetry-error').textContent=telemetryError;
 const hb=last&&s.heartbeat_seen&&Number.isFinite(s.heartbeat_age_ms)?s.heartbeat_age_ms+age:null;
 $('fc-heartbeat-age').textContent=hb===null?'Never seen':(hb/1000).toFixed(2)+' s ago';
 const dataFresh=key=>fresh&&Number.isFinite(s[key])&&s[key]+s.sample_age_ms+age<(s.data_timeout_ms||3000);
 const linked=fresh&&hb!==null&&hb<(s.heartbeat_timeout_ms||5000)&&s.linked;
 $('fc-link').textContent=!fresh?'Unknown · no fresh telemetry':!s.heartbeat_seen?'Waiting · never seen':linked?'Connected':'Lost · heartbeat stale';
 $('fc-armed').textContent=linked&&typeof s.armed==='boolean'?(s.armed?'Armed':'Disarmed'):'—';
 value('fc-mode',linked?s.mode:null);value('fc-altitude',linked&&dataFresh('position_age_ms')?s.relative_altitude_m:null,' m');value('fc-battery',linked&&dataFresh('status_age_ms')?s.battery_v:null,' V');
 $('fc-gps').textContent=linked&&dataFresh('gps_age_ms')&&Number.isFinite(s.gps_fix)&&Number.isFinite(s.satellites)?s.gps_fix+' / '+s.satellites:'—';
 value('fc-heartbeats',fresh?s.heartbeats:null);$('fc-uart').textContent=fresh?s.uart_bytes+' / '+s.bad_crc:'—';
 value('esp-uptime',fresh?s.uptime_ms/1000:null,' s');value('esp-heap',fresh?s.heap_free/1024:null,' KiB');value('esp-psram',fresh?s.psram_free/1048576:null,' MiB');
}
function stopTelemetry(){++telemetrySession;telemetryPlaying=false;if(telemetryAbort)telemetryAbort.abort();$('telemetry-toggle').textContent='Start telemetry test';telemetryError='';renderHealth();renderComparison();}
async function telemetryLoop(session){
 while(telemetryPlaying&&session===telemetrySession){
  const started=performance.now(),controller=new AbortController();telemetryAbort=controller;const timer=setTimeout(()=>controller.abort(),3000);
  try{
   const r=await fetch(wifiOrigin+'/telemetry',{cache:'no-store',signal:controller.signal});
   if(!r.ok)throw new Error('Telemetry HTTP '+r.status);
   const bytes=new Uint8Array(await r.arrayBuffer()),received=performance.now();
   const data=JSON.parse(new TextDecoder().decode(bytes));
   if(!Number.isFinite(data.uptime_ms)||!Number.isFinite(data.sample_age_ms))throw new Error('Invalid telemetry response. Upload current firmware.');
   if(!telemetryPlaying||session!==telemetrySession)break;
   telemetryLast={data,at:received};telemetryError='';recordMeasure('telemetry',received-started,bytes.length,started);
   $('telemetry-rtt').textContent=(received-started).toFixed(1)+' ms';$('status').textContent=JSON.stringify(data,null,2);
   if(!usbPlaying&&!wifiPlaying&&Number.isFinite(data.camera_fps))$('board-fps').textContent=data.camera_fps.toFixed(1);
   if(data.mission_active&&wifiPlaying){stopWifi();setState('wifi','Video paused during flight mission.');}
  }catch(error){if(!telemetryPlaying||session!==telemetrySession)break;recordFailure('telemetry',error,started);telemetryError=error.name==='AbortError'?'Telemetry request timed out; retrying.':error.message+' Retrying.';}
  finally{clearTimeout(timer);if(telemetryAbort===controller)telemetryAbort=null;}
  renderHealth();await sleep(Math.max(0,Number($('telemetry-interval').value)-(performance.now()-started)));
 }
}
function startTelemetry(){if(telemetryPlaying)return;telemetryPlaying=true;telemetryError='';$('telemetry-toggle').textContent='Stop telemetry test';renderComparison();telemetryLoop(++telemetrySession);}
$('telemetry-toggle').onclick=()=>telemetryPlaying?stopTelemetry():startTelemetry();
setInterval(()=>{renderHealth();renderComparison();},250);
$('snapshot').onclick=async()=>{
 if(snapshotRunning)return;snapshotRunning=true;$('snapshot').disabled=true;$('snapshot-panel').hidden=false;$('snapshot-state').textContent='Requesting latest snapshot…';renderComparison();
 const started=performance.now(),controller=new AbortController(),timer=setTimeout(()=>controller.abort(),5000);
 try{
  const r=await fetch(videoOrigin.origin+'/capture',{cache:'no-store',signal:controller.signal});if(!r.ok)throw new Error('Snapshot HTTP '+r.status);
  const bytes=new Uint8Array(await r.arrayBuffer()),received=performance.now();const bitmap=await createImageBitmap(new Blob([bytes],{type:'image/jpeg'}));
  const canvas=$('snapshot-image');canvas.width=bitmap.width;canvas.height=bitmap.height;canvas.getContext('2d').drawImage(bitmap,0,0);bitmap.close();recordMeasure('snapshot',received-started,bytes.length,started);
  const age=r.headers.get('X-Frame-Age-Ms');$('snapshot-state').textContent='Snapshot received in '+(received-started).toFixed(1)+' ms · '+bytes.length+' bytes'+(age!==null?' · frame age when sent '+age+' ms':'')+' · '+new Date().toLocaleTimeString()+' · not live video';
 }catch(error){recordFailure('snapshot',error,started);$('snapshot-state').textContent=error.name==='AbortError'?'Snapshot timed out. Telemetry test continues.':error.message;}
 finally{clearTimeout(timer);snapshotRunning=false;$('snapshot').disabled=false;renderComparison();}
};
renderComparison();
function setState(kind,text){$(kind+'-state').textContent=text;}
function metrics(m){$('board-fps').textContent=m.boardFps.toFixed(1);$('jpeg-ms').textContent=(m.jpegUs/1000).toFixed(1);$('jpeg-size').textContent=m.length?(m.length/1024).toFixed(1):'—';$('capture-ms').textContent=(m.captureUs/1000).toFixed(1);}
function parseHeader(bytes){
 if(bytes.length!==48||String.fromCharCode(...bytes.slice(0,4))!=='BSC1')throw new Error('Unexpected camera protocol. Upload the latest firmware.');
 const d=new DataView(bytes.buffer,bytes.byteOffset,bytes.byteLength);
 const m={length:d.getUint32(4,true),id:d.getUint32(8,true),captureUs:d.getUint32(20,true),jpegUs:d.getUint32(24,true),boardFps:d.getFloat32(32,true),age:d.getUint32(40,true),flags:d.getUint32(44,true),width:d.getUint16(36,true),height:d.getUint16(38,true)};
 if(m.length>524288||!Number.isFinite(m.boardFps)||![[320,240],[640,480],[1024,768]].some(([w,h])=>w===m.width&&h===m.height))throw new Error('Invalid camera frame header.');
 const profile=d.getUint32(28,true);if((profile>>>28)===10)m.profile={quality:profile&63,targetFps:(profile>>>6)&31,mode:(profile>>>11)&3,altitudeCm:(profile>>>13)&2047};
 return m;
}
async function draw(kind,m,bytes,started){
 if(m.flags)throw new Error(m.flags&1?'Video paused during flight mission.':'Camera frame unavailable. Check board status.');
 if(m.length!==bytes.length||!m.length)throw new Error('Incomplete camera image.');
 const blob=new Blob([bytes],{type:'image/jpeg'}),bitmap=await createImageBitmap(blob);
 if(bitmap.width!==m.width||bitmap.height!==m.height){bitmap.close();throw new Error('JPEG dimensions do not match frame header.');}
 if((kind==='usb'&&!usbPlaying)||(kind==='wifi'&&!wifiPlaying)){bitmap.close();return;}
 const canvas=$(kind+'-image');if(canvas.width!==m.width||canvas.height!==m.height){canvas.width=m.width;canvas.height=m.height;}
 const ctx=canvas.getContext('2d');ctx.drawImage(bitmap,0,0,m.width,m.height);bitmap.close();
 if(m.profile)$('profile-live').textContent='Actual frame: '+m.width+'×'+m.height+' · JPEG Q'+m.profile.quality+' · '+(m.profile.targetFps?'target '+m.profile.targetFps+' FPS':'unpaced')+' · '+(m.profile.mode?(m.profile.altitudeCm/100).toFixed(1)+' m simulated':'simulation off')+' · measured '+m.boardFps.toFixed(1)+' board FPS';
 if(kind==='usb'&&m.vision&&$('aruco-enabled').checked)showVision(m.vision,ctx,performance.now()-m.visionReceivedAt+20);
 const t=trackers[kind];t.blob=blob;
 const signature=[m.width,m.height,m.profile?.quality,m.profile?.targetFps,m.profile?.mode].join('/');if(t.profileSignature!==signature){t.samples=[];t.profileSignature=signature;$(kind+'-fps').textContent='Updating…';}
 if(kind==='usb'){if(t.lastId!==m.id)++t.total;t.lastAt=performance.now();}
 if(t.lastId!==m.id){t.samples.push({at:performance.now(),bytes:bytes.length});t.lastId=m.id;}
 metrics(m);$(kind+'-ms').textContent=(performance.now()-started).toFixed(0)+' ms';$(kind+'-age').textContent=m.age+' ms';
 setState(kind,'Connected · frame '+m.id+' · '+(bytes.length/1024).toFixed(1)+' KiB');
 if(kind==='usb')$('usb-save').disabled=false;
}
setInterval(()=>{const now=performance.now();for(const kind of ['wifi','usb']){const t=trackers[kind];t.samples=t.samples.filter(s=>now-s.at<2000);$(kind+'-fps').textContent=(t.samples.length/2).toFixed(1)+' FPS';$(kind+'-kbps').textContent=(t.samples.reduce((a,s)=>a+s.bytes,0)/2000).toFixed(1)+' kB/s';}
 const t=trackers.usb;if(t.started){const age=t.lastAt?now-t.lastAt:now-t.started;$('usb-session').textContent=t.total+' frames displayed · '+Math.floor((now-t.started)/1000)+' seconds since connection'+(usbPlaying&&age>2000?' · Waiting for fresh video; the displayed picture is stale.':!usbPlaying?' · Disconnected; showing last picture.':' · Live');}
},500);
function stopWifi(){++wifiSession;wifiPlaying=false;if(wifiAbort)wifiAbort.abort();$('wifi-toggle').textContent='Start video';setState('wifi','Stopped');}
async function wifiLoop(session){
 while(wifiPlaying&&session===wifiSession){
  const started=performance.now();const controller=new AbortController();wifiAbort=controller;const timeout=setTimeout(()=>controller.abort(),5000);
  try{
   const response=await fetch(videoOrigin.origin+'/frame?after='+(trackers.wifi.lastId||0),{cache:'no-store',signal:controller.signal});
   if(!response.ok)throw new Error(response.status===503?'Camera unavailable or mission running.':'HTTP '+response.status);
   const bytes=new Uint8Array(await response.arrayBuffer()),receivedAt=performance.now();
   if(!wifiPlaying||session!==wifiSession)break;
   if(bytes.length<48)throw new Error('Incomplete camera frame.');
   if(parseHeader(bytes.slice(0,48)).flags)throw new Error('Camera frame unavailable.');
   await draw('wifi',parseHeader(bytes.slice(0,48)),bytes.slice(48),started);
   if(wifiPlaying&&session===wifiSession)recordMeasure('video',receivedAt-started,bytes.length,started);
  }catch(error){if(!wifiPlaying||session!==wifiSession)break;recordFailure('video',error,started);setState('wifi',error.name==='AbortError'?'Wi-Fi request timed out. Reconnecting…':error.message+' Reconnecting…');await sleep(1000);}
  finally{clearTimeout(timeout);if(wifiAbort===controller)wifiAbort=null;}
 }
}
$('wifi-toggle').onclick=()=>{if(wifiPlaying)stopWifi();else{wifiPlaying=true;$('wifi-image').hidden=false;$('wifi-toggle').textContent='Stop video';wifiLoop(++wifiSession);}};
async function readExact(count){
 while(serialBuffer.length<count){const r=await reader.read();if(r.done)throw new Error('USB disconnected.');const joined=new Uint8Array(serialBuffer.length+r.value.length);joined.set(serialBuffer);joined.set(r.value,serialBuffer.length);serialBuffer=joined;if(serialBuffer.length>600000)throw new Error('USB buffer overflow. Reconnect.');}
 const bytes=serialBuffer.slice(0,count);serialBuffer=serialBuffer.slice(count);return bytes;
}
async function readPacket(){
 let magic=await readExact(4),skipped=0;
 while(String.fromCharCode(...magic)!=='BSC1'){if(++skipped>524288)throw new Error('USB protocol out of sync. Reconnect.');const next=await readExact(1);magic=new Uint8Array([magic[1],magic[2],magic[3],next[0]]);}
 const h=new Uint8Array(48);h.set(magic);h.set(await readExact(44),4);const m=parseHeader(h);return {m,bytes:await readExact(m.length)};
}
async function readVisionPacket(){
 const h=await readExact(8);if(String.fromCharCode(...h.slice(0,4))!=='BSV1')throw new Error('ArUco requires updated ESP32 firmware. Uncheck overlay for raw video.');
 const metadataAt=performance.now(); // Excludes waiting for the next analyzed frame.
 const length=new DataView(h.buffer,h.byteOffset,h.byteLength).getUint32(4,true);if(!length||length>4096)throw new Error('Invalid ArUco response length.');
 const vision=JSON.parse(new TextDecoder().decode(await readExact(length))),packet=await readPacket();
 if(vision.frame_id!==packet.m.id)throw new Error('ArUco result/frame mismatch.');
 const finiteArray=(a,n)=>Array.isArray(a)&&a.length===n&&a.every(Number.isFinite);
 const fields=['frame_id','age_ms','marker_side_m','target_height_m','processing_ms','decode_ms','worker_busy_percent','workspace_bytes','heap_free','psram_free','stack_free_bytes','reprojection_px'];
 if(!fields.every(k=>Number.isFinite(vision[k]))||typeof vision.fresh!=='boolean'||typeof vision.detected!=='boolean'||typeof vision.pose_valid!=='boolean'||
    (vision.detected&&(!Array.isArray(vision.corners)||vision.corners.length!==4||!vision.corners.every(p=>finiteArray(p,2))))||
    (vision.pose_valid&&(!finiteArray(vision.marker_in_camera_m,3)||!finiteArray(vision.camera_in_marker_m,3)||!finiteArray(vision.rpy_deg,3)||!Number.isFinite(vision.distance_m)||!Number.isFinite(vision.depth_m)))||
    !finiteArray(vision.body_velocity_mps,3)||!Number.isFinite(vision.yaw_rate_deg_s))throw new Error('Invalid ArUco metadata.');
 packet.m.vision=vision;packet.m.visionReceivedAt=metadataAt;return packet;
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
async function readProfile(){const h=await readExact(8);if(String.fromCharCode(...h.slice(0,4))!=='BSP1')throw new Error('Altitude simulation requires updated ESP32 firmware.');const n=new DataView(h.buffer,h.byteOffset,h.byteLength).getUint32(4,true);if(!n||n>4096)throw new Error('Invalid profile response.');return JSON.parse(new TextDecoder().decode(await readExact(n)));}
async function timedPacket(request,settings=false){
 let timer;const pending=(async()=>{await writer.write(request);return settings?readSettings():request[0]===65?readProfile():request[0]===86?readVisionPacket():readPacket();})();
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
 usbPlaying=false;pendingSettings=null;pendingProfile=null;controlsBusy=false;lastVisionAt=0;clearVision('USB disconnected.');$('camera-controls').disabled=standalone;await releaseUsb();port=null;$('usb-toggle').textContent='Connect USB';
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
  usbPlaying=true;pendingProfile=profileBody();let failures=0,recoveries=0;
  $('usb-toggle').textContent='Disconnect USB';$('usb-toggle').disabled=false;
  while(usbPlaying){
   try{
    if(!reader)await openUsb();
    if(!usbPlaying)break;
    if(pendingProfile){const body=pendingProfile;pendingProfile=null;const command=new Uint8Array([65,...body]);showProfile(await timedPacket(command));}
    if(pendingSettings || !lastSettingsAt || performance.now()-lastSettingsAt>1000){
     const body=pendingSettings;pendingSettings=null;const command=body?new Uint8Array([67,...body]):new Uint8Array([83]);
     showSettings(await timedPacket(command,true),!!body);lastSettingsAt=performance.now();
    }
    const started=performance.now(),request=new Uint8Array(5);request[0]=$('aruco-enabled').checked?86:70;new DataView(request.buffer).setUint32(1,trackers.usb.lastId||0,true);
    const packet=await timedPacket(request);
    if(!usbPlaying)break;
    if(packet.m.flags){if(packet.m.vision)showVision(packet.m.vision,null);failures=0;setState('usb',packet.m.flags&1?'Video paused during flight mission.':'Camera frame unavailable.');await sleep(500);continue;}
    await draw('usb',packet.m,packet.bytes,started);failures=0;
   }catch(error){
    if(!usbPlaying)break;
    clearVision(error.message);lastVisionAt=0;
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
$('aruco-enabled').onchange=()=>{lastVisionAt=0;clearVision($('aruco-enabled').checked?'Waiting for ESP32 ArUco result.':'ArUco overlay off · raw USB video.');};
$('usb-save').onclick=()=>{const blob=trackers.usb.blob;if(!blob)return;const a=document.createElement('a'),url=URL.createObjectURL(blob);a.href=url;a.download='BSHE27-'+Date.now()+'.jpg';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
$('usb-fullscreen').onclick=async()=>{try{await $('usb-image').requestFullscreen();}catch(error){setState('usb','Full screen unavailable: '+error.message);}};
$('compare-toggle').onclick=()=>{const panel=$('wifi-panel');panel.hidden=!panel.hidden;document.querySelector('.views').style.gridTemplateColumns=panel.hidden?'1fr':'';$('compare-toggle').textContent=panel.hidden?'Show Wi-Fi comparison':'Hide Wi-Fi comparison';};
$('read-exposure').onclick=async()=>{const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),3000);try{const r=await fetch(wifiOrigin+'/camera-control',{cache:'no-store',signal:controller.signal});if(!r.ok)throw new Error('HTTP '+r.status);showSettings(await r.json());}catch(error){$('exposure-state').textContent=error.message;}finally{clearTimeout(timer);}};
if(standalone){const views=document.querySelector(".views"),live=document.createElement("div");live.className="usb-live";document.body.insertBefore(live,$("telemetry-panel"));live.append(views,$("aruco-panel"));live.after($("usb-session"));document.title='BSHE27 · USB-C live camera';document.querySelector('h1').textContent='Live camera over USB-C.';document.querySelector('h1+p').textContent='Connect the board’s OTG USB-C socket, click Connect USB, and select the Espressif USB serial device. Video continues until you disconnect. No Wi-Fi or internet is required.';$('wifi-panel').hidden=true;document.querySelector('.views').style.gridTemplateColumns='1fr';$('compare-toggle').hidden=false;$('download').hidden=true;$('status').textContent='USB viewer works without Wi-Fi. Pixhawk status remains on the board dashboard.';setState('wifi','Optional: join BSHE27-Camera, then start Wi-Fi to compare.');}
else{$('camera-controls').disabled=false;startTelemetry();}
if(!navigator.serial)setState('usb','Download the offline USB viewer, then open it in desktop Edge or Chrome.');
window.addEventListener('pagehide',()=>{stopTelemetry();stopWifi();closeUsb();});
</script>
</body></html>
)BSC_HTML";
