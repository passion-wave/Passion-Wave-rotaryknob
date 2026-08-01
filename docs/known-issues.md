# Known issues

Stand: 2026-07-31. Pro Fehler: Überschrift plus genau eine Statuszeile.

## Offen

### PW-QA-001: Physische UI-Abnahme ist nicht vollständig automatisierbar
Am Gerät noch prüfen: Titeldarstellung, vier Lichter/Presets, Radar, Floorplan, Dimmen und schneller Seitenwechsel.

### PW-QA-002: Zweites Kundengerät fehlt im aktuellen Live-Test
Der Lauf deckt ein physisches Dual-MCU-Gerät ab; Clean-Onboarding, Schlüsseltrennung und Update auf einem zweiten Gerät bleiben offen.

### PW-FW-008: ESPHome-Abkündigungen erzeugen Build-Warnungen
`online_image`, `qspi_dbi` und alte Build-Flags vor ESPHome 2027.1/2026.12 migrieren; derzeit kein Laufzeitfehler.

### PW-MEDIA-006: Lautstärke sprang nach dem Verstellen kurz auf 50 %
Metadaten- und Ziel-Reconnectpfad überschrieben den Bridgewert; 50-%-Defaults entfernt, verlustfreie EC1-Batch-Auswertung wiederhergestellt.

### PW-HA-006: Wetterquelle ist noch Firmware-Konfiguration
Forecast-Kommandos akzeptieren ein `weather.*`-Ziel aus der Bridge; Auswahl und Bindung gehören künftig in den PassionWave Config Entry.

### PW-HA-007: Historische MQTT-Entities liegen noch in der HA-Registry
Die Laufzeit ist MQTT-frei, aber alte Registry-Einträge sind mit dem Gerät zusammengeführt; Bereinigung nur kontrolliert nach Nutzerfreigabe.

## In diesem Stand behoben

### PW-WEB-001: Web-Installer meldete beim Firmwareabruf „Failed to fetch“
Signierte Release-Weiterleitungen waren nicht CORS-stabil; Manifeste nutzen nun getaggte Raw-Dateien mit Cache-Buster und geprüften SHA-256-Summen.

### PW-REL-001: Öffentlicher Installer lag hinter dem Quellstand
Website, Firmware und HACS-Integration veröffentlichen gemeinsam `3.0.0-beta.12`; die vier unveränderlichen Images besitzen veröffentlichte Prüfsummen.

### PW-UPD-001: Firmware-Update war nicht öffentlich erreichbar
Die Website liefert beide stabilen OTA-Manifeste und Binärdateien; das kombinierte HA-Geräteupdate kann beta.12 für Bridge und S3 abrufen.

### PW-UPD-004: Bridge-Aktionen fehlten nach dem Kunden-OTA
Der kombinierte Updater lädt den ESPHome-Bridge-Eintrag zwischen Bridge und S3 neu; die umbenannten API-Aktionen sind dadurch sofort registriert.

### PW-WEATHER-001: Forecast-Anfrage konnte beim Neustart verloren gehen
Die Bridge wiederholt eine unbeantwortete Forecast-Anfrage alle zehn Sekunden; nach gültiger Tagesprognose endet der Retry automatisch.

### PW-UPD-003: Firmware fragte einen nicht auflösbaren Update-Host ab
`www.passion-wave.com` besaß kein DNS-Ziel; beide Chips verwenden nun direkt die veröffentlichte Passion-Wave-Site für ihre OTA-Manifeste.

### PW-UI-002: Screensaver startete hinter UI Next und ließ die Lichtseite blitzen
UI Next wird ausgeblendet und Seite 7 atomar gesetzt; Testgerät wechselte nach 30 s genau einmal, ohne 100-%-Wiederholung oder Encodertrigger.

### PW-UI-003: Albumcover erschien nicht aus dem Wetter-Screensaver
Behoben: HA sendet die dynamische Cover-URL an die Bridge; Heap-Reserve und Wechsel aus Seite 7 sind korrigiert, die Helligkeit wird wiederhergestellt.

