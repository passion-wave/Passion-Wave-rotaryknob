# Known issues

Stand: 2026-07-26

Dieses Dokument erfasst bestätigte Fehler über die drei koordinierten
Repositories `Passion-Wave-rotaryknob`, `Passion-Wave-web` und
`Passion-Wave-control`. Produkt-Roadmap, externe Freigaben und noch nicht
durchgeführte Hardwaretests sind keine Softwarefehler.

## Offen

Derzeit sind keine bestätigten, reproduzierbaren Softwarefehler offen.
Physische Release-Abnahmen bleiben Qualitätsgates und werden nicht als
Softwarefehler geführt.

## Behoben

### PW-REL-003: Release-CI erwartete auf dem S3 den falschen Improv-Transport

- **Status:** Behoben in Version 2.1.1
- **Betroffen:** Clean-Build der öffentlichen Dual-MCU-Release-Artefakte
- **Fehlerbild:** Beide Factory-Images kompilierten erfolgreich, der
  nachgelagerte CI-Check beendete den Release-Build dennoch ohne konkrete
  Diagnose.
- **Ursache:** Die Prüfung erwartete `UART0` auf beiden Prozessoren. Der
  klassische ESP32 verwendet diesen UART korrekt; der ESP32-S3 stellt die
  serielle Improv-Verbindung dagegen plattformgemäß über
  `USB_SERIAL_JTAG` bereit.
- **Behebung:** Die Prüfung validiert nun je Chip den richtigen Transport:
  `USB_SERIAL_JTAG` für den S3 und `UART0` für die Bridge, jeweils mit
  115200 Baud. Jede fehlende Release-Voraussetzung gibt zusätzlich eine
  eindeutige Fehlermeldung aus.

### PW-REL-002: Bridge-Flash öffnete die WLAN-Provisionierung nicht zuverlässig

- **Status:** Behoben in Version 2.1.1
- **Betroffen:** Öffentlicher ESP32-Bridge-Installer und Factory-Onboarding
- **Fehlerbild:** Nach dem Schreiben der Bridge-Firmware erschien nicht in
  jedem Installationslauf die erwartete WLAN-Auswahl.
- **Ursache:** ESP Web Tools öffnet Improv nur nach einem Factory-Erase
  automatisch. Ein bereits als Passion-Wave-Firmware erkannter Prozessor wurde
  dagegen als Update behandelt und durfte gespeicherte oder leere NVS-
  WLAN-Daten behalten. Die Website erklärte außerdem den erforderlichen
  `Next`-Schritt nach 100 Prozent nicht deutlich genug.
- **Behebung:** Der öffentliche Ersteinrichtungsbutton klassifiziert jede
  Verbindung ausdrücklich als Factory-Installation. Damit erfolgen Clean
  Erase, Neustart, Improv-Erkennung und WLAN-Dialog deterministisch. ESP Web
  Tools ist auf Version 10.4.0 fixiert; die Wartezeit bleibt 120 Sekunden.
  Der Assistent schaltet nicht anhand eines Flash-Events weiter, sondern erst
  nach expliziter WLAN-Bestätigung. Ein separater Bridge-WLAN-Button kann
  Improv nach einem USB-Reconnect öffnen, ohne erneut zu flashen. Beide
  Factory-Builds prüfen in CI Improv Serial sowie den plattformspezifischen
  Logger-Transport mit 115200 Baud.

### PW-WEB-001: ESP-Web-Tools-Abzweigungen unterbrachen den Installationsfluss

- **Status:** Behoben in Version 2.1.1
- **Betroffen:** Beide öffentlichen Factory-Manifeste und Improv-Profile
- **Fehlerbild:** Nach der WLAN-Eingabe bot der Dialog direkte Sprünge zum
  Gerät oder zu Home Assistant an, obwohl der zweite Prozessor beziehungsweise
  der geführte Abschluss noch fehlte.
- **Ursache:** `improv_serial.next_url` und `home_assistant_domain` erzeugten
  zusätzliche Aktionen im ESP-Web-Tools-Dialog.
- **Behebung:** Beide Felder sind aus Factory-Profilen, Manifestgenerator und
  ausgelieferten Manifesten entfernt. Home Assistant wird ausschließlich im
  fünften Website-Schritt geöffnet.

### PW-WEB-002: Website hatte keine englische Standardfassung

- **Status:** Behoben in Version 2.1.1
- **Betroffen:** `Passion-Wave-web`
- **Fehlerbild:** Produkt, Installer, Hilfe und Rechtstexte waren nur deutsch,
  wodurch der öffentliche Einstieg kein internationales Release abbildete.
- **Behebung:** Alle sieben kanonischen HTML-Seiten verwenden Englisch und
  `lang="en"`. Die Site-Prüfung erzwingt diese Vorgabe für neue Seiten.

### PW-WEB-003: Kein öffentlicher Rückkanal für Fehlerberichte

- **Status:** Behoben in Version 2.1.1
- **Betroffen:** Website und GitHub-Repository
- **Fehlerbild:** Käufer fanden keinen eindeutigen Weg für reproduzierbare
  Problemberichte.
- **Behebung:** Installer, Hilfe und Footer verlinken den aktivierten GitHub-
  Issue-Tracker. Ein strukturiertes Bug-Formular fragt Bereich, Version,
  Reproduktion und Diagnosen ab und verlangt die Bestätigung, dass Schlüssel
  und persönliche Daten entfernt wurden.

### PW-FW-001: Playlist-Paging endete am sichtbaren Listenfenster

- **Status:** Behoben im Version-2.1.1-Quellstand; automatisierter
  Gerätetransporttest bestanden
- **Betroffen:** S3-Medienauswahl in `Passion-Wave-rotaryknob`
- **Fehlerbild:** Die Playlist-Liste endete beim Touch-Scrollen am letzten
  Eintrag des 40er-Bootstrap-Fensters (`Ektschen`).
- **Ursache:** UI-Next-Seite 22, virtuelles Touch-Fenster, akkumulierter
  Cache-Zähler und die von Media-/Lichtzielabgleich unabhängige
  Paging-Fähigkeit waren nicht durchgängig verbunden. Asynchrone Antworten und
  verwaiste Stop-and-wait-Slots konnten den Fortschritt zusätzlich blockieren.
- **Behebung:** Touch und Encoder verschieben das virtuelle Fenster mit fünf
  überlappenden Zeilen. Die nächste Seite wird fünf Cache-Einträge vor dem Ende
  angefordert, Antworten erhalten die Scrollposition, und `has_more` sowie
  Offset überleben einen vorübergehend fehlenden Transport. Bibliothekspaging
  ist von zielgebundenen Aktionen entkoppelt; fertige asynchrone Seiten lösen
  blockierte UART-Retries sofort, und verwaiste Sendeslots laufen nach zwei
  Sekunden ab.
- **Abnahme:** Der Gerätetest übertrug nach dem 40er-Bootstrap zwei
  aufeinanderfolgende 24er-Seiten über Home Assistant → MQTT → ESP32 → UART →
  S3. Die Caches wuchsen auf 64 und 88 Einträge, ohne UART-Protokollfehler.
  Touch-/Encoder-Test `D04` bleibt ein physisches Release-Gate, ist aber kein
  noch offener Implementierungsfehler.

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
