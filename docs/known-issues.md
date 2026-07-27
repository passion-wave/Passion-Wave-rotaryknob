# Known issues

Stand: 2026-07-27

Dieses Dokument erfasst bestätigte Fehler über die drei koordinierten
Repositories `Passion-Wave-rotaryknob`, `Passion-Wave-web` und
`Passion-Wave-control`. Produkt-Roadmap, externe Freigaben und noch nicht
durchgeführte Hardwaretests sind keine Softwarefehler.

## Offen

### PW-HA-002: Verbindungszuordnung erschien als leeres Formular

- **Status:** Im Quellstand behoben; Home-Assistant-Neustart und
  Onboarding-Abnahme ausstehend
- **Betroffen:** Zuordnung von Bridge, Music-Assistant-Instanz und Medienplayer
  in der PassionWave-Ersteinrichtung unter Home Assistant 2026.7.4
- **Fehlerbild:** Home Assistant zeigte nur die englische Überschrift
  `Set up PassionWave Rotaryknob` und eine Submit-Schaltfläche. Die drei
  gefilterten Registry-Selektoren wurden vollständig unterdrückt.
- **Behebung:** Der Flow erzeugt die Optionen explizit aus Config-Entry-,
  Entity- und State-Registry und rendert sie über denselben stabilen
  Select-Selector wie die zuvor erfolgreich geprüfte S3-/Bridge-Auswahl.
  Nach der Zuordnung wird der Eintrag direkt mit der vollständigen
  Music-Assistant-Bibliothek über `__all__` erstellt. Die optionale
  Einschränkung bleibt unter **Konfigurieren** möglich.
- **Abnahme:** Home Assistant neu starten, den angefangenen Flow verwerfen und
  PassionWave erneut hinzufügen. Alle drei Auswahlfelder müssen sichtbar sein;
  nach ihrer Bestätigung muss der Config Entry unmittelbar erstellt werden.
  Anschließend müssen Playlist, Radio und Podcast ohne zusätzliche
  Filterkonfiguration geladen werden.

### PW-HA-003: Lichtzuordnung lag außerhalb der PassionWave-Integration

- **Status:** In 3.0.0-beta.5 umgesetzt; Live-Abnahme ausstehend
- **Betroffen:** Neukunden-Onboarding und spätere Zieländerungen
- **Fehlerbild:** Display, Bridge und Music Assistant wurden im PassionWave
  Config Flow zugeordnet, die vier Lichtplätze aber weiterhin über einen
  separaten Dynamic-Targets-Blueprint.
- **Ursache:** Die Integration besaß noch keine stabile Zuordnung zum
  ESPHome-S3-Config-Entry und konnte deshalb die firmwareeigenen Ziel- und
  Label-Textentitäten nicht eindeutig einem physischen Rotaryknob zuordnen.
- **Behebung:** Jeder PassionWave Config Entry speichert nun Display/S3,
  Bridge, Music Assistant, Wiedergabegerät und vier geordnete Lichtplätze. Die
  Integration schreibt Ziele und Anzeigenamen direkt auf das zugeordnete S3,
  spiegelt Medienstatus, Titel, Interpret und Cover und führt Umbenennungen von
  Zielentitäten nach. Der Setup-Blueprint wurde aus dem Repository entfernt.
- **Kundenweg:** **Einstellungen > Geräte & Dienste > PassionWave >
  Konfigurieren** öffnet Geräte/Wiedergabe, Lichtplätze und optionale
  Medienfilter immer in derselben Reihenfolge.
- **Abnahme:** Config Entry anlegen, vier Lichter prüfen, einen Lichtplatz über
  **Konfigurieren** wechseln und eine gewählte Lichtentität umbenennen. Anzeige
  und Zielsteuerung müssen ohne Blueprint oder Neustart folgen.

### PW-SEC-002: Home Assistant verlangt beim Factory-Onboarding einen Schlüssel

- **Status:** Im Quellstand 3.0.0-beta.3 behoben; End-to-End-Abnahme ausstehend
- **Betroffen:** Factory-Onboarding beider Prozessoren
- **Fehlerbild:** Home Assistant erkennt S3 und Bridge, zeigt aber ein
  Eingabefeld für einen dem Kunden unbekannten Encryption Key.
