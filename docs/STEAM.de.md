# Neben dem Spiel sitzen

*[English](STEAM.md) · **Deutsch***

Die Jukebox kann neben dem Launcher des Spiels erscheinen, sodass ein Klick auf
Spielen in Steam sie als weitere Wahlmöglichkeit anbietet.

Setze dazu die Startoptionen des Titels in Steam auf:

```
/voller/pfad/zu/tools/steam-launch-wrapper %command%
```

Ein Klick auf Spielen startet das Spiel genau wie zuvor — derselbe Launcher,
alles unverändert — daneben ein Jukebox-Knopf im Stil des Launchers, gezeichnet
aus dessen eigenen Grafiken. Ein Klick öffnet die Jukebox; sie schließt sich
mit dem Spiel.

## Es bringt Steam nicht durcheinander

Der Wrapper führt Steams eigenen Befehl unverändert aus und wartet auf ihn.
Steam verfolgt damit weiterhin das Spiel, das es gestartet hat: Spielzeit, das
Overlay und der Status „Im Spiel", den deine Freunde sehen, verhalten sich wie
immer. Nichts wird gepatcht, ersetzt oder eingeschleust, und die Dateien des
Spiels werden nie angefasst.

Er ist außerdem ehrlich im Fehlerfall, und genau das bewahrt Steam davor,
hängen zu bleiben. Getestet: ein normaler Lauf liefert 0 und der Knopf ist
weg; ein fehlender Befehl liefert 127; ein Spiel, das mit 42 endet, reicht 42
unverändert durch. In jedem Fall wird das Begleitfenster geschlossen, auf
jedem Ausstiegsweg, auch beim Abschießen.

> Geprüft, soweit ein einzelner Rechner das zulässt. Ob deine Freundesliste
> „Im Spiel" anzeigt, ist Steams eigene Buchführung über den Prozess, den es
> gestartet hat, und ein Wrapper in den Startoptionen ist der übliche Weg, sich
> davorzusetzen — dieselbe Bauform, die `gamemoderun` und `mangohud` benutzen.
> Die Sicht eines anderen Kontos darauf ließ sich von diesem Rechner aus nicht
> beobachten.

## Warum kein Workshop-Element

Weil der Workshop den Launcher nicht erreichen kann.

Sieht man sich an, was installierte Workshop-Elemente tatsächlich enthalten, so
ist ein Element entweder eine Karte (`MAPDATA.PGM`) oder eine Spiellogik-Mod —
eine `ccmod.json` neben `CCDATA/*.INI`-Regeln und mitunter einer neu gebauten
Spiel-DLL. Beides wird vom Spiel geladen, nachdem es gestartet ist.

Der Launcher ist `ClientLauncherG.exe`, eine eigenständige Windows-Anwendung,
die *vor* dem Spiel läuft und überhaupt keine Mod-Daten liest. Nichts, was über
den Workshop ausgeliefert wird, ist also in der Lage, ihm einen Knopf
hinzuzufügen.

Ihn zu ersetzen war die andere Idee, und auch die trägt nicht. `ClientG.exe`
nimmt kein Argument zur Spielauswahl entgegen, und der Launcher hält die
Auswahl nirgends fest — `Software\Petroglyph\CnCRemastered\Launcher` im Prefix
enthält zwei Thread-Flags und sonst nichts. Ein Ersatzauswahlfenster könnte nur
an den echten Launcher weiterreichen und stellte damit einen zweiten
Auswahlschritt vor das Spiel, statt einen wegzunehmen.

Daneben zu sitzen kostet nichts und nimmt nichts weg.

## Ohne Steam dazwischen

```bash
./tools/install-desktop-entry      # --remove nimmt ihn wieder heraus
```

Das trägt die Jukebox mit dem Symbol des Skins ins Anwendungsmenü ein, einen
Klick von überall entfernt. Geschrieben wird ausschließlich innerhalb von
`~/.local/share`.
