# cnc-remastered-jukebox

*[English](README.md) · **Deutsch***

Die Musik der **Command & Conquer Remastered Collection**, außerhalb des Spiels.

Zwei Programme, die beide zur Laufzeit aus deiner eigenen Installation lesen:

- **`cnc-jukebox`** — die Musik-Jukebox des Spiels, nachgebaut als eigenständiges
  Linux-Fenster. Dasselbe Layout, derselbe Skin, dieselben Schriften, dieselben
  Beschriftungen in der Sprache deines Systems.
- **`cnc_trackexport`** — der komplette Soundtrack als getaggte Dateien, benannt
  genau so, wie die Jukebox die Titel anzeigt.

> **Du brauchst dein eigenes Exemplar des Spiels.** Dieses Repository enthält
> keine Audiodaten, keine Grafiken, keine extrahierten Daten und keinen
> Spielcode — nur Programme, die die Dateien lesen, die ohnehin auf deiner
> Platte liegen. Nur unter Linux.

---

## Wozu eine eigenständige Jukebox

- **Der Soundtrack ohne das Spiel.** Zwölf Stunden davon, die nebenher laufen,
  ohne dass ein 26 GB großes Spiel dafür gestartet sein muss.
- **Die Jukebox, die das Spiel für sich behält.** Im Spiel ist sie nur über ein
  Menü erreichbar, und nur solange das Spiel läuft. Hier ist sie ein Fenster wie
  jedes andere, und ihre Wiedergabeliste bleibt unabhängig davon bestehen.
- **Jeder Titel, nicht nur die freigeschalteten.** Die Classic-Aufnahmen und die
  Bonus-Arrangements stehen in derselben Liste wie die remasterten, gefiltert
  wie du magst.
- **Die Titel als Dateien.** Alle 203, fürs Telefon, fürs Auto oder für überall
  dort, wo das Spiel nie laufen wird.
- **Nichts wird verändert.** Keine gepatchten Binärdateien, keine ersetzten
  Dateien, kein eingeschleuster Code. Beide Programme lesen die Installation und
  schreiben nur ihre eigene Ausgabe — es gibt nichts rückgängig zu machen und
  nichts, was ein Update kaputtmachen könnte.

## Voraussetzungen

- Command & Conquer Remastered Collection, installiert (Steam, Origin/EA, GOG)
- Linux, `python3` 3.6 oder neuer
- `ffmpeg` — und für die Jukebox zusätzlich `PyQt5` sowie eines von `paplay`,
  `aplay` oder `ffplay`

```bash
sudo apt install python3-pyqt5 ffmpeg      # Debian / Ubuntu
sudo dnf install python3-qt5 ffmpeg        # Fedora (ffmpeg über RPM Fusion)
sudo pacman -S python-pyqt5 ffmpeg         # Arch
```

Der Exporter allein braucht weder PyQt5 noch einen Soundserver.

## Installation

```bash
git clone https://github.com/SoulInfernoDE/cnc-remastered-jukebox.git
cd cnc-remastered-jukebox
```

Es gibt nichts zu bauen. Das Spielverzeichnis wird automatisch gefunden —
gewöhnliches Steam, Flatpak, Snap und jede weitere Bibliothek, die in
`libraryfolders.vdf` steht. `CNC_REMASTERED_DIR` überschreibt die Suche, falls
sie fehlschlägt.

Wie die Jukebox ins Anwendungsmenü kommt oder neben den Launcher des Spiels,
wenn du in Steam auf Spielen klickst, steht in [`docs/STEAM.de.md`](docs/STEAM.de.md).

## Die Jukebox

```bash
./cnc-jukebox                 # zuletzt benutzter Skin, Systemsprache
./cnc-jukebox -s td           # Tiberiumkonflikt
./cnc-jukebox -s allied       # Alarmstufe Rot, Alliierte
./cnc-jukebox -l EN-US        # Sprache überschreiben
```

Das Fenster hat keinen Rahmen, sodass nur die Jukebox selbst zu sehen ist. Zieh
es an einer freien Stelle der Oberfläche; Escape oder **Beenden** schließt es,
F11 schaltet Vollbild, die Leertaste die Wiedergabe.

Linksklick wählt einen Titel aus, Rechtsklick schiebt ihn zwischen den beiden
Listen hin und her, Doppelklick spielt ihn ab. Die Filter, „Mischen", die
Schieberegler für Pause und Lautstärke und die Wiedergabeleiste verhalten sich
wie im Spiel. Das Emblem des laufenden Titels dreht sich, solange er spielt.

Drei Bedienelemente in der Kopfleiste, jedes mit einem Hinweis beim Überfahren:

| | |
| --- | --- |
| **Linker Bolzen** | öffnet dieses Projekt auf GitHub |
| **Ordner** | öffnet den Ordner, in den der Exporter schreibt |
| **Rechter Bolzen** | wechselt den Skin, so wie das Spiel ein Gebäude hochzieht |

