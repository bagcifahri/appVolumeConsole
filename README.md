# Application Volume Console (NVDA add-on)

[Türkçe](README.tr.md)

Control the volume, mute state and the input and output devices of each Windows application that uses audio, from a single NVDA command layer.

## Usage

Press **NVDA+Windows+S** to open the console. You can change this gesture in NVDA menu > Preferences > Input gestures, under "Application Volume Console".

| Key | Action |
| --- | --- |
| Right / left arrow | Next / previous application |
| Home / End | First / last application |
| Up / down arrow | Increase / decrease volume |
| M | Mute / unmute |
| Alt + up / down arrow | Change the output device |
| Control + up / down arrow | Change the input device |
| Space | Report the current application again |
| F1 | List the commands |
| Escape | Close the console |

Any other key closes the console with a short beep. The console also closes when another window comes to the foreground.

Each application is announced as "name, volume (or "muted"), output device, input device". When an application uses the Windows default device, it is announced as "default (device name)". The first entry in the device list is "default", which makes the application follow the Windows default device again.

## Settings

The "Application Volume Console" category in NVDA settings contains:

- **When the console opens, start from:** the application in focus (default) or the first application in the list.
- **Volume step:** how many percent the arrow keys change the volume, from 1 to 25 (default 5).

## Notes

- The list contains the applications shown in the Windows Volume Mixer, that is, applications that have opened an audio session. The application that was in focus when the console was opened is also listed: its device can be chosen even before it plays audio.
- Choosing a device per application uses the same undocumented Windows interface as the "App volume and device preferences" page of Windows Settings. Some applications only switch to the new device after their audio restarts.

## Building

```
python build.py
```

This compiles the translations and creates `appVolumeConsole-<version>.nvda-addon` from the `addon` folder. Pushing a tag such as `v1.0.0` to GitHub builds the package and attaches it to a GitHub release.

## License

GNU General Public License, version 2. See [COPYING.txt](COPYING.txt).
