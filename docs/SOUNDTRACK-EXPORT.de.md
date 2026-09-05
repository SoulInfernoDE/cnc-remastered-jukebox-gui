# Den Soundtrack exportieren

*[English](SOUNDTRACK-EXPORT.md) · **Deutsch***

Notizen zu `cnc_trackexport`: woher die Titel stammen, warum alles umgerechnet
wird und was die verlustfreie Option zusichert.

---

## Woher die echten Titel kommen

In `MUSIC.MEG` heißen die Stücke `TDR_MUS_ACT_ON_INSTINCT.WAV` und
`RAB_MUS_HM_2_3_MEDLEY_FKTS.WAV`. Nichts in diesem Archiv sagt, dass das
„Act On Instinct (Remastered)" und „Hell March 2 & 3 Medley – Tiberian Sons
(Bonus)" sind. Die meisten Extraktoren lassen einen deshalb mit den rohen
internen Namen zurück oder raten hübschere.

Die echten Titel stehen in einem anderen Archiv, und der Exporter liest sie
dort, wo auch das Spiel sie liest:

| Quelle | Was sie liefert |
| --- | --- |
| `Data/MUSIC.MEG` | die Audiodaten (Petroglyph MEG V3) |
| `Data/CONFIG.MEG` → `AUDIO_SYSTEM_CONSTANTS.XML` | `<MusicJukeboxTracksList>` — buchstäblich die Jukebox-Liste: Dateiname → Text-ID |
| `Data/CONFIG.MEG` → `MASTERTEXTFILE_<LANG>.LOC` | Text-ID → der angezeigte Titel |

Die Zuordnung ist vollständig und exakt: **203 Jukebox-Einträge ↔ 203
Audiodateien ↔ 203 lokalisierte Titel**, auf keiner Seite bleibt etwas übrig.
Kein Raten, keine Nachschlagetabelle, die gepflegt werden müsste.

Container- und Zeichenkettenformat sind in
[`FILE-FORMATS.de.md`](FILE-FORMATS.de.md) beschrieben, einschließlich der
Einzelheit, über die die meisten MEG-Leser stolpern: die 20-Byte-Datensätze
sind **unausgerichtet** gepackt, die 32-Bit-Felder liegen also nicht auf
4-Byte-Grenzen.

## Warum alles auf 44,1 kHz umgerechnet wird

Die MP3-Ausgabe ist immer **44,1 kHz bei 320 kbit/s**, auch bei den
Classic-Titeln — und die Abtastrate ist dabei der Punkt, keine Äußerlichkeit.

Die Classic-Titel sind Mono in 22,05 kHz MS-ADPCM. Eine MP3-Kodierung bei
dieser Rate versetzt LAME in MPEG-2 Layer III, das bei 160 kbit/s gedeckelt ist
und, gegen diese Quellen gemessen, zusätzlich um 9,9 kHz herum abfällt —
während die Quelle Anteile bis 10,5 kHz trägt. Erst auf 44,1 kHz umzurechnen
hält LAME in MPEG-1 und bewahrt das Material:

| | bei 22,05 kHz kodiert | auf 44,1 kHz umgerechnet |
| --- | --- | --- |
| Spektralfehler gegenüber der Quelle | −10,1 dB | **−39,2 dB** |
| Energie oberhalb 9,9 kHz erhalten | 16 % | **100 %** |

Gemessen an der dekodierten Ausgabe gegen die dekodierte ADPCM-Quelle,
gemittelt über Fenster von 8192 Abtastwerten — ein phasenunabhängiger
Vergleich, die Verzögerung des Encoders kann das Ergebnis also nicht
schönen.

## Verlustfreie Ausgabe

`--format flac` ist die Archivvariante. Sie behält für jeden Titel die
ursprüngliche Abtastrate bei und ist **bitgenau**: das Dekodieren der FLAC und
das Dekodieren der ADPCM-Quelle ergeben byteidentisches PCM, geprüft durch
Vergleich der MD5-Summen der rohen dekodierten Ströme für alle drei im Archiv
vorkommenden Abtastraten. Tags und Titelbild werden genau so eingebettet wie
bei MP3.

Es kostet ungefähr das 2,5-fache des MP3-Exports — etwa 3,3 GiB — weil die
Quelle 4-Bit-ADPCM ist, FLAC aber das dekodierte 16-Bit-PCM verlustfrei
speichert.

`--format wav` ist die dritte Möglichkeit: die unveränderten ADPCM-Dateien
direkt aus dem Archiv, Byte für Byte, ohne Tags und ohne Neukodierung. Die
kleinste der drei Varianten (~1,4 GiB), aber für die meisten Abspielprogramme
unhandlich.

## Tags und Dateinamen

`title` trägt den exakten Jukebox-Titel. `artist` wechselt bei den Tiberian-
Sons-Arrangements auf „Frank Klepacki & The Tiberian Sons", und `grouping` und
`comment` enthalten Spiel und Titelart („Red Alert Bonus"), sodass eine
Bibliothek Classic, Remastered und Bonus auf einen Blick trennen kann. Die
Titelnummern folgen der alphabetischen Ordnung der Jukebox selbst.

Neun Titel enthalten ein echtes `/` („Warfare / Full Stop"), das kein Dateiname
tragen kann. Diese verwenden U+2215 DIVISION SLASH — optisch nicht zu
unterscheiden und auf ext4, NTFS und FAT32 gleichermaßen gültig. Das
`title`-Tag behält immer das echte Zeichen. `--portable` reduziert die
Dateinamen auf reines ASCII, falls das nötig ist.

## Nichts landet außerhalb des Zielverzeichnisses

Es werden überhaupt keine temporären Dateien angelegt. Die Audiodaten werden
ffmpeg über die Standardeingabe zugeleitet, und das Titelbild liegt in einer
anonymen Speicherdatei (`memfd_create`), die als `/dev/fd/N` übergeben wird.
Nach dem Lauf enthält das Zielverzeichnis die fertigen Titel und sonst nichts.

Ein Abbruch mit Strg+C ist unbedenklich: angefangene Dateien werden entfernt,
und der nächste Lauf macht dort weiter, wo er aufgehört hat.
