# cnc-jukebox

*[English](README.md) · **Deutsch***

Die Musik der **Command & Conquer Remastered Collection**, außerhalb des Spiels.

Die Musik-Jukebox des Spiels, nachgebaut als eigenständiges Linux-Fenster:
dasselbe Layout, derselbe Skin, dieselben Schriften, dieselben Beschriftungen
in der Sprache deines Systems — alles zur Laufzeit aus deiner eigenen
Installation gelesen.

> **Du brauchst dein eigenes Exemplar des Spiels.** Dieses Repository enthält
> keine Audiodaten, keine Grafiken, keine extrahierten Daten und keinen
> Spielcode — nur ein Programm, das die Dateien liest, die ohnehin auf deiner
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
- **Die Titel auch als Dateien.** Ein eigenes Programm,
  [der Exporter](https://github.com/SoulInfernoDE/cnc-remastered-jukebox-trackexport),
  schreibt alle 203 heraus — fürs Telefon, fürs Auto oder für überall dort, wo
  das Spiel nie laufen wird.
- **Nichts wird verändert.** Keine gepatchten Binärdateien, keine ersetzten
  Dateien, kein eingeschleuster Code. Die Jukebox liest die Installation und
  schreibt nur ihre eigenen Einstellungen — es gibt nichts rückgängig zu machen
  und nichts, was ein Update kaputtmachen könnte.

## Voraussetzungen

- Command & Conquer Remastered Collection, installiert (Steam, Origin/EA, GOG)
- Linux, `python3` 3.6 oder neuer
- `PyQt5`, `ffmpeg` sowie eines von `paplay`, `aplay` oder `ffplay` für die
  Ausgabe

```bash
sudo apt install python3-pyqt5 ffmpeg      # Debian / Ubuntu
sudo dnf install python3-qt5 ffmpeg        # Fedora (ffmpeg über RPM Fusion)
sudo pacman -S python-pyqt5 ffmpeg         # Arch
```

**Wenn PyQt5 installiert ist und die Jukebox es trotzdem vermisst**, gehört es
zu einem anderen Interpreter als dem, auf den `python3` zeigt — der
Normalzustand auf einem Rechner mit uv, pyenv oder einer paketierten
virtuellen Umgebung. Zu tun ist nichts: die Jukebox sucht sich einen
Interpreter, der Qt hat, übergibt an ihn und merkt sich das Ergebnis. Hat
keiner auf dem Rechner eines, richtet sie stattdessen eine eigene Umgebung in
`~/.cache/cnc-jukebox/venv` ein und installiert PyQt5 von PyPI hinein — ein
Download, und deshalb der letzte Ausweg statt der erste Griff.

Zum Selbstentscheiden: `CNC_JUKEBOX_PYTHON=/usr/bin/python3 ./cnc-jukebox`
benennt einen Interpreter, `CNC_JUKEBOX_NO_VENV=1` verbietet die eigene
Umgebung. Siehe [`docs/PYTHON.de.md`](docs/PYTHON.de.md).

## Installation

```bash
git clone https://github.com/SoulInfernoDE/cnc-remastered-jukebox-gui.git
cd cnc-remastered-jukebox-gui
```

Es gibt nichts zu bauen. Das Spielverzeichnis wird automatisch gefunden —
gewöhnliches Steam, Flatpak, Snap und jede weitere Bibliothek, die in
`libraryfolders.vdf` steht. `CNC_REMASTERED_DIR` überschreibt die Suche, falls
sie fehlschlägt.

Wie die Jukebox ins Anwendungsmenü kommt oder als Zeile an den unteren Rand des
Spiel-Launchers, wenn du in Steam auf Spielen klickst, steht in
[`docs/STEAM.de.md`](docs/STEAM.de.md).

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
| **Ordner** | öffnet den Soundtrack-Ordner, in den der Exporter seine Dateien schreibt |
| **Rechter Bolzen** | wechselt den Skin, so wie das Spiel ein Gebäude hochzieht |

Zwei weitere unten: **Beenden** und ein Knopf, der zwischen der Jukebox und der
**Soundbox** umschaltet — einem zweiten Bildschirm, der alle 1286 Soundeffekte
des Spiels neben 409 animierten Einheiten und Gebäuden auflistet.

Jeder Knopf hat eine Stimme aus dem passenden Spiel. **Button-Sounds** neben
„Mischen" schaltet das ab; Musik und Soundvorschau bleiben davon unberührt. Die
Einstellungen liegen in `~/.config/cnc-jukebox/playlist.json`.

## Den Soundtrack exportieren

Das ist ein eigenes Programm in einem eigenen Repository:
[**cnc-remastered-jukebox-trackexport**](https://github.com/SoulInfernoDE/cnc-remastered-jukebox-trackexport).
Es schreibt alle 203 Titel als getaggte Dateien, benannt genau so, wie diese
Jukebox sie anzeigt — 12 Stunden 6 Minuten, rund 1,6 GiB. Es braucht weder
PyQt5 noch einen Soundserver: ein Skript auf `python3` und `ffmpeg`.

Der Knopf **Ordner** oben öffnet das Verzeichnis, in das es schreibt.

## Wie es funktioniert

Die interessanten Teile sind aufgeschrieben, statt nur im Code zu stehen:

| | |
| --- | --- |
| [`docs/FILE-FORMATS.de.md`](docs/FILE-FORMATS.de.md) | der MEG-Container, die `.LOC`-Zeichenkettentabelle, die Titelliste |
| [`docs/JUKEBOX-UI.de.md`](docs/JUKEBOX-UI.de.md) | die `.BUI`-Layouts des Spiels, Texturen, Schriften und Sprite-Atlas |
| [`docs/REBUILD.de.md`](docs/REBUILD.de.md) | was der Nachbau daraus macht, und wo die Spieldaten überraschen |
| [`docs/STEAM.de.md`](docs/STEAM.de.md) | der Begleiter am Launcher, und warum das kein Workshop-Element ist |
| [`docs/PYTHON.de.md`](docs/PYTHON.de.md) | wie ein Interpreter mit Qt gefunden wird, und was gilt, wenn keiner einen hat |

Jedes Dokument gibt es auch auf Englisch; oben in jedem steht der Verweis.

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

Die Musik stammt von Frank Klepacki, bei den Bonus-Arrangements von Frank
Klepacki & The Tiberian Sons.

## Lizenz

[MIT](LICENSE) — gilt nur für den eigenen Code dieses Projekts, nicht für das,
was es liest oder erzeugt.