- **Ursache:** Der ESPHome-2026.7-Server unterstützt die dynamische
  Schlüssel-Provisionierung. Der normale Home-Assistant-ESPHome-Config-Flow
  setzt diesen Schlüssel jedoch noch nicht selbst.
- **Behebung:** PassionWave erkennt beide Prozessoren per mDNS, verbindet sich
  nach Bestätigung über den reservierten Zero-PSK-Noise-Kanal, erzeugt je Chip
  einen zufälligen 32-Byte-Schlüssel und installiert ihn. Danach legt
  PassionWave beide Endpunkte über den offiziellen ESPHome-Config-Flow an und
  übergibt die Schlüssel intern. Es gibt keinen gemeinsamen, veröffentlichten
  oder sichtbaren Schlüssel.
- **Abnahme:** Factory-Gerät aus- und einschalten, PassionWave innerhalb von
  20 Minuten hinzufügen, S3 und Bridge auswählen und prüfen, dass beide
  ESPHome-Einträge ohne Schlüsseldialog verbunden werden.

### PW-FW-006: Medienbibliotheken bleiben nach Factory-Onboarding leer

- **Status:** Im Quellstand behoben; Build- und Geräteabnahme ausstehend
- **Betroffen:** Playlist-, Radio- und Podcast-Auswahl
- **Fehlerbild:** Lichtnamen sind nach der Blueprint-Konfiguration sichtbar,
  Medienlisten bleiben jedoch auch nach Neustart leer.
- **Ursache:** Die Factory-Firmware verwendete einen anonymen MQTT-Client. Der
  Broker lehnte ihn erwartungsgemäß ab; gleichzeitig scheiterte zeitweise die
  Auflösung von `homeassistant.local`. Damit erreichten weder Bootstrap-Listen
  noch Paging-Antworten die Bridge.
- **Behebung:** MQTT ist aus beiden Firmware-Rollen entfernt. Die Bridge liest
  Bibliotheken über die verschlüsselte ESPHome Native API. Playlist-Titel
  werden in Home Assistant vor der Übertragung seitenweise begrenzt.
  Floorplan-Revisionen verwenden ebenfalls einen nativen HA-Zustand. Die
  Migration ist absichtlich nicht abwärtskompatibel und in
  [MQTT-free Native API migration](native-api-migration.md) beschrieben.
- **Abnahme:** Beide Images aus demselben Stand bauen, die
  `passion_wave`-Integration laden und anschließend Bootstrap sowie Paging fünf
  Einträge vor Listenende auf beiden physischen Testgeräten testen. Bis dahin
  wird nichts geflasht.

### PW-SEC-001: Zwei Testgeräte verwenden noch einen gemeinsamen Übergangsschlüssel

- **Status:** Factory-zu-Managed-Migration abgeschlossen; individuelle
  Endpunktschlüssel ausstehend
- **Betroffen:** Beide physischen Testgeräte mit je einem S3- und einem
  Bridge-Endpunkt
- **Fehlerbild:** Die Native API ist jetzt überall verschlüsselt, verwendet
  für die kontrollierte Erstmigration aber noch denselben bekannten privaten
  Installationsschlüssel.
- **Bewertung:** Dies ist kein geeigneter Best-Guess-Dauerzustand. Ein
  öffentlicher Factory-Build kann keinen geheimen individuellen Schlüssel
  enthalten; nach der Adoption benötigt jedoch jeder der vier vorhandenen
  ESPHome-Endpunkte einen eigenen API-Schlüssel.
- **Behebung:** Factory und Managed bleiben Profile desselben gemeinsamen
  Release-Cores. Der kontrollierte Übergang, die Schlüsselzuordnung und die
  Reihenfolge für beide MCUs sind in
  [ESPHome API security lifecycle](api-security-lifecycle.md) festgelegt.
- **Zwischenschritt:** Alle vier konsolidierten Managed-Entry-Points wurden am
  2026-07-27 mit API-Verschlüsselung und authentifiziertem OTA installiert.
  Vier verschlüsselte Handshakes, Home-Assistant-Integration und beide
  UART-Paare wurden erfolgreich geprüft.
