# Testkatalog: Dual-MCU Performance-Stufe 1

Dieser Katalog qualifiziert jeden physischen RotaryKnob getrennt mit der
koordinierten S3- und Bridge-Version `3.0.0-beta.15`. Vor einem schreibenden
Test das Zielgerät eindeutig über PassionWave Config Entry, Endpoint-Namen und
installierte Version identifizieren.

## Abnahmekriterien

- sichtbare oder haptische Encoderreaktion: p99 kleiner als 25 ms;
- `S3 UI Scheduler Gap`: während aktiver Bedienung kein Wert über 25 ms;
- verlorene oder doppelte langsame EC1-Rastungen: 0;
- `EC1 Encoder Read Errors`: 0;
- beide UART-Protokollfehlerzähler: nach dem Start unverändert 0;
- ungeplanter Seitenwechsel oder Touch-Durchgriff: 0;
- ungeplanter Neustart: 0;
- kein direkter S3-Anwendungsnetzpfad und keine unerwartete MQTT-Aktivität;
- alle in `known-issues.md` als live bestätigt markierten Funktionen bleiben
  verfügbar.

Vor jedem Block Diagnosezähler zurücksetzen, beide Versionsstände prüfen und
die Startwerte der Fehlerzähler notieren. Für p99 mindestens 100 Bedienaktionen
ausführen; höchstens eine davon darf 25 ms erreichen oder überschreiten, keine
darf erkennbar hängen bleiben. Wenn keine Messkamera verwendet wird, gilt der
Scheduler-Wert als technische Näherung und die sichtbare Reaktion wird
zusätzlich mit einer 120-fps-Aufnahme stichprobenartig kontrolliert.

## A. Start und Normalpfad

| ID | Durchführung | Soll |
| --- | --- | --- |
| A01 | Beide Prozessoren kalt starten. | Richtige UI erscheint und bleibt sichtbar; keine alte Wetterseite übernimmt. |
| A02 | 30 Sekunden warten. | Beide Link-Sensoren sind an, Coprocessor-Status meldet den aktiven HA-Bridge-Pfad. |
| A03 | Weitere 30 Sekunden warten. | Medien-, Licht- und Wetterzustände aktualisieren sich weiter; kein S3-Anwendungsfallback wird aktiv. |
| A04 | OTA-Erreichbarkeit beider IP-Adressen prüfen. | S3 und ESP32 sind separat erreichbar; der Rettungsweg bleibt erhalten. |
| A05 | Zehn Minuten ohne Bedienung beobachten. | Kein Neustart, keine wachsenden UART-Fehler und kein zyklischer Verbindungsabbruch. |

## B. Navigation und Touch

| ID | Durchführung | Soll |
| --- | --- | --- |
| B01 | Wetter, Licht, Medien, Zeit und Mehr jeweils 20-mal direkt antippen. | Jeder erste Klick reagiert; genau die gewählte Seite öffnet sich. |
| B02 | Medien und Zeit wiederholt öffnen. | Kein vertikaler Reststrich am aktiven Einsprungbutton. |
| B03 | Medien-Popup öffnen und schließen, danach dieselben Displaykoordinaten auf anderen Seiten antippen. | Kein unsichtbares altes UI und kein Touch-Durchgriff. |
| B04 | Licht-, Medien- und Wetter-Popup jeweils an Rand und Mitte bedienen. | Popup bleibt geometrisch stabil und überlagert die Einsprungtasten nicht. |
| B05 | Während 100 schneller Seitenwechsel `S3 UI Scheduler Gap` beobachten. | Kein aktiver Messwert über 25 ms, keine ausgelassene Eingabe. |
| B06 | Alle fünf Hauptmenüeinträge visuell und per Touch prüfen. | Symbolmittelpunkte folgen dem rechten Displaybogen; jeder Text endet rechtsbündig mit 7 px Abstand vor dem Symbol. Hintergründe sind vollständig transparent; kein Randmarker oder vertikaler Reststrich ist sichtbar. |
| B07 | Radar, Fotos, Haus und Einstellungen aus „Mehr“ öffnen. | Die rechte Hauptnavigation ist vollständig ausgeblendet; nur lokale Seitensteuerung wie Zurück und gegebenenfalls Neu laden bleibt bedienbar. |
| B08 | In Radar und Einstellungen bis zum Screensaver warten und anschließend aufwecken. | Die Zusatzansicht wird nicht restauriert; UI Next startet auf Wetter. |
| B09 | Akkustand unter 100% simulieren, `Wach halten` ausschalten und ohne Playback warten. Danach mit aktivem Playback wiederholen. | Nach der konfigurierten Dimmverzögerung fällt die Helligkeit auf den konfigurierten Wert. Ohne Playback schaltet das Display standardmäßig nach 60 s, mit Playback nach 180 s ab; Touch oder Encoder stellt sofort 70% her. |
| B10 | `DEV: Wach halten` in den Geräteeinstellungen sowie `Wach halten` in Home Assistant jeweils ein- und ausschalten. | Beide Bedienstellen bleiben synchron. Im eingeschalteten Zustand starten weder Screensaver noch Dimmen, Display-Abschaltung oder Deep Sleep. |