### PW-LIGHT-001: Externe Lichtänderungen erschienen nicht am Rotaryknob
Ein autoritativer Snapshot synchronisiert alle vier Slots; externe Änderung und Rücksetzung wurden auf Bridge und S3 identisch live bestätigt.

### PW-LIGHT-002: Detail-Popup für Hue und WLED blieb leer
Gezieltes Nachladen, Slot-Hash und Selbstheilung sind aktiv; WLED liefert zwei Presets, Hue weiterhin nur Szenen aus dem Raum der Leuchte.

### PW-BOOT-001: Home-Assistant-Verbindung benötigte nach Neustart 17 Sekunden
Direkte WLAN-Verbindung und sofortiges erstes Zeitpaket sind aktiv; live wurde die Zeitbestätigung bei 0,64 Sekunden Bridge-Uptime gemessen.

### PW-MEDIA-005: Geladene Playlist endete bei „Ektschen“
Die Bridge bewirbt Paging nun korrekt; der Live-Probe-Trigger erweiterte S3- und Bridge-Cache erfolgreich von 40 auf 88 Einträge.

### PW-UI-001: Titel bestand nur aus hochkant stehenden Rechtecken
Der 32-px-Titelfont enthält statt Ziffern-only nun 319 Latin-Glyphen inklusive Umlauten; S3-Build und OTA sind erfolgreich.

### PW-UPD-002: Kein HA-Geräteupdate für die zwei Firmwares
Eine PassionWave-Update-Entität führt Bridge → Reconnect → S3 → Reconnect aus; die beiden ESPHome-Quellen sind nur noch verborgene Recovery-Transporte.

### PW-HA-010: Zwei ESPHome-Kacheln statt einer PassionWave-Komponente
S3 startet genau einen PassionWave-Flow; Bridge-, Zeroconf- und verzögerte retained MQTT-Flows werden MAC-genau verborgen und intern gekoppelt.

### PW-SEC-003: ESPHome verlangte breite Home-Assistant-Aktionsrechte
Integration `3.0.0-beta.12` vermittelt validierte Commands; beide Firmwareprofile melden `homeassistant_services: false`.

### PW-HA-005: Integration startete vor den Bridge-Aktionen
Reload-Reihenfolge und Retry sind abgesichert; Bridge → S3 → PassionWave wurde live mit Bibliothek, Radar und Floorplan geprüft.

### PW-HA-004: Setup sprang zur sicheren Kopplung zurück
Der Connection-Schritt besitzt eine eigene Flow-ID und führt deterministisch zu Lichtplätzen und Abschluss.

### PW-HA-003: Lichtplätze benötigten ein Blueprint
Bis zu vier Lichter werden direkt im PassionWave Config Entry verwaltet; Web- und Control-Dokumentation verlinken kein Blueprint mehr.

### PW-MEDIA-004: Playlist endete beim ersten 40er-Block
Offene Gesamtlänge, Vorladen und Touch-Fokus sind korrigiert; automatisierte Integrationsprüfungen laufen grün.

### PW-FW-009: Flash-Helfer erkannte Bridge und USB-Serial nicht
Chip-Erkennung, `/dev/cu.usbserial*`, ESP-IDF-Factory-Pfad und `python -m esptool`-Fallback sind korrigiert.

### PW-HA-008: Startzustand `unknown` erzeugte Broker-Warnungen
Leere, `unknown`- und `unavailable`-Zustände werden vor dem JSON-Decoder verworfen; der Latenz-Probe-Button ist auf das erlaubte Ziel begrenzt.

### PW-HA-009: Legacy-Fallback rief ohne Berechtigung HA-Aktionen auf
Managed Dual-MCU sperrt die direkten Wetter-/Template-Fallbacks; Forecast, Lichtkatalog und Medienzustand laufen ausschließlich über Bridge und Integration.

### PW-FW-010: Uhrzeitpuffer konnte statisch als zu klein gelten
Der Puffer wurde von sechs auf neun Bytes erweitert; die ESPHome-Compilerwarnung ist damit beseitigt.