- **Restarbeit:** Nach erfolgreicher gemeinsamer Migration vier individuelle
  Schlüssel hinterlegen und Home Assistant jeweils synchron umstellen.

### PW-FW-005: Gedimmter Bildschirm blitzte sporadisch auf 100 Prozent

- **Status:** Behebung auf Produktions- und Test-S3 per OTA installiert;
  Langzeitabnahme der gedimmten Displays ausstehend
- **Betroffen:** EC1-Eingang und Helligkeitssteuerung auf dem ESP32-S3
- **Fehlerbild:** Ein auf 10 Prozent gedimmter Bildschirm, beispielsweise die
  Wetteransicht, blitzte selten etwa im Sekundentakt kurz auf 100 Prozent.
- **Erwartetes Verhalten:** Nur eine echte Drehbewegung darf Aktivität
  registrieren und die Wetteransicht für zwei Sekunden auf 100 Prozent
  anheben.
- **Ursache:** Der UI-Pfad bewertete bereits jede rohe EC1-Flanke als
  Aktivität, bevor er die signierte Richtung prüfte. Elektrisch gekoppelte
  Impulse konnten deshalb links und rechts gleichzeitig erhöhen und netto
  keinen Schritt ergeben, hatten den Helligkeits-Boost aber bereits
  ausgelöst. Am Produktionsgerät standen 615 linken 617 rechten Rohimpulsen
  nur zwei Nettoschritte und keine Lesefehler gegenüber.
- **Behebung:** Richtungsmehrdeutige Pakete mit Impulsen auf beiden
  EC1-Leitungen werden unmittelbar an der Erfassung verworfen. Nur ein
  eindeutiger Richtungsschritt aktualisiert Aktivität, weckt das Display oder
  startet den Helligkeits-Boost. Es wurde keine Entprell- oder Wartezeit
  ergänzt; gültige Drehimpulse behalten ihre bisherige Reaktionszeit. Die neue
  Diagnose `EC1 Encoder Rejected Common-mode Batches` macht den Filter im
  Betrieb messbar.
- **Restabnahme:** Die Wetteransicht auf 10 Prozent dimmen lassen und über
  einen längeren Leerlauf prüfen, dass steigende Common-mode-Diagnosewerte
  weder `Net Count` noch die Helligkeit verändern.

### PW-FW-004: Produktionsgerät lädt Radar und Floorplan nicht

- **Status:** Behebung in Home Assistant aktiv und auf Produktions- sowie
  Test-Bridge per OTA installiert; Display-Abnahme ausstehend
- **Betroffen:** Netzwerk-Assets der öffentlichen Dual-MCU-Firmware
- **Fehlerbild:** Radar endet mit `Asset-Fehler radar code=15 bytes=0`; auf
  der Haus-Seite erscheint kein aktueller Floorplan.
- **Ursache:** Die Bridge brach vor HTTP an der mDNS-Auflösung von
  `homeassistant.local` ab. Der Floorplan-Fallback zeigte zusätzlich auf einen
  veralteten Pfad, während die Invalidierung ausschließlich über einen in der
  öffentlichen Factory-Konfiguration nicht nutzbaren anonymen MQTT-Zugang
  lief. Das bereitgestellte Pyscript war zunächst nicht geladen.
- **Behebung:** Pyscript veröffentlicht absolute, intern erreichbare Radar- und
  Floorplan-URLs über die ESPHome Native API. Die Bridge verwendet diese URLs,
  invalidiert den Floorplan ohne MQTT-Abhängigkeit und besitzt korrigierte
  Dateifallbacks. Der mDNS-Vorcheck ist nicht mehr fatal. Pyscript wurde in
  Home Assistant neu geladen; Renderer, Zustände und HTTP-Abrufe sind geprüft.
- **Restabnahme:** Radar sowie Haus-Seite am Display prüfen. Die vollständige
  Diagnose steht in
  [Radar- und Floorplan-Wirkkette](radar-floorplan-data-flow.md).

## Behoben

