# Wie die Jukebox nachgebaut ist

*[English](REBUILD.md) · **Deutsch***

[`JUKEBOX-UI.de.md`](JUKEBOX-UI.de.md) beschreibt die Oberfläche des Spiels so,
wie sie auf der Platte liegt. Diese Datei beschreibt, was der Nachbau daraus
macht — die Entscheidungen, die Messungen und die Stellen, an denen die
Spieldaten seltsamer sind als erwartet.

Nichts davon wird mitgeliefert: jedes Pixel, jede Zeichenkette und jeder Klang
wird zur Laufzeit aus der eigenen Installation des Nutzers gelesen.

---

## Nichts ist nach Augenmaß

Jeder Bestandteil stammt aus dem Spiel:

| Element | Quelle |
| --- | --- |
| Geometrie aller ~40 Widgets | `.BUI`-Layoutdateien in `CONFIG.MEG` |
| Rahmen, Flächen, Scanlines, Menühintergrund | `TEXTURES_SRGB.MEG` |
| Embleme, Knöpfe, Kästchen, Regler, Abspielknopf | `MT_COMMANDBAR_COMMON`, der gemeinsame Sprite-Atlas |
| Schriften (RA_Orbitron, Francker, Noto CJK) | `DATA\ART\FONTS` in `CONFIG.MEG` |
| Jede Beschriftung | `MASTERTEXTFILE_<LANG>.LOC` |
| Titel, Längen, Spiel, Art | `<MusicJukeboxTracksList>` |
| Musik und Soundeffekte | `MUSIC.MEG`, `SFX2D_*.MEG`, `SFX3D.MEG` |
| Animationen von Einheiten und Gebäuden | die Texturarchive der Spiele |

Die Layoutzahlen stammen aus dem Eigenschaftsstrom der `.BUI`, der jedes Widget
als vier Fließkommazahlen relativ zu seinem Elternwidget ablegt. Dass das
Modell stimmt, lässt sich in einer Zeile prüfen: der Rahmen ist als 0,75156
breit und 1,00370 hoch abgelegt, was auf einem 16:9-Bildschirm exakt dem 4:3
der 2160×1620 großen Rahmentextur entspricht.

## Sprache

Die Beschriftungen folgen der Systemsprache — `LC_ALL`, `LC_MESSAGES`, `LANG`,
dann `LANGUAGE` — abgebildet auf die neun Sprachen, die das Spiel mitbringt
(EN-US, DE-DE, ES-ES, FR-FR, KO-KR, PL-PL, RU-RU, ZH-CN, ZH-TW), mit EN-US als
Rückfall. Koreanisch und Chinesisch werden über die spieleigene Noto-CJK-Schrift
gesetzt.

Wo eine Beschriftung unübersetzt aussieht, liegt das an den Daten des Spiels
und nicht an einer Lücke hier: die koreanische Tabelle lässt „Available Tracks"
und „Jukebox Music Volume" tatsächlich auf Englisch.

Vier Zeichenketten sind unsere eigenen und nicht die des Spiels, weil das Spiel
für das, was sie benennen, kein Wort hat: **Soundbox**, **Button-Sounds** und
die beiden zugehörigen Hinweise. Sie sind auf Deutsch und Englisch geschrieben
und fallen sonst auf Englisch zurück. Selbst dann kommt der Name des Ziels aus
der Zeichenkettentabelle, wo es einen gibt — `TEXT_JUKEBOX` ist lokalisiert und
lautet auf Russisch „Музыкальный плеер".

## Audio

Qt Multimedia wird bewusst nicht benutzt. Seine ALSA- und
PulseAudio-Erweiterungen stecken in einem eigenen Paket, das oft fehlt, und
`QAudioOutput` fällt dann wortlos auf ein stummes Nullgerät zurück. Die Titel
werden stattdessen mit ffmpeg dekodiert und an `paplay`, `aplay` oder `ffplay`
geschrieben, was überall funktioniert, wo der Desktop Ton hat. Nichts berührt
die Platte: die dekodierten Daten bleiben im Speicher.

### Eine Zeile, die nie aufgenommen wurde

„Gefechtsführung beendet" gibt es beim Tiberiumkonflikt auf Deutsch nicht. Die
Datei wird trotzdem ausgeliefert und enthält eine Viertelsekunde Raumton — 19
RMS, wo die echten Aufnahmen zwischen 3400 und 7900 liegen. Der Beenden-Knopf
schloss in diesem Skin deshalb lautlos.

