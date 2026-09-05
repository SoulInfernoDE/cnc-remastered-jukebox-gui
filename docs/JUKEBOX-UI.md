# The in-game jukebox UI

***English** · [Deutsch](JUKEBOX-UI.de.md)*

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

## The shared sprite atlas

The layouts name sprites such as `ui_jukebox_cnctd_icon` that exist as a file
in **no** archive — a full inventory of all 22 `.MEG` files (61 571 entries)
turns up nothing, and neither does a PE resource dump of `ClientG.exe`.  They
live in a shared UI atlas.

A full-text scan of every non-media archive entry (4 613 files, 47 MiB) finds
the name in exactly one place: `MT_COMMANDBAR_COMMON.MTD`, the index for
`MT_COMMANDBAR_COMMON.TGA` — a 6871 x 6716, 176 MiB uncompressed 32-bit TGA
with bottom-left origin.

### MTD index

```
uint32  0xFFFFFFFE                 magic
int32   count                      1554 entries
count x {
    uint32  namelen
    char    name[namelen]          NUL-terminated inside the field
    int32   rect[8]                x, y, w, h, 0, 0, w, h   (y from the top)
    uint8   pad
}
```

The record is 33 bytes past the name, not 32: there is a single padding byte
after the eight integers.  Parsed that way the file is consumed exactly, with
no bytes left over.

The atlas is far too large to hold in memory, but a sprite needs only its own
rows, so the reader seeks straight into the archive and reads `h` runs of
`w * 4` bytes.

### What the jukebox uses from it

| Sprite | Size |
| --- | --- |
| `UI_JUKEBOX_CNCTD_ICON`, `UI_JUKEBOX_CNCRA_ICON` | 28x28 |
| `UI_RA_JUKEBOX_PAUSEPLAY_BTN_NORMAL/HOVERED/PRESSED` | 97x86 |
| `UI_JUKEBOX_PLAYPAUSE_BTN_ON/HOVER` | 65x59 |
| `RA_UI_JUKEBOX_HOVERSTATE_SOVIET/ALLIED` | 866x47 |
| `RA_UI_JUKEBOX_SLIDERBAR_FILL_SOVIET/ALLIED` | 546x15 |
| `UI_JUKEBOX_MUSIC_TIMER_FILL` | 363x11 |

plus the shared checkbox, main-button and slider-ball families
(`RA_UI_OPTIONS_CHECK_BOX_*`, `UI_OPTIONS_CHECK_BOX_*`, `RA_UI_MAINBTN_*`,
`UI_BUTTON_MAIN_08_*`, `*_SLIDERBAR_BALL`, `*_SLIDERBAR_MINUS/PLUS`).

## Anchors and margins

The compact property block holds three candidates beyond the rectangle.
Measured across **all 207 `.BUI` files in the game, 7318 widgets**:

| Tag | Length | What it is | Distribution |
| --- | --- | --- | --- |
| `0x07` | 4 | sizing mode, horizontal | values 0-7; 4 in 87.5 % |
| `0x12` | 4 | sizing mode, vertical | values 0-5; 3 in 86.3 % |
| `0x26` | 16 | margin, four floats | non-zero on 518 widgets (7 %) |

`0x26` is a **pixel** margin, not a normalised one: the values that occur are
small integers such as `(2, 2, 2, 2)`, `(4, 4, 0, 0)`, `(0, 8, 0, 0)` and
`(0, -6, 0, 0)`.

The pair `(0x07, 0x12)` is `(4, 3)` for 85.8 % of all widgets.  In the jukebox
the only departures are `(1, 1)` on the text labels and `(7, 5)` on
`Background` / `Background_Darken` — the two widgets whose rectangle
deliberately overflows its parent (`-0.17188, 0, 1.34375, 1.0`) to cover the
whole screen.

### What this means for a rebuild

Across the six jukebox layouts, 139 widgets, **every margin is zero** and
every anchor is the default except those six screen-covering backgrounds.  So
the jukebox scales purely proportionally, and resolving the normalised
rectangles against a 4:3 surface is not an approximation — it is what the
layout says.  That is why the geometry matched the game on the first attempt.

## Still open

- The wide property block after each widget's name (uint32 tag, uint32 length)
  is not decoded.  It holds the name and at least tags `0x13`, `0x14` and
  `0x27`, and lengths there sometimes carry a high-bit flag.  The parent/child
  links are presumably in it; the ancestry is still declared by hand.
- The point sizes in the layouts ("46 Point Outline") are read as style names
  only; text is sized as a fraction of the window height instead.
- **The launcher window can be rebuilt after all.**  A PE resource dump of
  `ClientLauncherG.exe` yields its whole interface: a 560x616 background, four
  255x208 game buttons (normal and hover), two 30x30 close buttons and two
  515x99 map-editor buttons, all as uncompressed 24-bit DIBs.  Only the layout
  would have to be measured, since there is no `.BUI` for it.
