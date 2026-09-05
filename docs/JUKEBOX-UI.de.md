# Die Jukebox-Oberfläche im Spiel

*[English](JUKEBOX-UI.md) · **Deutsch***

Grundlagenarbeit, um die Jukebox originalgetreu nachzubauen. Alles Folgende
wurde mit [`tools/dump-jukebox-ui`](../tools/dump-jukebox-ui) aus einer
Verkaufsinstallation gelesen; nichts davon liegt diesem Repository bei.

```bash
./tools/dump-jukebox-ui -o jukebox_ui
```

---

## Layoutdefinitionen (`.BUI`)

Sechs Layouts in `CONFIG.MEG` unter `DATA\ART\GUI\`:

| Datei | Entpackt | Rolle |
| --- | ---: | --- |
| `UI_MUSICJUKEBOX.BUI` | 37 389 B | der Jukebox-Dialog des Tiberiumkonflikts |
| `RA_UI_MUSICJUKEBOX_ALLIED.BUI` | 40 239 B | Alarmstufe Rot, Skin der Alliierten |
| `RA_UI_MUSICJUKEBOX_SOVIET.BUI` | 40 134 B | Alarmstufe Rot, Skin der Sowjets |
| `MUSICJUKEBOX.BUI` | 15 806 B | gemeinsamer Basisdialog |
| `UI_MUSICJUKEBOX_LIST_ENTRY.BUI` | 1 233 B | eine Zeile der Titelliste |
| `RA_UI_MUSICJUKEBOX_LIST_ENTRY.BUI` | 1 233 B | eine Zeile, Skin von Alarmstufe Rot |

### Container

Eine `.BUI` besteht aus einem 36-Byte-Kopf, der mit dem ASCII-Kürzel `CH`
beginnt, gefolgt von einem schlichten **zlib-Strom**:

```python
raw   = open("UI_MUSICJUKEBOX.BUI", "rb").read()
plain = zlib.decompress(raw[raw.find(b"\x78\x9c"):])
```

Die entpackten Daten sind ein binärer Widget-Baum. Er ist nicht vollständig
entschlüsselt, aber Widget-Namen, Texturverweise, Schriftnamen und
Fließkomma-Farbkomponenten sind klar lesbar, was zum Rekonstruieren der
Hierarchie genügt.

### Widget-Baum

`UI_MUSICJUKEBOX.BUI` enthält der Reihe nach unter anderem:

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

Eine Listenzeile (`UI_MUSICJUKEBOX_LIST_ENTRY.BUI`) besteht aus nur vier
Elementen:

```
UI_Jukebox_List_Element
├─ UI_Jukebox_Product_Icon        → ui_jukebox_cnctd_icon / ui_jukebox_cncra_icon
├─ UI_Jukebox_Track_Title_Text    "Track Name"  (18 Point Outline)
├─ UI_Jukebox_Track_Time_Text     "00:00"       (18 Point Outline)
└─ UI_Jukebox_Listbox_Entry
```

Das spielabhängige Symbol bestätigt, was die Titelliste braucht: `Game` aus
`<MusicJukeboxTracksList>` wählt das Symbol, `TrackLengthSeconds` füllt das
Feld `00:00`, und der Titel aus der `.LOC` füllt die Zeile.

## Texturen

Neun Jukebox-Texturen in `TEXTURES_SRGB.MEG` unter
`DATA\ART\TEXTURES\SRGB\`, alle unkomprimiertes DDS in **2160 × 1620** mit
Alphakanal:

```
ui_jukebox_bg                    der Rahmen des Tiberiumkonflikts
ui_jukebox_scanlines             CRT-Scanlines als Auflage
ra_jukebox_bg                    Rahmen von Alarmstufe Rot
ra_jukebox_bg_blue / _red        Färbung Alliierte / Sowjets
ra_jukebox_bg_scanlinesblue / _scanlinesred
ra_ui_jukeboxbg_allied / _soviet
```

Dazu die beiden Produktsymbole (`ui_jukebox_cnctd_icon`,
`ui_jukebox_cncra_icon`) und die gemeinsamen Reglerbahn-Teile, auf die die
Layouts verweisen.

ffmpeg wandelt diese in PNG um, aber sein DDS-Dekodierer braucht eine
**springbare** Eingabe — über eine Pipe scheitert er mit „Output file does not
contain any stream". Der Dumper reicht ihm stattdessen eine anonyme
Speicherdatei über `/dev/fd/N`, die springbar ist und trotzdem die Platte nicht
berührt.

## Datenmodell

Der Nachbau braucht nichts, was der Exportpfad nicht ohnehin schon liest:

| Feld | Quelle |
| --- | --- |
| Titel | `MASTERTEXTFILE_<LANG>.LOC` über `TextID` |
| Länge (`00:00`) | `TrackLengthSeconds` |
| Produktsymbol | `Game` (`Tiberian_Dawn` / `Red_Alert`) |
| Classic / Remastered / Bonus | `TrackType` |
| Gesperrt oder nicht | `BonusContentUnlock` |
| Audio | `MUSIC.MEG`, ADPCM-WAV |

Zu den Containern siehe [`FILE-FORMATS.de.md`](FILE-FORMATS.de.md).

## Geometrie

Jedes Widget legt sein Rechteck als vier Fließkommazahlen relativ zum
Elternwidget ab, unter der Marke `0x02` mit der Länge `0x10`. Die Widgets
erscheinen in Tiefensuche, und das Rechteck steht vor dem Namen; paart man also
jedes Rechteck mit dem folgenden Namen, erhält man die flache Liste. Die
Verschachtelung selbst liegt in einer Form vor, die wir nicht entschlüsseln,
weshalb die Abstammung der maßgeblichen Widgets in `jukebox/layout.py` von Hand
erklärt ist.

Zwei Bezugssysteme sind im Spiel, und sie zu verwechseln ist die Falle:

- **Alarmstufe Rot** fasst die Oberfläche in `SovietJukebox_Group` bzw.
  `AlliesJukebox_Group` und gibt den Inhalt relativ dazu an.
- **Der Tiberiumkonflikt** hat keine solche Gruppe und gibt dieselben Widgets im
  Bildschirmraum an.

Beide führen auf dieselben absoluten Positionen, und genau das ist die Probe,
dass das Modell stimmt: `Available_Songs` landet in beiden Fällen bei 0,16979
der Bildschirmbreite.

Der entscheidende Test für den äußeren Rahmen ist das Seitenverhältnis. Die
Gruppe ist mit 0,75156 Breite und 1,00370 Höhe abgelegt; auf einem
16:9-Bildschirm sind das 12,02 mal 9,03 Einheiten, exakt das 4:3 der
2160×1620 großen Rahmentextur. Läse man sie stattdessen relativ zum Dialog,
käme ein Quadrat heraus, zu dem keine Textur passt. Die Gruppe ist also im
Bildschirmraum verortet — und sie *ist* das Fenster.

### Den Rahmen zuschneiden

Die Hintergrundtextur trägt außerhalb des Metallrahmens einen weichen
Schlagschatten. Im Spiel geht der in das dahinterliegende Menü über; ein
eigenständiges Fenster zeigte ihn als schwarzen Rand. Auf dem Alphakanal
gemessen nimmt der vollständig deckende Rahmen x 47..2113, y 33..1585 von
2160×1620 ein — normiert (0,02176, 0,02037, 0,95648, 0,95802), Seitenverhältnis
1,3312. Vergrößert man die Zeichenfläche um genau diesen Einzug, liegt der
Schatten außerhalb des Fensters, und Widget-Rechtecke, die gegen dieselbe
Fläche aufgelöst werden, bleiben passgenau.

## Texturen

Die Jukebox-Texturen sind unkomprimiertes 32-Bit-DDS, dessen Kanalmasken
(R=0x00ff0000, G=0x0000ff00, B=0x000000ff, A=0xff000000) genau das
Speicherlayout von `QImage::Format_ARGB32` beschreiben. Der Block hinter dem
128-Byte-Kopf lässt sich Qt also ohne jeden Dekodierschritt übergeben.

Die Listenflächen des Tiberiumkonflikts sind durchsichtig: die Layouts
schichten einen bildschirmfüllenden `Background` (`ui_mainmenubg_01`, bei
Alarmstufe Rot `ui_ra_menu_bg`) und ein `Background_Darken` hinter den Rahmen.
Ohne beides scheint die Menügrafik glatt durch die Flächen hindurch.

## Schriften

`CONFIG.MEG` führt die Oberflächenschriften unter `DATA\ART\FONTS`:

| Datei | Familie | Verwendet für |
| --- | --- | --- |
| `RA_ORBITRON.TTF` | RA_Orbitron | die Bildschirme von Alarmstufe Rot |
| `FRANCKERW1G-CONDENSEDREG.TTF` | Francker W1G | die Bildschirme des Tiberiumkonflikts |
| `RUSSEL SQUARE.TTF` | RussellSquare | das Command-&-Conquer-Logo |
| `NOTOSANSCJKTC-REGULAR.TTF` | Noto Sans CJK TC | Koreanisch und Chinesisch |

Sie laden mit `QFontDatabase::addApplicationFontFromData` direkt in Qt, sodass
der Nachbau die ursprüngliche Typografie trifft, ohne eine Schrift
mitzuliefern.

## Der gemeinsame Sprite-Atlas

Die Layouts benennen Sprites wie `ui_jukebox_cnctd_icon`, die in **keinem**
Archiv als Datei vorkommen — eine vollständige Bestandsaufnahme aller 22
`.MEG`-Dateien (61 571 Einträge) fördert nichts zutage, und ein PE-Ressourcen-
Dump von `ClientG.exe` ebenso wenig. Sie liegen in einem gemeinsamen
Oberflächen-Atlas.

Eine Volltextsuche über jeden Nicht-Medien-Eintrag der Archive (4 613 Dateien,
47 MiB) findet den Namen an genau einer Stelle: in `MT_COMMANDBAR_COMMON.MTD`,
dem Index zu `MT_COMMANDBAR_COMMON.TGA` — einem 6871 × 6716 großen,
unkomprimierten 32-Bit-TGA von 176 MiB mit Ursprung unten links.

### MTD-Index

```
uint32  0xFFFFFFFE                 Signatur
int32   count                      1554 Einträge
count x {
    uint32  namelen
    char    name[namelen]          im Feld nullterminiert
    int32   rect[8]                x, y, w, h, 0, 0, w, h   (y von oben)
    uint8   pad
}
```

Der Datensatz ist hinter dem Namen 33 Bytes lang, nicht 32: nach den acht
Ganzzahlen folgt ein einzelnes Füllbyte. So gelesen wird die Datei exakt
aufgebraucht, ohne dass Bytes übrig bleiben.

Der Atlas ist viel zu groß, um ihn im Speicher zu halten, aber ein Sprite
braucht nur seine eigenen Zeilen. Der Leser springt deshalb direkt in das
Archiv und liest `h` Läufe zu je `w * 4` Bytes.

### Was die Jukebox daraus verwendet

| Sprite | Größe |
| --- | --- |
| `UI_JUKEBOX_CNCTD_ICON`, `UI_JUKEBOX_CNCRA_ICON` | 28×28 |
| `UI_RA_JUKEBOX_PAUSEPLAY_BTN_NORMAL/HOVERED/PRESSED` | 97×86 |
| `UI_JUKEBOX_PLAYPAUSE_BTN_ON/HOVER` | 65×59 |
| `RA_UI_JUKEBOX_HOVERSTATE_SOVIET/ALLIED` | 866×47 |
| `RA_UI_JUKEBOX_SLIDERBAR_FILL_SOVIET/ALLIED` | 546×15 |
| `UI_JUKEBOX_MUSIC_TIMER_FILL` | 363×11 |

dazu die gemeinsamen Familien für Kästchen, Hauptknöpfe und Reglerkugeln
(`RA_UI_OPTIONS_CHECK_BOX_*`, `UI_OPTIONS_CHECK_BOX_*`, `RA_UI_MAINBTN_*`,
`UI_BUTTON_MAIN_08_*`, `*_SLIDERBAR_BALL`, `*_SLIDERBAR_MINUS/PLUS`).

## Anker und Ränder

Der kompakte Eigenschaftsblock enthält neben dem Rechteck drei weitere
Kandidaten. Gemessen über **alle 207 `.BUI`-Dateien des Spiels, 7318 Widgets**:

| Marke | Länge | Was es ist | Verteilung |
| --- | --- | --- | --- |
| `0x07` | 4 | Größenmodus, waagerecht | Werte 0–7; 4 zu 87,5 % |
| `0x12` | 4 | Größenmodus, senkrecht | Werte 0–5; 3 zu 86,3 % |
| `0x26` | 16 | Rand, vier Fließkommazahlen | ungleich null bei 518 Widgets (7 %) |

`0x26` ist ein Rand in **Pixeln**, kein normierter: die vorkommenden Werte sind
kleine ganze Zahlen wie `(2, 2, 2, 2)`, `(4, 4, 0, 0)`, `(0, 8, 0, 0)` und
`(0, -6, 0, 0)`.

Das Paar `(0x07, 0x12)` ist bei 85,8 % aller Widgets `(4, 3)`. In der Jukebox
weichen davon nur die Textbeschriftungen mit `(1, 1)` und `Background` sowie
`Background_Darken` mit `(7, 5)` ab — die beiden Widgets, deren Rechteck
absichtlich über das Elternelement hinausragt (`-0,17188, 0, 1,34375, 1,0`), um
den ganzen Bildschirm zu bedecken.

### Was das für einen Nachbau bedeutet

Über die sechs Jukebox-Layouts hinweg, 139 Widgets, ist **jeder Rand null**,
und jeder Anker steht auf dem Vorgabewert, ausgenommen jene sechs
bildschirmfüllenden Hintergründe. Die Jukebox skaliert also rein
proportional, und die normierten Rechtecke gegen eine 4:3-Fläche aufzulösen ist
keine Näherung — es ist das, was das Layout sagt. Deshalb saß die Geometrie
schon beim ersten Versuch.

## Noch offen

- Der breite Eigenschaftsblock hinter dem Namen jedes Widgets (uint32 Marke,
  uint32 Länge) ist nicht entschlüsselt. Er enthält den Namen und mindestens
  die Marken `0x13`, `0x14` und `0x27`, und die Längen tragen dort mitunter ein
  Flag im höchsten Bit. Vermutlich stecken darin die Eltern-Kind-Verweise; die
  Abstammung wird bis auf Weiteres von Hand erklärt.
- Die Punktgrößen in den Layouts („46 Point Outline") werden nur als Stilnamen
  gelesen; die Textgröße ergibt sich stattdessen als Bruchteil der Fensterhöhe.
- **Das Launcher-Fenster lässt sich doch nachbauen.** Ein PE-Ressourcen-Dump von
  `ClientLauncherG.exe` gibt dessen gesamte Oberfläche her: einen Hintergrund
  in 560×616, vier Spielknöpfe in 255×208 (normal und überfahren), zwei
  Schließknöpfe in 30×30 und zwei Karteneditor-Knöpfe in 515×99, alle als
  unkomprimierte 24-Bit-DIBs. Nur das Layout müsste vermessen werden, denn eine
  `.BUI` gibt es dafür nicht.
