# File formats

Notes from reading the Command & Conquer Remastered Collection data files.
Everything here was derived by inspecting the shipped archives; offsets were
verified against all 22 `.MEG` files of a retail install.

All integers are little-endian.

---

## Petroglyph MEG, version 3

Used by every `.MEG` in `Data/`.

### Header

| Offset | Type | Field |
| ---: | --- | --- |
| 0 | `uint32` | `0xFFFFFFFF` — optional prefix; when absent the magic is at offset 0 |
| 4 | `uint32` | `0x3F7D70A4` — magic |
| 8 | `uint32` | `data_start` — first byte of payload |
| 12 | `uint32` | `num_filenames` |
| 16 | `uint32` | `num_files` |
| 20 | `uint32` | `filename_table_size` in bytes |

`0xFFFFFFFF` conventionally marks an encrypted header, but the Remastered
Collection ships this prefix with the tables in plain text — so detect the
magic rather than assuming encryption.

### Filename table

Starts right after the header, `filename_table_size` bytes long,
`num_filenames` entries:

```
uint16 length
char   name[length]     // ASCII, NOT null-terminated
```

Paths use backslashes: `DATA\AUDIO\MUSIC\TDR_MUS_ACT_ON_INSTINCT.WAV`.
The table is sorted alphabetically, which is *not* the order of the payload.

### File table

`num_files` records of 20 bytes, immediately after the filename table.
Padding may follow the table before `data_start`; there is none before it.

**The records are packed unaligned** — the 32-bit fields are not on 4-byte
boundaries. Reading them with an aligned struct is the usual reason a MEG
parser produces nonsense:

| Offset | Type | Field |
| ---: | --- | --- |
| 0 | `uint16` | flags |
| 2 | `uint32` | CRC32 of the lowercased filename |
| 6 | `uint32` | record index |
| 10 | `uint32` | file size |
| 14 | `uint32` | file offset |
| 18 | `uint16` | index into the filename table |

Records are ordered by CRC32, so record *n* is not filename *n* — always go
through the `name_index` field.

```python
size, offset = struct.unpack_from("<II", records, i * 20 + 10)
name_index   = struct.unpack_from("<H",  records, i * 20 + 18)[0]
```

### Verification

For `MUSIC.MEG` every one of the 203 records points at a valid `RIFF`/`WAVE`
header and its stored size equals the RIFF size field + 8 — a cheap and
complete self-check for any implementation.

---

## MASTERTEXTFILE_&lt;LANG&gt;.LOC

The localisation string table, inside `CONFIG.MEG` at
`DATA\TEXT\MASTERTEXTFILE_<LANG>.LOC`.

```
uint32 count
count × {
    uint32 key_hash
    uint32 value_length     // in UTF-16 characters, not bytes
    uint32 key_length       // in bytes
}
```

Then the strings, and this is the part worth knowing: the values and the keys
are **two separate blocks**, not interleaved per record.

```
all values, concatenated, UTF-16LE, no terminators
all keys,   concatenated, ASCII,    no terminators
```

So value *i* and key *i* are found by summing the preceding lengths within
their own block. The file ends exactly at the end of the key block, which
makes for a precise sanity check:

```
4 + count*12 + Σ(value_length)*2 + Σ(key_length) == filesize
```

Records are sorted by `key_hash`.

---

## The jukebox track list

`CONFIG.MEG` → `DATA\XML\AUDIO\AUDIO_SYSTEM_CONSTANTS.XML`, element
`<MusicJukeboxTracksList>`. This is the list the in-game jukebox is built
from; `MUSICEVENTS.XML` only points at it in a comment.

```xml
<entry Name="Act_On_Instinct">
    <FileName> TDR_MUS_Act_On_Instinct.wav </FileName>
    <TextID> TEXT_MUSIC_TDR_MUS_ACT_ON_INSTINCT </TextID>
    <TrackType> Remaster </TrackType>
    <TrackLengthSeconds> 166 </TrackLengthSeconds>
    <Game> Tiberian_Dawn </Game>
    <BonusContentUnlock> False </BonusContentUnlock>
</entry>
```

`FileName` matches the basename in `MUSIC.MEG` case-insensitively; `TextID` is
a key in the `.LOC` table. Both sides cover all 203 tracks exactly.

### Two details

**`&&` means a single `&`.** The UI framework escapes ampersands, so
`Grinder 1 && 2 Medley` is displayed as `Grinder 1 & 2 Medley`.

**Music titles are not translated.** `MASTERTEXTFILE_DE-DE.LOC` and
`MASTERTEXTFILE_EN-US.LOC` return byte-identical strings for all 203
`TEXT_MUSIC_*` keys, so the language choice does not affect the output.

---

## Audio

Every track in `MUSIC.MEG` is a RIFF/WAVE file with format tag `0x0002`
(Microsoft ADPCM):

| Layout | Count | Corresponds to |
| --- | ---: | --- |
| stereo 44100 Hz | 114 | Remastered and Bonus |
| mono 22050 Hz | 84 | Classic (the 1995/96 originals) |
| stereo 44101 Hz | 4 | — |
| stereo 44099 Hz | 1 | — |

The off-by-one sample rates are in the source files themselves; ffmpeg
resamples them to 44100 Hz without complaint.
