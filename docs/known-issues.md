# Known issues

Stand: 2026-07-26

Dieses Dokument erfasst bestätigte Fehler über die drei koordinierten
Repositories `Passion-Wave-rotaryknob`, `Passion-Wave-web` und
`Passion-Wave-control`. Produkt-Roadmap, externe Freigaben und noch nicht
durchgeführte Hardwaretests sind keine Softwarefehler.

## Offen

### PW-FW-001: Playlist-Paging endete am sichtbaren Listenfenster

- **Status:** Auf S3 und ESP32 geflasht; automatisierter Paging-Test bestanden,
  manueller Scrolltest ausstehend
- **Betroffen:** S3-Medienauswahl in `Passion-Wave-rotaryknob`
- **Fehlerbild:** Die Playlist-Liste endete beim Touch-Scrollen am Ende des
  bereits gerenderten Fensters. In UI Next wurde keine Folgeseite angefordert;
  eingetroffene Seiten konnten außerdem die Scrollposition zurücksetzen.
- **Erwartet:** Touch und Encoder bewegen sich ohne sichtbare Unterbrechung
  durch einen Katalog, der größer als Bootstrap und erste Seite ist.
- **Ursache:** Der 200-ms-Paging-Pfad akzeptierte nur die Legacy-Medienseite
  `2`, nicht die UI-Next-Seite `22`. Die 16 persistenten LVGL-Zeilen hatten
  für Touch keine Fensterfortschaltung. Zusätzlich enthielt der Seitenzähler
  nur die zuletzt empfangene Seitengröße statt des gesamten S3-Caches. Die
  erste Korrektur reichte auf Geräten mit gespeicherten Laufzeitzielen nicht:
  Die aus dem ESP32 gemeldete Paging-Fähigkeit wurde an die Übereinstimmung
  aller Media- und Lichtziele gekoppelt. Bei einer Abweichung kam der
  40-Einträge-Bootstrap an, der S3 sperrte aber Folgeseiten und löschte
  `has_more`. Der sichtbare letzte Bootstrap-Eintrag war `Ektschen`.
- **Behebung:** Paging gilt nun für beide Medienseiten. Das virtuelle Fenster
  wird mit fünf überlappenden Zeilen fortgeschaltet, eine Folgeseite bereits
  fünf Cache-Einträge vor dem Ende angefordert und der Gesamtzähler aus dem
  akkumulierten Cache gebildet. Asynchrone Antworten behalten die aktuelle
  Touch-Position. Bibliothekstransport und Seitenanforderungen sind unabhängig
  von zielgebundenen Media-/Lichtaktionen freigegeben. Ein vorübergehend
  fehlender Transport bewahrt Offset und `has_more`, wartet ohne wiederholte
  Netzwerkanfragen und setzt nach Wiederkehr automatisch fort. Es wird bewusst
  nicht der vollständige Katalog im Hintergrund geladen. Meldet der ESP32 eine
  asynchron fertiggestellte Seite mit `LIBRARY_CHANGED`, wird ein passender,
  zuvor mit „noch nicht bereit“ abgewiesener UART-Retry sofort freigegeben.
  Seitenanforderung und 10-s-Retry können dadurch nicht mehr dauerhaft
  phasengleich in einem Livelock bleiben. Startet der S3 während eines
  Stop-and-wait-Transfers neu, verwirft der ESP32 den verwaisten Sendeslot nun
  nach zwei Sekunden ohne bestätigten Fortschritt. Die nächste Seitenanfrage
  wird damit ohne ESP32-Neustart wieder angenommen.
- **Abnahme:** Der kontrollierte Gerätetest am 2026-07-26 übertrug nach dem
  40er-Bootstrap zwei aufeinanderfolgende 24er-Seiten über
  Home Assistant → MQTT → ESP32 → UART → S3. Beide Caches wuchsen stabil auf
  64 und anschließend 88 Einträge; der ESP32 meldete dabei null
  UART-Protokollfehler. Test `D04` noch mit Touch und Encoder durchführen; erst
  danach in `Behoben` verschieben.

