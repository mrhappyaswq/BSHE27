"""Show each RGB pattern on the bench; never opens UART/camera or arms."""

from banshee import status_led as led
from banshee.compat import sleep_ms


def main(seconds_per_pattern=3):
    indicator = led.controller()
    if indicator is None:
        raise RuntimeError("RGB unavailable: enable RGB_ENABLED and run on MicroPython; check console")
    try:
        for state in led.PATTERNS:
            print("RGB:", state)
            led.set(state)
            sleep_ms(int(seconds_per_pattern * 1000))
            if indicator.error:
                raise RuntimeError("RGB driver error: " + indicator.error)
    except KeyboardInterrupt:
        led.set("stopped")
        raise
    except Exception:
        led.set("error")
        raise
    else:
        led.set("idle")


if __name__ == "__main__":
    main()
