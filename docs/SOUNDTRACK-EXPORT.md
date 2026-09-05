# Exporting the soundtrack

***English** · [Deutsch](SOUNDTRACK-EXPORT.de.md)*

Notes on `cnc_trackexport`: where the titles come from, why everything is
resampled, and what the lossless option guarantees.

---

## Where the real titles come from

Inside `MUSIC.MEG` the tracks are called `TDR_MUS_ACT_ON_INSTINCT.WAV` and
`RAB_MUS_HM_2_3_MEDLEY_FKTS.WAV`. Nothing in that archive says those are "Act
On Instinct (Remastered)" and "Hell March 2 & 3 Medley – Tiberian Sons
(Bonus)". Most extractors therefore leave you with the raw internal names, or
guess at prettier ones.

The real titles are in a different archive, and the exporter reads them from
where the game itself reads them:

| Source | What it provides |
| --- | --- |
| `Data/MUSIC.MEG` | the audio (Petroglyph MEG V3 container) |
| `Data/CONFIG.MEG` → `AUDIO_SYSTEM_CONSTANTS.XML` | `<MusicJukeboxTracksList>` — literally the jukebox list: filename → text id |
| `Data/CONFIG.MEG` → `MASTERTEXTFILE_<LANG>.LOC` | text id → the displayed title |

The mapping is complete and exact: **203 jukebox entries ↔ 203 audio files ↔
203 localised titles**, with nothing left over on either side. No guessing, no
lookup table to maintain.

The container and string-table formats are written up in
[`FILE-FORMATS.md`](FILE-FORMATS.md), including the detail that trips up most
MEG readers: the 20-byte file records are packed **unaligned**, so the 32-bit
fields do not sit on 4-byte boundaries.

## Why everything is resampled to 44.1 kHz

MP3 output is always **44.1 kHz / 320 kbps**, including the Classic tracks —
and the sample rate is the point, not a cosmetic detail.

The Classic tracks are mono 22.05 kHz MS-ADPCM. Encoding MP3 at that rate puts
LAME into MPEG-2 Layer III, which is capped at 160 kbps and, measured against
these sources, also rolls off around 9.9 kHz — while the source carries content
up to 10.5 kHz. Resampling to 44.1 kHz first keeps LAME in MPEG-1 and preserves
the material:

| | encoded at 22.05 kHz | resampled to 44.1 kHz |
| --- | --- | --- |
| spectral error vs. source | −10.1 dB | **−39.2 dB** |
| energy above 9.9 kHz retained | 16 % | **100 %** |

Measured on the decoded output against the decoded ADPCM source, averaged over
8192-sample frames — a phase-independent comparison, so encoder delay cannot
flatter the result.

## Lossless output

`--format flac` is the archival option. It keeps each track at its original
sample rate and is **bit-exact**: decoding the FLAC and decoding the source
ADPCM produce byte-identical PCM, verified by comparing MD5 sums of the raw
decoded streams for all three sample-rate variants in the archive. Tags and
cover art are embedded exactly as they are for MP3.

It costs roughly 2.5× the space of the MP3 export — about 3.3 GiB — because the
source is 4-bit ADPCM while FLAC stores the decoded 16-bit PCM losslessly.

`--format wav` is the third option: the untouched ADPCM files straight out of
the archive, byte for byte, with no tags and no re-encoding. Smallest of the
three (~1.4 GiB), but awkward for most players.

## Tags and filenames

`title` carries the exact jukebox title. `artist` switches to "Frank Klepacki &
The Tiberian Sons" for the Tiberian Sons arrangements, and `grouping` and
`comment` hold the game and track type ("Red Alert Bonus"), so a library can
separate Classic, Remastered and Bonus at a glance. Track numbers follow the
jukebox's own alphabetical order.

Nine titles contain a literal `/` ("Warfare / Full Stop"), which no filename
can hold. Those use U+2215 DIVISION SLASH — visually identical and valid on
ext4, NTFS and FAT32 alike. The `title` tag always keeps the real character.
`--portable` reduces filenames to plain ASCII if you need that.

## Nothing lands outside the output directory

No temporary files are created at all. Audio is piped to ffmpeg through stdin,
and the cover art is held in an anonymous memory file (`memfd_create`) handed
over as `/dev/fd/N`. When the run finishes, the output directory contains the
finished tracks and nothing else.

Interrupting with Ctrl+C is safe: partial files are removed, and the next run
resumes where it stopped.
