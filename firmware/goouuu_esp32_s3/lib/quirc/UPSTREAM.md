# Vendored quirc

Source: https://github.com/dlbeer/quirc

Pinned commit: `f2e4271ae43a15d9263704e07bc86cba5697d74d`.

The six files in `src/` are unchanged upstream library sources. Each carries
the upstream ISC permission notice. `library.json` is the local PlatformIO
wrapper. The firmware does not use `quirc_flip`, since it transposes the QR
bitmap without adjusting the reported corner orientation.

The build selects upstream's supported `QUIRC_FLOAT_TYPE=float` and
`QUIRC_USE_TGMATH` options, using the ESP32-S3's single-precision FPU rather than
software double-precision arithmetic. Library source files remain unchanged.
