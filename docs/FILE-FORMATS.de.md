# Dateiformate

*[English](FILE-FORMATS.md) · **Deutsch***

Notizen aus dem Lesen der Datendateien der Command & Conquer Remastered
Collection. Alles hier wurde durch Untersuchen der ausgelieferten Archive
hergeleitet; die Offsets sind gegen alle 22 `.MEG`-Dateien einer
Verkaufsinstallation geprüft.

Alle Ganzzahlen sind little-endian.

---

## Petroglyph MEG, Version 3

Wird von jeder `.MEG` in `Data/` benutzt.

### Kopf

| Offset | Typ | Feld |
| ---: | --- | --- |
| 0 | `uint32` | `0xFFFFFFFF` — optionales Präfix; fehlt es, steht die Signatur bei Offset 0 |
| 4 | `uint32` | `0x3F7D70A4` — Signatur |
| 8 | `uint32` | `data_start` — erstes Byte der Nutzdaten |
| 12 | `uint32` | `num_filenames` |
| 16 | `uint32` | `num_files` |
| 20 | `uint32` | `filename_table_size` in Bytes |

`0xFFFFFFFF` kennzeichnet üblicherweise einen verschlüsselten Kopf, doch die
Remastered Collection liefert dieses Präfix mit Tabellen im Klartext aus —
also die Signatur erkennen, statt Verschlüsselung anzunehmen.

### Dateinamentabelle

Beginnt direkt nach dem Kopf, ist `filename_table_size` Bytes lang und enthält
`num_filenames` Einträge:

```
uint16 length
char   name[length]     // ASCII, NICHT nullterminiert
```

Pfade verwenden Rückstriche: `DATA\AUDIO\MUSIC\TDR_MUS_ACT_ON_INSTINCT.WAV`.
Die Tabelle ist alphabetisch sortiert, was *nicht* der Reihenfolge der
Nutzdaten entspricht.

### Dateitabelle

`num_files` Datensätze zu je 20 Bytes, unmittelbar nach der Dateinamentabelle.
Zwischen Tabelle und `data_start` kann Füllmaterial folgen; davor gibt es
keines.

**Die Datensätze sind unausgerichtet gepackt** — die 32-Bit-Felder liegen nicht
auf 4-Byte-Grenzen. Sie mit einer ausgerichteten Struktur zu lesen ist der
übliche Grund, warum ein MEG-Parser Unsinn ausgibt:

| Offset | Typ | Feld |
| ---: | --- | --- |
| 0 | `uint16` | Flags |
| 2 | `uint32` | CRC32 des kleingeschriebenen Dateinamens |
| 6 | `uint32` | Datensatzindex |
| 10 | `uint32` | Dateigröße |
| 14 | `uint32` | Dateioffset |
| 18 | `uint16` | Index in die Dateinamentabelle |

Die Datensätze sind nach CRC32 sortiert, Datensatz *n* gehört also nicht zu
Dateiname *n* — immer über das Feld `name_index` gehen.

```python
size, offset = struct.unpack_from("<II", records, i * 20 + 10)
name_index   = struct.unpack_from("<H",  records, i * 20 + 18)[0]
```

### Nachprüfung

Bei `MUSIC.MEG` zeigt jeder der 203 Datensätze auf einen gültigen
`RIFF`/`WAVE`-Kopf, und die gespeicherte Größe entspricht dem RIFF-Größenfeld
+ 8 — eine billige und zugleich vollständige Selbstprüfung für jede
Umsetzung.

---

## MASTERTEXTFILE_&lt;LANG&gt;.LOC

Die Tabelle der lokalisierten Zeichenketten, in `CONFIG.MEG` unter
`DATA\TEXT\MASTERTEXTFILE_<LANG>.LOC`.

```
uint32 count
count × {
    uint32 key_hash
    uint32 value_length     // in UTF-16-Zeichen, nicht in Bytes
    uint32 key_length       // in Bytes
}
```

Dann die Zeichenketten, und das ist der Teil, den man kennen sollte: Werte und
Schlüssel liegen in **zwei getrennten Blöcken**, nicht abwechselnd je Datensatz.

```
alle Werte,     aneinandergehängt, UTF-16LE, ohne Trennzeichen
alle Schlüssel, aneinandergehängt, ASCII,    ohne Trennzeichen
```

Wert *i* und Schlüssel *i* findet man also, indem man die vorangehenden Längen
innerhalb des jeweils eigenen Blocks aufsummiert. Die Datei endet exakt am Ende
des Schlüsselblocks, was eine präzise Plausibilitätsprüfung ergibt:

```
4 + count*12 + Σ(value_length)*2 + Σ(key_length) == Dateigröße
```

Die Datensätze sind nach `key_hash` sortiert.

---

## Die Titelliste der Jukebox

`CONFIG.MEG` → `DATA\XML\AUDIO\AUDIO_SYSTEM_CONSTANTS.XML`, Element
`<MusicJukeboxTracksList>`. Das ist die Liste, aus der die Jukebox im Spiel
gebaut wird; `MUSICEVENTS.XML` verweist nur in einem Kommentar darauf.

```xml
<entry Name="Act_On_Instinct">
    <FileName> TDR_MUS_Act_On_Instinct.wav </FileName>
    <TextID> TEXT_MUSIC_TDR_MUS_ACT_ON_INSTINCT </TextID>
    <TrackType> Remaster </TrackType>
    <TrackLengthSeconds> 166 </TrackLengthSeconds>
    <Game> Tiberian_Dawn </Game>
    <BonusContentUnlock> False </BonusContentUnlock>
</entry>
```

`FileName` entspricht dem Basisnamen in `MUSIC.MEG` ohne Rücksicht auf
Groß- und Kleinschreibung; `TextID` ist ein Schlüssel in der `.LOC`-Tabelle.
Beide Seiten decken alle 203 Titel genau ab.

### Zwei Einzelheiten

**`&&` bedeutet ein einzelnes `&`.** Das UI-Framework maskiert
Kaufmannsunds, `Grinder 1 && 2 Medley` erscheint also als
`Grinder 1 & 2 Medley`.

**Musiktitel werden nicht übersetzt.** `MASTERTEXTFILE_DE-DE.LOC` und
`MASTERTEXTFILE_EN-US.LOC` liefern für alle 203 `TEXT_MUSIC_*`-Schlüssel
byteidentische Zeichenketten; die Sprachwahl wirkt sich auf die Ausgabe also
nicht aus.

---

## Audio

Jeder Titel in `MUSIC.MEG` ist eine RIFF/WAVE-Datei mit dem Formatkennzeichen
`0x0002` (Microsoft ADPCM):

| Aufbau | Anzahl | Entspricht |
| --- | ---: | --- |
| Stereo 44100 Hz | 114 | Remastered und Bonus |
| Mono 22050 Hz | 84 | Classic (die Originale von 1995/96) |
| Stereo 44101 Hz | 4 | — |
| Stereo 44099 Hz | 1 | — |

Die um eins danebenliegenden Abtastraten stecken in den Quelldateien selbst;
ffmpeg rechnet sie klaglos auf 44100 Hz um.
