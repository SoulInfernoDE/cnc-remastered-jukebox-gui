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

## Geometry

Each widget stores a rectangle as four floats normalised against its parent,
under tag `0x02` with length `0x10`.  Widgets appear depth-first and the
rectangle precedes the name, so pairing each rectangle with the following name
recovers the flat list; the nesting itself is not in a form we decode, so the
ancestry of the widgets that matter is declared in `jukebox/layout.py`.

Two frames of reference are in play, and mixing them up is the trap:

- **Red Alert** wraps the panel in `SovietJukebox_Group` / `AlliesJukebox_Group`
  and states the contents relative to it.
- **Tiberian Dawn** has no such group and states the same widgets in screen
  space.

Both resolve to the same absolute positions, which is the check that the model
is right: `Available_Songs` lands on 0.16979 of screen width either way.

The decisive test for the outer frame is the aspect ratio.  The group is stored
as 0.75156 wide by 1.00370 high; on a 16:9 screen that is 12.02 by 9.03 units,
exactly the 4:3 of the 2160x1620 frame texture.  Read as relative to the
dialog instead it would come out square, which no texture matches.  So the
group is positioned in screen space, and it *is* the window.

### Cropping the frame

The background texture carries a soft drop shadow outside the metal frame.
In the game that blends into the menu behind it; a standalone window would
show it as a black margin.  Measured on the alpha channel, the fully opaque
frame occupies x 47..2113, y 33..1585 of 2160x1620 - normalised
(0.02176, 0.02037, 0.95648, 0.95802), aspect 1.3312.  Scaling the drawing
surface up by that inset puts the shadow outside the window, and widget
rectangles resolved against the same surface stay aligned.

## Textures

The jukebox textures are uncompressed 32-bit DDS whose channel masks
(R=0x00ff0000, G=0x0000ff00, B=0x000000ff, A=0xff000000) describe exactly the
memory layout of `QImage::Format_ARGB32`, so the block after the 128-byte
header can be handed to Qt without any decoding step.

Tiberian Dawn's list panels are transparent: the layouts stack a full-screen
`Background` (`ui_mainmenubg_01`, or `ui_ra_menu_bg` for Red Alert) and a
`Background_Darken` behind the frame, and without both the menu artwork reads
straight through the panels.

## Fonts

`CONFIG.MEG` carries the interface typefaces under `DATA\ART\FONTS`:

| File | Family | Used for |
| --- | --- | --- |
| `RA_ORBITRON.TTF` | RA_Orbitron | the Red Alert screens |
| `FRANCKERW1G-CONDENSEDREG.TTF` | Francker W1G | the Tiberian Dawn screens |
| `RUSSEL SQUARE.TTF` | RussellSquare | the Command & Conquer logo |
| `NOTOSANSCJKTC-REGULAR.TTF` | Noto Sans CJK TC | Korean and Chinese |

They load straight into Qt with `QFontDatabase::addApplicationFontFromData`,
so the rebuild matches the original typography without shipping a font.

## Still open

- The binary widget stream is only partly decoded: rectangles, names, colours
  and texture references read out cleanly, but anchors, nine-slice metrics and
  the parent/child links do not.  The ancestry is therefore declared by hand.
- `ui_jukebox_cnctd_icon` and `ui_jukebox_cncra_icon` are named by the layouts
  but are in none of the shipped texture archives, under that name or any
  obvious variant.  Where they actually come from is unresolved.
- The point sizes in the layouts ("46 Point Outline", "18 Point Outline") are
  read as style names only; the rebuild sizes text as a fraction of the window
  height instead, tuned against the game's own screens.
