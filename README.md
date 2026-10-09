# HTML to JPEG Converter

A small desktop app that turns an HTML file (or a web page URL) into a single, full-length, high-resolution **JPEG**. It uses [Playwright](https://playwright.dev/python/) (headless Chromium) to render the page and [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) for the window.

It is built for report and landing-page style HTML, where the usual "print to image" approach leaves blank sections or large empty gaps at the bottom.

## Features

- **Full-page capture in one image.** The page is measured after layout and captured at its exact content height, with no extra blank space.
- **Adjustable resolution.** Choose 1x to 6x, or type a custom scale such as `4.5`. Higher scales give sharper text.
- **Automatic size limit.** Chromium cannot render images larger than 32,767 pixels per side. If your chosen scale would go past that on a very tall page, the app lowers the scale automatically and tells you.
- **Scroll-reveal sections are made visible.** Sections that normally fade in as you scroll are forced visible, so they are not captured blank.
- **Forced full-height layouts are relaxed.** Wrappers styled with `100vh` (common in A4 or print-style templates) are allowed to shrink to their content.
- **Waits for the page to settle.** The app waits for network activity and webfonts to finish loading before it measures and captures.
- **Responsive window.** Conversion runs in the background, so the window does not freeze.

## Requirements

- Python 3.9 or newer
- The packages in `requirements.txt` (`customtkinter`, `playwright`)
- Playwright's Chromium browser (a download of a few hundred MB, installed once)

## Installation

```bash
git clone <your-repository-url>
cd <repository-folder>
pip install -r requirements.txt
python -m playwright install chromium
```

On Linux, tkinter may need `sudo apt install python3-tk`. On macOS, use the Python from python.org, because the one bundled with Xcode often ships an outdated Tk.

## Usage

```bash
python htmlconvert.py
```

1. Click **Browse** next to *Input HTML file* and choose your `.html` or `.htm` file. You can also paste an `http://` or `https://` address into the box.
2. Click **Browse** next to *Output JPEG file* and choose where to save the result.
3. Pick a **Resolution scale** (default 2x).
4. Click **Convert to JPEG**. A message appears when it finishes.

### Resolution guide

The page is rendered at a fixed viewport width of 1280 px, then multiplied by the scale.

| Scale | Output width |
|---|---|
| 1x (standard) | 1,280 px |
| 2x (sharp) | 2,560 px |
| 3x (extra sharp) | 3,840 px |
| 4x (ultra) | 5,120 px |
| 5x (max) | 6,400 px |
| 6x | 7,680 px |

The height grows with your content. Higher scales produce larger files and take longer. JPEG quality is fixed at 100.

## Notes and limitations

- **The scroll-reveal fix targets specific class names:** `.reveal`, `.capital-card`, `.output-card`, `.outcome-card` and `.activity-col`. If your page hides sections with different class names or an animation library, some sections may still be blank. Add your class names to the CSS block in `html_to_jpeg()` in `htmlconvert.py`.
- **The height fix targets common wrapper names:** `.page`, `.container`, `.a4`, `.report-page`, `.sheet`, `.wrapper`, `.content` and `main`, plus `html` and `body`. A layout that intentionally relies on `100vh` may look different in the image.
- **External resources need internet.** Fonts, icons and scripts loaded from a CDN must be reachable, because the app waits for the network to go idle.
- **JPEG has no transparency.** Transparent areas are rendered on a white background.
- **Very tall pages** are captured at a reduced scale when needed (see the size limit above).
- **Paths on macOS and Linux:** the file URL is built for Windows-style paths. If a local file fails to load on macOS or Linux, tell the app to use a full `file://` address in the input box.

## Troubleshooting

| Problem | Fix |
|---|---|
| `Executable doesn't exist at ...` | The browser isn't installed. Run `python -m playwright install chromium`. |
| `No module named 'playwright'` or `'customtkinter'` | Run `pip install -r requirements.txt` with the same Python you use to start the app. |
| Some sections are blank | See the scroll-reveal note above. |
| Conversion hangs or times out | The page may keep loading something from the network. Check your connection and try again. |

## Security note

The app opens your page in a real browser engine, so the page's JavaScript runs. Only convert HTML files and URLs you trust.

## Building an executable

PyInstaller cannot cross-compile, so build on the operating system you are targeting, using the same Python that has the packages installed. Following the Playwright documentation, set `PLAYWRIGHT_BROWSERS_PATH=0` first so Chromium is installed inside the Playwright package and gets bundled. The result is a large executable.

Windows (PowerShell):

```powershell
$env:PLAYWRIGHT_BROWSERS_PATH="0"
python -m playwright install chromium
python -m pip install pyinstaller
python -m PyInstaller --onefile --windowed --collect-all customtkinter --collect-all playwright htmlconvert.py
```

The executable appears in `dist/`. While testing, leave out `--windowed` so any error shows in a console. Some antivirus programs flag PyInstaller executables; this is a known false positive.

## License

Released under the [MIT License](LICENSE).
