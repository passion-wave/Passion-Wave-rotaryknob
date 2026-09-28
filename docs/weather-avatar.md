# Wetteravatar: Gestaltung und Implementierungsplan

Status: spezifiziert, noch nicht in der Firmware implementiert. Die Bilder sind
Designvorlagen. Zeitsteuerung, Avatar-Button, Einstellungen und Wetterregeln
werden erst in einem folgenden Implementierungsschritt aktiviert.

## Zwei Ausführungen

| Kennung | Darstellung | Bildserie |
| --- | --- | --- |
| `brown_brown` | Braune Haare und braune Augen; bestehender Charakter | [20 braune Varianten](design/weather-outfit-boy/clay-series-v1/manifest.json) |
| `blond_hazel` | Honigblonde Haare, beide Augen grünbraun: olivgrüner Irisrand, braun/bernsteinfarben zur Pupille | [20 blonde Varianten und Zuordnung](design/weather-outfit-boy/avatar-identities-v1/manifest.json) |

Gesicht, Hautfarbe, Proportionen, Outfitnummern und Kleidung bleiben gleich.
Die Auswahl verändert ausschließlich das Aussehen, niemals Wetterregeln.
Der [direkte Vergleich](design/weather-outfit-boy/avatar-identities-v1/avatar-comparison.png)
zeigt die Augenfarben zusätzlich im Portrait.

## Bedienung und Zeitfenster

Die Automatik gilt täglich in der vorhandenen Gerätezeitzone `Europe/Berlin`,
einschließlich Sommer-/Winterzeit: **06:00:00 einschließlich bis 10:00:00 ausschließlich**.
Sie wird per Einstellung `Morgenavatar 06–10` ein-/ausgeschaltet.
In diesem experimentellen Feature soll sie eingeschaltet sein; eine allgemeine
Produktaktivierung gehört in den späteren Rollout.

Planannahme zur gewünschten durchgehenden Anzeige: Um 06:00 wird das Display
geweckt und bei Nichtbedienung bis 10:00 sichtbar gehalten, auch auf Akku.
Diese Auslegung ist im Plan festgehalten; die optionale Rückfrage zum Beibehalten
des bisherigen Schlafmodus ändert nur die Wachhaltepolitik, nicht die Bildwahl.

| Ereignis | Geplantes Verhalten |
| --- | --- |
| 06:00, Gerät unbedient oder schlafend | Display/LVGL wecken, Avatar automatisch öffnen. |
| Boot, Wiederaufwachen oder erste Zeitsynchronisation zwischen 06 und 10 | Aktuelles Fenster prüfen und denselben Zustand herstellen; keine verpasste 06-Uhr-Flanke voraussetzen. |
| Aktive Bedienung oder modaler Dialog | Bedienung hat Vorrang. Erst nach Schließen des Dialogs und anschließender Inaktivität gemäß bestehender Screensaver-Wartezeit, standardmäßig 30 Sekunden, zum Avatar zurückkehren. |
| Laufende Musikwiedergabe | Musik läuft weiter; automatische Coveranzeige verdrängt den Morgenavatar nicht. |
| Laufender Timer im Hintergrund | Avatar erlaubt; sichtbarer Timer während Bedienung bleibt bestehen. |
| Klingelnder Alarm oder Timer-Endmeldung | Meldung hat Vorrang; nach Quittierung und Inaktivität wieder Avatar. |
| OTA, Onboarding oder andere exklusive Systemansicht | Diese Ansicht behält Vorrang; Automatik anschließend erneut auswerten. |
| 10:00 | Nur automatisch geöffneten Avatar beenden, vorherige Hauptansicht bzw. regulären zulässigen Screensaver wiederherstellen und normale Schlafregeln wieder anwenden. |
| `Avatar`-Button in Wetteransicht | Jederzeit denselben Resolver und Renderer öffnen, auch außerhalb von 06–10. Ein manueller Aufruf bleibt um 10:00 geöffnet. |
| Tippen/Wischen im Avatar | Vollbild verlassen; auslösendes Ereignis konsumieren, damit kein darunterliegender Button ausgelöst wird. Manuell zurück zur Wetteransicht, automatisch zur gemerkten Hauptansicht. |
| Drehknopf im Avatar | Bestehende kurze Helligkeitsanhebung beibehalten; keine Lautstärke-/Lichtänderung und kein unbemerkter Profilwechsel. |
| Ungültige Gerätezeit | Keine automatische Zeitsteuerung; Button bleibt verfügbar. Ohne zeitlich verifizierbare Wetterdaten neutrale Ansicht. |

