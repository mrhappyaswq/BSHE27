"""RGB debug indicator. Soft timer updates; no sleeps in application paths.

Importing this module never opens hardware. LED failures must not stop flight
or telemetry. Patterns use one color, counted blinks and a dark pause.
"""

import sys
import config
from banshee.compat import ticks_diff, ticks_ms

# Each group: 180 ms lit, 180 ms between blinks, 1200 ms dark pause.
PATTERNS = {'off': ((0, 0, 0), (1000,)),
 'boot': ((255, 255, 255), (180, 1200)),
 'idle': ((255, 255, 255), (180, 180, 180, 1200)),
 'stopped': ((255, 255, 255), (180, 180, 180, 180, 180, 1200)),
 'wifi_up': ((0, 255, 255), (180, 1200)),
 'wifi_connected': ((0, 255, 255), (180, 180, 180, 1200)),
 'wifi_up_pixhawk': ((0, 255, 255), (180, 180, 180, 180, 180, 1200)),
 'connected': ((0, 255, 0), (180, 1200)),
 'wifi_connected_pixhawk': ((0, 255, 0), (180, 180, 180, 1200)),
 'qr_found': ((0, 255, 0), (180, 180, 180, 180, 180, 1200)),
 'streaming': ((0, 50, 255), (180, 1200)),
 'streaming_pixhawk': ((0, 50, 255), (180, 180, 180, 1200)),
 'mission': ((0, 50, 255), (180, 180, 180, 180, 180, 1200)),
 'camera_init': ((150, 0, 255), (180, 1200)),
 'camera_ready': ((150, 0, 255), (180, 180, 180, 1200)),
 'capture': ((150, 0, 255), (180, 180, 180, 180, 180, 1200)),
 'error': ((255, 0, 0), (180, 1200)),
 'link_lost': ((255, 0, 0), (180, 180, 180, 1200)),
 'telemetry_error': ((255, 0, 0), (180, 180, 180, 180, 180, 1200)),
 'wifi_up_camera_error': ((255, 120, 0), (180, 1200)),
 'wifi_connected_camera_error': ((255, 120, 0), (180, 180, 180, 1200)),
 'landing': ((255, 120, 0), (180, 180, 180, 180, 180, 1200)),
 'waiting': ((255, 0, 255), (180, 1200)),
 'qr_search': ((255, 0, 255), (180, 180, 180, 1200))}

# Kept empty: odd phases are intentionally dark.
PHASE_COLORS = {}

