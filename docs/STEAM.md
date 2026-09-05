# Sitting beside the game

***English** · [Deutsch](STEAM.de.md)*

The jukebox can appear next to the game's own launcher, so that pressing Play
in Steam offers it as one more choice.

Set the title's Steam launch options to:

```
/full/path/to/tools/steam-launch-wrapper %command%
```

Press Play and the game starts exactly as before — same launcher, same
everything — with a **Jukebox** row added to the bottom of it. One click opens
the jukebox.

## Made of the launcher's own pixels

The row is not a lookalike. The launcher's whole interface sits in
`ClientLauncherG.exe`'s PE resources as uncompressed bitmaps, and the row is
built out of them: the 130-pixel strip that closes the window off — the seam
above the last button, the button row itself, the riveted frame below it, side
rails and all — with the Map Editor slot replaced.

That slot is where the green comes from. The launcher tints one shared noise
texture per game: hue 215 for Tiberian Dawn, 22 for Red Alert. The Jukebox slot
gets 120, which is what a music button is coloured everywhere. How strongly
matters too — measured on the mean colour of each slot's noise, the game sits
at saturation 47 for its blue and 97 for its red on Qt's 0–255 scale, and this
green lands on 85, inside the family rather than shouting past it. The planet
and the lettering are replaced by the clean noise from either side of them, so
nothing of the Map Editor shows through, and only the interior is tinted: the
metal bevel stays exactly the pixels the launcher drew.

In front of the label sit the three app icons — Tiberian Dawn, Soviet, Allied —
overlapping left to right, the same cabinet the jukebox uses in the task bar.

Hovering follows the launcher's own pattern, which is two things at once: the
noise brightens — that comes from the game's hovered copy of the slot — and the
lettering leaves white for the slot's own colour. The Map Editor's goes to
(96, 189, 254); this one takes that blue's saturation and value at hue 120, so
the word turns green.

## It follows the launcher

The launcher window cannot be asked anything: it is a Windows binary under
Proton. The window manager can, though, so the row waits until the launcher is
actually on screen, then places itself over its bottom frame, at its width and
scaled to it. The seam disappears and the two read as a single window. Move the
launcher and the row moves with it, three times a second.

Finding that window takes some care. Its title is `CnCRemastered` — the
collection's name, not the launcher's — and the game beside it answers to the
same one; both even carry the same `WM_CLASS`, `steam_app_1213210`. What
separates them is the process: Proton names it after the Windows executable, so
`/proc/<pid>/comm` reads `ClientLauncherG` for one and `ClientG` for the other.
That is what the row goes by, with the title and the window's proportions as a
fallback for desktops that report no pid.

Where exactly it sits was measured rather than assumed, by sliding the
launcher's own bitmaps over a screenshot of it until they fit: the window is
560×618, it stretches its 560×616 background over the whole of that, and the
Map Editor row lands at x 24..538, y 490..588 — four pixels above where the
background's recess suggests. So the row begins 29 pixels above the foot of the
window, which is where that slot really ends. Anchoring to the background
instead left four rows of it showing through, and the extra edge made the two
windows look stacked rather than joined.

The row does not float above everything. It is tied to the launcher with the
same hint a dialog uses on the window it belongs to, so the desktop keeps it
just above that and nowhere else: bring another application forward and the
row disappears behind it exactly as the launcher does. Where a desktop ignores
the hint, the stacking order is checked instead, and the row is lifted only
when the launcher itself has come out on top.

When the launcher goes — a game was picked, the window was closed, or it was
merely minimised — the row goes with it, in the same moment. A jukebox opened
from it keeps playing: that is why the companion is started in its own session
rather than killed on the way out.

This needs X11. Under a Wayland session nothing can ask where another
program's window is, and the row falls back to the bottom-right corner of the
screen after waiting; Escape closes it there.

## Trying it without Steam

The real launcher only comes up through Steam and Proton, which makes the row
awkward to look at while working on it. So there is a stand-in:

```bash
./tools/mock-launcher
```

It opens a window with the launcher's title, size and artwork — read from the
installed executable, not shipped here — and starts the row against it. Drag
the window and the row follows; close it and the row goes in the same moment.
Open the jukebox from the row first, and it keeps playing after both are gone.

## It does not disturb Steam

The wrapper runs Steam's own command unchanged and waits for it, so Steam keeps
tracking the game it launched: play time, the overlay, and the "In-Game" state
your friends see all behave as they always did. Nothing is patched, replaced or
injected, and the game's own files are never touched.

It is also transparent about failure, which is what keeps Steam from being left
hanging. Tested: a normal run returns 0, a missing command returns 127, and a
game exiting 42 passes 42 straight through — with no window and no companion
process left behind in any of the three. The companion is told the wrapper's
pid and closes itself when that goes, so it cannot outlive the session that
asked for it even if the launcher window is never found.

> Verified here as far as a single machine allows. Whether your friends list
> shows "In-Game" is Steam's own bookkeeping about the process it started, and
> a launch-option wrapper is the ordinary way to sit in front of that — the
> same shape `gamemoderun` and `mangohud` use. Another account's view of it
> could not be observed from this machine.

## Why not a Workshop item

Because the Workshop cannot reach the launcher.

Looking at what installed Workshop items actually contain, an item is either a
map (`MAPDATA.PGM`) or a game-logic mod — a `ccmod.json` beside `CCDATA/*.INI`
rules and sometimes a rebuilt game DLL. Those are loaded by the game after it
starts.

The launcher is `ClientLauncherG.exe`, a separate Windows executable that runs
*before* the game and reads no mod data at all, so nothing shipped through the
Workshop is in a position to add a button to it.

Replacing it was the other idea, and it does not work either. `ClientG.exe`
takes no game-selection argument, and the launcher records the choice nowhere —
`Software\Petroglyph\CnCRemastered\Launcher` in the prefix holds two thread
flags and nothing else. A stand-in chooser could only hand off to the real
launcher, putting a second selection step in front of the game rather than
taking one away.

Sitting beside it costs nothing and takes nothing away.

## Without Steam in the way

```bash
./tools/install-desktop-entry      # --remove takes it back out
```

That puts the jukebox in the application menu with the skin's icon, one click
from anywhere. It writes only inside `~/.local/share`.