Abgedunkelte Anzeige bleibt im Morgenfenster sichtbar. Dafür die einstellbare
`Display Dimmhelligkeit` verwenden (Standard 10 %), nicht den festen Fade-Zielwert
des Fotoscreensavers. Bedienung stellt die normale Interaktionshelligkeit her.
Die zeitweilige Wachhaltung darf den persistenten Entwicklerschalter
`display_keep_awake` nicht verändern. Während aktiver Morgenautomatik überstimmt
sie dessen bisheriges Screensaver-Veto; `apply_display_keep_awake` darf dann den
Avatar nicht schließen. Bedienungs-/Modalvorrang bleibt bestehen. Außerhalb des
Fensters bleibt das bisherige DEV-Verhalten unverändert.
Bei vollständig ausgeschaltetem Gerät oder leerem Akku ist kein zeitgesteuertes
Einschalten durch die Firmware möglich.

Geplante Priorität: Alarm/Timer-Endmeldung und exklusive Systemansicht → aktive
Bedienung/modaler Dialog → Morgenavatar → automatisches Mediencover/Fotoscreensaver.
Das Zeitfenster wird im 1-s-Takt sowie bei Boot, Zeitabgleich und
Einstellungsänderung ausgewertet. Übergänge sind idempotent: kein wiederholtes
Wecken, Fading oder Dekodieren pro Sekunde.

## Umschaltung und Avatar-Button

- Lokale Einstellungen: `Avatar` mit `Braun · braune Augen` und
  `Blond · grünbraune Augen`; zusätzlich `Morgenavatar 06–10`.
- `avatar_variant` und `morning_avatar_enabled` werden beide auf dem S3 persistent
  gespeichert, Avatar-Standard `brown_brown`. Nur echte Änderungen schreiben
  die Preferences.
- Die PassionWave-Konfiguration in Home Assistant erhält dieselben Optionen.
  Native ESPHome-`select`/`switch` dienen als Transport, bleiben im üblichen
  Kundendashboard verborgen. S3-Zustand ist die Autorität; der Configure-Dialog
  liest ihn und schreibt über denselben Setter wie die lokale Bedienung.
  Eine lokale Änderung darf beim nächsten HA-Snapshot nicht durch einen alten
  Config-Entry-Wert überschrieben werden. Offline wird keine Änderung als
  erfolgreich bestätigt; Wiederverbindung liest den tatsächlichen S3-Wert.
- Beim Wechsel während sichtbarem Avatar wird die neue Bildfamilie atomar
  übernommen, sobald das richtige Outfit dekodiert ist. Das vorherige Bild
  bleibt bis dahin sichtbar; keine leere Zwischenansicht.
- Neuer Wetter-Button: kleines Avatar-Symbol plus `Avatar`. Geplanter Bereich
  `x=84, y=274, w=120, h=46` auf dem 360er Panel, unterhalb der Wettermetriken.
  Position ist ein geometrischer Entwurf, noch keine Hardwareabnahme.
- Neue Action `WEATHER_AVATAR` für LVGL und CST816-Fallback; bestehende
  Actionqueue, 180-ms-Deduplizierung und einmalige Haptik verwenden.
  Ein offener Wetterkontext darf nicht durchklickt werden.
