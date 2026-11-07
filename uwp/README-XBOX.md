# Xash3D FWGS on Xbox Series (Dev Mode)

Early test build: engine boots with the **software renderer** so we can confirm
the port works before switching to OpenGL.

## What's in the zip

| File | What it is |
|---|---|
| `Xash3DXbox-x64.appx` | The app |
| `Microsoft.VCLibs.x64.14.00.appx` | C++ runtime the app needs (install as a dependency) |
| `Xash3DXbox.cer` | Signing certificate (not needed on Xbox, kept for PC testing) |

## Install

1. On the Xbox (Dev Mode home), note the **Remote Access** address and open it in a
   browser on your PC (Xbox Device Portal).
2. **Home → My games & apps → Add**.
3. Pick `Xash3DXbox-x64.appx`, click **Next**, then add
   `Microsoft.VCLibs.x64.14.00.appx` as a dependency, and **Start** the install.
4. In the app list, open the app's **View details / Change view** and set it to
   **Game** (gives it far more memory than an App).

## Add your game files

The app reads game data from its **LocalState** folder.

1. In Device Portal open **File explorer → LocalAppData →
   HavocMasterChief.Xash3DXbox_… → LocalState**.
2. Upload your **`valve`** folder from your Steam install
   (`Steam\steamapps\common\Half-Life\valve`), keeping the folder structure.
   Device Portal uploads files, not folders, so recreate the subfolders
   (`maps`, `models`, `sound`, `sprites`, `gfx`, …) and upload into each, or
   use a tool like `XboxDevModeFileManager` / an FTP app.

## Run and report back

Launch the app. If it crashes or shows an error:

- `LocalState/engine.log` has the engine's full log (download it in File explorer).
- Note any error box text.

Send both back and we'll fix the next build.
