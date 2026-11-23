# BSHE27 - Start here

This project runs the camera and mission helper on your GOOUUU ESP32-S3 board. The Pixhawk controls the aircraft. The board program is C++; the camera page uses JavaScript. Python helpers run on your computer.

**First time? Read [Setup](Docs/Setup%20Guide.md).** For a guide to every folder, read the [Project Map](Docs/Project%20Map.md).

| Folder | What is inside |
| --- | --- |
| [Code](Code/) | The board program and its camera web page |
| [Docs](Docs/) | Setup, wiring, instructions and the Python package list |
| [Helpers](Helpers/) | Small programs you run on your computer to open or check the camera |
| [Checks](Checks/) | Programs that check whether the code and web page work |
| Saved Results | Pictures, measurements and reports saved on this computer |
| Build Tools | Downloaded tools and temporary files used to make the board program |

Inside **Code**:

- **main.cpp** starts the program and keeps it running.
- **Camera** takes pictures, sends USB video and changes camera settings.
- **ArUco** finds the square marker and estimates where it is.
- **Web Server** sends the camera page and information to your browser.
- **Pixhawk Communication** sends and reads MAVLink messages.
- **Flight Missions** holds the hover, move, circle and landing steps.
- **Board Settings** holds the board's pins, Wi-Fi name and other settings.

Open `BSHE27.code-workspace` in VS Code. **Ctrl+Shift+B builds and uploads**; use **GOOUUU: Build** to build only. Disconnect the camera viewer before uploading.

The board starts listening and running its camera services at boot. Flight missions need explicit serial commands. The ArUco display is a bench preview; it does not steer the aircraft. See the [mission guide](Docs/Missions%20Guide.md) and [camera guide](Docs/Camera%20Guide.md).

The few files that must stay at the project root are explained in the Project Map. Git and editor settings are hidden from the normal VS Code file view.
