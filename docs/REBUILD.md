# How the jukebox is rebuilt

`docs/JUKEBOX-UI.md` describes the game's own interface as it is stored on
disk. This file describes what the rebuild does with it — the decisions, the
measurements, and the places where the game's data is stranger than expected.

Nothing here is redistributed: every pixel, string and sound is read out of the
player's own installation at runtime.

---

## Nothing is eyeballed

Every part comes from the game:

| Element | Source |
| --- | --- |
| Geometry of all ~40 widgets | `.BUI` layout files in `CONFIG.MEG` |
| Frame, panels, scanlines, menu backdrop | `TEXTURES_SRGB.MEG` |
| Emblems, buttons, checkboxes, sliders, play button | `MT_COMMANDBAR_COMMON`, the shared sprite atlas |
| Typefaces (RA_Orbitron, Francker, Noto CJK) | `DATA\ART\FONTS` in `CONFIG.MEG` |
| Every caption and label | `MASTERTEXTFILE_<LANG>.LOC` |
| Track titles, durations, game, type | `<MusicJukeboxTracksList>` |
| Music and sound effects | `MUSIC.MEG`, `SFX2D_*.MEG`, `SFX3D.MEG` |
| Unit and structure animations | the per-game texture archives |

The layout numbers come out of the `.BUI` property stream, which stores each
widget as four floats normalised against its parent. That the model is right is
checkable in one line: the frame is stored as 0.75156 wide by 1.00370 high,
which on a 16:9 screen is exactly the 4:3 of the 2160×1620 frame texture.

## Language

Captions follow the system locale — `LC_ALL`, `LC_MESSAGES`, `LANG`, then
`LANGUAGE` — mapped onto the nine languages the game ships (EN-US, DE-DE,
ES-ES, FR-FR, KO-KR, PL-PL, RU-RU, ZH-CN, ZH-TW), falling back to EN-US.
Korean and Chinese render through the game's own Noto CJK font.

Where a caption looks untranslated, that is the game's data rather than a gap
here: the Korean table genuinely leaves "Available Tracks" and "Jukebox Music
Volume" in English.

Four strings are ours rather than the game's, because the game has no word for
what they name: **Soundbox**, **Button sounds**, and the two hover hints that
go with them. They are written in German and English and fall back to English
elsewhere. Even then the destination's own name comes from the string table
where one exists — `TEXT_JUKEBOX` is localised, and reads "Музыкальный плеер"
in Russian.

## Audio

Qt Multimedia is deliberately not used. Its ALSA and PulseAudio plugins ship in
a separate package that is often absent, and `QAudioOutput` then falls back to
a silent null device without saying so. Tracks are decoded with ffmpeg and
written to `paplay`, `aplay` or `ffplay` instead, which works wherever the
desktop has sound. Nothing touches the disk: the decoded audio stays in memory.

### A line that was never recorded

Tiberian Dawn's "battle control terminated" does not exist in German. The file
ships all the same, holding a quarter-second of room tone — 19 RMS, where the
real recordings sit between 3400 and 7900 — so the Exit button in that skin
used to close in silence.

The game admits it: the German `TEXT_SFX_TDC_SFX_BATLCON1` reads `empty` where
every other language carries the sentence. It is one specific gap and not a
missing voice pack — of Tiberian Dawn's 136 German EVA lines exactly two are
blank, and they are the classic and remastered takes of that one line.

So any clip measuring under 200 RMS is replaced by the English recording, the
way an untranslated subtitle already stays English in the sound box. The floor
clears both sides by a factor of seventeen. The same path covers a language
whose voice pack Steam has not downloaded, which otherwise leaves every button
mute.

Measuring costs nothing. `play_effect` already decodes on a worker thread, so
the test runs on PCM it is holding anyway, and the stand-in is fetched cheaply
but only decoded when it is actually wanted.

## The turning emblem

The emblem of the playing track turns as a struck token rather than a sheet of
paper. Rotating a plane about its vertical axis puts a point at
`x·cos θ + z·sin θ`. The axis runs through the middle of the material, so `z`
spans `-T/2` to `+T/2` rather than hanging off one face: the two faces land at
`±T/2·sin θ`, the silhouette stays centred, and the token turns in place
instead of swinging sideways.

