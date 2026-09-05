# cnc-remastered-jukebox — `gui` branch

A rebuild of the game's music jukebox as a standalone Linux window: the same
layout, the same skin, the same typefaces, the same captions in your system's
language. Nothing is redistributed — every pixel and every string is read out
of your own installation at runtime.

```bash
./cnc-jukebox                 # Soviet skin, system language
./cnc-jukebox -s allied       # Red Alert, Allied
./cnc-jukebox -s td           # Tiberian Dawn
./cnc-jukebox -l EN-US        # override the language
```

The stable soundtrack exporter lives on the [`export`](../../tree/export)
branch; this branch carries it too.

## What makes it a rebuild rather than a lookalike

Nothing here is eyeballed from a screenshot. Every part is read from the game:

| Element | Source |
| --- | --- |
| Geometry of all ~40 widgets | `.BUI` layout files in `CONFIG.MEG` |
| Frame, panels, scanlines, menu backdrop | `TEXTURES_SRGB.MEG` |
| Emblems, buttons, checkboxes, sliders, play button | `MT_COMMANDBAR_COMMON`, the shared sprite atlas |
| Typefaces (RA_Orbitron, Francker, Noto CJK) | `DATA\ART\FONTS` in `CONFIG.MEG` |
| Every caption and label | `MASTERTEXTFILE_<LANG>.LOC` |
| Track titles, durations, game, type | `<MusicJukeboxTracksList>` |
| Audio | `MUSIC.MEG` |

The layout numbers come out of the `.BUI` property stream, which stores each
widget as four floats normalised against its parent. That the model is right
is checkable in one line: the frame is stored as 0.75156 wide by 1.00370 high,
which on a 16:9 screen is exactly the 4:3 of the 2160×1620 frame texture.
See [`docs/JUKEBOX-UI.md`](docs/JUKEBOX-UI.md).

## Language

The captions follow the system locale — `LC_ALL`, `LC_MESSAGES`, `LANG`, then
`LANGUAGE` — mapped onto the nine languages the game ships (EN-US, DE-DE,
ES-ES, FR-FR, KO-KR, PL-PL, RU-RU, ZH-CN, ZH-TW), falling back to EN-US.
Korean and Chinese render through the game's own Noto CJK font.

Where a caption looks untranslated, that is the game's data, not a gap here:
the Korean table, for instance, genuinely leaves "Available Tracks" and
"Jukebox Music Volume" in English.

## Requirements

- Command & Conquer Remastered Collection, installed
- Linux, `python3` 3.6+, `PyQt5`
- `ffmpeg` for decoding, and one of `paplay`, `aplay` or `ffplay` for output

```bash
sudo apt install python3-pyqt5 ffmpeg      # Debian / Ubuntu
sudo dnf install python3-qt5 ffmpeg        # Fedora (ffmpeg via RPM Fusion)
sudo pacman -S python-pyqt5 ffmpeg         # Arch
```

Qt Multimedia is deliberately not used: its audio plugins ship in a separate
package that is often missing, and `QAudioOutput` then falls back to a silent
null device without saying so. Tracks are decoded with ffmpeg and written to
`paplay`/`aplay`/`ffplay` instead, which works wherever the desktop has sound.

## Using it

The window is frameless, so only the jukebox itself is on screen. Drag it by
any empty part of the panel; Escape or *Exit* closes it, F11 toggles
fullscreen, Space toggles playback.

Left-click a track to select it, right-click to move it between the two lists,
double-click to play. The four plate buttons, the filters, shuffle, the gap and
volume sliders and the progress bar all behave as they do in the game.

The emblem of the track currently playing turns while it plays, as a struck
token rather than a sheet of paper: the face is foreshortened while copies of
the emblem's own outline fill the thickness behind it, the nearest slice lit,
so edge-on it shows a solid rim instead of disappearing.

The playlist, filters, volume and chosen skin are kept in
`~/.config/cnc-jukebox/playlist.json`.

**Exit** closes the jukebox. **Apply** writes the playlist and settings out
there and then and stays open, confirming with the number of tracks it stored.
The window saves on close as well, so Apply is the deliberate "keep this, I am
done editing". In the game that button hands the playlist to the battle that
follows; standing on its own there is nothing to hand it to, so it commits the
file instead.

### The three header controls

Hover any of them for a hint.

- **Left bolt** — opens this project on GitHub.
- **Folder** — opens the soundtrack folder, drawn in the current skin's colour.
  That is the same folder `cnc_trackexport` writes to by default.