- Gemeinsame vorbereitete Vollbildansicht mit Öffnungsgrund
  `AUTO_MORNING` oder `MANUAL_WEATHER`, Rückkehrziel und Inhalt `PHOTO | AVATAR`.
  Bestehende Screensaver-Seite `page_7` und Suspendierung der UI-Next-Ebene
  wiederverwenden. Manuelle Ansicht folgt außerhalb des Fensters den normalen
  Inaktivitäts-/Schlafregeln.
- Im Avatar-Modus analoge Uhrzeiger und bestehende Foto-Overlays ausblenden.
  Kleine Digitaluhr oben, Temperaturbereich/Bezugszeitraum, große Figur in der
  Mitte, ein bis zwei kurze Kleidungsbegriffe unten. Temperatur, Wetterzeichen
  und Texte bleiben separate LVGL-Objekte und sind nicht ins Artwork gebrannt.
  Beim Wechsel zu `PHOTO` alle zugehörigen Sichtbarkeiten wiederherstellen.

## Welche Wetterdaten gelten?

**06–10 ist das Anzeigezeitfenster.** Als geplante V1-Produktentscheidung bewertet
die Kleidung jeweils einen vierstündigen Vorhersageabschnitt ab Erzeugung des
Wetterkontexts. Aktualisierung alle 15 Minuten; der konkrete Zeitraum wird
angezeigt, etwa `06–10 Uhr` oder `14–18 Uhr`. So zeigt auch der manuelle Button
am Nachmittag eine aktuelle Empfehlung. Screensaver und Button verwenden
denselben gecachten Kontext und liefern bei gleichen Eingaben dasselbe Bild.

Der Datenkontext enthält ausschließlich überlappende Stundenintervalle mit
echter UTC-Zeit. Für eine vollständige Vierstundenempfehlung müssen sie den
gesamten Abschnitt lückenlos abdecken. Keine nächstgelegene Stunde eines
anderen Tages verwenden. Stundenanfänge werden mit der vom Anbieter
dokumentierten Intervallsemantik interpretiert; ohne belegte Abdeckung gibt es
keine behauptete vollständige Vierstundenprognose.

Geplante Gültigkeit: erfolgreicher HA-Abruf höchstens 20 Minuten alt,
Kontextabschnitt noch aktuell und valide Felder. Ein UART-Replay aktualisiert
diese Frist nicht. Eine gegebenenfalls vorhandene Anbieter-Aktualisierungszeit
wird separat erhalten: Abrufzeit ist kein Beweis einer neuen Wetterberechnung.
Fehlen Forecastdaten, sind aktuelle Daten als ausdrücklich mit `Jetzt`
beschrifteter Fallback erlaubt: ebenfalls höchstens 20 Minuten seit erfolgreichem
HA-Abruf mit erhaltenem ursprünglichem Zeitstempel; ein bekanntes älteres
Beobachtungsdatum darf durch Abruf oder UART-Replay nicht verjüngt werden.
Fehlen auch diese gültigen Daten, gilt Motiv 20.

Jedes benötigte überlappende Intervall muss eine gültige Temperatur enthalten;
bei einer Lücke gibt es keine vollständige Vierstundenempfehlung, sondern den
beschrifteten Jetzt-Fallback oder Motiv 20. `T` ist dann das Minimum aller
Temperaturen im vollständigen Abschnitt. Gefühlte
Temperatur darf stattdessen nur genutzt werden, wenn sie für **alle** benötigten
Intervalle aus einer zuverlässigen Forecastquelle vorliegt. Sonst einheitlich
Lufttemperatur verwenden; niemals aktuelle Feuchte/Windwerte mit zukünftigen
Temperaturen mischen. Anzeige benennt bei Verwendung `Gefühlt`.

