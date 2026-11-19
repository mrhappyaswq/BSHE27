"""Explicit host-side camera Wi-Fi check; restores the original Windows profile.

This temporarily changes the computer's Wi-Fi connection. It never flashes the
board or sends flight commands. Run manually, not through unit-test discovery.
"""
import argparse
import ast
import json
import re
import subprocess
import socket
import time
import urllib.request
import uuid
from pathlib import Path
from xml.sax.saxutils import escape


def command(*args):
    result = subprocess.run(['netsh', 'wlan', *args], capture_output=True, text=True,
                            encoding='utf-8', errors='replace', timeout=20)
    if result.returncode:
        raise RuntimeError('netsh command failed: ' + result.stdout + result.stderr)
    return result.stdout


def interface_state(interface):
    text = command('show', 'interfaces')
    def field(name):
        match = re.search(r'^\s*' + re.escape(name) + r'\s*:\s*(.+)$', text, re.M)
        return match.group(1).strip() if match else None
    if field('Name') != interface:
        raise RuntimeError('Expected Wi-Fi interface is not selected')
    return {'state': field('State'), 'ssid': field('SSID'),
            'profile': field('Profile'), 'rssi': field('Rssi'), 'radio_type': field('Radio type')}


def wait_profile(interface, profile, timeout=30):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        state = interface_state(interface)
        if state['state'] == 'connected' and state['profile'] == profile:
            return state
        time.sleep(1)
    raise TimeoutError('Wi-Fi profile did not connect: ' + profile)


