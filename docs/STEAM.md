# Sitting beside the game

***English** · [Deutsch](STEAM.de.md)*

The jukebox can appear next to the game's own launcher, so that pressing Play
in Steam offers it as one more choice.

Set the title's Steam launch options to:

```
/full/path/to/tools/steam-launch-wrapper %command%
```

Press Play and the game starts exactly as before — same launcher, same
everything — with a Jukebox button in the launcher's own style beside it, drawn
from the launcher's own artwork. One click opens the jukebox; it closes with
the game.

## It does not disturb Steam

The wrapper runs Steam's own command unchanged and waits for it, so Steam keeps
tracking the game it launched: play time, the overlay, and the "In-Game" state
your friends see all behave as they always did. Nothing is patched, replaced or
injected, and the game's own files are never touched.

It is also transparent about failure, which is what keeps Steam from being left
hanging. Tested: a normal run returns 0 and the button is gone; a missing
command returns 127; a game exiting 42 passes 42 straight through. In every
case the companion window is closed, on any exit path, including a kill.

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
