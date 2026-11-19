import asyncio,json,socket
from apps.camera_web import start_access_point,serve
from banshee.camera import open_camera
from banshee.telemetry import TelemetryMonitor

async def request(path):
 r,w=await asyncio.open_connection('127.0.0.1',80)
 try:
  w.write(('GET '+path+' HTTP/1.1\r\nHost: camera\r\n\r\n').encode());await w.drain()
  return await asyncio.wait_for(r.read(),5)
 finally:
  w.close();await w.wait_closed()

async def check(ap,t):
 task=asyncio.create_task(serve(None,ap=ap,telemetry=t,camera_factory=open_camera))
 try:
  await asyncio.sleep(.1)
  page=await request('/')
  assert b'200 OK' in page and b'<!doctype html>' in page
  print('PASS: complete HTML delivered before camera startup')
  first=json.loads((await request('/status')).split(b'\r\n\r\n',1)[1])
  assert first['camera_state']=='initializing',first
  await asyncio.sleep(1)
  s=json.loads((await request('/status')).split(b'\r\n\r\n',1)[1]);assert s['ready'],s
  print('PASS: camera ready after page delivery')
  probe=await request('/generate_204');assert b'302 Found' in probe and b'Location: http://192.168.4.1/' in probe
  print('PASS: phone portal redirect')
  udp=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);udp.setblocking(False)
  try:
   udp.sendto(b'\x12\x34\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00\x06camera\x04test\x00\x00\x01\x00\x01',('127.0.0.1',53))
   answer=None
   for i in range(30):
    await asyncio.sleep(.02)
    try:answer=udp.recv(512);break
    except OSError:pass
   assert answer and answer[-4:]==bytes([192,168,4,1])
   print('PASS: hotspot DNS returns dashboard address')
  finally:udp.close()
  photo=await request('/capture');assert b'200 OK' in photo and b'\xff\xd8' in photo
  print('PASS: snapshot still works')
 finally:
  task.cancel()
  try:await task
  except asyncio.CancelledError:pass

ap=start_access_point();t=TelemetryMonitor()
try:asyncio.run(check(ap,t))
finally:t.close();ap.active(False)