## Behoben

### PW-REL-001: Öffentlicher Installer lieferte Altgerät mit Schlüsselabfrage

- **Status:** Behoben in Version 2.1.0
- **Betroffen:** Öffentliche Factory-Images, Web-Installer und Home-Assistant-
  Erstaufnahme
- **Fehlerbild:** Nach dem Browser-Flash erschien nur das alte Gerät
  `Wohnzimmer Scrollwheel (scrollwheel)` und Home Assistant verlangte einen
  unbekannten ESPHome Encryption Key.
- **Ursache:** Die Produktionswebsite stand noch auf dem einzelnen
  Version-1.2-Manifest, während die bereits vorbereitete Zwei-Chip-Toolchain
  nur lokal vorlag. Das ausgelieferte Manifest bot mit
  `new_install_prompt_erase: true` außerdem die Wahl, alte Daten beizubehalten,
  sodass frühere NVS-/Discovery-Daten überleben konnten. Während des zweiten
  Flash-Schritts konnte der S3 zudem vor der Home-Assistant-Erkennung in Deep
  Sleep wechseln.
- **Behebung:** Version 2.1.0 veröffentlicht zwei getrennte, MAC-suffigierte
  Factory-Nodes als `PassionWave Rotaryknob` und `PassionWave Rotaryknob
  Bridge`. Beide Manifeste behalten mit `new_install_prompt_erase: false` den
  automatischen vollständigen Factory-Erase von ESP Web Tools bei. Die
  öffentlichen API-Konfigurationen enthalten keinen Encryption Key; private
  Wrapper bleiben verschlüsselt. Der S3 setzt seine normale Deep-Sleep-Politik
  erst fort, nachdem Home Assistant mindestens einmal verbunden war.

### PW-FW-003: Radar war an Media-/Lichtzielvergleich gekoppelt

- **Status:** Behoben in Version 2.1.0
- **Betroffen:** Dual-MCU-Radartransport
- **Fehlerbild:** Ein korrekt erzeugtes Radarbild wurde nicht angefordert,
  sobald gespeicherte Media- oder Lichtziele von den kompilierten
  Bridge-Zielen abwichen.
- **Ursache:** Radar-Fähigkeit und UART-Client waren verfügbar, Warmup und
  Sendeweg verlangten jedoch zusätzlich das zielgebundene globale
  `dual_mcu_ha_bridge_ready`.
- **Behebung:** Radar-Warmup, Queue und Versand verwenden nun die unabhängige
  Radar-Client-Fähigkeit und einen frischen ESP32-Heartbeat. Floorplan-
  Invalidierungen überschreiben den Radar-Diagnosestatus nicht mehr.

### PW-FW-002: Veralteter WLED-Preset-Cache auf dem S3

- **Status:** Behoben im Quellstand am 2026-07-26; Hardware-Abnahme ausstehend
- **Betroffen:** Lichtdetail-Popup und Dual-MCU-Protokoll
- **Fehlerbild:** `dual_mcu_wled_preset_names` wurde befüllt, aber vom
  UI-Next-Lichtdialog nicht gelesen. Dadurch existierten zwei parallele
  S3-Caches für dieselben Preset-Namen.
- **Ursache:** Nach der Migration vom alten WLED-spezifischen Katalog auf den
  generischen WLED-/Hue-Lichtdetailkatalog blieb der alte S3-Empfänger als
  ungenutzter Kompatibilitätspfad bestehen.
- **Behebung:** Alter S3-Cache, Empfänger und Diagnoseentität sind entfernt.
  Das Popup verwendet ausschließlich `light_detail_labels` mit bis zu 32
  Einträgen je Lichtslot. Der klassische ESP32 sendet die alten Frames vorerst
  weiter, damit ein ESP32-first Rolling-OTA mit einem älteren S3 kompatibel
  bleibt; ein aktueller S3 ignoriert sie.
- **Abnahme:** Nach dem nächsten Flash WLED-Presets aller vier Lichtslots und
  einen gemischten ESP32-first OTA-Lauf prüfen.

