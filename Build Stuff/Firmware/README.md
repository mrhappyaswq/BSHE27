# Firmware sources

**Start with [Firmware Guide](../../Guides/Firmware%20Guide.md).**

`Sources/` contains editable interpreter, camera and SDK source code.
`Images/` contains the verified optional firmware image; now installed with octal PSRAM and 16 MB flash configuration.
`build.sh` builds your edited camera firmware under Linux/WSL, without flashing.
`source-lock.json` records the exact downloaded revisions and image checksum.

Your ordinary Python application stays in `../../Code/`.
