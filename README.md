# cnc-remastered-jukebox

***English** · [Deutsch](README.de.md)*

The music of the **Command & Conquer Remastered Collection**, outside the game.

Two programs, both reading your own installation at runtime:

- **`cnc-jukebox`** — the game's music jukebox rebuilt as a standalone Linux
  window. Same layout, same skin, same typefaces, same captions in your
  system's language.
- **`cnc_trackexport`** — the whole soundtrack as tagged files, named exactly
  the way the jukebox names them.

> **You need your own copy of the game.** This repository ships no audio, no
> artwork, no extracted data and no game code — only programs that read the
> files already on your disk. Linux only.

---

## Why a standalone jukebox

- **The soundtrack without the game.** Twelve hours of it, playing while you do
  something else, without a 26 GB game running to hear it.
- **The jukebox the game keeps to itself.** In the game it is reachable only
  from a menu, and only while the game runs. Here it is a window like any
  other, and its playlist survives independently.
- **Every track, not only the unlocked ones.** Classic recordings and Bonus
  arrangements sit in the same list as the Remastered ones, filtered however
  you like.
- **The tracks as files.** All 203 of them, for a phone, a car, or anywhere the
  game will never run.
- **Nothing is modified.** No patched binaries, no replaced files, no injected
  code. Both programs read the installation and write only their own output, so
  there is nothing to undo and nothing for an update to break.

## Requirements

- Command & Conquer Remastered Collection, installed (Steam, Origin/EA, GOG)
- Linux, `python3` 3.6 or newer
- `ffmpeg` — and, for the jukebox, `PyQt5` plus one of `paplay`, `aplay` or
  `ffplay`

```bash
sudo apt install python3-pyqt5 ffmpeg      # Debian / Ubuntu
sudo dnf install python3-qt5 ffmpeg        # Fedora (ffmpeg via RPM Fusion)
sudo pacman -S python-pyqt5 ffmpeg         # Arch
```

The exporter alone needs neither PyQt5 nor a sound server.

## Install

```bash
git clone https://github.com/SoulInfernoDE/cnc-remastered-jukebox.git
cd cnc-remastered-jukebox
```

There is nothing to build. The game directory is found automatically —
standard Steam, Flatpak, Snap, and any extra library listed in
`libraryfolders.vdf`. `CNC_REMASTERED_DIR` overrides the search if that fails.

To put the jukebox in your application menu, or beside the game's own launcher
when you press Play in Steam, see [`docs/STEAM.md`](docs/STEAM.md).

## The jukebox

```bash
./cnc-jukebox                 # last skin used, system language
./cnc-jukebox -s td           # Tiberian Dawn
./cnc-jukebox -s allied       # Red Alert, Allied
./cnc-jukebox -l EN-US        # override the language
```

The window is frameless, so only the jukebox itself is on screen. Drag it by
any empty part of the panel; Escape or **Exit** closes it, F11 toggles
fullscreen, Space toggles playback.

Left-click a track to select it, right-click to move it between the two lists,
double-click to play. The filters, shuffle, the gap and volume sliders and the
progress bar all behave as they do in the game. The emblem of the playing
track turns while it plays.

Three controls in the header, each with a hover hint:

| | |
| --- | --- |
| **Left fastener** | opens this project on GitHub |
| **Folder** | opens the folder the exporter writes to |
| **Right fastener** | changes the skin, the way the game puts up a building |

Two more at the bottom: **Exit**, and a button that switches between the
jukebox and the **Soundbox** — a second screen listing all 1286 sound effects
in the game beside 409 animated units and structures.

Every button has a voice from the matching game. **Button sounds**, beside
shuffle, turns that off; the music and the sound previews are unaffected.
Settings live in `~/.config/cnc-jukebox/playlist.json`.

## Exporting the soundtrack

```bash
./cnc_trackexport
```

203 tracks, 12 hours 6 minutes, about 1.6 GiB, written to the game's own user
folder by default. The filenames are the titles the jukebox shows, character
for character:

```
Act On Instinct (Classic).mp3
Act On Instinct – Tiberian Sons (Bonus).mp3
Grinder 1 & 2 Medley – Tiberian Sons (Bonus).mp3
Hell March Original Demo (Bonus, Unlocked).mp3
We Will Stop Them ∕ Deception (Remastered).mp3
```

```
  -o, --out DIR      output directory        (default: the game's own folder)
  -g, --game DIR     game directory          (default: autodetected)
  -f, --format FMT   mp3 | flac | wav        (default: mp3)
  -l, --lang LANG    EN-US, DE-DE, ...       (default: EN-US)
  -j, --jobs N       parallel encoders       (default: CPU cores, max 16)
      --no-cover     do not embed artwork
      --portable     restrict filenames to plain ASCII (FAT32 etc.)
      --force        re-encode instead of skipping existing files
      --list         show the mapping, write nothing
  -h, --help         help
```

MP3 is 44.1 kHz at 320 kbps; `--format flac` is bit-exact against the source.
Ctrl+C is safe, and the next run resumes where it stopped.

## How it works

The interesting parts are written down rather than left in the code:

| | |
| --- | --- |
| [`docs/FILE-FORMATS.md`](docs/FILE-FORMATS.md) | the MEG container, the `.LOC` string table, the track list |
| [`docs/JUKEBOX-UI.md`](docs/JUKEBOX-UI.md) | the game's `.BUI` layouts, textures, fonts and sprite atlas |
| [`docs/REBUILD.md`](docs/REBUILD.md) | what the rebuild does with all that, and where the game's data surprises |
| [`docs/SOUNDTRACK-EXPORT.md`](docs/SOUNDTRACK-EXPORT.md) | title mapping, audio quality measurements, tags |
| [`docs/STEAM.md`](docs/STEAM.md) | the launcher companion, and why this is not a Workshop item |

Each of them is also available in German; the link sits at the top of each.

## Branches

The stable exporter lives on [`export`](../../tree/export) on its own, with no
dependencies beyond `python3` and `ffmpeg`. This branch, [`gui`](../../tree/gui),
carries the jukebox and the exporter together.

## No screenshots

Any picture of the running window would be a picture of EA's artwork, so there
are none here.

## Legal

This is an unofficial fan project. It is **not affiliated with, endorsed by, or
sponsored by** Electronic Arts, Petroglyph Games or Valve. "Command & Conquer",
"Red Alert" and "Tiberian Dawn" are trademarks of Electronic Arts Inc.

The repository ships no game content whatsoever — no audio, no artwork, no
extracted data, and no code from the game. It reads only files that a licensed
installation already put on your own machine, and is intended for personal use
with a copy you own. Do not redistribute what it produces.

By default the exporter fetches the game's public Steam store image at runtime
to embed as cover art for your personal files. That image is EA's; it is never
stored in this repository. Use `--no-cover` to skip it.

The music is by Frank Klepacki, and for the Bonus arrangements by Frank
Klepacki & The Tiberian Sons.

## License

[MIT](LICENSE) — applies to this project's own code only, not to anything it
reads or produces.
