"""Integrated live camera, Wi-Fi and receive-only Pixhawk dashboard."""

from banshee import status_led
import asyncio
import json
import network
import config
from banshee.camera import open_camera
from banshee.http_transport import RadioWriter
from banshee.telemetry import TelemetryMonitor
from banshee.compat import ticks_ms, ticks_diff

# One stream plus bounded page/status/snapshot requests fit the S3's sockets.
MAX_CLIENTS = 6
REQUEST_TIMEOUT = 3
FRAME_WRITE_TIMEOUT = 5
MAX_HEADER_BYTES = 4096
MAX_SETTINGS_BYTES = 256


def wifi_details(ap):
    if ap is None:
        return {"wifi_up": None, "device_connected": None}
    try:
        up = bool(ap.active())
    except OSError:
        up = False
    try:
        connected = bool(ap.isconnected()) if up else False
    except (AttributeError, OSError):
        connected = None
    return {"wifi_up": up, "device_connected": connected}


def update_wifi_led(ap, camera_error=None, telemetry=None, streaming=False):
    details = wifi_details(ap)
    if details["wifi_up"] is None:
        return details
    if not details["wifi_up"]:
        status_led.set("error")
    else:
        state = "wifi_connected" if details["device_connected"] else "wifi_up"
        link = telemetry["state"] if telemetry else "disabled"
        if camera_error:
            state += "_camera_error"
        elif link == "error":
            state = "telemetry_error"
        elif link == "lost":
            state = "link_lost"
        elif streaming:
            state = "streaming_pixhawk" if link == "connected" else "streaming"
        elif link == "connected":
            state += "_pixhawk"
        status_led.set(state)
    return details


def start_access_point():
    interface = getattr(network.WLAN, "IF_AP", getattr(network, "AP_IF", 1))
    ap = network.WLAN(interface)
    try:
        # Clear a previous app's AP session before advertising the new one.
        ap.active(False)
        ap.active(True)
        try:
            ap.config(ssid=config.WIFI_SSID, key=config.WIFI_PASSWORD,
                      security=3, hidden=False, channel=1,
                      protocol=config.WIFI_PROTOCOL, pm=config.WIFI_POWER_MANAGEMENT)
        except (ValueError, TypeError):
            ap.config(essid=config.WIFI_SSID, password=config.WIFI_PASSWORD,
                      authmode=3, hidden=False, channel=1,
                      protocol=config.WIFI_PROTOCOL, pm=config.WIFI_POWER_MANAGEMENT)
        ap.ifconfig(("192.168.4.1", "255.255.255.0", "192.168.4.1", "192.168.4.1"))
        if not ap.active():
            raise RuntimeError("Wi-Fi access point did not activate")
        update_wifi_led(ap)
        print("Wi-Fi broadcasting:", config.WIFI_SSID)
        print("Join it and open http://%s/" % ap.ifconfig()[0])
        return ap
    except BaseException:
        ap.active(False)
        raise


async def read_request(reader):
    """Bound total time, bytes and lines before allocating a request body."""
    data = b""
    while b"\r\n\r\n" not in data:
        chunk = await reader.read(256)
        if not chunk:
            raise ValueError("Incomplete HTTP headers")
        data += chunk
        if len(data) > MAX_HEADER_BYTES:
            raise ValueError("HTTP headers too large")
    headers, body = data.split(b"\r\n\r\n", 1)
    lines = headers.split(b"\r\n")
    if len(lines) > 33 or len(lines[0]) > 1024:
        raise ValueError("HTTP headers too large")
    parts = lines[0].split(b" ")
    if len(parts) != 3 or parts[2] not in (b"HTTP/1.0", b"HTTP/1.1"):
        raise ValueError("Invalid HTTP request")
    length = None
    for line in lines[1:]:
        if b":" not in line:
            raise ValueError("Invalid HTTP header")
        name, value = line.split(b":", 1)
        name, value = name.lower(), value.strip()
        if name == b"transfer-encoding":
            raise ValueError("Chunked requests are not supported")
        if name == b"content-length":
            if length is not None or not value.isdigit():
                raise ValueError("Invalid content length")
            length = int(value)
    length = 0 if length is None else length
    if length > MAX_SETTINGS_BYTES:
        raise ValueError("Request body too large")
    while len(body) < length:
        chunk = await reader.read(length - len(body))
        if not chunk:
            raise ValueError("Incomplete request body")
        body += chunk
    return parts[0], parts[1].split(b"?", 1)[0], body[:length]