Which face is visible follows the same angle. Depth on the axis is `z·cos θ`,
so the near plane flips with the sign of cos, and at that moment the visible
face is mirrored, moved to the other offset, and the slices are drawn in
reverse.

Measured over a full turn the silhouette's centroid stays within 5 px of the
axis and never moves more than 1 px per 5 degrees. What remains is the emblem's
own asymmetry, which a real object would show too.

A second copy sits to the right of the playback bar, mirroring the play button
on the other side of it and turning off the same angle, so the two stay in
step.

## The sound box

Two catalogues read from the installation, side by side:

- **Left** — every effect in the game, 1286 of them, grouped by game, fidelity
  and kind, and played on click. Spoken lines show what they actually say: the
  string table files those under `TEXT_SFX_<stem>` with the `EVA_`/`UNT_` part
  dropped, which covers 369 of them. Only the classic-prefix keys are
  translated, so those are preferred; where the game itself never translated a
  line it stays English here too, exactly as in the game.
- **Right** — 409 units, structures and effects, each animated from its own
  sprite frames. The archives keep them as one zip of uncompressed TGA per
  object, listed by `TD_UNITS.XML` and friends; only the selected object is
  decoded, downscaled, and kept.

They sit side by side rather than one deriving the other, and that is
deliberate: **the games ship no mapping from a sound to "its" unit or
building.** Checking all 508 sound stems against all 192 object names yields no
match at all, and the few substring hits are coincidence. Pairing them would
mean inventing the pairing.

## The header controls

Red Alert's header carries round brass bolts and Tiberian Dawn's carries hex
heads, sitting higher and further out, so the hover outline follows the shape
and position each skin actually has — measured on the textures rather than
assumed.

- **Left fastener** — opens the project on GitHub, with EVA saying thank you in
  that game's own voice. The two games file it under different stems:
  `EVA_ETHANKS` for Tiberian Dawn, `EVA_THANKU1` for Red Alert.
- **Folder** — opens the soundtrack folder, drawn in the current skin's colour,
  over a one-second country sting. Red Alert ships no counterpart to that sting
  — only bleeps and tones — so all three skins use the Tiberian Dawn one, which
  is a jingle rather than a faction voice.
- **Right fastener** — changes the skin, the way the game puts up a building:
  the next faction's emblem appears across the whole player, EVA announces the
  construction, a build clock sweeps once around over three seconds, the
  "construction complete" line plays, and the new skin drops in with that
  game's building-placement sound.

## Where the second checkbox came from

**Button sounds** shares the shuffle row. There is room for it because none of
the nine translations of "shuffle" comes near filling its rect — Polish, the
widest, uses a third of it. So the box goes where that text actually stops
rather than where the layout says it may reach, and steps aside entirely if a
translation ever does need the room. Measured across all nine languages, both
typefaces and window sizes from 880×660 up, the tightest fit still clears by
61 px.

## The window icon

The window is frameless, so there is no title bar to carry an icon and the task
bar and window switcher would otherwise show a blank. It gets a drawn one
instead: a jukebox cabinet in the current skin's colours, its screen showing
that game's own emblem out of the atlas, over two round speakers in the accent
colour. It follows the skin, so changing the skin changes the icon too.

`--write-icon PATH` renders it to a file, which is how the desktop entry gets
its icon.

## Settings

The playlist, filters, volume, button sounds and chosen skin live in
`~/.config/cnc-jukebox/playlist.json`. The skin is read back before the window
is built, since the layout, textures, fonts and window icon all come from it.

## Still not reproduced

The launcher window — the one that appears when you press Play in Steam —
belongs to `ClientLauncherG.exe`. Its artwork is recoverable and the companion
button already draws from it, but unlike the jukebox it has no `.BUI`, so the
layout would have to be measured by hand. What the dump yields is listed under
"Still open" in [`JUKEBOX-UI.md`](JUKEBOX-UI.md), together with the two parts
of the `.BUI` format that remain undecoded.