Das Spiel gibt es selbst zu: die deutsche `TEXT_SFX_TDC_SFX_BATLCON1` lautet
`empty`, während jede andere Sprache dort den Satz trägt. Es ist eine einzelne,
bestimmte Lücke und kein fehlendes Sprachpaket — von den 136 deutschen
EVA-Zeilen des Tiberiumkonflikts sind genau zwei leer, und das sind die
klassische und die remasterte Aufnahme derselben Zeile.

Ein Klang, der unter 200 RMS herauskommt, wird deshalb durch die englische
Aufnahme ersetzt — so, wie ein unübersetzter Untertitel in der Soundbox schon
englisch bleibt. Der Schwellwert liegt nach beiden Seiten um den Faktor
siebzehn frei. Derselbe Weg deckt eine Sprache mit ab, deren Sprachpaket Steam
nicht heruntergeladen hat; sonst bliebe dort jeder Knopf stumm.

Das Messen kostet nichts. `play_effect` dekodiert ohnehin auf einem
Arbeitsthread, die Prüfung läuft also auf PCM, das dort bereits vorliegt, und
die Ersatzaufnahme wird günstig geholt, aber nur dann dekodiert, wenn sie
wirklich gebraucht wird.

## Das sich drehende Emblem

Das Emblem des laufenden Titels dreht sich wie ein geschlagenes Werkstück und
nicht wie ein Blatt Papier. Dreht man eine Ebene um ihre senkrechte Achse,
liegt ein Punkt bei `x·cos θ + z·sin θ`. Die Achse verläuft durch die Mitte des
Materials, `z` reicht also von `-T/2` bis `+T/2`, statt an einer Fläche zu
hängen: die beiden Flächen landen bei `±T/2·sin θ`, die Silhouette bleibt
mittig, und das Stück dreht sich an Ort und Stelle, statt seitlich
auszuschwenken.

Welche Fläche zu sehen ist, folgt demselben Winkel. Die Tiefe auf der Achse ist
`z·cos θ`, die nähere Ebene kippt also mit dem Vorzeichen des Kosinus, und in
diesem Moment wird die sichtbare Fläche gespiegelt, auf den anderen Versatz
gesetzt und die Schichten werden in umgekehrter Reihenfolge gezeichnet.

Über eine volle Umdrehung gemessen bleibt der Schwerpunkt der Silhouette
innerhalb von 5 px zur Achse und bewegt sich nie mehr als 1 px je 5 Grad. Was
übrig bleibt, ist die Asymmetrie des Emblems selbst, die ein echter Gegenstand
genauso zeigen würde.

Eine zweite Ausfertigung sitzt rechts neben der Wiedergabeleiste, spiegelt den
Abspielknopf auf deren anderer Seite und dreht sich um denselben Winkel, sodass
beide im Gleichschritt bleiben.

## Die Soundbox

Zwei Verzeichnisse aus der Installation, nebeneinander:

- **Links** — jeder Effekt des Spiels, 1286 an der Zahl, gruppiert nach Spiel,
  Klangtreue und Art, und auf Klick abgespielt. Bei gesprochenen Zeilen steht
  dabei, was sie tatsächlich sagen: die Zeichenkettentabelle führt sie unter
  `TEXT_SFX_<stem>` ohne den Teil `EVA_`/`UNT_`, was 369 von ihnen abdeckt. Nur
  die Schlüssel mit Classic-Präfix sind übersetzt, diese werden also
  bevorzugt; wo das Spiel selbst eine Zeile nie übersetzt hat, bleibt sie auch
  hier englisch, genau wie im Spiel.
- **Rechts** — 409 Einheiten, Gebäude und Effekte, jeweils aus den eigenen
  Sprite-Bildern animiert. Die Archive halten sie als je ein Zip aus
  unkomprimierten TGA pro Objekt, aufgelistet von `TD_UNITS.XML` und
  Geschwistern; nur das ausgewählte Objekt wird dekodiert, verkleinert und
  behalten.

Sie stehen nebeneinander, statt dass eins das andere herleitet, und das ist
Absicht: **die Spiele liefern keinerlei Zuordnung von einem Klang zu „seiner"
Einheit oder seinem Gebäude.** Ein Abgleich aller 508 Klangstämme gegen alle
192 Objektnamen ergibt überhaupt keine Übereinstimmung, und die wenigen
Teiltreffer sind Zufall. Sie zu paaren hieße, die Paarung zu erfinden.

