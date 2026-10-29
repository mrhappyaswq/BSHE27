"""Read-only UART check on the ESP32: no arm, mode or movement commands."""

from banshee.flight import connect_to_pixhawk


def main():
    vehicle = connect_to_pixhawk()
    try:
        for _ in range(10):
            vehicle.sleep(0.5)
            print("Mode:", vehicle.mode(), "Armed:", vehicle.armed(),
                  "Prearm:", vehicle.is_armable(), "GPS:", vehicle.gps_ready())
            try:
                print("Relative altitude: %.2f m" % vehicle.altitude())
            except RuntimeError as exc:
                print("Position telemetry:", exc)
    finally:
        vehicle.close()


if __name__ == "__main__":
    main()