Niederschlag und Wind werden zusätzlich über den Abschnitt gesammelt. Fehlende
optionale Werte sind unbekannt, nicht Null. Einheiten werden in HA nach °C,
km/h und mm normalisiert; unbekannte Einheiten machen das betroffene Feld
ungültig. Alle folgenden Zahlen sind **vorgeschlagene Produktregeln**,
keine bereits aktiven Firmwarewerte oder Standards eines Wetterdienstes.

## Temperatur bestimmt die Basiskleidung

| Referenzbild | Exakte Grenze für T | Basisoutfit |
| --- | --- | --- |
| 01 Hitze | `T >= 28 °C` | Sehr leichtes Shirt, Shorts; Sonnenhut nur bei Sonne/teilweise Sonne im Abschnitt. |
| 02 Warm | `22 <= T < 28 °C` | T-Shirt und Shorts. |
| 03 Mild | `16 <= T < 22 °C` | Leichter Pullover, lange Hose. |
| 04 Kühl | `10 <= T < 16 °C` | Leichte Jacke, lange Hose. |
| 05 Frisch | `0 <= T < 10 °C` | Warme Jacke, lange Hose, geschlossene Schuhe. |
| 06 Frost | `T < 0 °C` | Winterjacke, Mütze, Handschuhe und Winterstiefel. |

Bei 24 °C und Nebel bleibt somit ein leichtes Outfit erhalten; ein sonniger
Tag mit −6 °C bekommt Winterkleidung. Aufeinanderfolgende gültige Datensätze
wenden diese Grenzen exakt an. Es gibt in V1 keine versteckte Temperatur-
Hysterese; die 15-minütige Aktualisierung begrenzt unnötige Wechsel.

## Wetterschutz, Motiv und Vorrang

Regenbedarf liegt vor, wenn mindestens ein Intervall `rainy`, `pouring`,
`lightning-rainy` oder `snowy-rainy` meldet. Alternativ reichen eine gültige
Niederschlagswahrscheinlichkeit von mindestens 50 % oder eine positive Menge
flüssigen Niederschlags. Bei `snowy`/`hail` werden unspezifische
Niederschlagsmengen nicht zu Regen umgedeutet. Fehlt die Phaseninformation,
lautet die zusätzliche Empfehlung neutral `Nässeschutz`; ein Regenereignis
oder dessen Intensität wird nicht behauptet. `liquid_rain` und
`wet_phase_unknown` sind deshalb getrennte Flags. Unbekannte Nässe wählt eine
wasserdichte Kleidungsschicht, aber kein Regensymbol und keine Regenanimation.

Windschutz gilt bei `windy`/`windy-variant`, Wind ab 20 km/h oder Böen ab
35 km/h. Diese Schwellen dienen der Outfitwahl und sind keine Warnschwellen.
Ein fehlender Windwert überschreibt keine vorhandene Wind-Condition.

Die Tabelle wird **von oben nach unten** angewendet. Wetterschutzflags bleiben
auch dann erhalten, wenn eine höher priorisierte Szene gewinnt. Ihre Reihenfolge
ist eine eindeutige Darstellungsregel, keine amtliche Gefahrenrangfolge.