## Die Bedienelemente der Kopfleiste

Die Kopfleiste von Alarmstufe Rot trägt runde Messingbolzen, die des
Tiberiumkonflikts Sechskantköpfe, die höher und weiter außen sitzen. Die
Umrandung beim Überfahren folgt deshalb der Form und Lage, die der jeweilige
Skin tatsächlich hat — auf den Texturen gemessen, nicht angenommen.

- **Linker Bolzen** — öffnet das Projekt auf GitHub, wobei EVA sich in der
  Stimme des jeweiligen Spiels bedankt. Die beiden Spiele führen das unter
  verschiedenen Stämmen: `EVA_ETHANKS` beim Tiberiumkonflikt, `EVA_THANKU1` bei
  Alarmstufe Rot.
- **Ordner** — öffnet den Soundtrack-Ordner, gezeichnet in der Farbe des
  aktuellen Skins, über einem einsekündigen Country-Jingle. Alarmstufe Rot
  liefert dazu kein Gegenstück — dort gibt es nur Piepser und Töne —, weshalb
  alle drei Skins den des Tiberiumkonflikts verwenden; er ist ein Jingle und
  keine Fraktionsstimme.
- **Rechter Bolzen** — wechselt den Skin, so wie das Spiel ein Gebäude
  hochzieht: das Emblem der nächsten Fraktion erscheint über der ganzen
  Oberfläche, EVA kündigt den Bau an, eine Bauuhr läuft in drei Sekunden einmal
  herum, die Zeile „Konstruktion fertig" erklingt, und der neue Skin setzt sich
  mit dem Platzierungsklang des jeweiligen Spiels.

## Woher das zweite Kästchen kommt

**Button-Sounds** teilt sich die Zeile mit „Mischen". Dafür ist Platz, weil
keine der neun Übersetzungen von „Mischen" ihren Textrahmen auch nur annähernd
füllt — Polnisch, die längste, braucht ein Drittel davon. Das Kästchen setzt
deshalb dort an, wo der Text tatsächlich aufhört, und nicht dort, wo das Layout
ihn enden lassen dürfte; braucht eine Übersetzung den Platz doch einmal, tritt
es ganz zurück. Über alle neun Sprachen, beide Schriften und Fenstergrößen ab
880×660 gemessen bleibt im engsten Fall noch 61 px Luft.

## Das Fenstersymbol

Das Fenster hat keinen Rahmen, es gibt also keine Titelleiste, die ein Symbol
tragen könnte, und Taskleiste wie Fensterwechsler zeigten sonst eine Leerstelle.
Es bekommt daher ein gezeichnetes: ein Jukebox-Gehäuse in den Farben des
aktuellen Skins, dessen Scheibe das Emblem des jeweiligen Spiels aus dem Atlas
zeigt, über zwei runden Boxen in der Akzentfarbe. Es folgt dem Skin, ein
Skinwechsel wechselt also auch das Symbol.

`--write-icon PFAD` zeichnet es in eine Datei; so kommt der Menüeintrag zu
seinem Symbol.

## Einstellungen

Wiedergabeliste, Filter, Lautstärke, Button-Sounds und der gewählte Skin liegen
in `~/.config/cnc-jukebox/playlist.json`. Der Skin wird gelesen, bevor das
Fenster gebaut wird, denn Layout, Texturen, Schriften und Fenstersymbol hängen
alle daran.

## Weiterhin nicht nachgebaut

Das Launcher-Fenster — jenes, das beim Klick auf Spielen in Steam erscheint —
gehört zu `ClientLauncherG.exe`. Seine Grafiken sind wiederherstellbar, und die
Zeile, die dieses Projekt darunter setzt, ist aus eben diesen Bitmaps gebaut
(siehe [`STEAM.de.md`](STEAM.de.md)) — aber anders als die Jukebox hat es keine
`.BUI`, ein vollständiger Nachbau hieße also, das Layout von Hand zu
vermessen. Was der Dump hergibt,
steht unter „Noch offen" in [`JUKEBOX-UI.de.md`](JUKEBOX-UI.de.md), zusammen
mit den beiden Teilen des `.BUI`-Formats, die noch nicht entschlüsselt sind.