### PW-DOC-001: Widersprüchliche Factory-Hashes

- **Status:** Behoben am 2026-07-26
- **Betroffen:** `Passion-Wave-control/RELEASE.md`,
  `Passion-Wave-web/RELEASE.md`
- **Fehlerbild:** Beide Dokumente bezeichneten veraltete und untereinander
  verschiedene SHA-256-Summen als aktuellen Firmwarestand.
- **Behebung:** Die Angaben wurden mit den Binärdateien und `SHA256SUMS` aus
  Firmware- und Web-Repository abgeglichen. Verbindlich sind:
  - S3: `3ff5c25b9a99d1ae6dbb4722c07312acc30a1c44cb50112eefcf6ab77e48355b`
  - ESP32: `ea04ec704adf7951b292a57d1091633629d500c2cb0562d64bb7bf3b7cdab392`

### PW-DOC-002: Launch-Anleitung beschrieb den alten Ein-Chip-Installer

- **Status:** Behoben am 2026-07-26
- **Betroffen:** `Passion-Wave-control/launch-guide.md`,
  `Passion-Wave-control/open-topics.md`,
  `docs/automated-installation.md`, `docs/installation.md`
- **Fehlerbild:** Pfade, Beispiele und offene Punkte verwiesen auf ein
  einzelnes S3-Manifest und eine einzelne Factory-Datei, obwohl das Produkt
  zwei getrennte Prozessoren besitzt.
- **Behebung:** Alle Anleitungen verwenden nun die vorhandenen Pfade
  `firmware/rotaryknob/s3/` und `firmware/rotaryknob/esp32/` und unterscheiden
  die beiden chipgebundenen Installationsschritte.

### PW-DOC-003: Automatischer S3-Fallback widersprach Rescue Mode

- **Status:** Behoben am 2026-07-26
- **Betroffen:** Dual-MCU-Architektur-, Test- und Netzwerkdokumentation
- **Fehlerbild:** Historische Abschnitte versprachen bei Bridge-Verlust einen
  automatischen S3-Netzwerkfallback. Der aktuelle Version-2.0-Vertrag erlaubt
  diesen Pfad ausschließlich nach bewusster Aktivierung von
  `S3 Network Rescue Mode`.
- **Behebung:** Aktuelle Architektur und Abnahmeschritte beschreiben nun
  einheitlich den expliziten, nicht persistenten Rettungsmodus.

### PW-DOC-004: Fehlerhafte Test-ID und widersprüchliche UI-Markierung

- **Status:** Behoben am 2026-07-26
- **Betroffen:** `docs/stage1-responsiveness-test-catalog.md`,
  `docs/ui-next-framework.md`
- **Fehlerbild:** Der Medientest enthielt `D11` doppelt. Die UI-Dokumentation
  bezeichnete entfernte Randmarker an anderer Stelle noch als vorhanden.
- **Behebung:** Die Medienprüfungen sind fortlaufend nummeriert; der aktuelle
  aktive Zustand wird konsistent nur über Icon- und Textfarbe beschrieben.

### PW-DOC-005: Lokale Testidentitäten in öffentlicher Dokumentation

- **Status:** Behoben am 2026-07-26
- **Betroffen:** Release-, Bridge-, Benchmark-, Installations- und
  Review-Dokumentation
- **Fehlerbild:** Beispiele enthielten lokale Gerätepräfixe, konkrete
  Media-Player-Entitäten, eine Hardware-ID und private LAN-Adressen.
- **Behebung:** Die Angaben wurden durch neutrale Entity-Suffixe,
  Platzhalter-Adressen und rollenbasierte Beschreibungen ersetzt. Messwerte
  und technische Aussage bleiben erhalten.

## Neuen Eintrag anlegen

Ein neuer Eintrag benötigt mindestens ID, Status, betroffene Komponente,
reproduzierbares Fehlerbild, erwartetes Verhalten, Ursache oder Untersuchungs-
stand sowie Behebung oder Umgehung.
