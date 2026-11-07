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
2. Device Portal uploads single files, not folders, and the `valve` folder has
   thousands of them. Pack it into one archive instead:
   1. On your PC, open `Steam\steamapps\common\Half-Life\valve`.
   2. Select **everything inside it** (not the folder itself) and zip it
      (right-click → *Compress to ZIP file*).
   3. Rename the zip to **`hl_content.pk3`** (Xash3D reads zip files named `.pk3`
      straight from the game folder).
3. In **LocalState**, create a folder named **`valve`** and upload into it:
   - `hl_content.pk3`
   - `liblist.gam` (copy it loose from the Steam `valve` folder too, the engine
     looks for it before opening any archives)

## Run and report back

Launch the app. If it crashes or shows an error:

- `LocalState/engine.log` has the engine's full log (download it in File explorer).
- Note any error box text.

Send both back and we'll fix the next build.
