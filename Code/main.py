"""Boot the selected S3 app. No boot option starts a flight mission."""

import config
from banshee import status_led


@status_led.indicate("boot")
def main():
    config.validate_runtime()
    mode = config.BOOT_APP
    print("BSHE27 boot app:", mode)
    if mode == "camera":
        from apps.camera_web import main as run
    elif mode == "telemetry":
        from diagnostics.boot_telemetry import main as run
    else:
        raise ValueError("BOOT_APP must be 'camera' or 'telemetry'; boot never starts a mission")
    return run()


if __name__ == "__main__":
    main()