### PW-REL-004: Vier Endpunkte liefen über historisch getrennte Profile

- **Status:** Behoben und am 2026-07-27 auf alle vier Endpunkte ausgerollt
- **Betroffen:** Beide physischen Rotaryknobs mit jeweils S3 und ESP32-Bridge
- **Fehlerbild:** Produktions- und Testgerät wurden über unterschiedlich
  gewachsene Konfigurationsdateien gebaut. Gemeinsame Korrekturen konnten
  dadurch auseinanderlaufen.
- **Behebung:** Es gibt jetzt genau zwei gemeinsame Hardware-Rollen:
  `managed-s3.yaml` und `managed-esp32.yaml`. Produktions- und Testparameter
  stehen je physischem Gerät einmal unter `devices/`; vier sehr kleine
  Entry-Points erhalten nur stabile Namen und getrennte Build-Pfade. Factory
  und Managed besitzen denselben funktionalen Core, während nur die
  Deployment-Schicht API, OTA und WLAN bestimmt. Der Floorplan-Renderer liegt
  zusammen mit Blueprints und
  Packages unter dem einzigen Verzeichnis `home_assistant/`; der frühere
  parallele Pfad `home-assistant/` ist entfallen.
- **Warum zwei Binärtypen bleiben:** S3 und klassischer ESP32 haben
  unterschiedliche Chips, Flash-Layouts und Aufgaben. Ein einzelnes Binärimage
  für alle vier Endpunkte ist technisch nicht möglich; ein gemeinsamer
  Quellstand und Release ist erreicht.
- **Abnahme:** Vier OTA-Uploads bestätigt; alle verschlüsselten API-Handshakes
  erfolgreich; beide UART-Paare ohne Protokollfehler; alle vier ESPHome-
  Integrationseinträge geladen und konsistent benannt.

### PW-HA-001: Konfigurations-Blueprint schrieb in MQTT-Kompatibilitätskopien

- **Status:** Behoben am 2026-07-27; Blueprint in Home Assistant aktualisiert
- **Betroffen:** `Passion Wave Rotaryknob - Dynamic Targets`
- **Fehlerbild:** Die Blueprint-Automation wurde ohne Fehler beendet, die
  ausgewählten Medien- und Lichtziele kamen aber nicht zuverlässig in der
  aktiven Firmwarekonfiguration an.
- **Ursache:** `device_entities()` lieferte für das zusammengeführte
  Rotaryknob-Gerät sowohl native ESPHome-Textfelder als auch gleichnamige
  MQTT-Kompatibilitätskopien. Die bisherige Suche verwendete jeweils den ersten
  Namenstreffer und traf dadurch die MQTT-Entities mit Suffix `_2`.
- **Behebung:** Die Kandidatenmenge wird vor der Namenszuordnung mit
  `integration_entities('esphome')` geschnitten. Bestehende Blueprint-Inputs
  bleiben unverändert; der Gerätewähler bezeichnet den S3-/Display-Prozessor
  jetzt eindeutig. Beide Blueprint-Quelldateien verwenden außerdem
  kanonische Raw-GitHub-URLs, damit Home Assistant veröffentlichte Änderungen
  erneut importieren kann.

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
  WLAN-Daten behalten. Beim klassischen ESP32 wechselt die konkrete
  USB-UART-/Reset-Schaltung nach dem Schreiben außerdem nicht in jedem Lauf
  selbstständig in die Anwendung. Beim erneuten Öffnen wartete ESP Web Tools
  10.4.0 nur 1,5 Sekunden auf Improv; dieser Grenzwert war für den realen
  Neustartpfad zu knapp.
