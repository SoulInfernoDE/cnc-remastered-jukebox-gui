# Neben dem Spiel sitzen

*[English](STEAM.md) · **Deutsch***

Die Jukebox kann neben dem Launcher des Spiels erscheinen, sodass ein Klick auf
Spielen in Steam sie als weitere Wahlmöglichkeit anbietet.

Setze dazu die Startoptionen des Titels in Steam auf:

```
/voller/pfad/zu/tools/steam-launch-wrapper %command%
```

Ein Klick auf Spielen startet das Spiel genau wie zuvor — derselbe Launcher,
alles unverändert — nur mit einer zusätzlichen **Jukebox**-Zeile unten daran.
Ein Klick öffnet die Jukebox.

## Aus den Pixeln des Launchers gebaut

Die Zeile ist keine Nachahmung. Die gesamte Oberfläche des Launchers liegt als
unkomprimierte Bitmaps in den PE-Ressourcen von `ClientLauncherG.exe`, und die
Zeile ist daraus gebaut: aus dem 130 Pixel hohen Streifen, der das Fenster nach
unten abschließt — die Fuge über der letzten Schaltfläche, die Schaltflächen-
zeile selbst, der genietete Rahmen darunter, samt Seitenschienen — mit
ausgetauschtem Karteneditor-Feld.

Aus diesem Feld kommt auch das Grün. Der Launcher färbt eine gemeinsame
Rauschtextur je Spiel ein: Farbton 215 für den Tiberiumkonflikt, 22 für
Alarmstufe Rot. Das Jukebox-Feld bekommt 120, die Farbe, die musikbezogene
Dinge üblicherweise tragen. Auch die Stärke zählt: gemessen an der
Durchschnittsfarbe des jeweiligen Rauschens liegt das Spiel bei Sättigung 47
für sein Blau und 97 für sein Rot auf der 0–255-Skala von Qt, und dieses Grün
landet bei 85 — innerhalb der Familie, statt daran vorbeizuschreien. Planet und
Beschriftung werden durch das saubere Rauschen zu beiden Seiten ersetzt, sodass
nichts vom Karteneditor durchscheint, und eingefärbt wird nur das Innere: die
Metallfase bleibt genau das, was der Launcher gezeichnet hat.

Vor der Beschriftung stehen die drei App-Symbole — Tiberiumkonflikt, Sowjets,
Alliierte — von links nach rechts leicht überlappend, dasselbe Gehäuse, das die
Jukebox in der Taskleiste trägt.

Das Überfahren folgt dem Muster des Launchers, und das sind zwei Dinge auf
einmal: das Rauschen wird heller — das bringt die überfahrene Fassung des
Feldes von selbst mit — und die Beschriftung verlässt das Weiß zugunsten der
Farbe des Feldes. Beim Karteneditor wird sie (96, 189, 254); diese hier nimmt
Sättigung und Helligkeit jenes Blaus bei Farbton 120, das Wort wird also
grün.

## Sie folgt dem Launcher

Das Launcher-Fenster lässt sich nichts fragen: es ist eine Windows-Anwendung
unter Proton. Die Fensterverwaltung dagegen schon, und so wartet die Zeile, bis
der Launcher wirklich auf dem Bildschirm steht, und legt sich dann über dessen
unteren Rahmen, in seiner Breite und in seinem Maßstab. Die Naht verschwindet,
und beides liest sich als ein einziges Fenster. Verschiebst du den Launcher,
zieht die Zeile dreimal je Sekunde nach.

Dieses Fenster zu finden erfordert etwas Sorgfalt. Sein Titel lautet
`CnCRemastered` — der Name der Sammlung, nicht der des Launchers — und das
Spiel daneben hört auf denselben; beide tragen sogar dieselbe `WM_CLASS`,
`steam_app_1213210`. Was sie trennt, ist der Prozess: Proton benennt ihn nach
der Windows-Anwendung, `/proc/<pid>/comm` liest also für das eine
`ClientLauncherG` und für das andere `ClientG`. Daran hält sich die Zeile; der
Titel und die Fensterproportionen sind nur der Rückfall für Arbeitsumgebungen,
die keine Prozessnummer melden.

