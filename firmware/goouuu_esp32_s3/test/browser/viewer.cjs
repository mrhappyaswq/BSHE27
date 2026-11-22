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
  let id=0,fail=false,mission=false;
  const settings={ok:true,manual:false,exposure_ms:8,gain:2,row_us:32,frame_period_ms:36,max_exposure_ms:20,night_mode:false};
  function packet(){const h=Buffer.alloc(48);h.write('BSC1');h.writeUInt32LE(jpeg.length,4);h.writeUInt32LE(++id,8);h.writeUInt32LE(1000,12);h.writeUInt32LE(1100,16);h.writeUInt32LE(1234,20);h.writeUInt32LE(0,24);h.writeUInt32LE(0,28);h.writeFloatLE(12.5,32);h.writeUInt16LE(320,36);h.writeUInt16LE(240,38);h.writeUInt32LE(100,40);return Buffer.concat([h,jpeg]);}
  await page.route('http://camera.test/**',async route=>{
   const url=new URL(route.request().url());
   if(url.pathname==='/camera-control')return route.fulfill({json:settings});
   if(url.pathname==='/status')return route.fulfill({json:{mission_active:mission,camera_error:'',camera:{board_fps:12.5,capture_wait_ms:1.234,jpeg_ms:0,jpeg_bytes:jpeg.length}}});
   return route.fulfill({contentType:'text/html',body:html});
  });
  await page.route('http://camera.test:81/**',async route=>{await new Promise(r=>setTimeout(r,40));return route.fulfill({status:fail?503:200,contentType:fail?'text/plain':'application/octet-stream',headers:{'Access-Control-Allow-Origin':'*'},body:fail?'Unavailable':packet()});});
  await page.goto('http://camera.test/');
  await page.waitForFunction(()=>document.querySelector('#wifi-state').textContent.startsWith('Connected'));
  assert.equal(await page.locator('#board-fps').innerText(),'12.5');
  assert.equal(await page.locator('#jpeg-ms').innerText(),'0.0');
  await page.waitForFunction(()=>parseFloat(document.querySelector('#wifi-fps').textContent)>0);
  await page.locator('#wifi-toggle').click();
  await page.waitForTimeout(100);assert.equal(await page.locator('#wifi-state').innerText(),'Stopped');
  fail=true;await page.locator('#wifi-toggle').click();await page.getByText('Camera unavailable or mission running. Reconnecting…',{exact:true}).waitFor();
  fail=false;await page.waitForFunction(()=>document.querySelector('#wifi-state').textContent.startsWith('Connected'));
  mission=true;await page.getByText('Video paused during flight mission.',{exact:true}).waitFor();
  mission=false;await page.setViewportSize({width:390,height:844});
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'mobile layout must fit');
  await page.screenshot({path:path.resolve('local/camera-speed-mobile.png'),fullPage:true});
  await page.close();
  const usb=await context.newPage();usb.on('pageerror',e=>errors.push(e.message));
  await usb.goto(pathToFileURL(path.join(root,'data/viewer.html')).href);
  assert(await usb.evaluate(()=>isSecureContext&&!!navigator.serial),'local file must support Web Serial in Edge');
  await usb.addInitScript(({jpeg})=>{
   let controller,frame=0;
   globalThis.testUsb={paused:false,closed:false,hold:false,changes:0,settings:{ok:true,manual:false,exposure_ms:8,gain:2,row_us:32,frame_period_ms:36,max_exposure_ms:20,night_mode:false}};
   Object.defineProperty(navigator,'serial',{configurable:true,value:{requestPort:async()=>({
    open:async()=>{},setSignals:async()=>{},close:async()=>{testUsb.closed=true;},
    readable:new ReadableStream({start(c){controller=c;},cancel(){}}),
    writable:new WritableStream({async write(request){
     if(request[0]===83||request[0]===67){
      if(request[0]===67){if(request.length!==8)throw new Error('invalid settings request');const v=new DataView(request.buffer,request.byteOffset,request.byteLength);testUsb.settings.manual=!!request[1];if(request[1]){testUsb.settings.exposure_ms=v.getUint32(2,true)/1000;testUsb.settings.gain=v.getUint16(6,true)/16;}++testUsb.changes;}
      const body=new TextEncoder().encode(JSON.stringify(testUsb.settings)),h=new Uint8Array(8);h.set([66,83,83,49]);new DataView(h.buffer).setUint32(4,body.length,true);controller.enqueue(h.slice(0,3));controller.enqueue(h.slice(3));controller.enqueue(body);return;
     }
     if(request[0]!==70||request.length!==5)throw new Error('invalid frame request');
     while(testUsb.hold)await new Promise(r=>setTimeout(r,20));
     await new Promise(r=>setTimeout(r,25));
     const h=new Uint8Array(48),v=new DataView(h.buffer);h.set([66,83,67,49]);
     v.setUint32(4,testUsb.paused?0:jpeg.length,true);v.setUint32(8,++frame,true);v.setUint32(20,2000,true);v.setUint32(24,0,true);v.setUint32(28,0,true);v.setFloat32(32,10,true);v.setUint16(36,320,true);v.setUint16(38,240,true);v.setUint32(40,80,true);v.setUint32(44,testUsb.paused?1:0,true);
     const b=new Uint8Array(48+(testUsb.paused?0:jpeg.length));b.set(h);if(!testUsb.paused)b.set(jpeg,48);
     try{controller.enqueue(b.slice(0,7));controller.enqueue(b.slice(7,33));controller.enqueue(b.slice(33));}catch{}
    }})
   })}});
  },{jpeg:[...jpeg]});
  await usb.reload();
  assert.equal(await usb.locator('h1').innerText(),'Live camera over USB-C.');
  assert(await usb.locator('#wifi-panel').isHidden(),'offline viewer starts with only USB video');
  await usb.locator('#compare-toggle').click();assert(await usb.locator('#wifi-panel').isVisible());
  await usb.locator('#compare-toggle').click();assert(await usb.locator('#wifi-panel').isHidden());
  await usb.locator('#usb-toggle').click();
  await usb.waitForFunction(()=>document.querySelector('#usb-state').textContent.startsWith('Connected'));
  assert.equal(await usb.locator('#board-fps').innerText(),'10.0');
  await usb.waitForFunction(()=>trackers.usb.total>=50);
  await usb.locator('#preset-one').click();await usb.waitForFunction(()=>testUsb.changes===1&&!document.querySelector('#camera-controls').disabled);
  assert((await usb.locator('#exposure-state').innerText()).startsWith('Manual · exposure 1.000 ms · gain 4.00'));
  await usb.locator('#auto-exposure').click();await usb.waitForFunction(()=>testUsb.changes===2&&!document.querySelector('#camera-controls').disabled);
  assert((await usb.locator('#exposure-state').innerText()).startsWith('Auto'));
  await usb.locator('#exposure-ms').fill('50');await usb.locator('#manual-apply').click();
  assert.equal(await usb.evaluate(()=>testUsb.changes),2,'invalid input must not reach sensor');
  assert((await usb.locator('#exposure-state').innerText()).startsWith('Use exposure'));

  await usb.evaluate(()=>{testUsb.hold=true;});
  await usb.waitForFunction(()=>document.querySelector('#usb-session').textContent.includes('picture is stale'));
  await usb.evaluate(()=>{testUsb.hold=false;});
  await usb.waitForFunction(()=>document.querySelector('#usb-session').textContent.endsWith(' · Live'));
  const download=usb.waitForEvent('download');await usb.locator('#usb-save').click();assert((await download).suggestedFilename().endsWith('.jpg'));
  await usb.evaluate(()=>{testUsb.paused=true;});await usb.getByText('Video paused during flight mission.',{exact:true}).waitFor();
  await usb.evaluate(()=>{testUsb.paused=false;});await usb.waitForFunction(()=>document.querySelector('#usb-state').textContent.startsWith('Connected'));
  await usb.locator('#usb-toggle').click();await usb.waitForFunction(()=>document.querySelector('#usb-toggle').textContent==='Connect USB'&&!document.querySelector('#usb-toggle').disabled);
  assert(await usb.evaluate(()=>testUsb.closed));
  await usb.locator('#usb-toggle').click();
  await usb.waitForFunction(()=>trackers.usb.total>=3&&trackers.usb.total<20);
  await usb.screenshot({path:path.resolve('local/usb-camera-viewer.png'),fullPage:true});
  await usb.locator('#usb-toggle').click();
  await usb.waitForFunction(()=>document.querySelector('#usb-toggle').textContent==='Connect USB'&&!document.querySelector('#usb-toggle').disabled);
  assert.deepEqual(errors,[]);
  console.log('PASS: firmware/offline HTML match; Wi-Fi decoding/FPS and recovery; mobile layout; USB-first offline view; 50+ fragmented USB frames; stale-video warning and recovery; JPEG download; mission pause/resume; disconnect/reconnect with fresh counters; USB sensor status, manual preset, auto restore and input validation. Simulated transports.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
