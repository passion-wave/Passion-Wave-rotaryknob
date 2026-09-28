# Wetteravatar

Der S3 zeigt einen weich gestalteten 3D-Jungen mit temperaturgerechter Kleidung.
Beide Aufrufwege verwenden denselben Wetterkontext, Resolver und Bilddecoder.
Implementierung und automatisierte Tests sind vorhanden; Firmwarebuild,
Installationsstand und tatsächlich beobachtete Geräteabnahme werden ausschließlich
in [RELEASE.md](../RELEASE.md) und [known-issues.md](known-issues.md) festgehalten.

## Konfiguration und Bedienung

- Home Assistant: **Einstellungen → Geräte & Dienste → PassionWave → Konfigurieren**.
  Nach den Medienfiltern folgt **Wetteravatar** mit `Avatar Haare Braun` oder
  `Avatar Haare Blond` und dem Schalter `Morgenavatar 06–10`.
- Auf der PassionWave-Geräteseite stehen dieselben Optionen als
  Konfigurationsauswahl und Schalter bereit. Die technischen ESPHome-Entities
  bleiben verborgen.
- Am RotaryKnob: **Mehr → Einstellungen → System → Avatar Haare** bzw.
  **Morgenavatar 06–10**. Die Haarwahl verändert niemals die Wetterregeln.
- In der Wetteransicht öffnet **Avatar** das passende Bild jederzeit, auch
  außerhalb des Morgenfensters. Tippen oder Wischen schließt es; das auslösende
  Eingabeereignis wird konsumiert. Drehen hebt nur kurz die Helligkeit an.

Braune Haare gehen mit braunen Augen einher; blonde Haare mit grünbraunen Augen.
Standard ist Braun, Morgenautomatik ist eingeschaltet. Beide Werte liegen
persistent auf dem S3. Lokale und HA-Bedienung nutzen dieselben Setter.
HA liest den tatsächlichen Gerätezustand; gespeicherte alte HA-Optionen werden
nicht auf das Gerät zurückgespielt. Offline bzw. ohne bestätigte Rückmeldung
meldet eine Änderung einen Fehler. Ein unverändert abgesendetes Formular darf
zwischenzeitliche lokale Änderungen nicht überschreiben.

## Morgenfenster und Stromversorgung

Das tägliche Fenster ist **06:00:00 einschließlich bis 10:00:00 ausschließlich**
in der Gerätezeitzone `Europe/Berlin`, einschließlich Sommer-/Winterzeit.
Der Scheduler prüft den aktuellen Zustand jede Sekunde, auch nach Boot und
Zeitabgleich. Er benötigt keine zuvor beobachtete 06-Uhr-Flanke.

| Situation | Verhalten |
| --- | --- |
| Unbedientes Gerät um 06 Uhr | Nach bestehender Screensaver-Wartezeit, standardmäßig 30 Sekunden seit letzter Bedienung, Display wecken und Avatar anzeigen. Ein bereits lange unbedientes Gerät öffnet ihn sofort. |
| Aktive Bedienung | Bedienung bleibt bestehen; erst nach erneuter Inaktivität zurück zum Avatar. |
| Offener Dialog, Timer-Endmeldung, Alarm, OTA oder noch nicht abgeschlossenes Factory-Onboarding | Diese Ansicht hat Vorrang. |
| Hintergrund-Timer oder Musikwiedergabe | Läuft weiter; das automatische Mediencover verdrängt den Morgenavatar nicht. |
| 10 Uhr oder Automatik ausschalten | Automatisch geöffneten Avatar beenden, gemerkte Ansicht wiederherstellen und normale Schlafregeln anwenden. |
| Manuell über Wetter geöffnet | Rückkehr zur Wetteransicht; bleibt auch über 10 Uhr geöffnet. Außerhalb des Fensters gelten normale Schlafregeln. |
| Ungültige Uhrzeit | Keine Morgenautomatik; manueller Button funktioniert mit neutralem Datenhinweis. |

Im aktiven Morgenfenster bleibt die Anzeige auch auf Akku sichtbar. Die
Abdunkelung nutzt `Display Dimmhelligkeit`. Der persistente DEV-Schalter
`Wach halten` wird nicht verändert; die Morgenautomatik überstimmt dessen
Screensaver-Veto. Außerhalb des Fensters gilt wieder dessen normale Wirkung.
Vor Akku-Deep-Sleep wird zusätzlich zum Taster-Wakeup ein RTC-Termin für das
nächste lokale 06 Uhr gesetzt. Kalenderberechnung mit automatischer DST-Wahl
berücksichtigt 23- und 25-Stunden-Tage. Ohne gültige Zeit wird nach 15 Minuten
ein erneuter Synchronisationsversuch ermöglicht. Ein vollständig ausgeschaltetes
Gerät oder ein leerer Akku kann nicht durch Software eingeschaltet werden.

