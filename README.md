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

`CNC_REMASTERED_DIR` overrides the search if autodetection fails.

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
