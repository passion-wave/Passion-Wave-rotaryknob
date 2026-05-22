# UX Assurance Report

Stand: 2026-05-19

Dieser Bericht bewertet die Bedienbarkeit der Passion Wave Rotaryknob Firmware
auf dem runden 360 x 360 Display. Grundlage ist eine statische Pruefung der
LVGL-Definitionen in `esphome/passion-wave-rotaryknob.yaml`, der Rotary-Logik
und der Scroll-/Listenlogik.

## Pruefkriterien

- Displaymodell: 360 x 360 Pixel, runder Screen mit Zentrum `180/180`.
- Empfohlene Touchflaeche: mindestens 44 x 44 Pixel.
- Bedingt akzeptabel: 40 bis 43 Pixel nur bei Icon-Zielen, wenn Abstand und
  optische Erkennung klar sind.
- Nicht akzeptabel: unter 40 Pixel, oder ueberlappende Touchflaechen mit
  unterschiedlichen Aktionen.
- Listen: Zeilen muessen scrollbar sein, ausgewaehlte Eintraege muessen per
  Rotary sichtbar nachgefuehrt werden.
- Rotary: Haptik darf nur gespielt werden, wenn ein Rotary-Schritt tatsaechlich
  eine Aktion ausloest.
- Screensaver: Touch beendet den Screensaver, darf ihn aber nicht verschieben
  oder scrollen.

## Zusammenfassung

| Bereich | Ergebnis | Befund |
| --- | --- | --- |
| Seitenlogik | OK | Alle aktiven Seiten setzen `current_page` eindeutig. |
| Rotary-Rollen | OK | Rotary ist nur auf Licht, Media, Cover, Timer und Wecker aktiv. |
| Rotary-Haptik | OK | Haptik wird erst nach `action_handled` gespielt. |
| Screensaver Touch | OK | Scroll-/Gesture-Flags werden geloescht, Fullscreen-Exit liegt vorn. |
| Lesbarkeit | Bedingt OK | Lange Namen werden geklippt, aber nicht unkontrolliert ueberzeichnet. |
| Scrolllisten | OK | Media-Liste ist scrollbar, nutzt 44-px-Zeilen und wird per Rotary nachgefuehrt. |
| Touch-Mindestgroesse | OK | Alle aktiven LVGL-Buttons mit eigener Aktion sind mindestens 44 x 44 px gross. |
| Touch-Ueberlappung | OK | Foto-Seite nutzt einen zentralen Next-Bereich ohne Ueberlappung mit Pfeilen/Zurueck. |

## UseCase Matrix

| UseCase | Test | Ergebnis | Loesung bei negativem Ergebnis |
| --- | --- | --- | --- |
| Grundnavigation Licht/Media/Wetter per Pfeil | Pfeil-Hitboxen oben: 56 x 58 px. | OK | Keine Aenderung notwendig. |
| Swipe zwischen Licht/Media/Wetter | `on_swipe_left/right` plus Gesture-Bubble auf Hauptseiten. | OK | Hardwaretest mit schnellen Swipes bleibt sinnvoll. |
| Extra-Menue per Langdruck oben | Top-Mid-Hitbox 116 x 58 px. | OK | Keine Aenderung notwendig. |
| Lichtstatus vier Slots | Vier Status-Chips 48 x 48 px. | OK | Umgesetzt. |
| Licht aktuelles Licht toggeln | Zentraler Lampenbutton 80 x 80 px. | OK | Keine Aenderung notwendig. |
| Licht Prozent/Farbe antippen | Prozent-Hitbox 104 x 44 px; sekundaere Farb-/Kontextbox steht mit 2 px Abstand daneben. | OK | Umgesetzt. |
| Licht Drawer oeffnen | Label-Hitbox 232 x 44 px. | OK | Umgesetzt. |
| Licht Drawer Slot-Auswahl | Drawer-Buttons 126 x 44 px. | OK | Umgesetzt. |
| Licht Alle-Aus / Toggle unten | Buttons 118 x 46 px. | OK | Umgesetzt. |
| Media Cover/Mitte | Cover 124 x 124, Titelbereich 296 x 64. | OK | Keine Aenderung notwendig. |
| Media Play/Pause | 56 x 56 px. | OK | Keine Aenderung notwendig. |
| Media Previous/Next | 48 x 48 px. | OK | Umgesetzt. |
| Media Liste oeffnen | 48 x 48 sichtbar plus 64 x 64 Overlay. | OK | Keine Aenderung notwendig. |
| Media Shuffle/Repeat | 48 x 48 px. | OK | Keine Aenderung notwendig. |
| Media Auswahl-Popup schliessen | Close 44 x 44 px. | OK | Umgesetzt. |
| Media Tabs Liste/Playlist/Radio/Podcast | Tabs 62 x 44 px. | OK | Umgesetzt. |
| Media Popup Listeneintraege | Zeilen 248 x 44 px, Liste scrollbar, Rotary folgt Auswahl. | OK | Scrollziel auf 48-px-Zeilenschritt angepasst. |
| Media Popup Scrollen | `LV_DIR_VER`, Scrollbar auto, Scroll-Chain aus, `lv_obj_scroll_to_y`. | OK | Keine Aenderung notwendig. |
| Media Popup Nachladen | Auto-Nachladen bei letztem Eintrag bzw. Scroll-Bottom. | OK | Hardwaretest mit echter grosser MA-Library bleibt Pflicht. |
| Media Cover-Screensaver | Fullscreen-Touch 360 x 360, Rotary zeigt Volume-Arc. | OK | Keine Aenderung notwendig. |
| Wetter Hauptseite | Wetter-Zonen sind ueberwiegend Anzeige, Radar-Hitbox 104 x 58. | OK | Keine Aenderung notwendig. |
| Wetter Radar Popup schliessen | Close 44 x 44 px. | OK | Umgesetzt. |
| Regenradar Seite | Zwei Icons je 48 x 48 px. | OK | Umgesetzt. |
| Settings Zurueck | 48 x 44 px. | OK | Keine Aenderung notwendig. |
| Settings Fokus/Wert aendern | Pfeile 44 x 44, Hauptwert 176 x 44. | OK | Umgesetzt. |
| Settings Status WiFi/HA/IP | Textbreite fuer Home Assistant/IP ist verbreitert. | OK | Keine Aenderung notwendig. |
| Timer Preset vor/zurueck | 48 x 48 px. | OK | Umgesetzt. |
| Timer Minute/Sekunde waehlen | Zwei Hitboxen 125 x 82 px. | OK | Keine Aenderung notwendig. |
| Timer Start/Zurueck | 58 x 58 px. | OK | Keine Aenderung notwendig. |
| Timer Reset | 48 x 48 px. | OK | Umgesetzt. |
| Wecker Stunde/Minute | 68 x 44 px. | OK | Umgesetzt. |
| Wecker Pfeile/Zurueck/Aktivieren Icon | 48 x 48 px. | OK | Umgesetzt. |
| Wecker Toggle | 90 x 46 px. | OK | Keine Aenderung notwendig. |
| Foto Next durch Bildflaeche | Unsichtbarer Button 200 x 170 ohne Ueberlappung mit Pfeilen/Zurueck. | OK | Umgesetzt. |
| Foto Pfeile/Zurueck | 48 x 48 px. | OK | Umgesetzt. |
| Haus Zurueck | 48 x 48 px. | OK | Umgesetzt. |
| Screensaver verlassen | Fullscreen-Button 360 x 360, Scrollflags deaktiviert. | OK | Keine Aenderung notwendig. |

