# Firmware and integration 3.0.1-beta.16

Der Wetteravatar zeigt einen weich gestalteten 3D-Jungen mit passender Kleidung.
Braune Haare/braune Augen und blonde Haare/grünbraune Augen sind in Home
Assistant und direkt am Knob umschaltbar. Der Wetterbutton öffnet das Bild
jederzeit; die einschaltbare Morgenautomatik weckt das unbediente Display von
06 bis 10 Uhr Ortszeit, auch auf Akku.

## Verhalten

- 52 lokale Bildschlüssel decken beide Identitäten, sechs Temperaturbänder,
  vier Schutzarten, neutrale Darstellung und Sonnenhut ab.
- MET-Stundenprognosen liefern die nächsten vier vollständigen Stunden. Der
  sichtbare Zeitraum, Temperaturen und Wetter-/Schutzhinweise bleiben mit dem
  Bild konsistent. Andere Anbieter nutzen zunächst den beschrifteten Jetzt-Modus.
- Nach 20 Minuten ohne gültige Daten verschwindet die Empfehlung. Regen,
  Schnee, Wind, Gewitter und Hagel haben dokumentierte Prioritäten; unbekannte
  Niederschlagsphase wird nicht als Regen ausgegeben.
- S3 besitzt die persistenten Einstellungen. HA wartet auf Bestätigung und
  spielt keine veralteten Optionen zurück. Dialoge, Alarme und OTA behalten
  Vorrang; Avatar-Eingaben lösen keine Aktion auf der darunterliegenden Seite aus.

Bedienung, Wettergrenzen, Speicherbedarf und konkrete Tests stehen in
[docs/weather-avatar.md](docs/weather-avatar.md).

## Validierung und Release

Vor der Kandidatenqualifikation wurden die nativen C++-Tests für Resolver,
Scheduler, Transport und Decoder sowie alle 52 Bildschlüssel geprüft. Die
Integration wurde zusätzlich unter dem installierten Home Assistant 2026.9.3
getestet. Der offizielle Kandidatenlauf prüft die gepinnte HA-Matrix, alle sechs
ESPHome-Profile, native Avatar-Tests und die vollständige Web-Distribution.

Die unveränderliche Hosted-CI-Receipt enthält die abschließenden Ergebnisse,
exakten Quell-OIDs, Werkzeugversionen und vier Payload-Prüfsummen. Lokale
Builds sind Diagnoseevidenz. Die Installation erfolgt erst aus dem geprüften
CI-Kandidaten über den dokumentierten HACS-/Staging-Weg.

## Abnahme

Direkte visuelle, Touch-, Haptik-, Akku-/Zeitfenster- und Medienabnahme ist
weiterhin am Gerät erforderlich. Vorhandene automatisierte Tests und Remote-
Zustände gelten nicht als physische Abnahme. Die allgemeinen Beta-Gates für
Clean Install und beide Geräte bleiben vor globaler Promotion verbindlich.