Zwei weitere unten: **Beenden** und ein Knopf, der zwischen der Jukebox und der
**Soundbox** umschaltet — einem zweiten Bildschirm, der alle 1286 Soundeffekte
des Spiels neben 409 animierten Einheiten und Gebäuden auflistet.

Jeder Knopf hat eine Stimme aus dem passenden Spiel. **Button-Sounds** neben
„Mischen" schaltet das ab; Musik und Soundvorschau bleiben davon unberührt. Die
Einstellungen liegen in `~/.config/cnc-jukebox/playlist.json`.

## Den Soundtrack exportieren

```bash
./cnc_trackexport
```

203 Titel, 12 Stunden 6 Minuten, rund 1,6 GiB, standardmäßig in den eigenen
Benutzerordner des Spiels geschrieben. Die Dateinamen sind die Titel, die die
Jukebox anzeigt, Zeichen für Zeichen:

```
Act On Instinct (Classic).mp3
Act On Instinct – Tiberian Sons (Bonus).mp3
Grinder 1 & 2 Medley – Tiberian Sons (Bonus).mp3
Hell March Original Demo (Bonus, Unlocked).mp3
We Will Stop Them ∕ Deception (Remastered).mp3
```

```
  -o, --out DIR      Zielverzeichnis        (Standard: der Ordner des Spiels)
  -g, --game DIR     Spielverzeichnis       (Standard: automatisch gesucht)
  -f, --format FMT   mp3 | flac | wav       (Standard: mp3)
  -l, --lang LANG    EN-US, DE-DE, ...      (Standard: EN-US)
  -j, --jobs N       parallele Encoder      (Standard: CPU-Kerne, max. 16)
      --no-cover     kein Artwork einbetten
      --portable     Dateinamen auf reines ASCII beschränken (FAT32 usw.)
      --force        neu erzeugen statt vorhandene Dateien überspringen
      --list         nur die Zuordnung anzeigen, nichts schreiben
  -h, --help         Hilfe
```

MP3 sind 44,1 kHz bei 320 kbit/s; `--format flac` ist bitgenau zur Quelle.
Strg+C ist unbedenklich, und der nächste Lauf macht dort weiter, wo er
aufgehört hat.

## Wie es funktioniert

Die interessanten Teile sind aufgeschrieben, statt nur im Code zu stehen:

| | |
| --- | --- |
| [`docs/FILE-FORMATS.de.md`](docs/FILE-FORMATS.de.md) | der MEG-Container, die `.LOC`-Zeichenkettentabelle, die Titelliste |
| [`docs/JUKEBOX-UI.de.md`](docs/JUKEBOX-UI.de.md) | die `.BUI`-Layouts des Spiels, Texturen, Schriften und Sprite-Atlas |
| [`docs/REBUILD.de.md`](docs/REBUILD.de.md) | was der Nachbau daraus macht, und wo die Spieldaten überraschen |
| [`docs/SOUNDTRACK-EXPORT.de.md`](docs/SOUNDTRACK-EXPORT.de.md) | Titelzuordnung, Messungen zur Audioqualität, Tags |
| [`docs/STEAM.de.md`](docs/STEAM.de.md) | der Begleiter am Launcher, und warum das kein Workshop-Element ist |

Jedes Dokument gibt es auch auf Englisch; oben in jedem steht der Verweis.

## Branches

Der stabile Exporter liegt für sich allein auf [`export`](../../tree/export),
ohne Abhängigkeiten jenseits von `python3` und `ffmpeg`. Dieser Branch,
[`gui`](../../tree/gui), trägt die Jukebox und den Exporter zusammen.

## Keine Screenshots

Jedes Bild des laufenden Fensters wäre ein Bild von EAs Grafiken, deshalb gibt
es hier keine.

## Rechtliches

Dies ist ein inoffizielles Fan-Projekt. Es steht **in keiner Verbindung zu
Electronic Arts, Petroglyph Games oder Valve und wird von diesen weder
unterstützt noch gefördert.** „Command & Conquer", „Alarmstufe Rot" und
„Tiberiumkonflikt" sind Marken von Electronic Arts Inc.

Das Repository enthält keinerlei Spielinhalte — keine Audiodaten, keine
Grafiken, keine extrahierten Daten und keinen Code aus dem Spiel. Es liest
ausschließlich Dateien, die eine lizenzierte Installation ohnehin auf deinem
Rechner abgelegt hat, und ist für den persönlichen Gebrauch mit einem Exemplar
gedacht, das dir gehört. Gib nicht weiter, was dabei entsteht.

Standardmäßig lädt der Exporter zur Laufzeit das öffentliche Steam-Store-Bild
des Spiels, um es als Cover in deine persönlichen Dateien einzubetten. Dieses
Bild gehört EA; es wird nie in diesem Repository gespeichert. Mit `--no-cover`
bleibt es außen vor.

Die Musik stammt von Frank Klepacki, bei den Bonus-Arrangements von Frank
Klepacki & The Tiberian Sons.

## Lizenz

[MIT](LICENSE) — gilt nur für den eigenen Code dieses Projekts, nicht für das,
was es liest oder erzeugt.