- **Right bolt** — changes the skin, the way the game puts up a building: the
  next faction's emblem appears across the whole player, EVA announces the
  construction, a build clock sweeps once around over three seconds, the
  "construction complete" line plays, and the new skin drops in with that
  game's building-placement sound. Each of those is the game's own audio, in
  your language, from `SFX2D_<LANG>.MEG` and `SFX3D.MEG`.

## Alongside the game

Set the title's Steam launch options to:

```
/full/path/to/tools/steam-launch-wrapper %command%
```

Steam substitutes the real launch command, which the wrapper runs unchanged,
so the game starts exactly as before; the jukebox opens next to it and closes
with it.

## Not reproduced

- **The launcher window.** The window that appears when you press Play in
  Steam belongs to `ClientLauncherG.exe`. Its artwork *is* recoverable — the
  whole interface sits in that executable's PE resources as uncompressed
  bitmaps — but unlike the jukebox it has no `.BUI`, so the layout would have
  to be measured by hand. Not done yet.
- **No screenshots in this repository.** Any picture of the running window
  would be a picture of EA's artwork.

# cnc_trackexport

Exports the full soundtrack of the **Command & Conquer Remastered Collection**
as tagged MP3s — with filenames that match, character for character, the track
titles the game shows you in its own jukebox.

```
Act On Instinct (Classic).mp3
Act On Instinct (Remastered).mp3
Act On Instinct – OST Version (Remastered).mp3
Act On Instinct – Tiberian Sons (Bonus).mp3
Grinder 1 & 2 Medley – Tiberian Sons (Bonus).mp3
Hell March Original Demo (Bonus, Unlocked).mp3
We Will Stop Them ∕ Deception (Remastered).mp3
```

203 tracks, 12 hours 6 minutes, ~1.6 GiB.

> **You need your own copy of the game.** This repository contains no game
> data, no audio and no artwork — only a script that reads the files already
> on your disk. Linux only.

---

## The problem it solves

Inside `MUSIC.MEG` the tracks are called `TDR_MUS_ACT_ON_INSTINCT.WAV` and
`RAB_MUS_HM_2_3_MEDLEY_FKTS.WAV`. Nothing in that archive tells you those are
"Act On Instinct (Remastered)" and "Hell March 2 & 3 Medley – Tiberian Sons
(Bonus)". Most extractors therefore leave you with the raw internal names, or
guess at prettier ones.

The real titles are in a different archive. `cnc_trackexport` reads them from
where the game itself reads them:

| Source | What it provides |
| --- | --- |
| `Data/MUSIC.MEG` | the audio (Petroglyph MEG V3 container) |
| `Data/CONFIG.MEG` → `AUDIO_SYSTEM_CONSTANTS.XML` | `<MusicJukeboxTracksList>` — literally the jukebox list: filename → text id |
| `Data/CONFIG.MEG` → `MASTERTEXTFILE_<LANG>.LOC` | text id → the displayed title |

The mapping is complete and exact: **203 jukebox entries ↔ 203 audio files ↔
203 localised titles**, with nothing left over on either side. No guessing, no
lookup table to maintain.

## Requirements

- Command & Conquer Remastered Collection, installed (Steam, Origin/EA, GOG)
- Linux
- `python3` (3.6 or newer)
- `ffmpeg` with `libmp3lame` — only for MP3/FLAC output

```bash
sudo apt install python3 ffmpeg      # Debian / Ubuntu
sudo dnf install python3 ffmpeg      # Fedora (ffmpeg via RPM Fusion)
sudo pacman -S python ffmpeg         # Arch
```

## Usage

```bash
git clone https://github.com/SoulInfernoDE/cnc-remastered-jukebox.git
cd cnc-remastered-jukebox
./cnc_trackexport
```

That is all. The game directory is found automatically — standard Steam,
Flatpak, Snap, and any extra library listed in `libraryfolders.vdf`.

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

`CNC_REMASTERED_DIR` overrides the search if autodetection fails.\n\nBy default the tracks go to the game's own user folder — `Documents/CnCRemastered/Soundtrack` inside the Proton prefix, next to\n`Mods`, `Save` and `Replays`, which Steam leaves alone on updates. The\njukebox's folder button opens exactly that directory. Use `--out` for\nsomewhere else.

By default the tracks go to the game's own user folder —
`Documents/CnCRemastered/Soundtrack` inside the Proton prefix, next to `Mods`,
`Save` and `Replays`, which Steam leaves alone on updates. If that folder
cannot be found the music directory is used instead. `--out` overrides it, and
the destination is always printed before encoding starts.

