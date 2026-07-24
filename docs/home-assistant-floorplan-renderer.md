# Home-Assistant-Floorplan auf der Haus-Seite

## Ziel

Die Haus-Seite des Testgeräts zeigt eine für das runde 360×360-Display
aufbereitete Momentaufnahme des Home-Assistant-Floorplans. Der produktive
Rotaryknob auf Version 1.2.0 bleibt davon unabhängig.

## Datenfluss

1. `pyscript/passion_wave_floorplan.py` kombiniert das Basisbild mit den
   sichtbaren Licht-Layern des Home-Assistant-Floorplans.
2. Das Ergebnis wird atomar als
   `/config/www/passion-wave/floorplan-render/live.png` gespeichert.
3. Pyscript veröffentlicht eine neue Revision auf dem retained MQTT-Topic
   `passion_wave/floorplan/revision`.
4. Der ESP32 empfängt die Revision und meldet sie per UART an den ESP32-S3.
5. Ist die Haus-Seite sichtbar, fordert der S3 das neue Bild nach einer kurzen
   Entprellzeit über den ESP32 an. Beim Öffnen der Seite wird grundsätzlich die
   neueste Fassung geladen.

Damit verbleiben WLAN, HTTP und MQTT auf dem ESP32. Der S3 konzentriert sich auf
Touch, Encoder, PNG-Dekodierung und Display-Rendering.

## Aktualisierungsregeln

- Eine Änderung an einem der sieben im Floorplan dargestellten Lichter löst
  automatisch eine Aktualisierung aus.
- Mehrere kurz aufeinanderfolgende Änderungen werden 300 ms gesammelt.
- Alle zehn Minuten wird erneut gerendert, damit auch ausgetauschte
  Floorplan-Quelldateien ohne Neustart übernommen werden.
- Eine sofortige manuelle Aktualisierung ist über den Home-Assistant-Dienst
  `pyscript.passion_wave_floorplan_refresh` möglich.

## Ausgabeformat

- PNG, RGB, 360×360 Pixel
- vor der PNG-Kompression auf die RGB565-Farbpräzision des Displays reduziert
- Floorplan-Inhalt 340×255 Pixel
- Seitenabstand 10 Pixel
- schwarzer Hintergrund und vertikale Zentrierung für den runden Displayrand
- Layer-Verknüpfung per `lighter`, entsprechend dem bisherigen
  `mix-blend-mode: lighten` des Dashboards

## Fehlerverhalten

Das Bild wird zuerst vollständig in eine temporäre Datei geschrieben und danach
atomar ersetzt. Der ESP32 kann deshalb nie eine nur teilweise geschriebene
PNG-Datei abrufen. Ist die Haus-Seite beim Ereignis nicht aktiv, findet kein
unnötiger Transfer statt; beim nächsten Öffnen wird das aktuelle Bild geladen.
