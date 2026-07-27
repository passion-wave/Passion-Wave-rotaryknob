# Kunden-Onboarding für ungeflashte Geräte

## Ziel

Der Rotaryknob wird zwingend ungeflasht verkauft. Kunden sollen weder eine
Entwicklungsumgebung installieren noch YAML-Dateien kopieren müssen. Der
Standardweg besteht aus einem Browser-Assistenten, zwei chipgebundenen
Firmware-Images und einer Home-Assistant-App mit typisierten Auswahllisten.

## Warum zwei Flash-Schritte notwendig bleiben

Die Komponente enthält zwei unabhängig flashbare Prozessoren:

| USB-Ziel | Aufgabe | Öffentliches Profil | Web-Manifest |
|---|---|---|---|
| ESP32-S3 | Display, Touch, EC1-Encoder, Haptik, UI | `esphome/factory-s3.yaml` | `firmware/rotaryknob/s3/manifest-3.0.0-beta.3.json` |
| ESP32 | Home-Assistant-Bridge, EC2, Netzwerk-Offload | `esphome/factory-esp32.yaml` | `firmware/rotaryknob/esp32/manifest-3.0.0-beta.3.json` |

Die USB-C-Ausrichtung bestimmt das Ziel. Eine vollautomatische Umschaltung ist
ohne zusätzliche Hardware im Gerät nicht möglich. Die Website reduziert den
unvermeidbaren manuellen Vorgang auf: flashen, Stecker drehen, erneut flashen.

## Automatisierter Releaseweg

1. `factory-s3.yaml` und `factory-esp32.yaml` binden ausschließlich
   zugangsdatenfreie Core-Dateien ein.
2. `tools/build-public-release.sh` prüft die aufgelösten schlüsselfreien
   Konfigurationen, kompiliert beide Images und erstellt Manifeste sowie
   `SHA256SUMS` aus derselben Version.
3. Die GitHub Action `.github/workflows/public-firmware.yml` wiederholt den
   Build auf jedem Release-Tag in einem fest versionierten ESPHome-Container.
4. `Passion-Wave-web/tools/import-firmware.sh` prüft die Summen, kopiert beide
   Images in getrennte Ordner und validiert Manifeste sowie Website.
5. Erst nach erfolgreicher Website-Prüfung darf deployt werden.

Private Wrapper:

- `rotaryknob-s3-ui-core.yaml`
- `managed-production-s3.yaml`
- `managed-production-esp32.yaml`
- `managed-test-s3.yaml`
- `managed-test-esp32.yaml`

Sie enthalten die lokalen `!secret`-Verweise und sind niemals Teil eines
Factory-Builds.

## Kundenweg mit minimalen Handgriffen

1. Website in Chrome oder Edge auf einem Desktop öffnen.
2. USB-Datenkabel anschließen und im Portdialog `ESP32-S3` wählen.
3. `PassionWave Rotaryknob` installieren, nach 100 Prozent `Next` wählen und
   WLAN per Improv setzen. Der Factory-Assistent erzwingt Clean Erase.
4. Stecker abziehen, um 180 Grad drehen und erneut einstecken.
5. Im zweiten Dialog `ESP32` ohne `S3` wählen, `PassionWave Rotaryknob Bridge`
   installieren und bis `Installation complete` warten.
6. Den Installationsdialog schließen, USB für zwei Sekunden trennen und in
   derselben ESP32-Ausrichtung wieder verbinden. Danach den separaten
   Bridge-WLAN-Button öffnen, denselben Port wählen, bis zu zehn Sekunden auf
   Improv warten und dasselbe WLAN setzen. Ein zweiter Flash ist nicht nötig.
7. PassionWave über HACS installieren und Home Assistant neu starten.
8. Das Gerät vollständig aus- und einschalten, PassionWave innerhalb von
   20 Minuten hinzufügen und S3 sowie Bridge desselben Rotaryknob auswählen.
   PassionWave erzeugt je Controller einen individuellen Encryption-Key,
   provisioniert ihn und legt beide ESPHome-Einträge an. Der Kunde sieht und
   kopiert keinen Schlüssel.
9. Bridge,
   Music-Assistant-Instanz sowie Medienplayer in typisierten UI-Auswahllisten
   festlegen. Playlist-Einträge werden automatisch aus Music Assistant
   übernommen.
10. Den kompakten Funktionskatalog auf der Website abarbeiten.

Home Assistant muss Geräte- und Automationsanlage aus Sicherheitsgründen
bestätigen lassen. Diese Bestätigungen werden bewusst nicht durch externe
Skripte umgangen. Manuelle `configuration.yaml`- oder `.storage`-Änderungen
gehören nicht zum Kundenweg.

## OTA und Rettungsweg

Beide öffentlichen Profile enthalten:

- `dashboard_import` für Adoption in ESPHome;
- passwortloses ESPHome-OTA im lokalen Netz;
- `safe_mode`;
- einen Fallback-Access-Point;
- `improv_serial` für erneute WLAN-Provisionierung.
- Clean-Erase-Vorgabe gegen alte Namen, Netzdaten und API-Schlüssel;
- ein 20-minütiges API-Provisionierungsfenster mit `api.encryption` ohne
  einkompilierten Schlüssel;
- keine direkten Geräte-/Home-Assistant-Sprünge im Improv-Dialog;
- Onboarding-Wachschutz bis zur ersten Home-Assistant-Verbindung.

Updates werden pro Prozessor veröffentlicht und nie als gemeinsames,
chipunspezifisches Image angeboten. Fällt OTA aus, wird nur der betroffene Chip
über den passenden Web-Installer neu installiert.

## Qualitätsgates vor jedem Verkauf

1. Drei Konfigurationsläufe in einem Checkout ohne `secrets.yaml`.
2. Vollständiger Compile beider Factory-Profile.
3. SHA-256-Prüfung nach dem Kopieren in die Website.
4. Manifesttest: exakt ein Build und korrekte Chipfamilie je Schritt.
5. Link-, Sprach-, Bild- und Mobilansichtstest der Website.
6. Physischer Neuinstallationslauf an einem zurücksetzbaren Testgerät:
   S3-Flash → S3-WLAN → Bridge-Flash → Bridge-Neustart → Bridge-WLAN →
   Discovery → App → Encoder/Touch/Medien/Licht/Wetter → OTA.
7. Zweiter physischer Lauf mit absichtlich falscher USB-Ausrichtung und
   Wiederherstellung über den Assistenten.

Ein reiner Softwaretest kann den USB-Multiplexer, das konkrete Kabel und die
WLAN-Discovery nicht beweisen. Deshalb bleibt das physische Release-Gate
verpflichtend.

## Affiliate- und Bildpflege

Der Bestelllink steht ausschließlich in
`Passion-Wave-web/assets/site-config.js`. Bis eine echte Partner-URL vorliegt,
ist dort ein funktionierender, nicht vergüteter Lieferantenlink hinterlegt.
Nach Erhalt des Deep-Links werden nur `orderUrl` und `affiliateActive`
aktualisiert.

Die beiden SVG-Dateien mit `placeholder` im Namen markieren feste
Foto-Slots. Sie werden nach dem Fotoshooting durch optimierte Produktbilder
ersetzt; Seitenstruktur und responsive Bildflächen bleiben unverändert.
