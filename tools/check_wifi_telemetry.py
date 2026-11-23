"""Record Wi-Fi replies and optional TTL diagnostics while switching networks.

Only GET /telemetry and the passive serial `status` command are used.
Example: python tools/check_wifi_telemetry.py --port COM11 --seconds 300
The serial port must be the TTL console, not the native USB video port.
"""
import argparse
import http.client
import json
from pathlib import Path
import socket
import threading
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', help='Optional TTL console port; close other serial monitors')
    parser.add_argument('--seconds', type=float, default=300)
    parser.add_argument('--output', default='local/wifi-diagnostic.jsonl')
    parser.add_argument('--path', choices=['/telemetry', '/health'], default='/telemetry')
    args = parser.parse_args()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + args.seconds
    lock = threading.Lock()
    with output.open('w', encoding='utf-8', buffering=1) as log:
        def record(kind, **data):
            with lock:
                log.write(json.dumps(dict(time=time.time(), kind=kind, **data)) + '\n')

        def console():
            try:
                import serial
                port = serial.Serial(port=None, baudrate=115200, timeout=0.2)
                port.dtr = False
                port.rts = False
                port.port = args.port
                with port:
                    next_status = 0
                    while time.monotonic() < deadline:
                        if time.monotonic() >= next_status:
                            port.write(b'status\n')
                            next_status = time.monotonic() + 5
                        line = port.readline()
                        if line:
                            record('serial', line=line.decode('utf-8', errors='replace').strip())
            except Exception as error:
                record('serial_error', error=str(error))

        record('start', seconds=args.seconds, port=args.port,
               note='No network changes, JPEGs, or flight commands. HTTP bypasses system proxy.')
        worker = threading.Thread(target=console) if args.port else None
        if worker:
            worker.start()
        while time.monotonic() < deadline:
            started = time.monotonic()
            local_ip = None
            stage = 'connect'
            connection = http.client.HTTPConnection('192.168.4.1', timeout=3)
            try:
                # UDP connect selects a local route without sending a datagram.
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as route:
                    route.connect(('192.168.4.1', 80))
                    local_ip = route.getsockname()[0]
            except OSError:
                pass
            try:
                connection.connect()
                stage = 'headers'
                connection.request('GET', args.path, headers={'Connection': 'close'})
                response = connection.getresponse()
                record('headers', status=response.status, local_ip=local_ip,
                       ms=(time.monotonic() - started) * 1000,
                       content_length=response.getheader('Content-Length'))
                stage = 'body'
                body = response.read()
                elapsed = (time.monotonic() - started) * 1000
                if response.status != 200:
                    raise ValueError('HTTP ' + str(response.status))
                data = json.loads(body)
                if args.path == '/telemetry' and data.get('board') != 'GOOUUU ESP32-S3':
                    raise ValueError('Unexpected board response')
                record('reply', local_ip=local_ip, ms=elapsed, bytes=len(body), data=data)
            except Exception as error:
                record('http_error', stage=stage, local_ip=local_ip, ms=(time.monotonic() - started) * 1000,
                       error=str(error))
            finally:
                connection.close()
            time.sleep(max(0, 1 - (time.monotonic() - started)))
        if worker:
            worker.join()
        record('end')
    print(str(output.resolve()))


if __name__ == '__main__':
    main()