- **Behebung:** Der öffentliche Ersteinrichtungsbutton klassifiziert jede
  Verbindung ausdrücklich als Factory-Installation. Damit erfolgen Clean
  Erase und ein definierter Ausgangszustand. Nach `Installation complete` ist
  ein zweisekündiges Trennen und Wiederverbinden in derselben ESP32-
  Ausrichtung nun fester Onboarding-Schritt. Anschließend öffnet ein separater
  Bridge-WLAN-Button Improv, ohne erneut zu flashen. Die Website hostet ESP
  Web Tools 10.4.0 reproduzierbar selbst und erweitert ausschließlich die
  Improv-Erkennung für bereits geflashte Geräte von 1,5 auf 10 Sekunden. Ein
  direkter Protokolltest bestätigte Status `Ready`, Geräteinformationen und
  WLAN-Scan über UART0. Beide Factory-Builds prüfen in CI weiterhin Improv
  Serial und den plattformspezifischen Logger-Transport mit 115200 Baud.

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
- **Historische Abnahme:** Der Gerätetest übertrug nach dem 40er-Bootstrap zwei
  aufeinanderfolgende 24er-Seiten über den damaligen MQTT-Pfad. Die neue
  Native-API-Kette besitzt dafür ein separates Release-Gate.
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

- **Status:** Behoben am 2026-07-26; Rescue-Pfad in `3.0.0-beta.2` vollständig
  entfernt
- **Betroffen:** Dual-MCU-Architektur-, Test- und Netzwerkdokumentation
- **Fehlerbild:** Historische Abschnitte versprachen bei Bridge-Verlust einen
  automatischen S3-Netzwerkfallback. Der aktuelle Version-2.0-Vertrag erlaubt
  diesen Pfad ausschließlich nach bewusster Aktivierung von
  `S3 Network Rescue Mode`.
- **Behebung:** Die 2.1.x-Dokumentation beschrieb den expliziten,
  nicht persistenten Rettungsmodus. Version 3 entfernt sowohl den Modus als
  auch die zugehörigen S3-Abonnements und MQTT-Pfade.

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

### PW-FW-004: Playlist-, Radio- und Podcast-Listen blieben leer

- **Status:** Behoben im Quellstand `3.0.0-beta.2`; Hardware-Abnahme ausstehend
- **Betroffen:** Music-Assistant-Onboarding und Bibliotheks-Paging
- **Fehlerbild:** Vier Lichtnamen waren sichtbar, während Playlist, Radio und
  Podcast auch nach Neustart und Wartezeit leer blieben.
- **Ursache:** Der V2-Migrationsstand verteilte die notwendige Konfiguration auf
  ESPHome-Textfelder, Blueprint und optionales YAML-Package. Fehlte nur ein
  Teil oder war der Config Entry falsch zugeordnet, startete der Bootstrap
  nicht. Der Fehler war für Endkunden nicht eindeutig diagnostizierbar.
- **Behebung:** V3 ersetzt die verteilte Konfiguration durch einen
  `passion_wave` Config Flow. Die Bridge erhält genau eine PassionWave Config
  Entry ID. `passion_wave.get_library` und
  `passion_wave.get_playlist_tracks` kapseln Music Assistant, normalisieren
  Antworten und begrenzen Seiten vor dem Firmwaretransport.
- **Abnahme:** Pro physischem Gerät Config Entry anlegen, alle drei Listen
  öffnen, über mindestens zwei Seiten scrollen und in einer großen Playlist
  denselben Test für Tracks wiederholen.

### PW-FW-005: S3 enthielt weiterhin Single-MCU-Netzwerkpfade

- **Status:** Behoben im Quellstand `3.0.0-beta.2`; Hardware-Abnahme ausstehend
- **Betroffen:** S3-Laufzeit, Speicher und Fehlerisolation
- **Fehlerbild:** Obwohl der ESP32 Bridge-Eigentümer war, enthielt das S3-Profil
  noch direkte HA-State-Abonnements, SNTP und einen manuell aktivierbaren
  Rescue-/HTTP-Pfad.
- **Behebung:** Standalone-Einstieg und Rescue-Schalter sind entfernt. Der
  ausgelieferte S3-Core entfernt alle direkten Anwendungs-State-Abonnements,
  bezieht Zeit und Gerätemanagement nur über die Native API und transportiert
  Anwendungsdaten sowie Assets ausschließlich per UART über die Bridge.

## Neuen Eintrag anlegen

Ein neuer Eintrag benötigt mindestens ID, Status, betroffene Komponente,
reproduzierbares Fehlerbild, erwartetes Verhalten, Ursache oder Untersuchungs-
stand sowie Behebung oder Umgehung.
