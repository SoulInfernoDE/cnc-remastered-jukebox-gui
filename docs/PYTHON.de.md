# Einen Interpreter mit Qt finden

*[English](PYTHON.md) · **Deutsch***

Die Jukebox startet über eine Shebang-Zeile und beginnt damit unter dem, was
`python3` auf dem jeweiligen Rechner gerade bedeutet. Auf einem Rechner mit
uv, pyenv oder einer paketierten virtuellen Umgebung ist das selten der
Interpreter, für den das PyQt5 der Arbeitsumgebung installiert wurde — und
bisher wurde dann aufgegeben und „install python3-pyqt5" ausgegeben, was auf
einem solchen Rechner gleich doppelt falsch ist: das Paket liegt längst da,
nur nicht im Suchpfad dieses Interpreters.

---

## Wie das in Wirklichkeit aussieht

Gemessen auf einem Linux Mint 22.3 mit installiertem uv:

| Interpreter | Version | PyQt5 |
| --- | --- | --- |
| `python3` → `~/.local/bin/python3` → uvs CPython | 3.15.0 | **nein** |
| `/usr/bin/python3` | 3.12.3 | ja |

uv hatte sein eigenes `python3` im `PATH` vor das des Systems gesetzt. Nichts
war kaputt und nichts fehlte; die beiden trafen einander nur nie.

Hinter der ersten Falle steckt eine zweite. Auf jenem Rechner ist PyQt5 eine
pip-Installation in `~/.local/lib/python3.12/site-packages`, gegen die
Qt-Bibliotheken des Systems gebunden, und sie bringt keine eigenen Qt-Plugins
mit:

```
>>> QCoreApplication.libraryPaths()
[]
>>> QApplication(sys.argv)
This application failed to start because no Qt platform plugin could be initialized.
```

Der Import gelingt einwandfrei, und trotzdem lässt sich kein Fenster öffnen.
**Dass PyQt5 importierbar ist, beweist also nicht, dass ein Interpreter
brauchbar ist** — deshalb geht die Prüfung hier einen Schritt weiter und
vergewissert sich, dass auch ein Plattform-Plugin erreichbar ist.

## Was jetzt geschieht

1. **Dieser Interpreter**, sofern er PyQt5 importieren und ein
   Plattform-Plugin erreichen kann. Fehlt nur der Plugin-Pfad — der Fall oben
   —, wird er repariert, indem `QT_PLUGIN_PATH` auf ein vorhandenes
   Plugin-Verzeichnis zeigt, und sonst geschieht überhaupt nichts.
2. **Irgendein anderer Interpreter auf dem Rechner.** Der der Distribution
   zuerst, denn dort liegt das PyQt5 einer Distribution, und genau ihn
   verdeckt ein paketiertes Python. Jeder Kandidat wird in einem eigenen
   Prozess befragt, der antwortet, ob er PyQt5 importieren kann *und* wo seine
   Plugins liegen. Der erste, der kann, bekommt das Programm per `execve`.
3. **Eine eigene Umgebung** in `~/.cache/cnc-jukebox/venv`, mit PyQt5 von
   PyPI. Diese Fassung bringt ihr eigenes Qt und ihre eigenen Plugins mit und
   funktioniert deshalb auch auf einem Rechner ganz ohne Qt — sie ist aber ein
   Download und darum der letzte Ausweg statt des ersten Griffs.

Das Ergebnis wird in `~/.cache/cnc-jukebox/interpreter.json` festgehalten und
wiederverwendet, die Suche findet also einmal statt:

```
Kaltstart, Suche und Übergabe             0,76 s
Warmstart, direkt zum gemerkten           0,27 s
Aufbau der eigenen Umgebung               22,5 s, 217 MB auf der Platte
```

Funktioniert der gemerkte Interpreter einmal nicht mehr — entfernt,
aktualisiert, Qt deinstalliert —, verwirft der zweite Versuch die Notiz und
sucht erneut. Ein Zähler in der Umgebung beendet das nach zwei Übergaben,
damit ein Rechner, auf dem gar nichts geht, eine Meldung bekommt und keine
Schleife.

## Selbst entscheiden

```bash
CNC_JUKEBOX_PYTHON=/usr/bin/python3 ./cnc-jukebox   # diesen nehmen
CNC_JUKEBOX_NO_VENV=1 ./cnc-jukebox                 # nie eine Umgebung bauen
rm -rf ~/.cache/cnc-jukebox                         # vergessen und neu suchen
```

## Warum nicht einfach alles in ein venv

Weil auf dem Rechner oben PyQt5 bereits installiert war und funktionierte. Mit
einer eigenen Umgebung anzufangen hätte eine zweite Fassung von Qt
heruntergeladen und 217 MB aufgewendet, um etwas zu ersetzen, das einen Pfad
weiter lag — und zwar auf jedem Rechner, auch auf den vielen, bei denen das
Paket der Distribution genau richtig ist. Die eigene Umgebung ist die richtige
Antwort für einen Rechner ohne Qt; für einen, der es nur woanders hat, ist sie
die falsche.

## Der Exporter ist nicht betroffen

`cnc_trackexport` verwendet ausschließlich die Standardbibliothek, jeder
Interpreter führt ihn also aus — auch der von uv. Geprüft unter CPython 3.15,
er liest alle 203 Titel korrekt.