## Rotary Absicherung

| State | Rotary-Funktion | Ergebnis |
| --- | --- | --- |
| `page_1` Licht | Helligkeit in 5%-Schritten; bei Szenen-/Farbauswahl Auswahlwert. | OK |
| `page_2` Media normal | Lautstaerke in 2%-Schritten. | OK |
| `page_2` Media Popup | Tab-abhaengige Auswahl; Playlist-Nachladen bei Listenende. | OK |
| `page_2` Trackauswahl | Trackauswahl mit Auto-Nachladen. | OK |
| `page_6` Cover | Lautstaerke; Volume-Arc kurz sichtbar. | OK |
| `page_11` Timer | Dauer nur wenn Timer nicht laeuft; Minuten 60 s, Sekunden 10 s. | OK |
| `page_12` Wecker | Aktives Feld Stunde/Minute; Minuten in 5er-Schritten. | OK |
| `page_4/5/7/8/9/10` | Keine Rotary-Aktion, keine Haptik. | OK |

## Umgesetzte Fix-Pakete

### Paket A: Touch-Mindestgroessen

Ziel: Alle interaktiven Flaechen auf mindestens 44 x 44 px bringen, ohne das
sichtbare Design stark zu veraendern.

- 42 x 42 Icon-Buttons wurden auf 48 x 48 gesetzt.
- 38 x 38 Reset/Close-Ziele wurden auf 44/48 px vergroessert.
- 34/38 px hohe Textbuttons wurden auf 44 px bzw. 46 px erhoeht.

### Paket B: Media-Popup

Ziel: Popup bleibt scroll- und rotary-freundlich, wird aber touch-sicher.

- Close-Button 44 x 44.
- Vier kompakte Tabs mit 62 x 44 px.
- Listenzeilen 248 x 44 px; Auto-Nachladen und `lv_obj_scroll_to_y` bleiben aktiv.

### Paket C: Foto-Seite

Ziel: Keine ueberlappenden Touchflaechen mit unterschiedlichen Aktionen.

- Grossen Next-Button auf `x: 80, y: 104, width: 200, height: 170`
  reduziert, sodass Pfeile und Zurueck separat bleiben.

### Paket D: Settings/Timer/Wecker

Ziel: Kleine Utility-Controls auf dem runden Display sicher treffen.

- Settings-Hauptwert 176 x 44.
- Settings-Pfeile 44 x 44.
- Timer Preset-Pfeile 48 x 48.
- Timer Reset: 48 x 48 Hitbox.
- Wecker Stunde/Minute: 68 x 44.
- Wecker Rand-Icons: 48 x 48.

## Freigabeempfehlung

Der aktuelle Stand ist nach statischer LVGL-Pruefung touch-faehig: aktive
Buttons erreichen mindestens 44 px in Breite und Hoehe, und die bekannte
Foto-Ueberlappung ist entfernt.

Vor einer Veroeffentlichung als Endanwenderprodukt bleibt ein echter
Hardwaretest Pflicht: trockene Finger, schnelle Swipes, langsame
Rotary-Bedienung, Media-Library mit vielen Eintraegen und wiederholtes
Aufwachen aus dem Screensaver.