## Wetterdaten und Aktualität

Die Bridge fordert den HA-Wetterbericht über den bestehenden Forecastpfad an.
Der Avatar-Kontext wird auf dessen 15-Minuten-Aktualisierung aufgebaut. Die
stündlichen Originaldaten bleiben für den Avatar erhalten; die alte verdichtete
Wetteransicht bleibt protokollkompatibel.

Der MET-Adapter bewertet die nächsten vier vollständigen Prognosestunden. Der
erste Zeitstempel muss zwischen Abruf und höchstens einer Stunde danach liegen;
das Fenster endet genau vier Stunden später. Beispielsweise zeigt ein Abruf um
06:15 den verfügbaren Zeitraum 07:00–11:00. Die vorherige Lücke wird nicht als
Prognose ausgegeben. Doppelte Zeitstempel, Lücken oder fehlende Temperaturen
verhindern eine vollständige Empfehlung. Es werden keine Stunden eines anderen
Tages ersatzweise herangezogen.

Der Adapter ist auf die dokumentierte MET-Stundenstruktur begrenzt. Andere
Wetteranbieter verwenden zunächst den beschrifteten Jetzt-Fallback, bis eine
passende Zeitsemantik angebunden ist. MET-Temperaturen sind Stützstellen, keine
kontinuierlichen Messungen. Die stündlichen Conditions beschreiben die folgende
Stunde. Ein erfolgreicher Abruf beweist keine neue Anbieterberechnung.

- Vollständige Prognose: Temperaturminimum und -maximum über diesen Zeitraum;
  Beschriftung mit konkreten lokalen Uhrzeiten.
- Fehlende vollständige Prognose: gültiger aktueller Zustand mit **Jetzt**.
- Fehlende, ungültige oder veraltete Daten: neutrale Figur und
  **Keine Wetterdaten / Noch keine Empfehlung**.
- Gültige Gewitter-/Hagelhinweise bleiben auch bei fehlender Temperatur sichtbar.
- Der ursprüngliche Abruf darf höchstens 20 Minuten alt sein. UART-Replay und
  Bildschirmaufrufe verlängern diese Frist nicht. Bekannte alte oder ungültige
  Beobachtungszeitstempel werden nicht durch einen neuen Abruf verjüngt.
- Temperatur wird nach °C, Wind/Böen nach km/h und Niederschlag nach mm
  normalisiert. Nicht unterstützte Einheiten bleiben unbekannt. Fehlende Werte
  werden niemals als echte Null interpretiert.
- Für die Kleidungswahl wird Lufttemperatur verwendet. Eine gefühlte Prognose
  wird nicht aus aktueller Feuchte und zukünftigen Temperaturen konstruiert.
- Teilweise fehlende optionale Daten erhalten den Zusatz **teils unbekannt**.

Der native UART-Kontext verwendet Schema 1 und 38 Bytes: Modus, Sequenz,
Abruf-/Anbieterzeit, UTC-Fenster, Temperaturbereich, Original-Conditionmaske,
Condition des ersten Schritts, Niederschlagswahrscheinlichkeit/-menge,
Wind/Böen und Validitätsflags. Neue Fähigkeiten werden zwischen Bridge und S3
verhandelt; ein nicht unterstützter Kontext erzeugt keine falsche Empfehlung.

## Kleidung und Wetterregeln

`T` ist das Minimum der gültigen Lufttemperaturen im ausgewerteten Fenster,
im Jetzt-Modus die aktuelle Lufttemperatur. Der Resolver arbeitet in Zehntelgrad.

| T | Basiskleidung |
| --- | --- |
| `T ≥ 28 °C` | Leichtes Shirt, Shorts; bei Sonne/teilweise Sonne zusätzlich Sonnenhut. |
| `22 ≤ T < 28 °C` | T-Shirt und Shorts. |
| `16 ≤ T < 22 °C` | Leichter Pullover und lange Hose. |
| `10 ≤ T < 16 °C` | Leichte Jacke und lange Hose. |
| `0 ≤ T < 10 °C` | Isolierte Jacke, lange Hose und warme Schuhe. |
| `T < 0 °C` | Winterjacke, Mütze, Schal, Handschuhe und Winterstiefel. |