class StatusLED:
    def __init__(self, pixel, timer_factory, clock=ticks_ms, brightness=0.08,
                 button=None, debounce_ms=50):
        self.pixel = pixel
        self.clock = clock
        self.brightness = max(0, min(1, brightness))
        self.state = "off"
        self.started = clock()
        self.overlay = None
        self.last_color = None
        self.error = None
        self.timer = None
        self.enabled = True
        self.closed = False
        self.button = button
        self.button_error = None
        self.debounce_ms = max(1, debounce_ms)
        self._button_raw = None
        self._button_stable = None
        self._button_changed = self.started
        # A BOOT button held during startup must be released before toggling.
        self._button_armed = False
        try:
            self.timer = timer_factory()
            self._tick(None)
            # ESP32 hardware timers invoke Python callbacks as soft callbacks.
            self.timer.init(period=50, mode=self.timer.PERIODIC, callback=self._tick)
        except Exception:
            self.close()
            raise

    def set(self, state):
        if state not in PATTERNS:
            raise ValueError("Unknown RGB state: " + state)
        if state != self.state:
            self.state, self.started = state, self.clock()
            self.overlay = None
        self._tick(None)

    def pulse(self, state, duration=400):
        if state not in PATTERNS:
            raise ValueError("Unknown RGB state: " + state)
        # An activity flash must never hide a persistent fault indication.
        if (self.state in ("error", "link_lost", "telemetry_error") or
                self.state.endswith("_camera_error")):
            return
        self.overlay = (state, self.clock(), duration)
        self._tick(None)

    def set_enabled(self, enabled):
        """Mute the pixel without losing the current state or pattern phase."""
        self.enabled = bool(enabled)
        self._tick(None)
        return self.enabled

    def _poll_button(self, now):
        if self.button is None:
            return
        try:
            pressed = not self.button.value()  # GPIO0 BOOT is active low.
            if pressed != self._button_raw:
                self._button_raw = pressed
                self._button_changed = now
            if (pressed == self._button_stable or
                    ticks_diff(now, self._button_changed) < self.debounce_ms):
                return
            self._button_stable = pressed
            if not pressed:
                self._button_armed = True
            elif self._button_armed:
                self.enabled = not self.enabled
                self._button_armed = False
        except Exception as exc:
            # A broken button must not disable the indicator or application.
            self.button_error = str(exc)
            self.button = None

    def _tick(self, timer):
        if self.error or self.closed:
            return
        try:
            now = self.clock()
            self._poll_button(now)
            state, started = self.state, self.started
            if self.overlay:
                if ticks_diff(now, self.overlay[1]) < self.overlay[2]:
                    state, started = self.overlay[:2]
                else:
                    self.overlay = None
            rgb, segments = PATTERNS[state]
            phase = max(0, ticks_diff(now, started)) % sum(segments)
            on = True
            for index, duration in enumerate(segments):
                if phase < duration:
                    on = index % 2 == 0
                    break
                phase -= duration
            rgb = PHASE_COLORS.get(state, {}).get(index, rgb if on else (0, 0, 0))
            color = (tuple(int(channel * self.brightness) for channel in rgb)
                     if self.enabled else (0, 0, 0))
            if color != self.last_color:
                self.pixel[0] = color
                self.pixel.write()
                self.last_color = color
        except KeyboardInterrupt:
            # mpremote sends Ctrl+C to enter the REPL. If it lands in this
            # soft callback, do not print a traceback into the REPL handshake.
            return
        except Exception as exc:
            # Never raise an LED driver failure from a scheduled callback.
            self.error = str(exc)

    def close(self):
        self.closed = True
        if self.timer is not None:
            try:
                self.timer.deinit()
            except Exception:
                pass
        try:
            self.pixel[0] = (0, 0, 0)
            self.pixel.write()
        except Exception:
            pass


_controller = None
_failed = False


def controller():
    global _controller, _failed
    if (_failed or not config.RGB_ENABLED or
            sys.implementation.name != "micropython"):
        return None
    if _controller is None:
        try:
            from machine import Pin, Timer
            from neopixel import NeoPixel
            config.validate_board()
            button = None
            if config.RGB_BUTTON_ENABLED:
                try:
                    button = Pin(config.RGB_BUTTON_PIN, Pin.IN, Pin.PULL_UP)
                except Exception as exc:
                    print("RGB button unavailable:", exc)
            _controller = StatusLED(NeoPixel(Pin(config.RGB_PIN, Pin.OUT), 1),
                                    lambda: Timer(config.RGB_TIMER_ID),
                                    brightness=config.RGB_BRIGHTNESS,
                                    button=button,
                                    debounce_ms=config.RGB_BUTTON_DEBOUNCE_MS)
        except Exception as exc:
            _failed = True
            print("RGB indicator unavailable:", exc)
    return _controller


def set(state):
    led = controller()
    if led:
        led.set(state)


def pulse(state, duration=400):
    led = controller()
    if led:
        led.pulse(state, duration)


def set_enabled(enabled):
    """Set the debug indicator visibility; subsystem state keeps updating."""
    led = controller()
    return led.set_enabled(enabled) if led else False


def is_enabled():
    led = controller()
    return bool(led and led.enabled and not led.closed and not led.error)


def telemetry(last_heartbeat, now):
    """Passive monitor only: None means no target heartbeat has arrived yet."""
    if last_heartbeat is None:
        set("waiting")
    elif ticks_diff(now, last_heartbeat) > config.HEARTBEAT_TIMEOUT * 1000:
        set("link_lost")
    else:
        set("connected")


def indicate(start, success="idle"):
    """Report explicit app startup/finish and errors without hiding tracebacks."""
    def decorate(function):
        def run(*args, **kwargs):
            set(start)
            try:
                result = function(*args, **kwargs)
            except KeyboardInterrupt:
                set("stopped")
                raise
            except Exception:
                set("error")
                raise
            else:
                if success is not None:
                    set(success)
                return result
        return run
    return decorate