## C. Encoder

| ID | Durchführung | Soll |
| --- | --- | --- |
| C01 | Je 40 langsame Rastungen links und rechts. | EC1 zählt jede Rastung genau einmal; Richtung stimmt. |
| C02 | Zehn schnelle volle Drehungen je Richtung. | UI bleibt bedienbar; keine Totzone bei schneller Drehung. |
| C03 | 100 schnelle Richtungswechsel. | Keine falsche Richtung, kein Hängen und keine Lesefehler. |
| C04 | Auf Wetter und Mehr drehen. | Hauptmenü und Werte ändern sich nicht. |
| C05 | Medienauswahl öffnen und drehen. | Nur die Liste scrollt; kein Hauptmenüwechsel und kein Lichtbefehl. |
| C06 | Lichtseite drehen. | Nur Helligkeit der ausgewählten Leuchte ändert sich; Haptik folgt der Aktion. |
| C07 | Medienseite drehen. | Nur Lautstärke ändert sich; Fortschritt und Seite bleiben stabil. |

## D. Medien und Music Assistant

| ID | Durchführung | Soll |
| --- | --- | --- |
| D01 | Play/Pause, Vor, Zurück jeweils 20-mal bedienen. | Lokale UI reagiert sofort; genau ein HA-Befehl pro Klick. |
| D02 | Lautstärke langsam und mindestens fünf Sekunden konstant schnell in beide Richtungen ändern. | Zahl und Bogen folgen monoton ohne Rücksprünge; 350 ms nach Drehende darf HA auf den bestätigten Endwert konvergieren. |
| D03 | Shuffle und Repeat im Kontextfenster ändern. | Zustand wird einmal ausgeführt und korrekt zurückgespiegelt. |
| D04 | Medienauswahl öffnen und mit Touch sowie Encoder über Bootstrap, erste Seite und mindestens zwei weitere Seitengrenzen scrollen. | Popup wird vor einer Netzwerkanfrage sichtbar. Das virtuelle 16-Zeilen-Fenster rückt ohne sichtbaren Sprung weiter; fünf Einträge vor dem Cache-Ende wird genau eine 24er-Folgeseite über den ESP32 angefordert. Scrollposition und Eingaben bleiben während der Antwort stabil. |
| D05 | Eine Playlist auswählen. | Sofort erscheint `WIRD GESTARTET`; Titelliste wird über den ESP32 geladen und der erste Titel startet. Das Popup schließt erst nach positiver HA-Bestätigung. |
| D06 | Radio und Podcast auswählen. | Auswahl startet; kein Wechsel auf Licht und kein Helligkeitsbefehl. |
| D07 | Einen langen Titel abspielen. | Laufschrift läuft ohne Überdeckung des Kreisbogens. |
| D08 | Fortschritt mindestens 60 Sekunden beobachten. | Fortschrittsanzeige läuft, ohne Touch oder Encoder zu verzögern. |
| D09 | Während Paging schnell Encoder und Play/Pause bedienen. | Eingaben bleiben verlustfrei; Scheduler-Lücke bleibt im Ziel. |
| D10 | Coverwechsel auslösen und sofort weiter bedienen. | Download startet erst nach der Ruhephase; aktive Bedienung bleibt unmittelbar. |
| D11 | `Run Encoder Volume SIL Benchmark` auslösen. | 20/20 bestätigt, 0 Timeouts, lokales Rendern < 2 ms, p95 Ende-zu-Ende < 150 ms und Abschlusslautstärke 0 %. |
| D12 | Titel, Radio und Podcast nacheinander auswählen. | Der gewählte Name erscheint sofort im modalen Ladezustand; Diagnose meldet zuerst `Angenommen` und dann `Gestartet`. Bei Fehler bleibt die Auswahl mit verständlicher Meldung offen. |
| D13 | Abschließenden HA-Callback unterdrücken, aber ESP32-Annahme zulassen; danach auch ESP32-Annahme unterdrücken. | Nach Annahme schließt der Ladezustand nach vier Sekunden. Ohne Annahme endet er nach 15 Sekunden mit vollständig lesbarem `START UNKLAR`; kein Touch-Durchgriff. |
| D14 | Während stabiler Bridge eine Playlist auswählen und S3-Netzwerklog beobachten. | Paging läuft über ESP32; der S3 führt keinen normalen `input_select.select_option`-Aufruf aus. |
| D15 | Bei stabiler Bridge retained Playlist-, Radio-, Podcast- und Track-Payloads erneut publizieren. | Der S3 ignoriert die JSON-Payloads; Listen und Auswahl kommen ausschließlich über die ESP32-Binärbridge. |
| D16 | Nach Kaltstart das Medien-Popup erstmals öffnen, schließen und erneut öffnen. | Beide Aufrufe zeigen das vollständige Popup in einem Frame; kein halbseitiger Aufbau. Kalter und warmer Aufruf reagieren ohne wahrnehmbare Blockade. |
| D17 | Eine Playlist öffnen und während ihres Queue-Aufbaus drei unterschiedliche Titel in Abständen von unter zwei Sekunden wählen; danach denselben Titel zweimal schnell wählen. | Jede Eingabe wird sofort als angenommen angezeigt. Music-Assistant-Aufrufe überholen sich nicht; ausstehende Zwischenziele dürfen entfallen und ausschließlich die letzte Generation erhält den finalen Callback. Spätestens nach dem begrenzten Bestätigungs-/Retryfenster spielt der Player den zuletzt gewählten Titel. Eine alte oder identische Abschlussmeldung darf den neueren Auftrag nicht schließen. |

