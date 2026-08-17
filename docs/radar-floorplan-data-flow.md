# Radar- und Floorplan-Wirkkette

Stand: 2026-07-28

Dieses Dokument beschreibt die vollständige Produktionskette, ihre
Diagnosepunkte und den vorgesehenen Updateweg. Radar und Floorplan sind
Netzwerk-Assets: Home Assistant erzeugt sie, der klassische ESP32 lädt sie und
der ESP32-S3 dekodiert und zeichnet sie. Der Display-Prozessor führt dabei
weder HTTP noch MQTT im normalen Betriebsmodus aus.

## Gemeinsamer Transport

```text
Home Assistant
  │  ESPHome Native API: absolute Asset-URL
  ▼
ESP32-Bridge
  │  HTTP GET im LAN
  │  begrenzte Chunks + CRC-32 + ACK über 2-Mbit/s-UART
  ▼
ESP32-S3
  │  JPEG-/PNG-Dekodierung außerhalb des UI-Hotpaths
  ▼
LVGL-Bild auf der sichtbaren Radar- oder Haus-Seite
```

Die absolute URL wird von
`home_assistant/pyscript/passion_wave_floorplan.py` mit Home Assistants
Netzwerkhelfer erzeugt. Dadurch verwendet die Bridge die von Home Assistant
erkannte interne IPv4-Adresse. Ein funktionierender Asset-Transfer hängt nicht
mehr von `homeassistant.local` oder anonymem MQTT ab.

Seit Home Assistant 2026.7 werden Pillow-Untermodule im Pyscript explizit
importiert. Lädt dieses Modul nicht, fehlen Radar- und Floorplan-URL
gleichzeitig; `pyscript.reload` und das Systemprotokoll sind deshalb der erste
gemeinsame Diagnosepunkt.

## Radar

1. Das Home-Assistant-Radar-Paket aktualisiert die Radardaten im Fünf-Minuten-
   Raster.
2. Der Renderer erzeugt atomar drei 320×320-JPEGs:
   `rain_radar_z0.jpg`, `rain_radar_z1.jpg` und `rain_radar_z2.jpg`.
3. `sensor.scrollwheel_rain_radar_image_path` veröffentlicht den relativen
   Mittelzoom-Pfad mit Revisionsparameter.
4. Pyscript ergänzt die von Home Assistant erkannte interne Basis-URL und
   veröffentlicht das Ergebnis als
   `pyscript.passion_wave_radar_asset_url`.
5. Die ESPHome Native API überträgt diese URL ohne Polling an die ESP32-Bridge.
6. Der S3 fordert beim Öffnen oder Zoomen die gewünschte Stufe an. Die Bridge
   ersetzt nur den Teil `_z0`, `_z1` oder `_z2` der aktuellen URL.
7. Die Bridge lädt das JPEG per HTTP und sendet `BEGIN`, begrenzte Datenchunks
   und `END` mit Länge und CRC-32 über UART.
8. Der S3 bestätigt den Transfer, dekodiert das JPEG und aktualisiert das
   LVGL-Bild.

## Floorplan

1. Pyscript beobachtet die sieben dargestellten Licht-Entitäten.
2. Änderungen einer Szene werden 300 ms gesammelt.
3. Basisbild und aktive Licht-Layer werden wie im Dashboard mit `lighter`
   kombiniert, auf 340×255 skaliert und in eine 360×360-Leinwand gesetzt.
4. Das PNG wird zuerst vollständig als temporäre Datei geschrieben und danach
   atomar nach
   `/config/www/passion-wave/floorplan-render/live.png` verschoben.
5. `pyscript.passion_wave_floorplan_revision` erhält eine neue Revision und im
   Attribut `asset_url` eine absolute interne URL mit Revisionsparameter.
6. Die ESPHome Native API liefert das Attribut an die ESP32-Bridge. Die Bridge
   speichert die URL und sendet `FLOORPLAN_INVALIDATED` an den S3.
7. Ist die Haus-Seite sichtbar, fordert der S3 nach der kurzen UI-Entprellung
   das Bild an. Andernfalls erfolgt der Transfer erst beim Öffnen der Seite.
8. HTTP-, UART-, CRC-, ACK-, Dekodier- und LVGL-Pfad entsprechen dem Radar.

Es gibt keinen parallelen MQTT-Invalidierungspfad mehr.

## Schrittweise Diagnose