Wo genau sie sitzt, wurde gemessen statt angenommen: die Bitmaps des Launchers
wurden über einen Bildschirmabzug von ihm geschoben, bis sie passten. Das
Fenster ist 560×618, es zieht seinen 560×616 großen Hintergrund über die ganze
Fläche, und die Karteneditor-Zeile landet bei x 24..538, y 490..588 — vier
Pixel höher, als die Vertiefung im Hintergrund vermuten lässt. Die Zeile
beginnt deshalb 29 Pixel über dem unteren Fensterrand, dort, wo jenes Feld
wirklich endet. Am Hintergrund ausgerichtet blieben vier Zeilen davon sichtbar,
und diese zusätzliche Kante ließ die beiden Fenster gestapelt statt verbunden
aussehen.

Die Zeile schwebt nicht über allem. Sie ist an den Launcher gebunden, mit
demselben Hinweis, den ein Dialog auf sein zugehöriges Fenster setzt; die
Arbeitsumgebung hält sie damit direkt darüber und sonst nirgends: holst du eine
andere Anwendung nach vorn, verschwindet die Zeile dahinter, genau wie der
Launcher. Ignoriert eine Umgebung den Hinweis, wird stattdessen die
Stapelreihenfolge geprüft, und die Zeile nur dann angehoben, wenn der Launcher
selbst nach vorn gekommen ist.

Verschwindet der Launcher — weil ein Spiel gewählt, das Fenster geschlossen
oder auch nur minimiert wurde — verschwindet die Zeile im selben Moment mit.
Eine zuvor darüber geöffnete Jukebox läuft weiter: deshalb wird der Begleiter
in einer eigenen Sitzung gestartet und nicht beim Beenden abgeräumt.

Dafür braucht es X11. In einer Wayland-Sitzung kann niemand erfragen, wo das
Fenster eines anderen Programms steht; dort weicht die Zeile nach einer
Wartezeit in die untere rechte Bildschirmecke aus und lässt sich mit Escape
schließen.

## Ausprobieren ohne Steam

Der echte Launcher kommt nur über Steam und Proton hoch, was das Betrachten der
Zeile während der Arbeit daran umständlich macht. Deshalb gibt es einen
Stellvertreter:

```bash
./tools/mock-launcher
```

Er öffnet ein Fenster mit Titel, Größe und Grafiken des Launchers — aus der
installierten Anwendung gelesen, nicht hier mitgeliefert — und startet die
Zeile dagegen. Zieh das Fenster, und die Zeile folgt; schließ es, und die Zeile
geht im selben Moment. Öffne vorher die Jukebox über die Zeile, dann spielt sie
weiter, wenn beide fort sind.

## Es bringt Steam nicht durcheinander

Der Wrapper führt Steams eigenen Befehl unverändert aus und wartet auf ihn.
Steam verfolgt damit weiterhin das Spiel, das es gestartet hat: Spielzeit, das
Overlay und der Status „Im Spiel", den deine Freunde sehen, verhalten sich wie
immer. Nichts wird gepatcht, ersetzt oder eingeschleust, und die Dateien des
Spiels werden nie angefasst.

Er ist außerdem ehrlich im Fehlerfall, und genau das bewahrt Steam davor,
hängen zu bleiben. Getestet: ein normaler Lauf liefert 0, ein fehlender Befehl
127, und ein Spiel, das mit 42 endet, reicht 42 unverändert durch — in allen
drei Fällen bleibt weder ein Fenster noch ein Begleitprozess zurück. Der
Begleiter kennt die Prozessnummer des Wrappers und beendet sich, sobald diese
verschwindet; er kann die Sitzung, die ihn angefordert hat, also selbst dann
nicht überleben, wenn das Launcher-Fenster nie gefunden wird.

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