## E. Licht

| ID | Durchführung | Soll |
| --- | --- | --- |
| E01 | Prozentanzeige zehnmal antippen. | Nur die ausgewählte Leuchte toggelt. |
| E02 | Leuchtenname mindestens achtmal antippen. | Jeder Tap wählt lokal genau die nächste konfigurierte Leuchte; leere Slots werden übersprungen, nach dem letzten Slot folgt der erste. Name, Zustand und Helligkeit reagieren p99 unter 25 ms. |
| E03 | WLED in jedem konfigurierten Slot auswählen, Detail öffnen und jedes Preset einmal wählen. Touchbestätigung, Bridge-Befehl, HA-Select-Zustand und sichtbaren Effekt getrennt zeitlich erfassen. | Der Dialog erscheint vollständig in einem Frame und zeigt die Presets des gewählten WLED-Geräts; pro Auswahl wird genau ein `select.select_option` gesendet. Es gibt keine wiederholten Kataloganfragen für unbelegte Platzhalter-Slots. Die lokale Bedienreaktion bleibt sofort; eine konfigurierte WLED-Überblendzeit wird separat von Transport und Bestätigung bewertet. |
| E04 | Hue-Leuchte auswählen und Detail öffnen. Danach eine Szene aus dem Popup wählen. | Es erscheinen nur Hue-Szenen aus dem Home-Assistant-Bereich der Leuchte; genau ein `scene.turn_on` wird gesendet. |
| E05 | Zwischen mehreren Leuchten wechseln und deren Detail-Popup mehrfach schnell öffnen und schließen. | Keine Details des vorherigen Slots oder halb aufgebauten Zeilen werden kurz eingeblendet; Schließen und erneutes Öffnen funktionieren sofort. |
| E06 | Normale Leuchte ohne Details sowie Hue-Leuchte ohne Bereich testen. | Lesbarer leerer Zustand; kein erfundener Eintrag und kein Home-Assistant-Befehl. |
| E07 | Helligkeit bei gleichzeitigem HA-Zustandswechsel drehen. | Lokale Eingabe gewinnt während des Override-Fensters; danach konsistente Rückmeldung. |
| E08 | ESP32 neu starten, Lichtdetail sofort nach Wiederverbindung öffnen. | Der letzte vollständige S3-Katalog bleibt sichtbar; danach stimmen `ESP32 Light Detail Catalog` und `S3 Light Detail Catalog` ohne halbfertige Zwischenliste überein. |
| E09 | Gemischtes OTA: zuerst nur ESP32 aktualisieren, anschließend S3. | Alte S3-Firmware ignoriert neue Frames; nach S3-Update ist die generische Katalogfähigkeit aktiv. Beide OTA-Endpunkte bleiben erreichbar. |
| E10 | Bridge unterbrechen und Lichtdetail öffnen. | Letzter vollständiger Katalog bleibt sichtbar oder zeigt klar „nicht verfügbar“; der S3 sendet keinen direkten Netzwerkbefehl. |
| E11 | Drei Hue-Slots mit je mindestens 27 Szenen kalt starten und während des Katalogtransfers den Encoder drehen. | Alle drei Kataloge sind in unter einer Sekunde vollständig; Eingabe bleibt direkt und beide Protokollfehlerzähler bleiben nach dem Start-Reset bei null. |
| E12 | Nur den S3 neu starten, während ESP32, Home Assistant und Bibliotheksproxy weiterlaufen. | Der S3 fordert selbstständig Snapshots an, bis alle vier Slots vollständig sind. Nach dem Start-Reset bleiben beide Fehlerzähler auch über den nächsten 60-s-Snapshot bei null. |
| E13 | Home Assistant neu starten oder nur die ESP32-API kurz unterbrechen und die Lichtdetails während der Wiederverbindung öffnen. Danach einmal `Refresh Light Detail Catalog` drücken. | Der letzte vollständige Dialog bleibt bedienbar; ein vorübergehend fehlgeschlagener Registry-Aufruf ersetzt ihn nicht durch eine leere Liste. Nach 1,5 s plus Abfragezeit konvergieren ESP32 und S3 automatisch; der Diagnoseknopf erzwingt dasselbe ohne MCU-Neustart. |
| E14 | Beim Wechsel über den Leuchtennamen Bridge-/HA-Aktionsdiagnose und UART-Traffic beobachten; anschließend sofort Helligkeit drehen und Ein/Aus antippen. | Die reine Slotwahl erzeugt keinen HA-Lichtbefehl und keine neue UART-Aktion. Die Folgeaktionen adressieren ausschließlich den sichtbar ausgewählten Slot; kein veralteter Helligkeits- oder Farbbefehl läuft nach. |
| E15 | Während schneller Namens-Taps den 100-ms-Snapshot, externe Lichtänderungen und das Öffnen/Schließen des Detail-Popups überlappen lassen. | Auswahl bleibt deterministisch, Popup zeigt nur Details des sichtbaren Slots, kein Touch-Durchgriff; `S3 UI Scheduler Gap` bleibt unter 25 ms und beide UART-Fehlerzähler bleiben unverändert. |