def wait_ipv4(interface, timeout=20):
    deadline = time.monotonic() + timeout
    last = ''
    while time.monotonic() < deadline:
        info = subprocess.run(['netsh', 'interface', 'ipv4', 'show', 'config', 'name=' + interface],
                              capture_output=True, text=True, timeout=10)
        last = info.stdout
        found = re.search(r'IP Address:\s*(192\.168\.4\.\d+)', last)
        if found:
            return found.group(1)
        time.sleep(1)
    raise TimeoutError('No camera-subnet DHCP address: ' + last)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--restore-profile', required=True)
    parser.add_argument('--interface', default='Wi-Fi')
    parser.add_argument('--seconds', type=int, default=120)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--start-delay', type=int, default=0)
    parser.add_argument('--status-only', action='store_true')
    args = parser.parse_args()
    time.sleep(args.start_delay)
    root = args.project.resolve()
    output = args.output.resolve()
    if not output.is_relative_to(root / 'Build Stuff' / 'local'):
        raise RuntimeError('Results must remain inside project local artifacts')
    output.mkdir(parents=True, exist_ok=False)
    result = {'ok': False, 'restored': False, 'frames': 0, 'errors': [],
              'test': 'real camera over computer Wi-Fi, sequential JPEG/status'}
    result_file = output / 'result.json'
    def save():
        result_file.write_text(json.dumps(result, indent=2), encoding='utf-8')
    current = interface_state(args.interface)
    if current['profile'] != args.restore_profile or current['state'] != 'connected':
        raise RuntimeError('Original connection changed; refusing to switch Wi-Fi')
    settings = {}
    tree = ast.parse((root / 'Code/config.py').read_text(encoding='utf-8'))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in ('WIFI_SSID', 'WIFI_PASSWORD'):
                    settings[target.id] = ast.literal_eval(node.value)
    profile = 'BSHE27-Verify-' + uuid.uuid4().hex
    profile_file = output / 'temporary-wifi.xml'
    xml = '''<?xml version="1.0"?>
<WLANProfile xmlns="http://www.microsoft.com/networking/WLAN/profile/v1">
<name>{name}</name><SSIDConfig><SSID><name>{ssid}</name></SSID></SSIDConfig>
<connectionType>ESS</connectionType><connectionMode>manual</connectionMode>
<MSM><security><authEncryption><authentication>WPA2PSK</authentication>
<encryption>AES</encryption><useOneX>false</useOneX></authEncryption>
<sharedKey><keyType>passPhrase</keyType><protected>false</protected>
<keyMaterial>{password}</keyMaterial></sharedKey></security></MSM></WLANProfile>'''
    profile_file.write_text(xml.format(name=profile, ssid=escape(settings['WIFI_SSID']),
                                      password=escape(settings['WIFI_PASSWORD'])), encoding='utf-8')
    added = False
    connected = False
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    def request(path, changes=None, timeout=10):
        data = None if changes is None else json.dumps(changes).encode()
        req = urllib.request.Request('http://192.168.4.1' + path, data=data,
                                      headers={'Content-Type': 'application/json'} if data else {})
        with opener.open(req, timeout=timeout) as response:
            body = response.read(262145)
            if len(body) > 262144:
                raise RuntimeError('Oversized camera response')
            return body
    def status():
        return json.loads(request('/status', timeout=5))
    def photo():
        body = request('/capture')
        if body[:2] != b'\xff\xd8' or body[-2:] != b'\xff\xd9':
            raise RuntimeError('Incomplete JPEG')
        return body
    try:
        save()
        command('add', 'profile', 'filename=' + str(profile_file), 'user=current')
        added = True
        command('connect', 'name=' + profile, 'interface=' + args.interface)
        link = wait_profile(args.interface, profile)
        connected = True
        result['wifi_rssi'] = link['rssi']
        result['radio_type'] = link['radio_type']
        result['ipv4_address'] = wait_ipv4(args.interface)
        time.sleep(2)
        result['ping'] = subprocess.run(['ping', '-n', '2', '-w', '1000', '192.168.4.1'],
                                        capture_output=True, text=True, timeout=8).stdout
        attempts = []
        for attempt in range(3):
            try:
                html = request('/', timeout=12)
                result['html_bytes'] = len(html)
                break
            except Exception as exc:
                attempts.append(type(exc).__name__ + ': ' + str(exc))
                result['initial_http_attempts'] = attempts
                save()
                if attempt == 2:
                    raise
                time.sleep(1)
        assert b'receiveFrames' in html and b'/capture?t=' in html
        for attempt in range(8):
            state = status()
            if state['ready'] or args.status_only:
                break
            time.sleep(.5)
        assert state['ready'] or args.status_only, state
        assert state['quality'] == 35 and state['fps_limit'] == 1, state
        result['starting_status'] = state
        samples = []
        started = time.monotonic()
        while time.monotonic() - started < args.seconds:
            cycle = time.monotonic()
            state = status()
            assert args.status_only or (state['ready'] and state['error'] is None), state
            if args.status_only:
                result['status_checks'] = result.get('status_checks', 0) + 1
                result['elapsed_seconds'] = round(time.monotonic() - started, 2)
                save()
                time.sleep(max(0, 1 - (time.monotonic() - cycle)))
                continue
            image = photo()
            if result['frames'] == 0:
                (output / 'first-frame.jpg').write_bytes(image)
            result['frames'] += 1
            samples.append(len(image))
            if result['frames'] % 15 == 0:
                result['elapsed_seconds'] = round(time.monotonic() - started, 2)
                save()
            time.sleep(max(0, 1 - (time.monotonic() - cycle)))
        result['elapsed_seconds'] = round(time.monotonic() - started, 2)
        if args.status_only:
            result['ok'] = True
            return 0
        assert result['frames'] >= 60, result
        result['jpeg_bytes_min'] = min(samples)
        result['jpeg_bytes_max'] = max(samples)
        request('/settings', {'quality': 90, 'fps_limit': 3})
        high = photo()
        assert status()['quality'] == 90
        result['quality_90_jpeg_bytes'] = len(high)
        request('/settings', {'quality': 35, 'fps_limit': 1})
        result['final_status'] = status()
        assert result['final_status']['quality'] == 35
        result['ok'] = True
    except BaseException as exc:
        result['errors'].append(type(exc).__name__ + ': ' + str(exc))
        if connected:
            try:
                with socket.create_connection(('192.168.4.1', 80), timeout=3) as connection:
                    result['tcp_connect_after_error'] = True
            except Exception as tcp_error:
                result['tcp_connect_after_error'] = repr(tcp_error)
    finally:
        if connected and not args.status_only:
            try:
                request('/settings', {'quality': 35, 'fps_limit': 1}, timeout=5)
            except Exception as exc:
                result['settings_restore_error'] = str(exc)
        if added:
            # Always rejoin the existing saved profile, even if a test failed.
            for attempt in range(3):
                try:
                    command('connect', 'name=' + args.restore_profile, 'interface=' + args.interface)
                    wait_profile(args.interface, args.restore_profile, timeout=20)
                    result['restored'] = True
                    break
                except Exception as exc:
                    result['restore_error'] = str(exc)
                    time.sleep(2)
            try:
                command('delete', 'profile', 'name=' + profile, 'interface=' + args.interface)
            except Exception as exc:
                result['cleanup_error'] = str(exc)
        profile_file.unlink(missing_ok=True)
        save()
    return 0 if result['ok'] and result['restored'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