| Rang | Bedingung | Referenzmotiv / Darstellung |
| --- | --- | --- |
| 1 | Kein zeitlich gültiger Datensatz, fehlende Temperatur oder keine interpretierbare Wetterinformation | **20 Keine Wetterdaten**, neutrale Figur, keine erfundene Empfehlung. Ein trotzdem gültiger Gewitter-/Hagelhinweis bleibt als separater Hinweis sichtbar. |
| 2 | `exceptional` | **19 Besondere Wetterlage**, neutrale Figur und `Vorhersage prüfen`; keine amtliche Warnung behaupten. |
| 3 | `hail` | **16 Hagel**, geschützte Szene und `Schutz suchen`; Kleidung weiterhin gemäß T. |
| 4 | `lightning-rainy` oder `lightning` zusammen mit belegtem flüssigem Regen | **18 Gewitter mit Regen**, geschützte Szene. |
| 5 | `lightning` ohne belegten flüssigen Regen | **17 Gewitter**, geschützte Szene und `Drinnen bleiben`; bei unbekannter Nässe zusätzlich neutraler Nässeschutz, kein Regenmotiv erfinden. |
| 6 | `snowy-rainy` oder Regen- und Schneezustände innerhalb des Abschnitts | **12 Schneeregen / wechselnder Niederschlag**, isolierende wasserdichte Schicht; bei zeitlich getrennten Zuständen explizit `Regen und Schnee`. |
| 7 | `snowy` | **13 Schnee**, thermisch passende Schneeschutzkleidung und griffige geschlossene Schuhe. |
| 8 | `pouring` | **11 Starker Regen**, Kapuze/Regenhose; leichte oder warme Unterschicht gemäß T. Eine hohe Wahrscheinlichkeit allein reicht hierfür nicht. |
| 9 | Regen-/Nässeschutzbedarf und `T >= 18 °C` | **09 Warmer Regen**, leichte wasserdichte Schicht. |
| 10 | Regen-/Nässeschutzbedarf und `5 <= T < 18 °C` | **10 Kühler Regen**, Regenschutz plus passende Wärmeschicht. |
| 11 | Regen-/Nässeschutzbedarf und `T < 5 °C` | **Zusätzliche Produktionsvariante `cold_rain`**, warm und wasserdicht. Keine Schneeflocken erfinden; die Vorlage 12 darf nicht unverändert als Regenbild dienen. |
| 12 | Windschutz und `T >= 10 °C` | **07 Wind**, winddichte Schicht entsprechend dem Temperaturband. |
| 13 | Windschutz und `T < 10 °C` | **08 Kalter Wind**, isolierter Windschutz; Frostzubehör bei T unter Null erhalten. |
| 14 | `fog` | **14 Nebel** als Sichtbarkeits-/Reflektorvariante der Temperaturbasis. |
| 15 | Aktuell gültiges `clear-night` im ersten relevanten Intervall und kein höherer Rang | **15 Klarer früher Morgen** als Nachtszene der Temperaturbasis. Vergangene Nachtstunden dürfen vormittags keinen Mond erzwingen. |
| 16 | Übrige bekannte Zustände, insbesondere `sunny`, `partlycloudy`, `cloudy` | **01–06** nach T, dazu passendes Wetterzeichen. |

Alle 15 Home-Assistant-Conditions sind damit abgedeckt. Nicht erkannte
Conditions werden nicht stillschweigend als Sonne oder trocken interpretiert.
Bei unvollständigen optionalen Daten darf eine belegte Teilinformation benutzt
werden; UI und Begründung zeigen die Einschränkung. Eine Regenwahrscheinlichkeit
von 60 % bedeutet ohne belegte flüssige Phase lediglich `Niederschlag möglich`,
nicht `Es regnet`; Kleidung und Hinweis sind entsprechend neutral anzupassen.

## Bildnummer ist nicht gleich fertiges Laufzeitbild

Die 20 bisherigen Bilder je Avatar zeigen **Beispielkombinationen**. Insbesondere
07–19 dürfen nicht allein anhand der Condition unverändert ausgewählt werden,
weil ihre Kleidung auf den Beispieltemperaturen basiert. Der Produktionsschlüssel
lautet daher mindestens:

```text
avatar_variant + thermal_band + protection + accessory_set
```

`protection` unterscheidet trocken, Wind, Regen, starken Regen und Schnee/Mix;
Regenbekleidung berücksichtigt zugleich Windschutz. Zubehör umfasst etwa Hut
oder Reflektor. Wettersymbol, Hinweistext und geschützte Szene werden getrennt
gewählt. Derselbe Resolver liefert Bildschlüssel, Referenzmotiv, Begründung,
Zeitraum und Datenmodus an beide Aufrufwege.

