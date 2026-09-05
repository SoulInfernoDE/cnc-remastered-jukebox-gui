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

The window is frameless, so only the jukebox itself is on screen — which is
why it carries a drawn icon for the task bar and the window switcher: a
jukebox cabinet in the current skin's colours, its screen showing that game's
own emblem out of the atlas over two round speakers in the accent colour. It
follows the skin, so changing the skin changes the icon too.

The window is frameless, so only the jukebox itself is on screen. Drag it by
any empty part of the panel; Escape or *Exit* closes it, F11 toggles
fullscreen, Space toggles playback.

Left-click a track to select it, right-click to move it between the two lists,
double-click to play. The four plate buttons, the filters, shuffle, the gap and
volume sliders and the progress bar all behave as they do in the game.

A second copy of the emblem sits to the right of the playback bar, mirroring
the play button on the other side of it and turning off the same angle, so the
two stay in step.

The emblem of the track currently playing turns while it plays, as a struck
token rather than a sheet of paper. Rotating a plane about its vertical axis
puts a point at `x·cos θ + z·sin θ`. The axis runs through the middle of the
material, so `z` spans `-T/2` to `+T/2` rather than hanging off one face: the
two faces land at `±T/2·sin θ`, the silhouette stays centred, and the token
turns in place instead of swinging sideways. Which face is visible follows the
same angle — depth on the axis is `z·cos θ`, so the near plane flips with the
sign of cos, and at that moment the visible face is mirrored, moved to the
other offset, and the slices are drawn in reverse. Measured over a full turn
the silhouette's centroid stays within 5 px of the axis and never moves more
than 1 px per 5 degrees; what remains is the emblem's own asymmetry, which a
real object would show too.

The playlist, filters, volume and chosen skin are kept in
`~/.config/cnc-jukebox/playlist.json`.

**Exit** closes the jukebox, with EVA signing off in that game's own voice.
The button beside it switches screens and is named after where it leads:
**Soundbox** from the jukebox, **Jukebox** from the sound box. The playlist and
settings are written on close either way.

"Soundbox" names a screen the game does not have, so it and the two hover
hints are the only text here not read out of the installation. The
destination's own name still comes from the string table where one exists —
`TEXT_JUKEBOX` is localised, and reads "Музыкальный плеер" in Russian.

### The sound box

Two catalogues read from the installation, side by side:

- **Left** — every effect in the game, 1286 of them, grouped by game, fidelity
  and kind, and played on click. Spoken lines show what they actually say:
  the string table files those under `TEXT_SFX_<stem>` with the `EVA_`/`UNT_`
  part dropped, which covers 369 of them. Only the classic-prefix keys are
  translated, so those are preferred; where the game itself never translated a
  line it stays English here too, exactly as in the game.
- **Right** — 409 units, structures and effects, each animated from its own
  sprite frames. The archives keep them as one zip of uncompressed TGA per
  object, listed by `TD_UNITS.XML` and friends; only the selected object is
  decoded, downscaled, and kept.

They sit side by side rather than one deriving the other, and that is
deliberate: **the games ship no mapping from a sound to "its" unit or
building.** Checking all 508 sound stems against all 192 object names yields
no match at all, and the few substring hits are coincidence. Pairing them
would mean inventing the pairing.

### The three header controls

Hover any of them for a hint. Red Alert's header carries round brass bolts and
Tiberian Dawn's carries hex heads, sitting higher and further out, so the hover
outline follows the shape and position each skin actually has — measured on the
textures rather than assumed.

- **Left fastener** — opens this branch on GitHub, with EVA saying thank you
  in that game's own voice. Like the other lines, the two games file it under
  different stems: `EVA_ETHANKS` for Tiberian Dawn, `EVA_THANKU1` for Red
  Alert.
- **Folder** — opens the soundtrack folder, drawn in the current skin's colour.
  That is the same folder `cnc_trackexport` writes to by default.
- **Right fastener** — changes the skin, the way the game puts up a building: the
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

Press Play and the game starts exactly as before — same launcher, same
everything — with a Jukebox button in the launcher's own style beside it, drawn
from the launcher's own artwork. One click opens the jukebox; it closes with
the game.

For the jukebox on its own, without Steam in the way:

```bash
./tools/install-desktop-entry      # --remove takes it back out
```

That puts it in the application menu with the skin's icon, one click from
anywhere. It writes only inside `~/.local/share`.

### It does not disturb Steam

The wrapper runs Steam's own command unchanged and waits for it, so Steam
keeps tracking the game it launched: play time, the overlay, and the "In-Game"
state your friends see all behave as they always did. Nothing is patched,
replaced or injected, and the game's own files are never touched.

It is also transparent about failure, which is what keeps Steam from being
left hanging. Tested: a normal run returns 0 and the button is gone; a missing
command returns 127; a game exiting 42 passes 42 straight through. In every
case the companion window is closed, on any exit path, including a kill.

> Verified here as far as a single machine allows. Whether your friends list
> shows "In-Game" is Steam's own bookkeeping about the process it started, and
> a launch-option wrapper is the ordinary way to sit in front of that — the
> same shape `gamemoderun` and `mangohud` use. I could not observe another
> account's view of it from this machine.

### Why not a Workshop item

Because the Workshop cannot reach the launcher. Looking at what installed
Workshop items actually contain, an item is either a map (`MAPDATA.PGM`) or a
game-logic mod — a `ccmod.json` beside `CCDATA/*.INI` rules and sometimes a
rebuilt game DLL. Those are loaded by the game after it starts.

The launcher is `ClientLauncherG.exe`, a separate Windows executable that runs
*before* the game and reads no mod data at all, so nothing shipped through the
Workshop is in a position to add a button to it.

Replacing it was the other idea, and it does not work either: `ClientG.exe`
takes no game-selection argument, and the launcher records the choice nowhere —
`Software\Petroglyph\CnCRemastered\Launcher` in the prefix holds two thread
flags and nothing else. A stand-in chooser could only hand off to the real
launcher, putting a second selection step in front of the game rather than
taking one away. Sitting beside it costs nothing and takes nothing away.

## What this is good for

- **The soundtrack without the game.** Twelve hours of it, playing while you do
  something else, without a 26 GB game running to hear it.
- **The jukebox the game keeps to itself.** In the game it is reachable only
  from a menu and only while the game runs; here it is a window like any other,
  and its playlist survives independently.
- **Every track, not only the unlocked ones.** The Classic recordings and the
  Bonus arrangements sit in the same list as the Remastered ones, filtered
  however you like.
- **The tracks as files.** `cnc_trackexport` writes all 203 with the names the
  jukebox shows, into the game's own folder, as MP3 or lossless FLAC — for a
  phone, a car, or anywhere the game will never run.
- **Nothing is modified.** No patched binaries, no replaced files, no injected
  code. Both programs read the installation and write only their own output, so
  there is nothing to undo and nothing for an update to break.
- **It is documented.** The container, string-table and layout formats are
  written down in `docs/`, so the next person does not have to work them out
  from hex dumps again.


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