Ein Regenzustand (`rainy`, `pouring`, `lightning-rainy`, `snowy-rainy`) verlangt
wasserdichte Kleidung. Niederschlagswahrscheinlichkeit ab 50 % oder positive
unspezifische Niederschlagsmenge ohne belegte flüssige Phase ergeben
**Niederschlag möglich / Nässeschutz**, kein erfundenes Regensymbol.
Schnee/Hagel werden durch eine Mengenangabe nicht in Regen umgedeutet.
Windschutz gilt bei `windy`, `windy-variant`, Wind ab 20 km/h oder Böen ab 35 km/h.
Diese Grenzen sind Outfitregeln, keine amtlichen Warnschwellen.

Die folgende Reihenfolge entscheidet das Motiv. Die thermisch richtige Kleidung
und zusätzliche Wetterschutzflags bleiben dabei erhalten.

| Vorrang | Bedingung | Darstellung |
| --- | --- | --- |
| 1 | Keine gültige Temperatur/Wetterinformation oder abgelaufene Daten | Neutral, keine Empfehlung; unabhängige gültige Gefahrhinweise bleiben. |
| 2 | `exceptional` | Neutral, `Vorhersage prüfen`; keine amtliche Warnung behaupten. |
| 3 | `hail` | Temperaturgerechtes Outfit, `Schutz suchen`, bei Bedarf zusätzlich Gewitterhinweis. |
| 4 | Gewitter mit belegtem Regen | Passender Nässeschutz, Gewitter-/Schutzsymbol, `Drinnen bleiben`. |
| 5 | Gewitter ohne belegten Regen | Temperaturgerechtes Outfit und Schutzhinweis; unbekannte Nässe bleibt neutral. |
| 6 | `snowy-rainy` oder Regen und Schnee im Abschnitt | Wasserfeste Kleidung, `Regen und Schnee`. |
| 7 | `snowy` | Thermisch passender Schneeschutz mit geschlossenen griffigen Schuhen. |
| 8 | `pouring` | Wasserfeste Jacke und Hose, passende leichte/warme Unterschicht. |
| 9 | Regen/Nässeschutz | Passende wasserfeste Schicht: warm ab 18 °C, kühl ab 5 °C, kalter Regen darunter; keine erfundenen Schneeflocken. |
| 10 | Windschutz | Leichte oder isolierte Windschicht; Frostzubehör bleibt erhalten. |
| 11 | `fog` | Temperaturgerechtes Outfit, Sichtbarkeitshinweis. |
| 12 | `clear-night` im ersten relevanten Schritt | Temperaturgerechtes Outfit mit Nachtsymbol. |
| 13 | Sonne, Teilbewölkung, Wolken | Temperaturbasis und passendes separates Wettersymbol. |

## Bilder, Decoder und Speicher

Das [Produktionsmanifest](../assets/weather-avatar/manifest.json) enthält
**52 Schlüssel**: zwei Identitäten × sechs Temperaturbänder × vier Schutzarten,
zusätzlich neutrale Darstellung und Sonnenhut pro Identität. Wetterzeichen,
Schutzhinweise, Uhr und Texte sind getrennte LVGL-Objekte.
Die [Konzepttafeln](design/weather-outfit-boy/avatar-identities-v1/manifest.json)
bleiben als Entwurfsprovenienz erhalten; ihre historischen Versionsfehler gelten
nicht als aktuelles Prüfergebnis.

Die vier Produktionsatlanten wurden mit dem eingebauten `image_gen` erstellt;
Prompts und unveränderte Quellen liegen unter `assets/weather-avatar/`.
`tools/export-weather-avatar.py` exportiert die visuell geprüfte Zellzuordnung
auf 368 × 368 Pixel. Äquivalente Kleidung darf mehrere passende Schlüssel
bedienen, etwa die dünne Windjacke für heiß/warm. Der überprüfte Zellplan
vermeidet Fehlzuordnungen aus der vom Generator gewählten Reihenfolge.

Die 360er Anzeige schneidet vier Pixel Overscan ab; es gibt keine Laufzeitskalierung.
Baseline-JPEGs liegen lokal in Flash. Identische JPEGs werden im erzeugten Header
dedupliziert. Das Manifest nennt die tatsächliche Bytezahl, Prüfsummen und
Geometrie. Zwei RGB565-Puffer benötigen zusammen höchstens **541.696 Bytes**,
zusätzlich Decoder-/LVGL-Arbeitsspeicher. Tatsächliche OTA-Größe und freier
Gerätespeicher müssen durch Build bzw. Gerätediagnose belegt werden.