| Prüfstufe | Prüfung | Erwartung | Befund am 28.07.2026 |
|---|---|---|---|
| Radar-Quelle | Dateien unter `/config/www/scrollwheel/` | drei gültige JPEGs, 320×320 | bestanden |
| Radar-Zustand | `sensor.scrollwheel_rain_radar_image_ready` | `ready` | bestanden |
| Radar-Pfad | `sensor.scrollwheel_rain_radar_image_path` | `/local/..._z1.jpg?v=...` | bestanden |
| Radar-URL | `pyscript.passion_wave_radar_asset_url` | `http://<HA-LAN-IP>:8123/local/...` | bestanden |
| Floorplan-Renderer | Dienst `pyscript.passion_wave_floorplan_refresh` | vorhanden und ausführbar | nach `pyscript.reload` bestanden |
| Floorplan-Datei | `floorplan-render/live.png` | gültiges RGB-PNG, 360×360, kleiner als 64 KiB | bestanden, 42.715 Byte |
| Floorplan-URL | Attribut `asset_url` der Revision | absolute interne URL | bestanden |
| HTTP | GET auf alle vier Assets | HTTP 200 | bestanden; 18–133 ms |
| ESP32/S3-Link | Link-Sensor und UART-Fehler | verbunden, keine Protokollfehler | bestanden |
| Produktions-ESP32 | Radar-Proxy-Diagnose | HTTP- oder Transferstatus | vor Pyscript-Reload Fehlercode 2; absolute IPv4-URL danach vorhanden |
| S3-Bereitschaft | `ESP32 Home Assistant Bridge` | `on` | Firmwarefehler eingegrenzt; Korrektur in 3.0.0-beta.6 |
| S3-Anzeige | sichtbare Radar-/Haus-Seite | aktuelles Bild | ausstehend bis Firmware-OTA |

### Gefundener Problempunkt

Die Produktions-Bridge baute Radar-URLs fest aus
`http://homeassistant.local:8123` auf. Der Proxy führte vor dem HTTP-Aufruf
eine eigene mDNS-Abfrage aus. Deren Fehlschlag erzeugte Fehlercode `15` und
beendete den Download mit null Byte. Der Radar-Renderer war zu diesem Zeitpunkt
bereits vollständig funktionsfähig.

Beim Floorplan kamen zwei unabhängige Probleme hinzu:

- der Factory-Fallback zeigte noch auf die nicht vorhandene Datei
  `/local/passion-wave/floorplan.png`;
- die Invalidierung hing in der öffentlichen Factory-Konfiguration von einem
  MQTT-Login mit leeren Zugangsdaten ab.

Außerdem lag das Pyscript zwar unter `/config/pyscript`, war nach seiner
Bereitstellung aber nicht geladen. Deshalb fehlten Dienst und Revisionsentität
bis zum Pyscript-Reload.

### Umgesetzte Korrektur

- Home Assistant veröffentlicht beide Assets als absolute interne URL über die
  ESPHome Native API.
- Die Bridge verwendet die dynamische Radar-URL für alle Zoomstufen und die
  dynamische Floorplan-URL für Haus-Anforderungen.
- Eine geänderte Floorplan-URL invalidiert den S3 direkt über UART.
- Factory-Fallbacks zeigen auf die tatsächlich erzeugten Dateien.
- Ein fehlgeschlagener expliziter mDNS-Vorcheck ist nicht mehr fatal; der
  normale HTTP-Resolver erhält als Rückfallebene noch eine Chance.
- Das aktive Pyscript wurde neu geladen und die erzeugten URLs sowie alle
  Dateien wurden per HTTP geprüft.

## Home-Assistant-orchestrierter ESPHome-Updateweg

Der robuste Weg besteht aus zwei getrennten, versionierten Firmware-Zielen:
Bridge und S3 bleiben unabhängig aktualisierbar.

1. CI baut beide Factory- und OTA-Binärdateien aus einem unveränderlichen
   Release-Tag, prüft beide ESPHome-Konfigurationen und veröffentlicht
   Prüfsummen sowie Release Notes.
2. Jeder in den ESPHome Device Builder übernommene **Prozessor-Endpunkt**
   verwendet nur einen dünnen lokalen Wrapper. Die beiden Endpunkte gehören
   gemeinsam zu einem physischen RotaryKnob. Hardware und Logik kommen als
   Remote-Package aus einem festgelegten Release-Tag; lokale WLAN-, API- und
   Zielkonfiguration bleibt im Wrapper.
3. Home Assistant meldet verfügbare Firmware über je eine `update`-Entität.
   Installation erfolgt über die native Aktion `update.install`; es werden
   keine Geräte-IDs in Automationen fest verdrahtet.
4. Vor dem Update prüft eine HA-Automation:
   beide Prozessoren online, UART-Link verbunden, keine Protokollfehler,
   externe Versorgung oder ausreichender Akkustand, kein laufender
   Asset-Transfer und kein aktives Playback.
5. Nach einer manuellen Freigabe wird zuerst die ESP32-Bridge aktualisiert.
   Das Protokoll muss dabei noch mit der vorherigen S3-Version kompatibel
   bleiben.
6. HA wartet auf API-Reconnect, gültigen Heartbeat und einen erfolgreichen
   Link-Smoke-Test. Erst danach folgt der S3.
7. Nach dem S3-Reconnect prüft HA Versionen, UART, Radar, Floorplan und eine
   lokale Eingabelatenzprobe. Bei einem Fehlschlag stoppt die Sequenz; das
   vorherige Release bleibt als klar benannter Rollback verfügbar.

Für schlafende Geräte kann der ESPHome Device Builder ab Version 2026.7 ein
kompiliertes Update in eine Warteschlange stellen und beim nächsten
Netzwerkfenster installieren. Das passt zum S3: Home Assistant hält ihn nur für
das freigegebene Wartungsfenster wach. Automatische ungeprüfte Updates aus
`main` sind ungeeignet; Produktionsgeräte folgen ausschließlich Release-Tags
und einem expliziten Freigabegate.