Interrupting with Ctrl+C is safe: partial files are removed, and the next run
resumes where it stopped.

## Audio quality

Everything is encoded at **44.1 kHz / 320 kbps**, including the Classic
tracks — and the sample rate is the point, not a cosmetic detail.

The Classic tracks are mono 22.05 kHz MS-ADPCM. Encoding MP3 at that rate puts
LAME into MPEG-2 Layer III, which is capped at 160 kbps and, measured against
these sources, also rolls off around 9.9 kHz — while the source carries content
up to 10.5 kHz. Resampling to 44.1 kHz first keeps LAME in MPEG-1 and preserves
the material:

| | encoded at 22.05 kHz | resampled to 44.1 kHz |
| --- | --- | --- |
| spectral error vs. source | −10.1 dB | **−39.2 dB** |
| energy above 9.9 kHz retained | 16 % | **100 %** |

(Measured on the decoded output against the decoded ADPCM source, averaged
over 8192-sample frames — a phase-independent comparison, so encoder delay
cannot flatter the result.)

### Lossless output

`--format flac` is the archival option. It keeps each track at its original
sample rate and is **bit-exact**: decoding the FLAC and decoding the source
ADPCM produce byte-identical PCM (verified by comparing MD5 sums of the raw
decoded streams for all three sample-rate variants in the archive). Tags and
cover art are embedded exactly as they are for MP3.

It costs roughly 2.5× the space of the MP3 export — about 3.3 GiB — because
the source is 4-bit ADPCM while FLAC stores the decoded 16-bit PCM losslessly.

`--format wav` is the third option: the untouched ADPCM files straight out of
the archive, byte for byte, with no tags and no re-encoding. Smallest of the
three (~1.4 GiB), but awkward for most players.

## Tags

`title` carries the exact jukebox title, `artist` switches to
"Frank Klepacki & The Tiberian Sons" for the Tiberian Sons arrangements, and
`grouping`/`comment` hold the game and track type ("Red Alert Bonus"), so a
library can separate Classic, Remastered and Bonus at a glance. Track numbers
follow the jukebox's own alphabetical order.

Nine titles contain a literal `/` ("Warfare / Full Stop"), which no filename
can hold. Those use U+2215 DIVISION SLASH — visually identical and valid on
ext4, NTFS and FAT32 alike. The `title` tag always keeps the real character.
`--portable` reduces filenames to plain ASCII if you need that.

## Notes on how it works

The container and string-table formats are documented in
[`docs/FILE-FORMATS.md`](docs/FILE-FORMATS.md), including the detail that trips
up most MEG readers: the 20-byte file records are packed **unaligned**, so the
32-bit fields do not sit on 4-byte boundaries.

Nothing is written outside the output directory, and no temporary files are
created at all — audio is piped to ffmpeg through stdin and the cover art is
held in an anonymous memory file (`memfd_create`) handed over as `/dev/fd/N`.
When the run finishes, the output directory contains the finished tracks and
nothing else.

## Also in this repository

The [`gui`](../../tree/gui) branch carries a rebuild of the game's own music
jukebox as a standalone Linux window — the same layout, skin and typefaces,
with every caption in your system's language. It reads all of that from your
installation at runtime, the same way this exporter reads the track names: the
widget geometry comes out of the `.BUI` layout files, the skin out of
`TEXTURES_SRGB.MEG`, and the fonts out of `CONFIG.MEG`.

It is a separate program with its own requirements (PyQt5 on top of ffmpeg),
so it lives on its own branch rather than here. This branch stays what it is:
one script, no install, no extra dependencies.

## Legal

This is an unofficial fan project. It is **not affiliated with, endorsed by, or
sponsored by** Electronic Arts, Petroglyph Games or Valve. "Command & Conquer",
"Red Alert" and "Tiberian Dawn" are trademarks of Electronic Arts Inc.

The repository ships no game content whatsoever — no audio, no artwork, no
extracted data, and no code from the game. It reads only files that a licensed
installation already put on your own machine, and is intended for personal use
with a copy you own. Do not redistribute what it produces.

By default the script fetches the game's public Steam store image at runtime to
embed as cover art for your personal files. That image is EA's; it is never
stored in this repository. Use `--no-cover` to skip it.

The music is by Frank Klepacki (and, for the Bonus arrangements, Frank Klepacki
& The Tiberian Sons).

## License

[MIT](LICENSE) — applies to this script only, not to anything it extracts.