async def close_writer(writer):
    try:
        writer.close()
        # MicroPython Stream.close() is a no-op; wait_closed() closes the socket.
        await asyncio.wait_for(writer.wait_closed(), 1)
    except (OSError, asyncio.TimeoutError):
        pass


async def send_body(writer, body):
    view = memoryview(body)
    for offset in range(0, len(view), 1024):
        writer.write(view[offset:offset + 1024])
        await writer.drain()


async def serve(camera, camera_error=None, ap=None, telemetry=None, camera_factory=None):
    lock = asyncio.Lock()
    stream_lock = asyncio.Lock()
    page_requested = asyncio.Event()
    clients = {}
    state = {"error": camera_error, "streaming": False, "frames_sent": 0,
             "last_frame_at": None, "stream_error": None, "stream_task": None,
             "fps_limit": getattr(config, "CAMERA_FPS_LIMIT", 10), "fps_actual": 0.0,
             "initializing": camera_factory is not None, "preview_at": None}

    def update_indicator():
        link = telemetry.snapshot() if telemetry is not None else None
        preview_active = state["preview_at"] is not None and ticks_diff(ticks_ms(), state["preview_at"]) < 3000
        details = update_wifi_led(ap, state["error"], link, state["streaming"] or preview_active)
        details["pixhawk"] = link
        return details

    def settings():
        return {"quality": getattr(camera, "quality", config.CAMERA_JPEG_QUALITY),
                "fps_limit": state["fps_limit"]}

    async def capture_jpeg():
        async with lock:
            try:
                capture_async = getattr(camera, "capture_async", None)
                image = await capture_async() if capture_async else camera.capture()
                if image is None:
                    raise RuntimeError("Capture failed")
                # Native encoder returns owned bytes. Copy only driver memoryviews.
                return image if isinstance(image, bytes) else bytes(image)
            finally:
                camera.free_buffer()

    async def send_frame(writer, image):
        writer.write(b"--bshe27frame\r\nContent-Type: image/jpeg\r\nContent-Length: " +
                     str(len(image)).encode() + b"\r\n\r\n")
        await send_body(writer, image)
        writer.write(b"\r\n")
        await writer.drain()

    async def write_stream(writer):
        state["streaming"] = True
        state["stream_error"] = None
        state["fps_actual"] = 0.0
        failures = 0
        measured_at, measured_frames = ticks_ms(), 0
        update_indicator()
        try:
            writer.write(b"HTTP/1.1 200 OK\r\nContent-Type: multipart/x-mixed-replace; boundary=bshe27frame\r\nCache-Control: no-store\r\nConnection: close\r\n\r\n")
            await asyncio.wait_for(writer.drain(), FRAME_WRITE_TIMEOUT)
            while True:
                started = ticks_ms()
                try:
                    image = await capture_jpeg()
                except Exception as exc:
                    state["error"] = str(exc)
                    update_indicator()
                    print("Camera stream capture:", exc)
                    failures += 1
                    if failures >= 3:
                        state["stream_error"] = "Camera capture failed three times: " + str(exc)
                        break
                    await asyncio.sleep(0.25)
                    continue
                failures = 0
                state["error"] = None
                # A whole frame has one deadline: a drip-fed socket cannot keep
                # the sole viewer occupied indefinitely by draining each chunk.
                await asyncio.wait_for(send_frame(writer, image), FRAME_WRITE_TIMEOUT)
                image = None
                state["frames_sent"] += 1
                state["last_frame_at"] = ticks_ms()
                measured_frames += 1
                elapsed = ticks_diff(state["last_frame_at"], measured_at)
                if elapsed >= 1000:
                    state["fps_actual"] = round(measured_frames * 1000 / elapsed, 1)
                    measured_at, measured_frames = state["last_frame_at"], 0
                delay_ms = 1000 / state["fps_limit"] - ticks_diff(ticks_ms(), started)
                await asyncio.sleep(max(0.001, delay_ms / 1000))
        except (OSError, asyncio.TimeoutError) as exc:
            state["stream_error"] = "Viewer disconnected or Wi-Fi write timed out: " + str(exc)
            print("Camera stream transport:", state["stream_error"])
        finally:
            state["streaming"] = False
            state["fps_actual"] = 0.0
            update_indicator()
            await close_writer(writer)

    async def replace_stream(writer):
        # Serialize ownership changes so an old stream's finally cannot clear
        # a newer viewer's state or leave two capture loops running together.
        async with stream_lock:
            previous = state["stream_task"]
            if previous is not None:
                previous.cancel()
                try:
                    await previous
                except asyncio.CancelledError:
                    pass
            task = asyncio.create_task(write_stream(writer))
            state["stream_task"] = task
        try:
            await task
        finally:
            if state["stream_task"] is task:
                state["stream_task"] = None

    async def respond(writer, code, body, kind=b"application/json"):
        writer.write(b"HTTP/1.1 " + code + b"\r\nContent-Type: " + kind +
                     b"\r\nCache-Control: no-store\r\nConnection: close\r\nContent-Length: " +
                     str(len(body)).encode() + b"\r\n\r\n")
        await asyncio.wait_for(send_body(writer, body),
                               15 if kind.startswith(b"text/html") else FRAME_WRITE_TIMEOUT)

    async def handle(reader, writer):
        # The pinned MicroPython stream exposes its nonblocking socket as .s.
        # Keep the reader unchanged; pace only outgoing Wi-Fi traffic.
        if getattr(writer, "s", None) is not None:
            try:
                writer = RadioWriter(writer)
            except OSError as exc:
                print("HTTP radio setup:", exc)
                await close_writer(writer)
                return
        if len(clients) >= MAX_CLIENTS:
            await close_writer(writer)
            return
        clients[writer] = asyncio.current_task()
        try:
            try:
                method, path, request_body = await asyncio.wait_for(read_request(reader), REQUEST_TIMEOUT)
            except ValueError as exc:
                await respond(writer, b"400 Bad Request", json.dumps({"error": str(exc)}).encode())
                return
            if method != (b"POST" if path == b"/settings" else b"GET"):
                await respond(writer, b"405 Method Not Allowed", b'{"error":"Method not allowed"}')
                return
            if path in (b"/status", b"/stream", b"/capture", b"/settings"):
                page_requested.set()
            code, kind = b"200 OK", b"application/json"
            if path == b"/stream":
                if camera is not None:
                    await replace_stream(writer)
                    return
                code = b"503 Service Unavailable"
                body = json.dumps({"error": state["error"] or "Camera unavailable"}).encode()
            elif path == b"/capture":
                body = None
                if camera is not None:
                    try:
                        body = await capture_jpeg()
                    except Exception as exc:
                        state["error"] = str(exc)
                        print("Camera capture:", exc)
                if body is None:
                    code = b"503 Service Unavailable"
                    body = json.dumps({"error": state["error"] or "Camera unavailable"}).encode()
                else:
                    state["error"] = None
                    kind = b"image/jpeg"
                update_indicator()
            elif path == b"/settings":
                try:
                    changes = json.loads(request_body)
                    if not isinstance(changes, dict) or not changes or any(
                            key not in ("quality", "fps_limit") for key in changes):
                        raise ValueError("Expected quality and/or fps_limit")
                    for key, low, high in (("quality", 35, 90), ("fps_limit", 1, 15)):
                        if key in changes and (type(changes[key]) is not int or
                                               not low <= changes[key] <= high):
                            raise ValueError("%s must be an integer from %d to %d" % (key, low, high))
                    if camera is None:
                        code = b"503 Service Unavailable"
                        body = json.dumps({"error": state["error"] or "Camera unavailable"}).encode()
                    else:
                        async with lock:
                            if "quality" in changes:
                                camera.set_quality(changes["quality"])
                            if "fps_limit" in changes:
                                state["fps_limit"] = changes["fps_limit"]
                        body = json.dumps(settings()).encode()
                except (ValueError, TypeError) as exc:
                    code = b"400 Bad Request"
                    body = json.dumps({"error": str(exc)}).encode()
                except Exception as exc:
                    code = b"503 Service Unavailable"
                    body = json.dumps({"error": "Settings could not be applied: " + str(exc)}).encode()
            elif path == b"/status":
                details = update_indicator()
                age = None if state["last_frame_at"] is None else max(
                    0, ticks_diff(ticks_ms(), state["last_frame_at"]))
                details.update({"board": config.BOARD_NAME, "ready": camera is not None,
                                "camera_state": "initializing" if state["initializing"] else
                                                ("unavailable" if camera is None else
                                                 ("capture_error" if state["error"] else "ready")),
                                "error": state["error"], "streaming": state["streaming"],
                                "frames_sent": state["frames_sent"], "last_frame_age_ms": age,
                                "stream_error": state["stream_error"], "app_version": 7,
                                "led_enabled": status_led.is_enabled(),
                                "fps_actual": state["fps_actual"] if age is not None and age < 2000 else 0.0})
                details.update(settings())
                body = json.dumps(details).encode()
            elif path in (b"/generate_204", b"/gen_204", b"/hotspot-detect.html",
                          b"/connecttest.txt", b"/ncsi.txt", b"/redirect", b"/canonical.html"):
                writer.write(b"HTTP/1.1 302 Found\r\nLocation: http://192.168.4.1/\r\nContent-Length: 0\r\nConnection: close\r\n\r\n")
                await asyncio.wait_for(writer.drain(), 3)
                return
            elif path == b"/":
                with open("web/index.html", "rb") as page:
                    body = page.read()
                kind = b"text/html; charset=utf-8"
            else:
                code, body, kind = b"404 Not Found", b"Not found", b"text/plain"
            await respond(writer, code, body, kind)
            if path == b"/capture" and kind == b"image/jpeg":
                state["preview_at"] = ticks_ms()
                update_indicator()
        except (OSError, asyncio.TimeoutError) as exc:
            # A socket timeout is not a camera or Pixhawk fault.
            print("Camera HTTP transport:", exc)
        except Exception as exc:
            print("Camera HTTP:", exc)
        finally:
            clients.pop(writer, None)
            await close_writer(writer)

    async def initialize_camera():
        nonlocal camera
        # Bind and accept HTTP before native camera initialization can block.
        # A joining browser gets a loading page instead of connection refused.
        await page_requested.wait()
        await asyncio.sleep(0.2)
        try:
            camera = camera_factory()
            state["error"] = None
            print("Camera ready: 320x240 color, MJPEG /stream")
        except Exception as exc:
            state["error"] = str(exc)
            print("Camera unavailable; Wi-Fi diagnostics remain available:", exc)
        finally:
            state["initializing"] = False
            update_indicator()

    server = await asyncio.start_server(handle, "0.0.0.0", 80, backlog=4)
    dns = None
    if ap is not None:
        try:
            from banshee.portal import PortalDNS
            dns = PortalDNS()
        except OSError as exc:
            print("Hotspot DNS unavailable:", exc)
    print("HTTP dashboard listening on http://192.168.4.1/")
    initializer = asyncio.create_task(initialize_camera()) if camera_factory is not None else None
    try:
        while True:
            if dns is not None:
                dns.poll()
            if telemetry is not None:
                telemetry.poll()
            update_indicator()
            await asyncio.sleep(0.02)
    finally:
        if dns is not None:
            dns.close()
        server.close()
        await server.wait_closed()
        if initializer is not None:
            initializer.cancel()
            try:
                await initializer
            except asyncio.CancelledError:
                pass
        stream_task = state["stream_task"]
        if stream_task is not None:
            stream_task.cancel()
            try:
                await stream_task
            except asyncio.CancelledError:
                pass
        # MicroPython asyncio.run() does not cancel outstanding client tasks.
        # Explicit teardown avoids stale sockets after restarting the app.
        current = asyncio.current_task()
        pending = list(clients.items())
        for writer, task in pending:
            if task is not current:
                task.cancel()
            await close_writer(writer)
        for writer, task in pending:
            if task is not current:
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        if camera_factory is not None and camera is not None:
            camera.deinit()


@status_led.indicate("camera_init")
def main():
    ap = start_access_point()
    telemetry = None
    try:
        telemetry = TelemetryMonitor()
        asyncio.run(serve(None, ap=ap, telemetry=telemetry, camera_factory=open_camera))
    finally:
        try:
            ap.active(False)
        finally:
            if telemetry is not None:
                telemetry.close()


if __name__ == "__main__":
    main()
