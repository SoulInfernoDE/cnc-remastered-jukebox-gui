# The in-game jukebox UI

Groundwork for rebuilding the jukebox faithfully. Everything below was read
out of a retail installation with [`tools/dump-jukebox-ui`](../tools/dump-jukebox-ui);
none of it is shipped in this repository.

```bash
./tools/dump-jukebox-ui -o jukebox_ui
```

---

## Layout definitions (`.BUI`)

Six layouts in `CONFIG.MEG` under `DATA\ART\GUI\`:

| File | Decompressed | Role |
| --- | ---: | --- |
| `UI_MUSICJUKEBOX.BUI` | 37 389 B | the Tiberian Dawn jukebox dialog |
| `RA_UI_MUSICJUKEBOX_ALLIED.BUI` | 40 239 B | Red Alert, Allied skin |
| `RA_UI_MUSICJUKEBOX_SOVIET.BUI` | 40 134 B | Red Alert, Soviet skin |
| `MUSICJUKEBOX.BUI` | 15 806 B | shared base dialog |
| `UI_MUSICJUKEBOX_LIST_ENTRY.BUI` | 1 233 B | one row in the track list |
| `RA_UI_MUSICJUKEBOX_LIST_ENTRY.BUI` | 1 233 B | one row, Red Alert skin |

### Container

A `.BUI` is a 36-byte header beginning with ASCII `CH`, followed by a plain
**zlib stream**:

```python
raw   = open("UI_MUSICJUKEBOX.BUI", "rb").read()
plain = zlib.decompress(raw[raw.find(b"\x78\x9c"):])
```

The decompressed payload is a binary widget tree. It has not been fully
decoded, but widget names, texture references, font names and float colour
components are plainly readable, which is enough to reconstruct the hierarchy.

### Widget tree

`UI_MUSICJUKEBOX.BUI`, in order, contains among others:

```
MusicJukeboxDialog
├─ Background                 → ui_mainmenubg_01
├─ Background_Darken          → beall
├─ Grey_BG                    → beall
├─ Scanlines                  → ui_jukebox_scanlines
├─ Scanlines_Animation / Scanline_Sheen
├─ Frame                      → ui_jukebox_bg
├─ Header
│  └─ Title_Text                          (46 Point Outline)
├─ Functionality_Notificiation_Text       (18 Point Outline)   [sic]
├─ Available_Songs
│  ├─ Available_Songs_Text                (22 Point Outline)
│  ├─ Available_Songs_Listbox_Sample_Entry
│  └─ V_Scroll_Bar  → UI_Slider_Track_Left / _Middle / _Right
…
```

One list row (`UI_MUSICJUKEBOX_LIST_ENTRY.BUI`) is just four elements:

```
UI_Jukebox_List_Element
├─ UI_Jukebox_Product_Icon        → ui_jukebox_cnctd_icon / ui_jukebox_cncra_icon
├─ UI_Jukebox_Track_Title_Text    "Track Name"  (18 Point Outline)
├─ UI_Jukebox_Track_Time_Text     "00:00"       (18 Point Outline)
└─ UI_Jukebox_Listbox_Entry
```

The per-game icon confirms what the track list needs: `Game` from
`<MusicJukeboxTracksList>` picks the icon, `TrackLengthSeconds` fills the
`00:00` field, and the `.LOC` title fills the row.

## Textures

Nine jukebox textures in `TEXTURES_SRGB.MEG` under
`DATA\ART\TEXTURES\SRGB\`, all uncompressed DDS at **2160 × 1620** with alpha:

```
ui_jukebox_bg                    the Tiberian Dawn frame
ui_jukebox_scanlines             CRT scanline overlay
ra_jukebox_bg                    Red Alert frame
ra_jukebox_bg_blue / _red        Allied / Soviet tint
ra_jukebox_bg_scanlinesblue / _scanlinesred
ra_ui_jukeboxbg_allied / _soviet
```

Plus the two product icons (`ui_jukebox_cnctd_icon`, `ui_jukebox_cncra_icon`)
and the shared slider-track pieces referenced by the layouts.

ffmpeg converts these to PNG, but its DDS decoder needs a **seekable** input —
a pipe fails with "Output file does not contain any stream". The dumper hands
it an anonymous memory file via `/dev/fd/N` instead, which is seekable and
still touches no disk.

## Data model

The rebuild needs nothing beyond what the export path already reads:

| Field | Source |
| --- | --- |
| track title | `MASTERTEXTFILE_<LANG>.LOC` via `TextID` |
| duration (`00:00`) | `TrackLengthSeconds` |
| product icon | `Game` (`Tiberian_Dawn` / `Red_Alert`) |
| Classic / Remastered / Bonus | `TrackType` |
| locked state | `BonusContentUnlock` |
| audio | `MUSIC.MEG`, ADPCM WAV |

See [`FILE-FORMATS.md`](FILE-FORMATS.md) for the container details.

## Open questions

- The binary widget layout (positions, anchors, nine-slice metrics) is not
  decoded yet; only names, textures and colours are recovered. Exact geometry
  still has to be measured against screenshots.
- The fonts are referenced by style name ("46 Point Outline"), not by file.
  Which font asset backs them is not established.
- Launching alongside the game on Linux is straightforward through Steam's
  launch options (`wrapper %command%`), which is the intended integration
  point. Whether a companion window can be delivered through the Steam
  Workshop at all is **not** established — Workshop items for this title are
  maps and mods, so this needs verifying before it is promised.
