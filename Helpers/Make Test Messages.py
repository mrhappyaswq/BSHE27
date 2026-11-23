"""Create MAVLink test messages. Packages are listed in Docs/Python Packages.txt."""
from pathlib import Path
project = Path(__file__).resolve().parents[1]
try:
    from pymavlink.dialects.v10 import common as v1
    from pymavlink.dialects.v20 import common as v2
except ImportError:
    raise SystemExit('Install the optional Python packages first: python -m pip install -r "Docs/Python Packages.txt"')
out=['// Generated using pymavlink 2.4.50 common dialect; independent wire fixtures.']
def emit(name,version,msg,sysid=1,comp=1):
 data=msg.pack(version.MAVLink(None,srcSystem=sysid,srcComponent=comp))
 out.append('static const uint8_t '+name+'[] = {'+','.join(hex(b) for b in data)+'};')
emit('heartbeat1',v1,v1.MAVLink_heartbeat_message(2,3,0,0,3,3))
emit('heartbeat2',v2,v2.MAVLink_heartbeat_message(2,3,128,4,4,3))
emit('otherSystem',v1,v1.MAVLink_heartbeat_message(2,3,0,0,3,3),2)
emit('wrongAutopilot',v1,v1.MAVLink_heartbeat_message(2,12,0,0,3,3))
emit('acceptedTakeoff',v2,v2.MAVLink_command_ack_message(22,0))
emit('deniedArm',v1,v1.MAVLink_command_ack_message(400,2))
emit('expectedVelocity',v1,v1.MAVLink_set_position_target_local_ned_message(1000,1,1,8,0x05c7,0,0,0,0.1,-0.2,0.05,0,0,0,0,0.3),245,191)
emit('expectedGoto',v1,v1.MAVLink_set_position_target_global_int_message(1000,1,1,3,0x0df8,370000000,-1220000000,1.5,0,0,0,0,0,0,0,0),245,191)
(project / 'Checks' / 'Code Checks' / 'vectors.h').write_text('\n'.join(out)+'\n')