Vor der Implementierung müssen passende Einzelassets ohne eingebrannte Texte
und Wettersymbole exportiert werden. Beide Avatarfamilien erhalten denselben
Schlüsselsatz. Noch erforderliche Kombinationen sind insbesondere kalter Regen
ohne Schnee, warmer Starkregen, Frost mit Wind/Nässe, warmer Nebel/klare Nacht
und temperaturgerechte Gewitter-/Hagelkleidung. Die genaue Packgröße wird aus
der Regeltabelle und den unterstützten Kombinationen erzeugt, nicht auf die
40 Konzeptbilder begrenzt.

Fehlt ein kombiniertes Asset, bleibt die **thermisch richtige Basis** sichtbar,
dazu der explizite Wetterschutz-/Warnhinweis. Das ist ein dokumentierter
technischer Fallback, keine vollständig illustrierte Outfitdarstellung; die
Release-Abnahme verlangt vollständige Assets für alle vorgesehenen Kombinationen.

Beispiele zur späteren Resolver-Abnahme:

| Eingabe (gültiger Forecast) | Erwartete Auswahl, für beide Avatare identisch |
| --- | --- |
| Sonne, 32 °C, kein Regen/Wind | 01, leichtes Outfit mit Sonnenhut. |
| Sonne, 24 °C | 02, T-Shirt/Shorts. |
| Wolken, 18 °C | 03, Pullover/lange Hose. |
| Wolken, 12 °C | 04, leichte Jacke. |
| Sonne, 6 °C | 05, warme Jacke. |
| Sonne, −6 °C | 06, vollständiges Frostoutfit. |
| Sonne, 24 °C, Wind 20 km/h | 07, leichte Windschicht; kein Winteroutfit. |
| Wind, −3 °C | 08 plus Frostbasis einschließlich Handschuhen. |
| Regen, 21 °C | 09, dünner Regenschutz. |
| Regen, 10 °C | 10, Regen-/Wärmeschicht. |
| Regen, 2 °C | `cold_rain`, keine Schneeflocken. |
| Starker Regen, 26 °C | 11 mit leichtem Unterbau, nicht das warme 7-°C-Beispiel. |
| Schneeregen, 1 °C | 12, warm/wasserdicht. |
| Schnee, −2 °C | 13 mit Frostbasis. |
| Nebel, 24 °C | 14 mit leichter Basis/Reflektor; keine warme Jacke. |
| Klare Nacht, 23 °C | 15 mit leichtem Outfit; keine automatische 7-°C-Jacke. |
| Hagel und Gewitter, 4 °C | 16; Hinweis nennt beide Zustände. |
| Gewitter trocken, 22 °C | 17, geschützte Szene. |
| Gewitter mit Regen, 16 °C | 18, geschützte Szene mit Nässebedarf. |
| `exceptional`, 20 °C | 19; keine amtliche Warnung vortäuschen. |
| Keine Temperatur / veralteter Forecast ohne aktuellen Fallback | 20; niemals 0 °C als Ersatzwert. |
| Sonne 18 °C, Niederschlagswahrscheinlichkeit genau 50 %, Phase unbekannt | Schutzkleidung wie 09, aber neutrales `Nässeschutz` ohne Regensymbol; bei 49 % und ohne weitere Nässebelege 03. |
| Gültig jetzt 12 °C, Forecast fehlt | 04 mit Datenmodus `Jetzt`, keine Vierstundenbehauptung. |

## Vorhandene Architektur und erforderliche Änderungen

