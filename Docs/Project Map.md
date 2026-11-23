# Project map

| Folder | Simple meaning |
| --- | --- |
| Code | The instructions the board follows |
| Docs | The instructions for you |
| Helpers | Small programs to open the camera, check USB or update the web page |
| Checks | Practice checks run on your computer without flying |
| Saved Results | The pictures and reports those checks save |
| Build Tools | The toolbox used to turn code into a board program |

The old project folder names `src`, `include`, `data`, `firmware`, `tools` and `local` are no longer used. Code and its related headers now sit together by feature.

## Inside Code

| Folder or file | What it does |
| --- | --- |
| main.cpp | Starts the board program and runs its main loop |
| Board Settings | Pins, Wi-Fi settings, image defaults and board limits |
| Camera | Takes pictures, shares frames, handles USB video and camera controls |
| ArUco | Finds the square marker, estimates pose and prepares the preview |
| Web Server | The browser page and the code that serves it over Wi-Fi |
| Pixhawk Communication | Reads telemetry and sends MAVLink commands |
| Third Party | The pinned JPEG decoder library and its license, used by the camera analysis |
| Flight Missions | Steps for hover, movement, circle and marker-input missions |

A `.cpp` file contains C++ program instructions. A `.h` file contains shared definitions or instructions used by other files. They work together, which is why both kinds are in each feature folder.

In **Web Server**, edit `viewer.html` to change the page. `dashboard_page.h` is a generated copy that fits inside the board program. Run `python "Helpers/Update Web Page.py"` after editing the HTML.

ArUco is the name of the square marker system. The onboard ArUco preview does not feed the flight missions; those currently need separate serial marker input.

## The special files

A few tools require specific filenames or locations:

| File or folder | Why it exists |
| --- | --- |
| README.md | This project's front page; Git hosting also displays it automatically |
| BSHE27.code-workspace | Opens this project in VS Code |
| platformio.ini | The build recipe: which board, tools and folders PlatformIO uses |
| .gitignore | Tells Git to leave downloaded tools, results and private settings out of version history |
| .git | Git's saved version history; do not delete it to tidy the project |
| .vscode | VS Code's build buttons and editor settings |

Git/editor items are hidden in the normal VS Code Explorer. Hiding them does not delete them. The unnecessary `.gitattributes` file was removed; the page updater preserves exact line endings itself.

## Computer-only files

**Saved Results** keeps measurements, images, manuals and the record confirming deletion of the 74 approved old items. **Saved Results/Code Checks** contains temporary test executables.

**Build Tools** contains PlatformIO's downloaded board tools, its **Temporary Files** cache, and retained computer-only Python/document/test-message dependencies. These are tools or generated files, not another version of your application. You normally do not edit them. The current project uses PlatformIO; retained package folders are computer-only tooling. Python helpers use the packages installed for your selected Python interpreter, as described in the Setup Guide.

Both folders are ignored by Git. The active project can be rebuilt on another computer using the setup instructions.