## F. Wetter, Forecast und Radar

| ID | Durchführung | Soll |
| --- | --- | --- |
| F01 | Wetterseite mit bekannten HA-Werten öffnen. | Temperaturbogen, Tages-Min/Max, gefühlte Temperatur, Feuchte und Wind sind korrekt. |
| F02 | Ungültige Tages-Min/Max simulieren. | Bogen nutzt -10 bis +40 °C. |
| F03 | Kontext öffnen. | Stundenabschnitte und zwei weitere Tagesforecasts zeigen passende, unterscheidbare Symbole. |
| F04 | Radar laden und während der Übertragung navigieren und drehen. | Steuerframes bleiben priorisiert; kein Eingabeverlust und keine UART-Fehler. |
| F05 | Nach 2,5 Sekunden ohne Eingabe warten. | Radar wird dekodiert und angezeigt; anschließend kehrt Scheduler-Lücke in den Zielbereich zurück. |
| F06 | Positive und negative ein- und zweistellige Temperaturen anzeigen. | Temperatur und Gradzeichen sind vollständig sichtbar; das Wettersymbol überlagert sie nicht. |

## G. Fehler- und Rückfallverhalten

| ID | Durchführung | Soll |
| --- | --- | --- |
| G01 | Nur den ESP32 neu starten und innerhalb von 12 Sekunden wieder verbinden lassen. | EC1 und lokale UI funktionieren durchgehend; ein kurz unbereiter Bibliothekscache startet keinen direkten S3-Netzwerkpfad. |
| G02 | ESP32 wieder verbinden. | Vollständiger Snapshot kommt an und die ESP32-Bridge übernimmt wieder vollständig. |
| G03 | Während ESP32-Ausfall Play/Pause und Licht testen. | Lokale UI bleibt bedienbar, zeigt den Ausfall und sendet keinen direkten Netzwerkbefehl. |
| G04 | Eine Paging-Proxyanfrage gezielt ablehnen. | S3 zeigt einen begrenzten Fehler; keine Endlosschleife und kein falscher Titelstart. |
| G05 | Home Assistant neu starten. | UI und Encoder bleiben lokal responsiv; Zustände synchronisieren sich nach Wiederkehr. |
| G06 | WLAN kurz trennen und wiederherstellen. | Kein Reboot; lokale Bedienung bleibt möglich, Bridge und Zustände erholen sich. |
| G07 | ESP32/Bridge länger als 12 Sekunden getrennt lassen und danach wiederherstellen. | Remote-Funktionen bleiben klar nicht verfügbar, lokale Funktionen bleiben bedienbar; nach Wiederherstellung übernimmt ausschließlich der ESP32 und alle Zustände konvergieren. |

## H. Dauer- und Lasttest

| ID | Durchführung | Soll |
| --- | --- | --- |
| H01 | 24 Stunden mit Medienfortschritt, Forecast, zehn Radarabrufen und wiederholtem Paging betreiben. | Keine UART-Fehler, keine Encoderfehler und kein ungeplanter Neustart oder Verbindungswechsel. |
| H02 | Pro Stunde fünf Minuten schnell zwischen Navigation, Encoder und Popups wechseln. | Kein Touch-Durchgriff, kein Hänger, Scheduler-Ziel während aktiver Phasen erfüllt. |
| H03 | 72 Stunden gemischter Normalbetrieb. | Kein ungeplanter Neustart und keine fortschreitende Verschlechterung. |

## Fehlerprotokoll

Für jeden Fehlschlag Zeitstempel, Test-ID, aktive Seite, letzte Eingabe,
`S3 UI Scheduler Gap`, beide UART-Fehlerzähler, EC1-Lesefehler,
Fallback-Zustand sowie die letzten 30 Sekunden beider ESPHome-Logs sichern.
Ein Fehler darf erst nach dokumentierter Ursache und erfolgreicher Wiederholung
des betroffenen Blocks geschlossen werden.