| Bereich | Bestehender Pfad / geplanter Eingriff |
| --- | --- |
| HA-Forecast | `custom_components/passion_wave/broker.py`, `_async_forecast_request`: stündliche Originalfelder erhalten, Einheiten/UTC normalisieren und separaten Avatar-Kontext ableiten. Der heutige Filter verwirft Wind/Böen. |
| Bridge | `esphome/dual-mcu-esp32-core.yaml`: versionierten Avatar-Kontext cachen/übertragen; existierenden Weather-/Forecastpfad kompatibel belassen. |
| UART | `esphome/dual_mcu_link.h`: zusätzlicher capability-verhandelter Kontextframe; festes bestehendes 42-Byte-Forecastformat nicht umdeuten. |
| S3-Resolver | Geplantes eigenes Modul `weather_avatar.h`: deterministische Datenprüfung, thermische Basis, Schutz/Referenzmotiv und Assetschlüssel; keine Netzwerkzugriffe. |
| Wetteransicht | `esphome/ui_next_framework.h`: Actionenum, `build_weather_`, Touch-Fallback und suspendierte Vollbildansicht. |
| Screensaver | `esphome/rotaryknob-s3-ui-core.yaml`: `show_weather_screensaver`, Rückkehr, `refresh_weather_screensaver`, `page_7`, 10-ms-Actiondispatcher und 1-s-Scheduler. |
| Einstellungen | Dieselbe S3-YAML: persistente Globals und Settingsliste; derzeit harte 12er-Fokusgrenzen durch eine gemeinsame Anzahl ersetzen. HA-Configure-Flow spiegelt denselben Zustand. |
| Bilddecoder | Vorhandenes Core-0-JPEG-Muster in `dual-mcu-s3-core.yaml` / `dual_mcu_radar_proxy.h` für begrenztes lokales Dekodieren adaptieren. |

Der bestehende S3-Forecast enthält nur Temperatur/Condition nahe 08/13/19/23 Uhr
ohne Slot-Zeitstempel. Der Bridgepfad fasst teilweise Hagel, Starkregen und
Schneeregen zu Regen zusammen, ersetzt fehlende Temperatur durch Null und
interpretiert Datum derzeit ohne zuverlässige RFC3339-Offsetbehandlung.
Diese verdichteten Werte reichen für die geplanten Regeln nicht aus.

Der neue `AvatarWeatherContext` braucht Schema/Sequenz, tatsächlichen
HA-Abrufzeitpunkt, optionalen Providerzeitpunkt, Bezugsintervall UTC,
Datenmodus `forecast | current | unavailable`, Temperaturminimum/-maximum mit
Gültigkeit, rohe Condition-Bitmaske, Condition des aktuellen ersten Intervalls,
maximale Niederschlagswahrscheinlichkeit, Nässe-/Phaseninformation sowie
Wind-/Böenmaxima mit eigenen Validitätsbits. Optional gefühlte Temperatur nur
bei passender Quelle. Wiederholte Übertragung behält Originalzeitstempel.
Ein nicht unterstützter Kontext führt nachvollziehbar zu Motiv 20, nicht zur
alten ungenauen Vierstundenableitung.

Der aktuelle Screensaver verlangt 100 % Akku, keine Musikwiedergabe und keinen
laufenden Timer; automatische Coveranzeige kann ihn ersetzen. Unter 100 %
greifen Display-Aus und auf Akku Deep Sleep. Die neue Morgenpolitik muss diese
Guards explizit integrieren. Ein bloßer Bildwechsel erfüllt 06–10 nicht.
Vor dem nächtlichen Deep Sleep ist zusätzlich zum bestehenden GPIO9-Wakeup ein
RTC-Timer bis zum nächsten **lokalen** 06-Uhr-Termin zu setzen. Kalender/DST
berechnen, nicht einfach 86.400 Sekunden addieren; nach Wake Uhrzeit neu prüfen.
Ohne gültige Zeit keine vorgetäuschte Zeitgarantie. Die beiden vorhandenen
Zeit-IDs sind HA-Zeitquellen, auch wenn eine `sntp_time` heißt.

## Speicher und Rendering

40 rohe 368×368-RGB565-Bilder benötigen bereits 10.833.920 Bytes; die
bestehenden 15 Wetterbilder weitere 4.062.720 Bytes. Weitere Kombinationen
vergrößern das Pack. Deshalb keine ungeprüfte Erweiterung aller Bilder als
kompilierte RGB565-Arrays im 16-MB-S3.