Ein Worker auf Core 0 dekodiert jeweils nur ein Bild; die letzte Auswahl gewinnt.
Bild und Beschriftung werden erst nach vollständigem Decode auf dem UI-Thread
umgeschaltet. Ein Datenablauf, Decodefehler oder überlanges Warten lässt keine
alte Kleidung als aktuelle Empfehlung stehen. Decodefehler werden angezeigt;
der Wiederholungsversuch nutzt monotone Zeit. Foto-Screensaver und Avatar teilen
Seite 7, besitzen aber getrennte Inhalte; beim Verlassen wird die Fotoansicht
wiederhergestellt.

## Automatisierte und manuelle Tests

Automatisiert werden Wettergrenzen und kombinierte Bedingungen, beide Identitäten,
vollständige Assetabdeckung, JPEG-/Header-Prüfsummen, UTC/DST, Datenlücken,
Einheiten, Replay, HA-Konfigurationsbestätigung, Decoderfehler und verspätete
Bildwechsel geprüft. Die nativen C++-Tests führen die tatsächlich verwendeten
Header aus. Zusätzlich gelten die regulären HA-, S3-, Bridge- und Release-Gates.

Nach Installation bitte auf **jedem RotaryKnob** prüfen:

1. Wetter → Avatar öffnen. Figur, Kleidung, Text, Uhr und alle Kreisränder prüfen.
2. In HA Braun → Blond → Braun wählen. Haar- und Augenfarbe müssen wechseln;
   Wetter und Kleidung müssen gleich bleiben. Dasselbe lokal ausprobieren.
3. Blond auswählen, Gerät neu starten. Blond und der Morgen-Schalter müssen
   erhalten bleiben; HA muss den tatsächlichen Gerätestand anzeigen.
4. Avatar durch Tippen/Wischen verlassen: kein unbeabsichtigter Button darunter.
   Drehen darf weder Lautstärke noch Licht ändern, sondern nur die Helligkeit.
5. Morgenautomatik einschalten: um 06 Uhr muss das unbediente Gerät aufwachen,
   um 10 Uhr die automatisch geöffnete Ansicht verlassen. Boot im Fenster,
   Akku-/Netzbetrieb und eine laufende Musikwiedergabe separat prüfen.
6. Manuell vor 10 Uhr öffnen: um 10 Uhr bleibt dieser Aufruf bestehen. Außerhalb
   des Fensters manuell öffnen und die normale Schlafregel prüfen.
7. Während eines Dialogs sowie bei Timer-Ende/Alarm dürfen Hinweise nicht vom
   Avatar verdeckt werden. Nach Quittieren/Inaktivität soll er zurückkehren.
8. Wetterquelle vorübergehend unerreichbar machen: nach Ablauf der 20 Minuten
   muss die Empfehlung neutral werden. Quelle wiederherstellen und die nächste
   Aktualisierung abwarten. Keine Systemuhr oder produktiven Wetterwerte verstellen.
9. Mehrfach schnell Braun/Blond wechseln, danach Mediencover und Radar öffnen:
   keine Bildreste, Abstürze oder verlorenen Eingaben. Abschließend den logischen
   Firmware-Updatestatus und beide Prozessorverbindungen kontrollieren.

Zeitgrenzen, DST, fehlerhafte JPEGs und synthetische Extremwetter sind zusätzlich
in den automatisierten Tests reproduzierbar; Remote-Entities beweisen keine
visuelle, haptische oder akustische Geräteabnahme.

## Quellen und Zuständigkeiten

- [UI-Architektur](ui-next-framework.md), [Konfiguration](configuration.md),
  [HA-/Bridge-Vertrag](dual-mcu-ha-bridge.md), [Release-Weg](release-runbook.md).
- [Home Assistant Weather](https://www.home-assistant.io/integrations/weather/)
  und [Weather-Entity-Vertrag](https://developers.home-assistant.io/docs/core/entity/weather/)
  definieren Conditions, Zeitstempel und optionale Einheiten; Outfitgrenzen sind
  Produktentscheidungen. Der [MET-Forecastvertrag](https://docs.api.met.no/doc/ForecastJSON.html)
  beschreibt die verwendeten Stundenintervalle und Temperatur-Stützstellen.
