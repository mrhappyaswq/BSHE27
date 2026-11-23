const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {pathToFileURL}=require('node:url');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
(async()=>{
 const root=path.resolve(__dirname,'../..');
 const html=fs.readFileSync(path.join(root,'data/viewer.html'),'utf8').replace(/^\uFEFF/,'');
 const embedded=fs.readFileSync(path.join(root,'include/dashboard_page.h'),'utf8');
 assert.equal(embedded.split('R"BSC_HTML(')[1].split(')BSC_HTML"')[0],html,'firmware and offline viewer must match');
 const browser=await chromium.launch({channel:'msedge',headless:true});
 const errors=[];
 try{
  const context=await browser.newContext({acceptDownloads:true});
  const page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));
  const jpeg=Buffer.from(await page.evaluate(()=>{const c=document.createElement('canvas');c.width=320;c.height=240;const x=c.getContext('2d');x.fillStyle='#238572';x.fillRect(0,0,320,240);return c.toDataURL('image/jpeg').split(',')[1];}),'base64');
  let id=0,fail=false,mission=false,telemetryFail=false,telemetryStall=false,heartbeatSeen=false,heartbeatAge=50,staleSample=false,images=0,telemetryRequests=0;
  const settings={ok:true,manual:false,exposure_ms:8,gain:2,row_us:32,frame_period_ms:36,max_exposure_ms:20,night_mode:false};
  function packet(){const h=Buffer.alloc(48);h.write('BSC1');h.writeUInt32LE(jpeg.length,4);h.writeUInt32LE(++id,8);h.writeUInt32LE(1000,12);h.writeUInt32LE(1100,16);h.writeUInt32LE(1234,20);h.writeUInt32LE(0,24);h.writeUInt32LE(0,28);h.writeFloatLE(12.5,32);h.writeUInt16LE(320,36);h.writeUInt16LE(240,38);h.writeUInt32LE(100,40);return Buffer.concat([h,jpeg]);}
  await page.route('http://camera.test/**',async route=>{
   const url=new URL(route.request().url());
   if(url.pathname==='/telemetry'){
    ++telemetryRequests;await new Promise(r=>setTimeout(r,telemetryStall?3300:15));
    const linked=heartbeatSeen&&heartbeatAge<5000;
    try{return await route.fulfill({status:telemetryFail?503:200,json:{seq:telemetryRequests,uptime_ms:12345,sample_age_ms:staleSample?2000:20,heartbeat_seen:heartbeatSeen,heartbeat_age_ms:heartbeatSeen?heartbeatAge:null,heartbeat_timeout_ms:5000,linked,armed:linked?false:null,mode:linked?4:null,relative_altitude_m:linked?1.25:null,battery_v:linked?12.3:null,gps_fix:linked?3:null,satellites:linked?12:null,position_age_ms:30,status_age_ms:40,gps_age_ms:50,data_timeout_ms:3000,heartbeats:heartbeatSeen?42:0,uart_bytes:1200,bad_crc:0,heap_free:150000,psram_free:7340032,camera_fps:12.5,mission_active:mission,camera_error:''}});}catch{return;}
   }
   if(url.pathname==='/camera-control')return route.fulfill({json:settings});
   if(url.pathname==='/status')return route.fulfill({json:{mission_active:mission,camera_error:'',camera:{board_fps:12.5,capture_wait_ms:1.234,jpeg_ms:0,jpeg_bytes:jpeg.length}}});
   return route.fulfill({contentType:'text/html',body:html});
  });
  await page.route('http://camera.test:81/**',async route=>{++images;await new Promise(r=>setTimeout(r,40));const snapshot=new URL(route.request().url()).pathname==='/capture';return route.fulfill({status:fail?503:200,contentType:fail?'text/plain':snapshot?'image/jpeg':'application/octet-stream',headers:{'Access-Control-Allow-Origin':'*','Access-Control-Expose-Headers':'X-Frame-Age-Ms','X-Frame-Age-Ms':'100'},body:fail?'Unavailable':snapshot?jpeg:packet()});});
  await page.goto('http://camera.test/');
  await page.waitForFunction(()=>document.querySelector('#fc-link').textContent.includes('never seen'));
  await page.waitForTimeout(350);assert.equal(images,0,'telemetry-only startup must not download any JPEG');
  assert.equal(await page.locator('#fc-armed').innerText(),'—');
  heartbeatSeen=true;await page.waitForFunction(()=>document.querySelector('#fc-link').textContent==='Connected');
  assert.equal(await page.locator('#fc-armed').innerText(),'Disarmed');
  assert.equal(await page.locator('#fc-battery').innerText(),'12.30 V');
  heartbeatAge=6000;await page.waitForFunction(()=>document.querySelector('#fc-link').textContent.startsWith('Lost'));
  assert.equal(await page.locator('#fc-armed').innerText(),'—');
  heartbeatAge=50;await page.waitForFunction(()=>document.querySelector('#fc-link').textContent==='Connected');
  staleSample=true;await page.waitForFunction(()=>document.querySelector('#telemetry-state').textContent.includes('stale'));
  assert.equal(await page.locator('#fc-mode').innerText(),'—');staleSample=false;
  await page.waitForFunction(()=>document.querySelector('#fc-link').textContent==='Connected');
  telemetryStall=true;await page.waitForFunction(()=>measurements.telemetry.timeouts>0,null,{timeout:7000});
  assert.equal(await page.locator('#fc-armed').innerText(),'—');telemetryStall=false;
  await page.waitForFunction(()=>document.querySelector('#fc-link').textContent==='Connected');
  await page.locator('#snapshot').click();await page.waitForFunction(()=>measurements.snapshot.ok===1);
  assert.equal(images,1,'snapshot makes exactly one image request');
  assert.equal(await page.evaluate(()=>measurements.video.ok),0);
  assert((await page.locator('#snapshot-state').innerText()).includes('not live video'));
  assert.equal(await page.evaluate(()=>comparison(250,100,'latency')),'150.0% higher · 2.50× latency');
  assert.equal(await page.evaluate(()=>comparison(50,100,'payload')),'50.0% lower · 0.50× payload');
  await page.locator('#wifi-toggle').click();
  await page.waitForFunction(()=>document.querySelector('#wifi-state').textContent.startsWith('Connected'));
  assert.equal(await page.locator('#board-fps').innerText(),'12.5');
  assert.equal(await page.locator('#jpeg-ms').innerText(),'0.0');
  await page.waitForFunction(()=>parseFloat(document.querySelector('#wifi-fps').textContent)>0);
  await page.locator('#wifi-toggle').click();
  await page.waitForTimeout(100);assert.equal(await page.locator('#wifi-state').innerText(),'Stopped');
  const beforeFailure=telemetryRequests;fail=true;await page.locator('#wifi-toggle').click();await page.getByText('Camera unavailable or mission running. Reconnecting…',{exact:true}).waitFor();
  assert(telemetryRequests>=beforeFailure,'telemetry remains independent of failed video');fail=false;await page.waitForFunction(()=>document.querySelector('#wifi-state').textContent.startsWith('Connected'));
  mission=true;await page.getByText('Video paused during flight mission.',{exact:true}).waitFor();
  mission=false;await page.screenshot({path:path.resolve('local/wifi-telemetry-comparison.png'),fullPage:true});await page.locator('#reset-comparison').click();assert.equal(await page.evaluate(()=>measurements.snapshot.ok+measurements.video.ok),0);await page.setViewportSize({width:390,height:844});
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'mobile layout must fit');
  await page.screenshot({path:path.resolve('local/camera-speed-mobile.png'),fullPage:true});
  await page.screenshot({path:path.resolve('local/wifi-telemetry-dashboard.png'),fullPage:true});
  await page.close();
  const usb=await context.newPage();usb.on('pageerror',e=>errors.push(e.message));
  await usb.goto(pathToFileURL(path.join(root,'data/viewer.html')).href);
  const jpegs=await usb.evaluate(()=>Object.fromEntries([320,640,1024].map(w=>{const c=document.createElement('canvas');c.width=w;c.height=w*3/4;c.getContext('2d').fillRect(0,0,c.width,c.height);return [w,Array.from(atob(c.toDataURL('image/jpeg').split(',')[1]),x=>x.charCodeAt(0))];})));
  assert(await usb.evaluate(()=>isSecureContext&&!!navigator.serial),'local file must support Web Serial in Edge');
  await usb.addInitScript(({jpeg,jpegs})=>{
   let controller,frame=0;
   globalThis.testUsb={paused:false,closed:false,hold:false,detected:true,mismatch:false,rawRequests:0,visionRequests:0,changes:0,settings:{ok:true,manual:false,exposure_ms:8,gain:2,row_us:32,frame_period_ms:36,max_exposure_ms:20,night_mode:false}};
   testUsb.profile={enabled:false,altitude_m:0,width:320,height:240,quality:20,target_fps:0,mode:0};testUsb.profileChanges=[];
   Object.defineProperty(navigator,'serial',{configurable:true,value:{requestPort:async()=>({
    open:async()=>{},setSignals:async()=>{},close:async()=>{testUsb.closed=true;},
    readable:new ReadableStream({start(c){controller=c;},cancel(){}}),
    writable:new WritableStream({async write(request){
     if(request[0]===65){
      if(request.length!==4)throw new Error('invalid altitude request');const cm=new DataView(request.buffer,request.byteOffset,request.byteLength).getUint16(2,true),enabled=!!request[1];testUsb.profileChanges.push(cm);
      const p=enabled?(cm<200?{width:320,height:240,quality:28,target_fps:20,mode:1}:cm<800?{width:640,height:480,quality:20,target_fps:8,mode:2}:{width:1024,height:768,quality:10,target_fps:2,mode:3}):{width:320,height:240,quality:20,target_fps:0,mode:0};
      testUsb.profile={...p,enabled,altitude_m:enabled?cm/100:0};
      const body=new TextEncoder().encode(JSON.stringify({ok:true,...testUsb.profile})),prefix=new Uint8Array(8);prefix.set([66,83,80,49]);new DataView(prefix.buffer).setUint32(4,body.length,true);controller.enqueue(prefix.slice(0,2));controller.enqueue(prefix.slice(2));controller.enqueue(body);return;
     }
     if(request[0]===83||request[0]===67){
      if(request[0]===67){if(request.length!==8)throw new Error('invalid settings request');const v=new DataView(request.buffer,request.byteOffset,request.byteLength);testUsb.settings.manual=!!request[1];if(request[1]){testUsb.settings.exposure_ms=v.getUint32(2,true)/1000;testUsb.settings.gain=v.getUint16(6,true)/16;}++testUsb.changes;}
      const body=new TextEncoder().encode(JSON.stringify(testUsb.settings)),h=new Uint8Array(8);h.set([66,83,83,49]);new DataView(h.buffer).setUint32(4,body.length,true);controller.enqueue(h.slice(0,3));controller.enqueue(h.slice(3));controller.enqueue(body);return;
     }
     if(![70,86].includes(request[0])||request.length!==5)throw new Error('invalid frame request');
     if(request[0]===86)++testUsb.visionRequests;else ++testUsb.rawRequests;
     while(testUsb.hold)await new Promise(r=>setTimeout(r,20));
     const profile=testUsb.profile,frameJpeg=jpegs[profile.width]||jpeg;
     await new Promise(r=>setTimeout(r,profile.target_fps?1000/profile.target_fps:25));
     const h=new Uint8Array(48),v=new DataView(h.buffer);h.set([66,83,67,49]);
     v.setUint32(4,testUsb.paused?0:frameJpeg.length,true);v.setUint32(8,++frame,true);v.setUint32(20,2000,true);v.setUint32(24,0,true);v.setUint32(28,(0xa0000000|profile.quality|(profile.target_fps<<6)|(profile.mode<<11)|(Math.round(profile.altitude_m*100)<<13))>>>0,true);v.setFloat32(32,profile.target_fps||10,true);v.setUint16(36,profile.width,true);v.setUint16(38,profile.height,true);v.setUint32(40,80,true);v.setUint32(44,testUsb.paused?1:0,true);
     const b=new Uint8Array(48+(testUsb.paused?0:frameJpeg.length));b.set(h);if(!testUsb.paused)b.set(frameJpeg,48);
     if(request[0]===86){
      const body=new TextEncoder().encode(JSON.stringify({frame_id:frame+(testUsb.mismatch?1:0),age_ms:80,max_age_ms:700,heap_free:150000,stack_free_bytes:4096,fresh:true,detected:testUsb.detected&&!testUsb.paused,pose_valid:true,marker_id:0,placeholder:true,mount_verified:false,marker_side_m:.2,target_height_m:.75,corners:[[90,50],[210,50],[210,170],[90,170]],marker_in_camera_m:[.1,-.05,.8],camera_in_marker_m:[-.1,.05,-.8],rpy_deg:[0,15,30],distance_m:.808,depth_m:.8,reprojection_px:.4,bit_errors:0,processing_ms:75,decode_ms:40,worker_busy_percent:37.5,workspace_bytes:919844,psram_free:6000000,command:'ALIGN over marker',body_velocity_mps:[.025,.05,0],yaw_rate_deg_s:15,error:''}));
      const prefix=new Uint8Array(8);prefix.set([66,83,86,49]);new DataView(prefix.buffer).setUint32(4,body.length,true);controller.enqueue(prefix.slice(0,3));controller.enqueue(prefix.slice(3));controller.enqueue(body.slice(0,23));controller.enqueue(body.slice(23));
     }
     try{controller.enqueue(b.slice(0,7));controller.enqueue(b.slice(7,33));controller.enqueue(b.slice(33));}catch{}
    }})
   })}});
  },{jpeg:[...jpeg],jpegs});
  await usb.reload();
  assert.equal(await usb.locator('h1').innerText(),'Live camera over USB-C.');
  assert(await usb.locator('#wifi-panel').isHidden(),'offline viewer starts with only USB video');
  await usb.locator('#compare-toggle').click();assert(await usb.locator('#wifi-panel').isVisible());
  await usb.locator('#compare-toggle').click();assert(await usb.locator('#wifi-panel').isHidden());
  await usb.locator('#usb-toggle').click();
  await usb.waitForFunction(()=>document.querySelector('#usb-state').textContent.startsWith('Connected'));
  assert.equal(await usb.locator('#board-fps').innerText(),'10.0');
  await usb.waitForFunction(()=>trackers.usb.total>=50);
  assert.equal(await usb.locator('#aruco-id').innerText(),'7×7 · ID 0');
  assert.equal(await usb.locator('#aruco-distance').innerText(),'0.808 m');
  assert((await usb.locator('#aruco-command').innerText()).includes('ALIGN over marker'));
  assert((await usb.locator('#aruco-config').innerText()).includes('PLACEHOLDER'));
  assert.equal(await usb.evaluate(()=>testUsb.rawRequests),0,'onboard vision requests are distinct from raw frames');
  await usb.evaluate(()=>{testUsb.detected=false;});await usb.waitForFunction(()=>document.querySelector('#aruco-command').textContent.startsWith('HOLD'));
  assert.equal(await usb.locator('#aruco-distance').innerText(),'—','lost marker clears pose immediately');
  await usb.evaluate(()=>{testUsb.detected=true;});await usb.waitForFunction(()=>document.querySelector('#aruco-distance').textContent==='0.808 m');
  await usb.locator('#aruco-enabled').uncheck();await usb.waitForFunction(()=>testUsb.rawRequests>2);
  assert.equal(await usb.locator('#aruco-distance').innerText(),'—');await usb.locator('#aruco-enabled').check();
  await usb.waitForFunction(()=>document.querySelector('#aruco-distance').textContent==='0.808 m');
  await usb.locator('#altitude-slider').fill('12');await usb.locator('#altitude-slider').dispatchEvent('input');
  await usb.waitForFunction(()=>document.querySelector('#profile-live').textContent.includes('1024×768'));
  assert.equal(await usb.locator('#aruco-enabled').isChecked(),false,'simulation selects raw video for full camera cadence');
  assert.equal(await usb.locator('#board-fps').innerText(),'2.0');assert.equal(await usb.locator('#usb-image').evaluate(c=>c.width),1024);
  assert((await usb.locator('#profile-live').innerText()).includes('JPEG Q10'));
  await usb.screenshot({path:path.resolve('local/altitude-high-preview.png'),fullPage:true});
  await usb.locator('#altitude-slider').fill('4');await usb.locator('#altitude-slider').dispatchEvent('input');
  await usb.waitForFunction(()=>document.querySelector('#profile-live').textContent.includes('640×480'));assert.equal(await usb.locator('#board-fps').innerText(),'8.0');
  await usb.locator('#altitude-slider').fill('1');await usb.locator('#altitude-slider').dispatchEvent('input');
  await usb.waitForFunction(()=>document.querySelector('#profile-live').textContent.includes('JPEG Q28'));assert.equal(await usb.locator('#board-fps').innerText(),'20.0');
  await usb.locator('#altitude-enabled').uncheck();await usb.waitForFunction(()=>document.querySelector('#profile-live').textContent.includes('simulation off'));
  assert(await usb.locator('#aruco-enabled').isChecked());await usb.waitForFunction(()=>document.querySelector('#aruco-distance').textContent==='0.808 m');
  await usb.locator('#preset-one').click();await usb.waitForFunction(()=>testUsb.changes===1&&!document.querySelector('#camera-controls').disabled);
  assert((await usb.locator('#exposure-state').innerText()).startsWith('Manual · exposure 1.000 ms · gain 4.00'));
  await usb.locator('#auto-exposure').click();await usb.waitForFunction(()=>testUsb.changes===2&&!document.querySelector('#camera-controls').disabled);
  assert((await usb.locator('#exposure-state').innerText()).startsWith('Auto'));
  await usb.locator('#exposure-ms').fill('50');await usb.locator('#manual-apply').click();
  assert.equal(await usb.evaluate(()=>testUsb.changes),2,'invalid input must not reach sensor');
  assert((await usb.locator('#exposure-state').innerText()).startsWith('Use exposure'));

  await usb.evaluate(()=>{testUsb.hold=true;});
  await usb.waitForFunction(()=>document.querySelector('#usb-session').textContent.includes('picture is stale'));
  await usb.waitForFunction(()=>document.querySelector('#aruco-command').textContent.startsWith('HOLD'));
  await usb.evaluate(()=>{testUsb.hold=false;});
  await usb.waitForFunction(()=>document.querySelector('#usb-session').textContent.endsWith(' · Live'));
  const download=usb.waitForEvent('download');await usb.locator('#usb-save').click();assert((await download).suggestedFilename().endsWith('.jpg'));
  await usb.evaluate(()=>{testUsb.paused=true;});await usb.getByText('Video paused during flight mission.',{exact:true}).waitFor();
  await usb.evaluate(()=>{testUsb.paused=false;});await usb.waitForFunction(()=>document.querySelector('#usb-state').textContent.startsWith('Connected'));
  await usb.locator('#usb-toggle').click();await usb.waitForFunction(()=>document.querySelector('#usb-toggle').textContent==='Connect USB'&&!document.querySelector('#usb-toggle').disabled);
  assert(await usb.evaluate(()=>testUsb.closed));
  const mismatch=await usb.evaluate(async()=>{
   const body=new TextEncoder().encode(JSON.stringify({frame_id:2})),prefix=new Uint8Array(8),frame=new Uint8Array(48),v=new DataView(frame.buffer);prefix.set([66,83,86,49]);new DataView(prefix.buffer).setUint32(4,body.length,true);frame.set([66,83,67,49]);v.setUint32(8,1,true);v.setUint16(36,320,true);v.setUint16(38,240,true);
   serialBuffer=new Uint8Array(8+body.length+48);serialBuffer.set(prefix);serialBuffer.set(body,8);serialBuffer.set(frame,8+body.length);
   try{await readVisionPacket();return '';}catch(e){return e.message;}finally{serialBuffer=new Uint8Array();}
  });assert.equal(mismatch,'ArUco result/frame mismatch.');
  await usb.locator('#usb-toggle').click();
  await usb.waitForFunction(()=>trackers.usb.total>=3&&trackers.usb.total<20);
  assert(await usb.evaluate(()=>document.querySelector('#aruco-panel').getBoundingClientRect().left>document.querySelector('.views').getBoundingClientRect().left),'desktop keeps pose beside USB video');
  await usb.screenshot({path:path.resolve('local/aruco-usb-viewer.png'),fullPage:true});
  await usb.setViewportSize({width:390,height:844});
  assert(await usb.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'USB pose layout fits mobile width');
  await usb.screenshot({path:path.resolve('local/aruco-usb-mobile.png'),fullPage:true});
  await usb.screenshot({path:path.resolve('local/usb-camera-viewer.png'),fullPage:true});
  await usb.locator('#usb-toggle').click();
  await usb.waitForFunction(()=>document.querySelector('#usb-toggle').textContent==='Connect USB'&&!document.querySelector('#usb-toggle').disabled);
  assert.deepEqual(errors,[]);
  console.log('PASS: firmware/offline HTML match; telemetry-only startup without JPEGs; heartbeat freshness and timeout/recovery; snapshot/comparison; Wi-Fi failure/reset; mobile layout; USB-first view; fragmented BSV1 vision + BSC1 frames; frame-matched pose/commands; marker loss clears pose; raw-video toggle; altitude slider switches XGA/2, VGA/8, QVGA/20 with confirmed profile metadata and restores ArUco; stale vision clears command; disconnect/reconnect; exposure controls. Simulated transports.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