Vorgesehen sind firmwarelokale komprimierte JPEGs und begrenztes Dekodieren
nur bei geändertem Assetschlüssel. Native 368×368 Pixel mit vier Pixeln
Overscan bleiben erhalten; kein Skalieren zur Laufzeit. Zwei RGB565-Puffer
benötigen zusammen 541.696 Bytes (529 KiB), zusätzlich Decoder-/LVGL-Speicher.
Ein Decoderjob zur Zeit, letzter angeforderter Schlüssel gewinnt. Erst nach
erfolgreichem vollständigem Decode atomar umschalten; alten Puffer erst nach
LVGL-Freigabe wiederverwenden. Datenablauf darf kein altes Outfit als gültige
Empfehlung stehen lassen: dann neutrale lokale Fallbackansicht und Hinweis.

Das Produktionsmanifest führt pro Schlüssel Datei, Abmessungen, Bytezahl und
SHA-256. Build-Abnahme misst tatsächlich freie OTA-Partition und PSRAM-Spitzen
einschließlich Medien-/Radar-Dekoder. Die jetzigen Tafeln sind weder fertige
JPEG-Einzelassets noch ein nachgewiesenes Speicherbudget.

## Umsetzung und Abnahme

1. Regeln/Datenschema und reine Resolver-Logik mit Fällen und Grenzwerten absichern.
2. Beide vollständigen Assetfamilien ohne eingebrannte UI herstellen, Manifest
   prüfen und Decoder-/Speicherbudget messen.
3. Wetterkontext im HA-Broker und auf Bridge/S3 ergänzen; UTC, Einheiten,
   fehlende Felder, abgelaufene Daten und UART-Replay prüfen.
4. Persistente Auswahl, Avatar-Button und gemeinsame Vollbildansicht integrieren.
5. Morgenfenster mit Sleep/Wake, Coverpriorität, Alarmen und Rückkehrpfaden verbinden.
6. Passende lokale Integrations-, Bridge- und S3-Prüfungen gemäß
   [AGENTS](../AGENTS.md) sowie koordinierte Qualifizierung gemäß
   [Release-Runbook](release-runbook.md) ausführen; Hardware separat beobachten.

Erforderliche Hardwarefälle: 05:59:59/06:00/09:59:59/10:00; Boot um 07:30;
beide DST-Wechsel; Zeitsprung über eine Grenze; GPIO- und RTC-Wakeup;
Akku/extern versorgt; Playback; laufender und klingelnder Timer; Alarm;
manueller Aufruf außerhalb des Fensters/über 10:00; Variante wechseln und
Neustart; kein Durchklicken; Encoder verändert kein Gerät; Datenverlust;
JPEG-Fehler; schnelle Avatarwechsel; Speicherpeak und unveränderte OTA-Fähigkeit.
Die Augenfarben sind im echten 360-Pixel-Display zusätzlich visuell zu prüfen.

## Quellen und Zuständigkeiten

- [Bestehendes UI-Framework](ui-next-framework.md),
  [Konfigurationsmodell](configuration.md),
  [Bild-/Overscanvertrag](../assets/screensaver/README.md).
- [Home Assistant Weather](https://www.home-assistant.io/integrations/weather/):
  Conditionnamen und optionale Wetterattribute.
- [Home Assistant Weather entity](https://developers.home-assistant.io/docs/core/entity/weather/):
  Forecastfelder, UTC-Zeitstempel und Einheiten. Die hier festgelegten
  Outfitgrenzen stammen aus diesem Produktplan, nicht aus Home Assistant.
- [ESP-IDF Sleep Modes](https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/api-reference/system/sleep_modes.html):
  Timer-Wakeup zusätzlich zu externem Wakeup; konkrete Einbindung gegen die
  im Projekt gepinnte Toolchain prüfen.
