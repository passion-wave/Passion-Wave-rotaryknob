# Known issues

Stand: 2026-08-18. Offene Fehler behalten eine eindeutige Statuszeile;
Live-Nachweise und Restabnahme werden zusätzlich als prüfbare Tabellen geführt.

## Beta.19: Beobachtbarer Firmware-Updatepfad

### PW-UPD-008: Updatefenster blitzte nur, der Auftrag scheiterte später

Status: In Firmware Beta.19 und Integration Beta.19.1 korrigiert; automatisierte
Tests, alle sechs Firmware-Builds und die Live-Abnahme auf Marco bestanden.

Der Marco-Lauf am 2026-08-18 startete im Hintergrund, obwohl Home Assistant
`in_progress` sofort wieder auf `false` setzte. Nach fünf Minuten endete er mit
`Processor did not reconnect with firmware 3.0.0-beta.18`; Bridge und S3
blieben auf Beta.16. Zwei unabhängige Ursachen wurden nachgewiesen:

- `async_install` erzeugte einen losgelösten Task und kehrte sofort zurück;
  Home Assistant beendete deshalb seinen sichtbaren Installationszustand.
- Die interne ESPHome-Aktion rief nur `update.perform` auf. Dieses startet
  ausschließlich bei einem bereits als verfügbar bekannten Update; das
  HTTP-Manifest durfte jedoch bis zu sechs Stunden alt sein.

Beta.19 hält den HA-Service bis zum Abschluss offen und meldet kombinierten
Fortschritt. Jeder Prozessor erhält die Zielversion, führt zuerst
`update.check` aus und veröffentlicht Manifest-, OTA-Start-, Download- und
Fehlerzustände über die verschlüsselte Native API. Ein Manifestfehler,
abweichender Zielstand oder OTA-Fehlercode beendet den Auftrag unmittelbar mit
dieser Ursache. Eine vorhandene verborgene Alt-Update-Entität wird für den
Übergang reaktiviert und aktualisiert. Marcos sauberes Beta.16-Onboarding hatte
diese Entität nicht; Bridge und S3 wurden deshalb einmalig per ESPHome OTA auf
Beta.19 gehoben. Beta.19.1 meldet diesen Fall künftig sofort mit dem konkreten
Recoveryweg statt nach einem weiteren generischen Reconnect-Timeout.

Live-Abnahme am 2026-08-18: Der Home-Assistant-Service blieb sichtbar aktiv,
meldete `updating_bridge` bei 10 Prozent und wechselte nach dem Bridge-Reconnect
zu `updating_s3` bei 50 Prozent. Der ursprüngliche Service schloss erst, nachdem
beide Prozessoren Beta.19 meldeten. Endzustand: `phase=complete`,
`in_progress=false`, kein Ziel, kein Fehler und beide Transportdiagnosen
`idle`.

### PW-INT-009: Beta.19-Registry-Casing setzte den Eintrag auf `setup_retry`

Status: In Integration Beta.19.1 korrigiert und auf Marco live nachgetestet.

Beta.16 registrierte die S3-Vertragstexte als `Rotaryknob …`, Beta.19 meldet
`RotaryKnob …`. Home Assistant behandelt `original_name` case-sensitiv; ein
Reload nach dem Firmwarewechsel fand die Zieltexte deshalb nicht. Beta.19.1
normalisiert ausschließlich diese beiden historischen Präfixvarianten in
Config Flow, Migration und Laufzeitauflösung. Zusätzlich ist der
Systemstatus-Callback jetzt als Event-Loop-Callback markiert, sodass Home
Assistant keine thread-unsichere `async_write_ha_state`-Warnung mehr erzeugt.

## Beta.18: Start- und Medien-Runtime

### PW-UI-004: Sichtbarer Titel blieb auf „Keine Wiedergabe“

Status: In Beta.18 im Quellcode korrigiert; automatisierte Vertrags- und
Konfigurationsprüfung bestanden, physische Anzeigeabnahme nach OTA ausstehend.

Die Live-Diagnose am 2026-08-18 zeigte eine eindeutige Trennung zwischen
Transport und Darstellung. Der in Home Assistant ausgewählte Player spielte
und meldete aktuelle Titel. PassionWave, Bridge und S3 führten denselben
autoritativen Zustand einschließlich richtigem Titel und Interpreten. Das
sichtbare LVGL-Titellabel blieb dennoch beim Fallback `Keine Wiedergabe`.

Zwei Bedingungen konnten den Fehler stabil halten:

- eine idempotente Wiederholung des bereits ausgewählten Player-Ziels leerte
  den Titelcache nach einem gültigen Runtime-Snapshot;
- ein über UART eingetroffener `MEDIA_TEXT`-Frame aktualisierte zwar Cache und
  Diagnoseentität, erzwang aber kein sofortiges LVGL-Rendering.

Beta.18 ignoriert identische Zielschreibvorgänge, ordnet die periodische
Ziel-/Runtime-Synchronisation deterministisch und rendert nach
`RUNTIME_STATE` sowie `MEDIA_TEXT` sofort neu. `RotaryKnob Rendered Media
Title` liest den tatsächlich sichtbaren LVGL-Text zurück. Bei Zustand
`playing` ohne Titel fordert der S3 nach zehn Sekunden erneut einen kompletten
Snapshot an.

Physisches Abnahmekriterium: Während auf dem ausgewählten Home-Assistant-
Player mehrere Titel wechseln, müssen `Media Runtime Title`, `Rendered Media
Title` und die sichtbare Anzeige ohne dauerhaften Fallback übereinstimmen.

### PW-BOOT-001: Uhrzeit und Startdaten erschienen erst nach über 30 Sekunden

Status: In Beta.18 im Quellcode korrigiert; messbare physische Kaltstartabnahme
nach OTA ausstehend.

Die Bridge sendete ihren vollständigen HELLO-Snapshot sofort, die aktuelle
Home-Assistant-Zeit jedoch nur über ein separates zehnsekündiges
Wartungsintervall. Bei asynchronen API- und UART-Reconnects konnte sich die
sichtbare Bereitschaft deshalb über mehrere Intervalle ziehen; der
Screensaver erhielt die Daten häufig erst später und verdeckte damit die
eigentliche Startverzögerung.

Beta.18 stellt `TIME_STATE` an den Anfang jedes Bridge-Snapshots und ergänzt
`RotaryKnob UI Ready Time`, `RotaryKnob Clock Ready Time` und `RotaryKnob UI
Startup Status`. Damit sind LVGL-Bereitschaft und erste gültige Uhrzeit
getrennt messbar. Ein unvollständiger Runtime-Titel besitzt zusätzlich einen
eigenen Snapshot-Recovery-Pfad.

Physisches Abnahmekriterium: Kaltstart von Bridge und S3, anschließend die
beiden Ready-Zeiten protokollieren. Uhrzeit und vorhandener aktueller Titel
müssen auf der normalen UI vor Ablauf des 30-Sekunden-Screensaver-Timeouts
sichtbar sein.

## Beta.16: Konsolidierter Updatevertrag

Status: Automatisierte Tests, alle sechs Firmware-Builds und sämtliche
manuellen Beta.16-Vertragsprüfungen bestanden. Marco und Timo wurden sauber
neu angelegt, zeigen die lokale Versionskombination Beta.16/Beta.16/Beta.16.5
und besitzen jeweils genau ein konsolidiertes Firmwareupdate.

- Neue Config Entries verwenden ausschließlich `rotaryknob_<S3-MAC>` als
  Produktidentität. Legacy-Einträge werden nicht migriert und dürfen für den
  Abnahmetest neu angelegt werden.
- S3 und Bridge besitzen interne OTA-Aktionen; nur die PassionWave-Integration
  erzeugt eine sichtbare Firmwareentität.
- Der Auftrag bleibt bei fehlendem Prozessor bis zu 24 Stunden gespeichert und
  führt Bridge → Reconnect → S3 → Reconnect aus.
- Die Settings-Seite zeigt S3-, Bridge- und Integrationsversion über den
  versionierten UART-Vertrag `VERSION_STATE`.

Manuelle Release-Gates:

| Schritt | Erwartung | Status |
| --- | --- | --- |
| M01 Integration installieren | PassionWave meldet Beta.16 ohne Setupfehler. | Beta.16.5 bestanden |
| M02 Marco aktualisieren | Eine sichtbare Firmwareaktion; beide MCU Beta.16. | Bestanden |
| M03 Timo im Schlafzustand anstoßen | Auftrag wartet und setzt nach Aufwecken fort. | Kontrollierter Offline-/Neustarttest bestanden |
| M04 Settings prüfen | S3/Bridge zeigen Beta.16, HA zeigt Beta.16.5. | Marco und Timo bestanden |
| M05 Neu-Onboarding | Marco/Timo erhalten ihre eigene S3-basierte Identität. | Bestanden: `…a142a4` / `…a13c8c` |
| M06 Neustart/Recovery | Wartender Auftrag bleibt nach HA-Neustart erhalten. | Bestanden im kontrollierten Timo-Offlinetest |

### PW-UPD-006: Erfolgreicher Flash blieb als fehlgeschlagener Auftrag stehen

Status: In Integration Beta.16.2 korrigiert und physisch bestanden.

Beim Marco-Lauf am 2026-08-17 installierten Bridge und S3 nachweislich
Firmware `3.0.0-beta.17`. Der S3-Transport meldete währenddessen jedoch
`Update installation already in progress`. Beta.16.1 behandelte diese
Rückmeldung sofort als Fehler, obwohl der bereits angenommene Flash danach
erfolgreich neu startete. Dadurch zeigte die konsolidierte Entität korrekt
beide installierten Versionen, behielt aber irrtümlich Phase `failed`, Ziel
Beta.16 und den Transportfehler.

Beta.16.2 wartet bei genau diesem ESPHome-Zustand weiter auf den verifizierten
Reconnect. Zusätzlich gleicht sie gespeicherte Aufträge mit den realen
Geräteversionen ab und entfernt einen überholten Fehler automatisch, sobald
beide Prozessoren das Ziel ausführen. Die Regression ist auf Home Assistant
2026.7.4 und 2026.8.2 in insgesamt 53 Tests plus vier Subtests abgedeckt.

Live-Retest am 2026-08-17 nach Installation und Home-Assistant-Neustart:
Marcos gespeicherter Fehler wurde selbstständig entfernt, die Phase steht auf
`complete`, Ziel und Fehler sind leer, und Bridge sowie S3 melden weiterhin
Beta.16.

### PW-UPD-007: Bridge-Reconnect brach an Versionsmetadaten ab

Status: In Integration Beta.16.3 korrigiert und physisch bestanden.

Timos S3 wachte vor dem geplanten Offline-Klick wieder auf. Der Auftrag
aktualisierte daraufhin die Bridge erfolgreich von Beta.15 auf Beta.16. Nach
dem verifizierten Firmware-Reconnect lud die Integration den ESPHome-Eintrag
neu und rief die Aktion für die lokale HA-Versionsanzeige sofort auf. Obwohl
die Aktion bereits registriert war, war die API-Verbindung noch nicht wieder
bereit. Der reine Metadatenfehler beendete den Auftrag fälschlich vor dem
S3-Schritt; Timo steht deshalb kontrolliert auf Bridge Beta.16 und S3 Beta.15.

Beta.16.3 wiederholt die Metadatenübertragung nach dem Reload bis zu 60
Sekunden. Bleibt die optionale Anzeigeübertragung unerreichbar, läuft die über
die realen Prozessorversionen abgesicherte Firmwaresequenz trotzdem weiter.
Zwei Regressionstests decken erfolgreichen Retry und nicht blockierenden
Timeout ab; insgesamt bestehen 55 Tests plus vier Subtests auf beiden
unterstützten Home-Assistant-Versionen.

Der anschließende Timo-Retest bestand vollständig: Ein bei deaktiviertem S3-
ESPHome-Eintrag gestarteter Auftrag blieb in `waiting_for_devices`, überlebte
einen Home-Assistant-Neustart und setzte nach Aktivierung automatisch beim
S3-Schritt fort. Bridge und S3 meldeten danach Beta.16, Phase `complete`, kein
Ziel und keinen Fehler. Die lokale Settings-Seite zeigte S3 und Bridge
Beta.16 sowie HA Beta.16.3.

### PW-HA-012: Discovery-Flow blockierte manuelles Neu-Onboarding

Status: In Integration Beta.16.4 korrigiert und physisch bestanden.

Beim sauberen Neuaufbau wurde die historische Fehlidentität sichtbar: Timos
Legacy-PassionWave-Eintrag trug Marcos S3-Produkt-ID `…a142a4`. Nach dem
planmäßigen Löschen beider logischen Einträge waren keine Produkt-Config-
Entries mehr vorhanden. Home Assistant hielt jedoch weiterhin je einen
Zeroconf-Discovery-Flow für `a142a4` und `a13c8c` offen. Der explizite
Benutzerflow erreichte das korrekte Verbindungsformular, kollidierte aber nach
Submit mit dem gleichzeitigen Marco-Discovery-Flow und brach mit
`already_in_progress` ab.

Beta.16.4 beendet vor dem Setzen der S3-basierten Produkt-ID ausschließlich
den fremden Discovery-Flow mit derselben ID. Der aktive Benutzerflow und die
Discovery des anderen RotaryKnobs bleiben unberührt. Die irreführende Meldung
spricht nun vom bereits konfigurierten RotaryKnob statt von einer Bridge. Ein
Regressionstest deckt die selektive Flow-Auflösung ab; insgesamt bestehen 56
Tests plus vier Subtests auf beiden unterstützten HA-Versionen.

Der physische Marco-Retest am 2026-08-17 bestand: Das manuelle Onboarding
erreichte trotz paralleler Discovery die Lichtauswahl und erzeugte den
geladenen Eintrag mit der korrekten S3-Identität `…a142a4`.

### PW-HA-013: „Nicht belegt“ wurde als fehlendes Pflichtfeld abgewiesen

Status: In Integration Beta.16.5 korrigiert und physisch bestanden.

Beim Timo-Onboarding erreichte Beta.16.4 korrekt die Lichtauswahl. Position 4
sollte mit `Nicht belegt` leer bleiben. Das Schema markierte jedoch alle vier
Selektoren als Pflichtfelder, während der Wert für `Nicht belegt` die leere
Zeichenkette ist. Die Home-Assistant-Oberfläche verwarf das Formular deshalb
vor dem Config Flow mit `Not all required fields are filled in.`

Beta.16.5 kennzeichnet die vier Selektoren als optional und ergänzt fehlende
Positionen weiterhin deterministisch mit der leeren Zeichenkette. Eine
Regression prüft sowohl die optionalen Formularmarker als auch alle vier
normalisierten Ergebniswerte.

Der physische Timo-Retest am 2026-08-17 bestand. Das Onboarding erzeugte die
korrekte Produktidentität `…a13c8c`; Positionen 1 bis 3 wurden auf die
vorgesehenen Lichter übertragen und Position 4 blieb leer. Marco und Timo
zeigen jeweils genau eine Firmwareentität mit Bridge/S3 Beta.16, ohne Ziel,
Warteschlange oder Fehler.

## Beta.15: Responsive Power Runtime

Status: Release-Kandidat für den ausschließlich über Home Assistant geführten
Kundenupdatepfad. Automatisierte Builds und Prüfungen sind verbindlich;
physische Installation, Strommessung und Langzeittest werden nicht vorweg als
bestanden dokumentiert.

- Factory-, Timo- und Marco-Profile aktivieren dieselbe verbundene
  Modem-Sleep-Policy auf Akku.
- Externe Versorgung, Bedienung und laufende Asset-Transfers halten beide
  Prozessoren im responsiven WLAN-Modus.
- Das kombinierte Update bleibt Bridge → Reconnect → S3 → Reconnect.

### PW-UI-004: Medien-Startfehler kann Screensaver blockieren

Status: Offen und in Beta.15 bewusst nicht geändert.

Live-Diagnose am 2026-08-14 auf Timo: Akku 100 %, `Wach halten` aus,
Screensaver-Verzögerung 30 Sekunden und Medienzustand `idle`; gleichzeitig
meldete der S3 `Fehler kind=5 index=0 code=3 match=1`. Der passende Fehlerpfad
beendet den Ladevorgang, lässt den Medien-Picker aber offen. Da der
Screensaver nur bei geschlossenem Picker startet, bleibt er bis zum manuellen
Schließen blockiert. Eine spätere Korrektur muss Fehlerfeedback und
Idle-Verhalten gemeinsam festlegen.

## Beta.14: konsolidierter Kundenstand

Status: Quellstand, automatisierte Prüfungen und beide öffentlichen
Firmware-Builds bestanden. Die physische Beta.14-Abnahme folgt nach der
Veröffentlichung über das kombinierte Home-Assistant-Update.

- Im normalen PassionWave-Gerät bleiben nur kombiniertes Firmwareupdate,
  `Systemproblem` und `Supportdiagnose` sichtbar.
- Bestehende technische ESPHome-Entities werden bei der einmaligen
  Config-Entry-Migration deaktiviert; notwendige Transportentities bleiben
  intern aktiviert und verborgen.
- Media- und Lichtänderungen werden sofort ereignisbasiert übertragen. Ohne
  Ereignis senden Integration, Bridge und S3 spätestens nach 15 Minuten einen
  aktuellen autoritativen Snapshot.
- `Supportdiagnose` schaltet die hochfrequente Diagnose auf S3 und Bridge
  gemeinsam. Das ist kein normaler Betriebsmodus und muss nach einer
  Fehleraufzeichnung wieder ausgeschaltet werden.
- Home-Assistant-Integrationstests: 41 Tests plus vier Subtests bestanden.
  Managed S3 und Bridge wurden mit ESPHome 2026.7.0 validiert; der öffentliche
  koordinierte Factory-Build wurde erfolgreich erzeugt.

Restprüfung nach Installation: pro Gerät einen Zustandswechsel sofort
bestätigen, danach ohne weitere Aktion den 15-Minuten-Snapshot im
Supportprotokoll nachweisen, Supportdiagnose ein/aus testen und kontrollieren,
dass das Kundengerät keine technischen Entity-Listen mehr zeigt.

Live-Abnahme 2026-08-05: HACS installierte die Integration
`v3.0.0-beta.14`; beide PassionWave Config Entries wurden nach gültigem
Konfigurationscheck und Home-Assistant-Neustart geladen. Beim ersten
Updateversuch verwiesen die Website-Manifeste auf GitHub-Release-Assets mit
Weiterleitung. Marcos koordinierter Updater brach deshalb nach fünf Minuten
kontrolliert in der Bridge-Phase ab, ohne Bridge oder S3 zu verändern. Die
vier bereits geprüften Binärdateien wurden anschließend in den öffentlichen
unveränderlichen Tagpfad aufgenommen und die Website-Manifeste auf direkte
CORS-fähige Raw-URLs umgestellt. Alle vier Ziele antworteten danach mit HTTP
200 und exakt den veröffentlichten Dateigrößen.

Nach erneutem Katalogabgleich aktualisierte Home Assistant Marco und Timo
jeweils in der Reihenfolge Bridge → verifizierter Reconnect → S3. Beide
logischen Updateentities und alle vier verborgenen Transportentities melden
installiert und aktuell `3.0.0-beta.14`; beide logischen Phasen stehen auf
`complete`. `Systemstatus` blieb bei beiden Geräten `off`. Die beiden
`Supportdiagnose`-Schalter waren nach gezieltem Reload der S3 Config Entries
verfügbar, ließen sich jeweils erfolgreich ein- und wieder ausschalten und
stehen abschließend `off`.

Live-Stand 2026-08-03: Home Assistant wurde mit gültiger Konfiguration neu
gestartet und beide PassionWave Config Entries auf Registry-Migration V4
angehoben. Beim erreichbaren Gerät wurden Bridge und S3 aus frisch erzeugten
Managed-Binaries in der Reihenfolge Bridge → S3 installiert. Home Assistant
registrierte danach alle vier Supportaktionen; `Supportdiagnose` wurde
erfolgreich ein- und wieder ausgeschaltet, `Systemstatus` blieb `off`. Alle 127
nativen ESPHome-Entities dieses Paars sind verborgen, 96 technische Entities
zusätzlich deaktiviert; sichtbar bleiben am logischen Gerät nur Firmware,
Systemstatus und Supportdiagnose.

Am 2026-08-04 wurde auch das zweite Gerät aufgeweckt und aus den zuvor frisch
kompilierten Managed-Binaries in der Reihenfolge Bridge → Reconnect → S3
aktualisiert. Beide OTAs waren erfolgreich, beide Prozessoren meldeten sich per
API zurück und Home Assistant registrierte die vier Supportaktionen. Der
kombinierte Systemstatus blieb `off` mit `s3_connected=true` und
`bridge_connected=true`; Supportdiagnose ließ sich erfolgreich ein- und wieder
ausschalten. Alle 126 nativen ESPHome-Entities sind verborgen, 95 technische
Entities zusätzlich deaktiviert. Der kombinierte Updater wurde außerdem gegen
eine noch ältere öffentliche Releasequelle gehärtet: Bei installiertem Beta.13
und veröffentlichtem Beta.12 bietet er keinen Downgrade mehr an. Nach dem
abschließenden Home-Assistant-Neustart melden beide logischen Firmwareentities
`off`, installiert und aktuell jeweils `3.0.0-beta.13`. Der zeitbasierte
15-Minuten-Nachweis bleibt als separater Langzeittest offen.

## Live-Verifikation Beta.12

Die folgenden Ergebnisse wurden am 2026-08-01 für den Testaufbau mit zwei in
der PassionWave Integration gelisteten RotaryKnobs gemeldet. Wo nicht
ausdrücklich getrennt geprüft, müssen sie noch pro Gerät wiederholt werden.
„Bestanden“ bedeutet einen erfolgreichen Funktionstest, nicht automatisch
einen bestandenen Dauer-, Neustart- oder Fehlerfalltest.

| Funktion | Ergebnis | Nachweis / Restpunkt |
| --- | --- | --- |
| PassionWave-Gerätezuordnung | Bestanden | Beide logischen RotaryKnobs werden von der Integration gelistet. |
| Firmwaregeneration | Vorläufig bestanden | Beide Geräte zeigen Beta.12; die vier technischen Endpoint-Versionen noch exakt gegenprüfen. |
| Playlist-Aufruf | Teilweise bestanden | Playlist-Katalog und Start funktionieren. Die korrigierte Titelliste liefert im Service-Test Seiten mit 16 Einträgen; physische Popup-Prüfung offen. |
| Radio-/Podcast-Katalog | Bestanden | Nach dem Bridge-Recovery-Fix melden beide S3 `P 64 · R 3 · O 40`; der Nutzer bestätigte Radio und Podcast anschließend physisch. |
| Cover-Screensaver | Auf `a13c8c` bestanden | Erstes Vollbild-Cover und mehrere nachfolgende Coverwechsel erscheinen nach dem LVGL-Cache-Fix korrekt; Wiederholung auf dem zweiten Gerät offen. |
| Dimmung auf der Medienseite | Bestanden | Dimmung setzt während der Medienansicht ein. |
| Lichtsteuerung | Bestanden | Grundsteuerung und lokaler Leuchtenwechsel über den Namen sind auf Timos Gerät physisch bestätigt; externe Zustandsänderungen sowie Hue-/WLED-Details noch regressieren. |
| Wetter | Bestanden mit Sichtprüfung | Anzeige wirkt aktuell; Werte und Forecast noch einmal direkt mit der gewählten HA-Wetterentity vergleichen. |
| Wetterradar | Bestanden | Radarbild wird geladen. |
| Haus-Floorplan | Bestanden | Floorplan wird unter Settings/Haus geladen. |

### Laufender V02/V03-Test: Gerät 2

Live-Abgleich am 2026-08-01 um 15:14 Uhr (Europe/Berlin): Home Assistant
erhielt einen frischen, in sich konsistenten Medienzustand. Beide MCU-
Verbindungen waren online und die Bridge bestätigte die Übernahme der
Cover-URL. Auf dem Display blieben Titel und Interpret jedoch auf den
Fallbackwerten `Keine Wiedergabe` und `Home Assistant`; auch das Vollbild-Cover
erschien nicht.

| Prüfpunkt | Beobachtung | Bewertung |
| --- | --- | --- |
| Runtime-State | `playing` | Bestanden |
| Runtime-Titel / Interpret | `Celebrate The Summer` / `Gregor Le Dahl` | Bestanden |
| Runtime-Cover-URL | Nicht leere HTTP-URL des Image-Proxys | Bestanden |
| S3- und Bridge-Verbindung | Beide online | Bestanden |
| Bridge-Cover-Übergabe | `S3 hat Cover-URL übernommen` | Bestanden |
| Sichtbarer Medieninhalt | Weiterhin `Keine Wiedergabe` / `Home Assistant` | Fehlgeschlagen |
| Vollbild-Cover nach Ruhezeit | Erscheint nicht | Fehlgeschlagen |
| S3-Media-Debug | Aus; Status blieb seit Boot bei `boot reset=poweron` | Kein Decoder-Nachweis |

Beim Wiederholungslauf mit aktiviertem Media-Debug erschienen Titel und
Interpret kurz korrekt und sprangen danach wieder auf `Keine Wiedergabe` /
`Home Assistant`. Der letzte Debugstatus meldete
`esp_cover_update_deferred item=empty type=media_image_url`. Damit ist ein
grundsätzlicher Empfangs- oder LVGL-Fehler ausgeschlossen: Nach dem Entfernen
der direkten Subscriptions blieb in der gestuften Beta.12-Kompatibilität noch
ein zweiter Löschpfad bestehen. Die alte Integration sendet Titel, Interpret
und Friendly Name direkt an den S3, enthält diese Felder aber nicht in ihrer
autoritativen Bridge-Aktion. Der periodische Bridge-Snapshot sendete deshalb
kurz darauf seine noch leeren Präsentationsfelder und überschrieb den bereits
korrekt gerenderten S3-Cache.

V02 ist damit fehlgeschlagen. Die Datenbeschaffung in Home Assistant und die
Bridge-Übergabe sind nachgewiesen. Die Autoritätskollision ist im Quellstand
behoben. Die Bridge des Testgeräts wurde anschließend erfolgreich OTA mit dem
rückwärtskompatiblen Fix aktualisiert und meldete sich neu an. Im danach
beobachteten Ruhezustand `idle` blieben die zuletzt empfangenen Metadaten
`Rave Hard (Braveheart)` / `Gregor Le Dahl` erhalten; ein laufender Titel lag
zu diesem Zeitpunkt nicht an. Dieser erste Zwischenstand genügte deshalb noch
nicht als physischer Wiedergabe-Nachweis. Beim nächsten Lauf mit `Photograph` /
`Ed Sheeran` waren die vier Runtime-Diagnosen erneut korrekt (`playing`, Titel,
Interpret und nicht leere Image-Proxy-URL), während die sichtbare Anzeige
wieder zurücksprang. Der nun korrigierte Snapshot sendet
Präsentationsfelder erst, nachdem die aktuelle Integration sie ausdrücklich
als autoritativ geliefert hat. Dieser zweite Bridge-Fix wurde nach dem
vollständigen Systemneustart erneut erfolgreich per OTA auf `918d3c`
installiert und im unten protokollierten 15-Sekunden-Retest bestätigt.

Der fehlende Cover-Screensaver besitzt zusätzlich eine unabhängige Ursache auf
dem noch installierten S3-Stand: Der Live-Debug meldete
`esp_cover_update_skip_heap ... heap=1915044`. Die alte 2-MiB-Schranke
verhindert damit jeden Cover-Decode trotz korrekter URL. Im konsolidierten
S3-Quellstand ist die Schranke auf 1,25 MiB abgesenkt und der autoritative
`RUNTIME_STATE`-Handler plant den Cover-Screensaver beim Wechsel auf `playing`
nach zehn Sekunden ein. Dieser S3-Fix ist gebaut und automatisiert getestet,
aber bewusst noch nicht einzeln OTA installiert; er wird zusammen mit der
aktuellen Integration ausgerollt, damit kein gemischter Runtime-Vertrag
entsteht.

Nach dem vollständigen Systemneustart konvergierten Home Assistant, Bridge und
S3 wieder selbstständig. Bridge und S3 meldeten dieselbe neue Runtime-Session
und Sequenz (`R253166883:21`), der S3-Link stand auf `verbunden` und sowohl
UART-Protokollfehler als auch Encoder-Queue-Overflows blieben bei null. Im
Ruhezustand `idle` blieben `Photograph` / `Ed Sheeran` erhalten; das ist ein
positiver Teilnachweis für V08 und den neuen Metadaten-Schutz, ersetzt aber
nicht den noch ausstehenden 15-Sekunden-Test bei laufender Wiedergabe. Der
Radar-Decoder war nach dem Neustart erfolgreich (`Asset aktiv: radar`), der
Coverpfad blieb dagegen im Retry-Backoff.

Der anschließende Wiedergabe-Retest um 17:38 Uhr bestand den
Metadaten-Teil von V02: Der Nutzer bestätigte, dass der sichtbare Titel stehen
blieb. Home Assistant meldete gleichzeitig `playing`, `Love Yourself` /
`Conor Maynard`, eine nicht leere Cover-URL sowie auf Bridge und S3 exakt
`R253166883:120 V50 L0000`; die UART-Protokollfehler blieben bei null. Damit
ist das Zurückspringen auf `Keine Wiedergabe` auf `918d3c` behoben. Der
Cover-Teil von V02/V03 bleibt getrennt fehlgeschlagen: URL-Auflösung und
UART-Übernahme waren erfolgreich, der installierte S3 meldete weiterhin
`esp_cover_update_failed_backoff` bei rund 1,71 MiB freiem Heap.

Beim anschließenden koordinierten Update wurde eine falsche Versionsannahme
korrigiert: Home Assistant meldete den S3 `a13c8c` noch als
`3.0.0-beta.10`, während die Bridge bereits Beta.12 ausführte. Die drei
abweichenden Integrationsdateien wurden auf den autoritativen Snapshot-Vertrag
synchronisiert, Home Assistant kontrolliert neu gestartet und erst nach
identischer Bridge-/S3-Runtime-Session der neu gebaute S3 per OTA installiert.
Danach meldete der S3 Beta.12, `playing`, `Love Yourself` / `Conor Maynard`,
eine auf 256 Pixel normalisierte Cover-URL und erstmals einen erfolgreichen
Cover-Transfer samt Decode (`Asset aktiv: cover decode=335ms`). Der Nutzer
bestätigte anschließend die sichtbare Vollbilddarstellung; V02/V03 sind damit
auf `a13c8c` bestanden. Ein einzelner
Inter-MCU-Protokollfehler trat beim S3-OTA-Neustart auf und ist auf weiteres
Wachstum zu beobachten.

Beim erweiterten Titelwechseltest trat danach eine zweite, unabhängige
Cover-Regression auf: Das erste Cover wurde sichtbar, nach dem Wechsel auf
weitere Titel blieb die Vollbildfläche jedoch schwarz. Runtime-State, Titel,
Interpret und Cover-URL waren korrekt; Bridge und S3 hatten dieselbe
Runtime-Sequenz. Der S3 lud jeweils 25.244 Byte und meldete den Decode als
erfolgreich. Auch das direkt abgerufene 256×256-JPEG war gültig und nicht
schwarz. Ursache war damit der LVGL-Bildcache: Die `RuntimeImage` behält beim
Coverwechsel dieselbe Descriptor-Adresse, während ihr PSRAM-Pixelpuffer ersetzt
wird. LVGL konnte deshalb einen Draw-Cache-Eintrag des bereits freigegebenen
Puffers wiederverwenden. Der S3 verwirft den betroffenen Cache-Eintrag nun vor
dem Pufferwechsel und erneut nach erfolgreichem Decode. Der korrigierte
Beta.12-Build wurde am 2026-08-01 erfolgreich per OTA auf `a13c8c` installiert;
nach dem Neustart sind beide MCU-Stände synchron, der Cover-Transfer ist aktiv
und der Inter-MCU-Protokollfehlerzähler steht bei null. Der physische Retest mit
mehreren aufeinanderfolgenden Titelwechseln zeigte anschließend jedes Cover
korrekt. V02/V03 sind damit einschließlich wiederholter Coverwechsel auf
`a13c8c` bestanden.

Die zwischenzeitliche Diagnose `Asset-Fehler radar code=2 bytes=0` auf dem
Testgerät ist ein separater HTTP-Verbindungsfehler des Radar-Abrufs und kein
Beleg für einen defekten Cover-Decoder. Das zweite Gerät dekodierte im selben
Stand ein Cover erfolgreich (`Asset aktiv: cover`). Radar und Cover werden in
V03/V06 deshalb getrennt bewertet.

## Verbleibende Gesamtfunktionsprüfung

Die Blöcke pro physischem RotaryKnob getrennt protokollieren. Bei einem Fehler
Gerät, Uhrzeit, aktive Seite und die letzten 30 Sekunden der S3- und
Bridge-Logs festhalten.

| ID | Prüfung | Sollzustand |
| --- | --- | --- |
| V01 | In PassionWave und den beiden verborgenen ESPHome-Updatequellen die installierte Version prüfen. | Integration, S3 und Bridge melden je Gerät exakt `3.0.0-beta.15`; kein gemischtes Prozessorpaar. |
| V02 | Einen Titel mit bekanntem Cover starten und 15 Sekunden weder Touch noch Encoder bedienen. | Runtime-State ist `playing`, Cover-URL ist nicht leer und das Vollbild-Cover erscheint nach mindestens 10 Sekunden Ruhe. |
| V03 | Während V02 die Diagnosen `ESP32 Media Cover URL Status`, `ESP32 Media Cover Proxy Status`, `RotaryKnob Media Runtime Cover URL` und `scrollwheel Media Debug Status` beobachten. | URL meldet `resolved=... http`, Proxy bestätigt die S3-Übernahme und der S3-Decoder endet ohne Backoff/Fehler. |
| V04 | Playlist über mindestens drei Seitengrenzen scrollen, Titel starten und anschließend Vor/Zurück, Pause und Lautstärke testen. | Keine Lücke oder Doppelladung; genau ein Befehl je Eingabe; Lautstärke springt nicht auf einen alten Wert zurück. |
| V05 | Alle vier Lichtplätze testen, danach dieselben Lichter extern in HA ändern sowie Hue-Szenen/WLED-Presets öffnen. | RotaryKnob folgt externen Änderungen; Detailkataloge passen zum gewählten Slot und enthalten keine alten Einträge. |
| V06 | Temperatur, Wetterzustand und zwei Forecast-Tage direkt mit der konfigurierten `weather.*`-Entity vergleichen; Radar dreimal neu laden. | Werte und Zustände stimmen überein; Radar lädt wiederholt ohne steigende UART-Fehler. |
| V07 | Floorplan-Quelle ändern bzw. Revision erhöhen und Haus erneut öffnen. | Das neue 360×360-PNG erscheint; kein dauerhaftes Cachebild und kein `Hausbild fehlt`. |
| V08 | Jeweils nur Bridge, nur S3 und danach Home Assistant neu starten. | Lokale UI bleibt bedienbar; Link, Medien-, Licht-, Wetter- und Assetzustände konvergieren selbstständig. |
| V09 | WLAN kurz trennen und wiederherstellen. | Kein ungeplanter MCU-Neustart; beide API-Verbindungen und der vollständige Snapshot kehren zurück. |
| V10 | Encoder je 40 langsame Rastungen und zehn schnelle Drehungen pro Richtung testen. | `EC1 Encoder Read Errors`, beide Protokollfehlerzähler und Queue-Overflows bleiben null; Richtung und Schritte stimmen. |
| V11 | Navigation, Touch, Haptik, Timer, Wecker, Wetter-Screensaver, Medien-Cover, Dimmen, Display-Aus und Aufwecken prüfen. | Keine falsche Seite, kein Touch-Durchgriff; jede Schutzstufe startet und endet mit korrekter Helligkeit. |
| V12 | Kombiniertes Geräteupdate ohne Installation öffnen und Recovery-Transporte kontrollieren. | Eine sichtbare PassionWave-Firmwareentität sowie zwei verborgene, erreichbare Prozessorquellen pro Gerät; Reihenfolge Bridge → S3 dokumentiert. |
| V13 | 24 Stunden gemischten Betrieb, danach optional bis 72 Stunden fortsetzen. | Kein Reset, keine wachsenden Fehlerzähler, kein Speicher-/UI-Abbau und keine dauerhaft verlorene Verbindung. |

### Laufender V13-Dauertest: beide Geräte

Der 24-Stunden-Lauf startete am 2026-08-01 um 18:12 Uhr (Europe/Berlin) und
endet regulär am 2026-08-02 um 18:12 Uhr. Vor dem Start wurde das zweite Paar
in der vorgeschriebenen Reihenfolge Bridge `9186b4` → Reconnect → S3 `a142a4`
aktualisiert. Beide OTA-Installationen waren erfolgreich. Integration, Bridge
und S3 melden für beide physischen Geräte Beta.12; alle vier logischen
Verbindungen sind online.

| Gerät | S3-/Bridge-Runtime bei Start | S3-Protokollfehler | Bridge-UART-Fehler | Queue-Overflows |
| --- | --- | ---: | ---: | ---: |
| `a13c8c` / `918d3c` | identisch: `R1400352246:331 V32 L0000` | 0 | 0 | 0 |
| `a142a4` / `9186b4` | identisch: `R2063022322:305 V76 L1000` | 0 | 0 | 0 |

Die erste Historienkontrolle um 18:14 Uhr wertete den Home-Assistant-Recorder
ab Testbeginn aus. Alle vier Verbindungsentitäten blieben ohne Zwischenzustand
durchgehend `on`; die vier Uptime-Reihen stiegen ohne Rücksprung. Sämtliche
S3-Protokollfehler, Bridge-UART-Fehler und Encoder-Queue-Overflows blieben über
den gesamten bis dahin aufgezeichneten Zeitraum unverändert bei null. Diese
Historienauswertung wird beim Abschluss wiederholt, damit ein aktueller
Momentzustand keine kurzen Ausfälle verdeckt.

Um 18:15:58 Uhr stieg beim Paar `a13c8c` / `918d3c` ausschließlich der
Bridge-Zähler `UART Protocol Errors` einmalig von 0 auf 2. Der S3-Zähler blieb
bei 0, beide Queue-Overflow-Zähler blieben bei 0, der S3-Link blieb ohne
Unterbrechung `on`, beide Uptimes liefen ohne Rücksprung weiter und S3 sowie
Bridge meldeten weiterhin dieselbe Runtime-Sequenz. Der Zähler fasst CRC-,
Decode-, Versions- und Link-Queue-Fehler zusammen; die vorhandene Telemetrie
trennt die zwei Ereignisse daher nicht weiter auf. Nach dem strikten V13-
Sollzustand „keine wachsenden Fehlerzähler“ ist dieser Lauf damit bereits
auffällig und kann nicht mehr uneingeschränkt als bestanden gelten. Die
Beobachtung läuft dennoch bis zum geplanten Ende weiter, um zwischen einem
isolierten UART-Störimpuls und fortlaufendem Linkabbau unterscheiden zu können.
Während des laufenden Tests erfolgt bewusst kein weiterer Firmwareeingriff.

Um 18:19:01 Uhr stieg anschließend auch beim zweiten Paar ein Zähler: Auf S3
`a142a4` wechselte `Inter-MCU Protocol Errors` von 0 auf 1, während die Bridge
`9186b4` bei 0 blieb. Auch dieses Ereignis hatte weder Linkverlust noch
Uptime-Rücksprung, Reset oder Runtime-Abweichung zur Folge. Der erste
Bridge-Zähler auf `918d3c` blieb gleichzeitig stabil bei 2. Dass beide
physischen Geräte innerhalb weniger Minuten in jeweils entgegengesetzter
Empfangsrichtung einzelne Fehler erfassen, spricht gegen einen rein
gerätespezifischen Ausfall und macht die gemeinsame 2-Mbit/s-UART-Strecke bzw.
die aggregierte Fehlerzählung zum vorrangigen Untersuchungspunkt. V13 läuft zur
Bestimmung der weiteren Fehlerrate unverändert weiter; die Abschlussbewertung
bleibt wegen des bereits nachgewiesenen Zählerwachstums auffällig.

Am 2026-08-02 wurde während des Laufs ein funktionaler Bibliotheksfehler
gefunden: Bei Timo waren Playlist, Radio und Podcast nach kurzer Zeit wieder
vorhanden, bei Marco blieben Radio und Podcast leer. Die direkte Abfrage von
`passion_wave.get_library` lieferte für beide Config Entries dieselben
Kataloge, darunter drei Radios und mehr als 40 Podcasts. Marcos S3 blieb aber
auf `ESP32 Bibliothek wird vorbereitet`, während die Bridge nur die letzte
Playlist-Seite bestätigt hatte. Ursache war ein fehlender Recovery-Übergang:
Wenn die Bridge einen Bootstrap-Response verpasst hatte, beantwortete sie die
S3-Retries dauerhaft mit „Cache nicht bereit“, ohne die fehlende Liste erneut
bei Home Assistant anzufordern.

Die Bridge behandelt eine S3-Anfrage für einen noch nicht bereiten Cache nun
als autoritative On-Demand-Anforderung. Nach dem HA-Response meldet
`LIBRARY_CHANGED` genau diesen Katalog als bereit und löst den Client-Backoff.
Der Fix wurde mit einem statischen Contract-Test, ESPHome-Validierung und
vollständigen Builds beider Bridge-Profile geprüft und anschließend per OTA
auf `9186b4` und `918d3c` installiert. Beim direkten OTA mussten die beiden
ESPHome Config Entries anschließend gezielt neu geladen werden, damit Home
Assistant die Bridge-Aktionen wieder registrierte. Marco konvergierte danach
auf `P 64 · R 3 · O 40`. Timo meldete während eines gleichzeitig laufenden
Cover-Transfers einmal `Bibliothek Fehler 7`, wiederholte den Transfer aber
selbstständig und konvergierte ebenfalls auf `P 64 · R 3 · O 40`; beide
aktuellen Bridge-UART-Zähler blieben dabei bei null.

Die zwei Bridge-OTAs um 10:30 Uhr und 10:34 Uhr sind geplante Neustarts und
unterbrechen den ursprünglichen 24-Stunden-Lauf. Dieser Zeitraum ist deshalb
kein ununterbrochener V13-Nachweis. Ein neues Beobachtungsfenster begann am
2026-08-02 um 10:37 Uhr und endet regulär am 2026-08-03 um 10:37 Uhr.

| Gerät | S3-/Bridge-Runtime beim Neustart von V13 | S3-Protokollfehler | Bridge-UART-Fehler | Queue-Overflows | Bibliothek |
| --- | --- | ---: | ---: | ---: | --- |
| `a13c8c` / `918d3c` | identisch: `R1400352246:12373 V38 L0000` | 0 | 0 | 0 | `P 64 · R 3 · O 40` |
| `a142a4` / `9186b4` | identisch: `R2063022322:12236 V63 L0100` | 2 | 0 | 0 | `P 64 · R 3 · O 40` |

Der Zählerstand 2 auf `a142a4` ist der neue V13-Ausgangswert und darf im neuen
Fenster nicht weiter steigen. Beide Richtungen des S3-/Bridge-Links waren beim
Start `on`; Runtime-State und Bibliothekscache waren je Paar konvergiert.

Bei der anschließenden Funktionsprüfung wurden zwar Radio und Podcast auf
Marco bestätigt, die Titelliste ausgewählter Playlists blieb aber auf beiden
Geräten leer. Die S3- und Bridge-Diagnosen zeigten jeweils eine formal
erfolgreiche Track-Seite `0/0`. Die direkte Browse-Abfrage enthielt dagegen
620 Titel für Marcos Testplaylist und 94 Titel für Timos Testplaylist. Ursache
war Home Assistants aktueller `BrowseMedia`-Rückgabetyp: Innerhalb eines
Service-Handlers liegt er als Objekt mit `as_dict()` vor; erst an der
WebSocket-Grenze wird daraus ein normales Dictionary. Der PassionWave-
Normalisierer akzeptierte nur `Mapping` und verwarf daher das vollständige
Objekt als leere Seite.

Der Normalisierer konvertiert nun interne HA-Response-Objekte kontrolliert über
`as_dict()` und wendet erst danach das begrenzte Track-Paging an. Ein neuer
Regressionstest deckt diesen Objektpfad ab. Nach Synchronisierung der
Integration und kontrolliertem HA-Neustart lieferte
`passion_wave.get_playlist_tracks` für Marco `16/620` und für Timo `16/94`,
jeweils mit Titel, Interpret und abspielbarer Track-URI. Die physische
Titellistenprüfung bleibt offen.

Die hierfür notwendigen Home-Assistant-Neustarts um 16:36 und 16:41 Uhr
unterbrachen auch das um 10:37 Uhr begonnene V13-Fenster. Außerdem stand Timos
Bridge-UART-Zähler nach der Rückkehr um 16:42 Uhr bei 1 statt beim bisherigen
Ausgangswert 0; Link, Runtime-Konvergenz und Queue-Overflows blieben intakt.
Der vorherige Zeitraum erfüllt damit erneut nicht den strikten V13-Sollzustand.
Das aktuelle 24-Stunden-Fenster begann am 2026-08-02 um 16:44 Uhr und endet am
2026-08-03 um 16:44 Uhr.

| Gerät | S3-/Bridge-Runtime beim aktuellen V13-Start | S3-Protokollfehler | Bridge-UART-Fehler | Queue-Overflows | Bibliothek |
| --- | --- | ---: | ---: | ---: | --- |
| `a13c8c` / `918d3c` | identisch: `R1674866336:20 V36 L0000` | 0 | 1 | 0 | `P 64 · R 3 · O 40` |
| `a142a4` / `9186b4` | identisch: `R268818886:21 V55 L0000` | 2 | 0 | 0 | `P 64 · R 3 · O 40` |

Während V13 beide Geräte normal gemischt bedienen: Medien inklusive mehrerer
Coverwechsel, Licht, Wetter/Radar, Floorplan, Dimmen und Aufwecken. Nach 24
Stunden Versionsstände, Verbindungen, Uptime/Resetgrund, Runtime-Konvergenz,
beide Protokollfehlerzähler und Queue-Overflows erneut aufnehmen. Jeder
ungeplante Neustart, dauerhaft schwarze Asset-Fläche, verlorene Verbindung
oder wachsende Fehlerzähler beendet V13 als fehlgeschlagen und wird mit Uhrzeit
und aktiver Seite protokolliert.

## Offen

### PW-QA-001: Physische UI-Abnahme ist nicht vollständig automatisierbar
Grundfunktionen für Playlist, Licht, Wetter, Radar, Floorplan und Medien-Dimmung sind live bestätigt; offen bleiben die Blöcke V01–V13 einschließlich Cover, Detailfunktionen, Neustarts und Dauerlauf.

### PW-QA-002: Zweites Kundengerät ist noch nicht vollständig abgenommen
Beide Geräte werden inzwischen in PassionWave gelistet; der getrennte Nachweis aller vier Endpoint-Versionen, der Schlüsseltrennung und der vollständigen V01–V13-Abnahme pro Gerät bleibt offen.

### PW-MEDIA-009: Playlist-Titelliste wurde als erfolgreiche leere Seite geliefert
Die `BrowseMedia`-Objektkonvertierung ist korrigiert, auf Home Assistant aktiv
und mit echten Seiten (`16/620` und `16/94`) verifiziert. Offen ist nur die
abschließende Sichtprüfung und das Starten eines Titels aus der Liste auf dem
Display.

### PW-MEDIA-010: Neuer Titel konnte von älterem Playliststart überschrieben werden
Beim Lauf am 2026-08-03 erreichte `Magic Moment` die Bridge beim ersten Tap um
12:21:59,949 und wurde auf dem S3 um 12:22:00,068 als gesendet bestätigt. Ein
älterer, seit 12:21:33 laufender Playlistauftrag beendete seinen internen
Music-Assistant-Queue-Aufbau jedoch später und startete um 12:22:14 den
vorherigen Titel. Erst der zweite Auftrag um 12:22:24,551 setzte sich durch;
der Zielplayer meldete `Magic Moment` um 12:22:28,724. Touch und UART hatten
keinen Befehl verloren.

Die Integration verwendet nun pro Config Entry einen generationsbasierten
Latest-command-wins-Worker. Noch nicht ausgeführte Befehle werden auf das
neueste Sollziel reduziert, Music-Assistant-Aufrufe laufen seriell, veraltete
Abschlussmeldungen werden verworfen und einzelne Titel ersetzen die bestehende
Queue statt in einen noch laufenden Aufbau eingefügt zu werden. Der gewünschte
Track wird bis zu zehn Sekunden am `media_content_id` bestätigt und bei einer
beobachtbaren Abweichung genau einmal erneut gesetzt; eine neuere Auswahl
unterbricht diese Wartephase spätestens nach 100 ms. Der Quell- und Live-Stand
besteht 25 gezielte Tests und wurde um 14:07 Uhr durch einen kontrollierten
Home-Assistant-Neustart aktiviert. Offen ist die physische D17-Abnahme mit
schnellen unterschiedlichen sowie identischen Titelauswahlen.

### PW-LIGHT-004: WLED-Presets reagieren teilweise verzögert
Am 2026-08-03 lagen acht gemessene RotaryKnob-Rundläufe vom Bridge-Befehl bis
zum bestätigten WLED-Select-Zustand zwischen 1,250 und 1,314 Sekunden. Direkte
native `select.select_option`-Kontrollläufe benötigten vor dem Fix 1,725 und
nach dem Neustart 1,638 beziehungsweise 1,664 Sekunden. Acht direkte WLED-
Statusabrufe lagen dagegen zwischen 31,7 und 122,6 ms. Damit liegt die
dominante physische Latenz hinter dem lokalen Touch-/UART-Pfad. Die WLED-
Presets 1 bis 8 speichern außerdem jeweils `transition: 7`; diese gewollte
Überblendzeit von ungefähr 700 ms trägt zur wahrgenommenen Verzögerung bei.

Zusätzlich fragte Timos Bridge wegen des unbelegten Platzhalters in Licht-Slot
4 alle rund 2,5 Sekunden erneut einen Detailkatalog an (2.874 protokollierte
Anfragen in zwei Stunden). Integration und beide Preset-Aktionspfade behandeln
solche Platzhalter nun als unbelegt und beenden die WLED-Validierung nach dem
passenden Ziel. Nach Bereitstellung, zwei kontrollierten Home-Assistant-
Neustarts und dem abschließenden Textaktions-Fix blieb der Broker nach der
einmaligen Boot-Anfrage um 12:06:59 ruhig; die Retry-Folge ist damit live
behoben. Alle 21 gezielten Tests bestehen. Offen bleiben ein physischer E03-
Retest und die bewusste Entscheidung, die WLED-Überblendzeit beispielsweise
auf `transition: 1` zu reduzieren.

### PW-UI-003: Albumcover-Screensaver war leer oder nach Titelwechsel schwarz
Metadatenfehler auf `918d3c` live behoben; S3-Cover-Fix ausgerollt und Decode
einschließlich sichtbarer Vollbilddarstellung auf `a13c8c` bestanden.
Erstens überschrieb der
periodische Bridge-Snapshot bei der gestuften Kombination aus alter Integration
und neuer Bridge die direkt empfangenen S3-Texte mit leeren
Präsentationsfeldern. Der Snapshot ist nun bis zum ersten ausdrücklich
autoritativen Präsentationspaket gesperrt; der Titel blieb im physischen
Wiedergabe-Retest stabil. Zweitens verwirft der installierte
S3 den Cover-Decode bei rund 1,915 MiB freiem Heap wegen seiner alten
2-MiB-Schranke. Der aktualisierte S3-Pfad nutzt 1,25 MiB und plant das Cover auch
für `RUNTIME_STATE=playing`. Der konsolidierte Pfad besitzt nur noch eine
Autorität (Integration → Bridge-Snapshot → UART → S3); direkte
Medien-Subscriptions, direkte HA-Aktionen und beschreibbare S3-Runtime-
Diagnosen wurden entfernt. Der koordinierte Stand dekodierte und zeigte das
Cover auf `a13c8c` zunächst erfolgreich. Für nachfolgende Coverwechsel wird nun
zusätzlich der LVGL-Bildcache vor und nach dem Austausch des Runtime-Puffers
invalidiert. Der Fix ist auf `a13c8c` installiert und mit mehreren
aufeinanderfolgenden Titelwechseln physisch bestätigt; V02/V03 anschließend
auf dem zweiten Gerät wiederholen.

### PW-FW-008: ESPHome-Abkündigungen erzeugen Build-Warnungen
`online_image`, `qspi_dbi` und alte Build-Flags vor ESPHome 2027.1/2026.12 migrieren; derzeit kein Laufzeitfehler.

### PW-MEDIA-006: Lautstärke sprang nach dem Verstellen kurz auf 50 %
Metadaten- und Ziel-Reconnectpfad überschrieben den Bridgewert; 50-%-Defaults entfernt, verlustfreie EC1-Batch-Auswertung wiederhergestellt.

### PW-HA-006: Wetterquelle ist noch Firmware-Konfiguration
Forecast-Kommandos akzeptieren ein `weather.*`-Ziel aus der Bridge; Auswahl und Bindung gehören künftig in den PassionWave Config Entry.

### PW-HA-007: Historische MQTT-Entities liegen noch in der HA-Registry
Die Laufzeit ist MQTT-frei, aber alte Registry-Einträge sind mit dem Gerät zusammengeführt; Bereinigung nur kontrolliert nach Nutzerfreigabe.

## In diesem Stand behoben

### PW-LIGHT-003: Leuchtenwechsel über den Namen benötigte zwei Touchschritte
Der neue eindeutige S3-Schnellpfad schaltet beim Tap auf den Leuchtennamen lokal
zur nächsten konfigurierten Leuchte, überspringt leere beziehungsweise
öffentliche Platzhalter-Slots und rendert sofort. Er löst dabei weder UART- noch
Home-Assistant-Aktionen aus; Detailtaste und Lichtsteuerung bleiben unverändert.
Der vollständige Managed-Test-S3-Build wurde am 2026-08-03 um 11:21 Uhr auf
Timos S3 `a13c8c` installiert. Link- und Fehlerdiagnosen blieben anschließend
unauffällig, und der Nutzer bestätigte den Schnellwechsel physisch als
funktionierend. Die Wiederholungsprüfung auf Gerät 2 bleibt Bestandteil der
Release-Abnahme, ist aber kein bekannter Implementierungsfehler mehr.

### PW-MEDIA-008: Marcos Radio-/Podcast-Popup war nach Bootstrap dauerhaft leer
Der fehlende Bridge-On-Demand-Recovery ist behoben und auf beiden Bridges
installiert. Home Assistant, Bridge und S3 weisen für Marco drei Radios und 40
zwischengespeicherte Podcasts nach; der Nutzer bestätigte beide Tabs physisch.
Ein einmaliger Transfer-Timeout auf Timo heilte ohne Linkverlust oder
UART-Fehler selbst aus.

### PW-WEB-001: Web-Installer meldete beim Firmwareabruf „Failed to fetch“
Signierte Release-Weiterleitungen waren nicht CORS-stabil; Manifeste nutzen nun getaggte Raw-Dateien mit Cache-Buster und geprüften SHA-256-Summen.

### PW-REL-001: Öffentlicher Installer lag hinter dem Quellstand
Website, Firmware und HACS-Integration veröffentlichen gemeinsam `3.0.0-beta.14`; die vier unveränderlichen Images besitzen veröffentlichte Prüfsummen.

### PW-UPD-001: Firmware-Update war nicht öffentlich erreichbar
Die Website liefert beide stabilen OTA-Manifeste und Binärdateien; das kombinierte HA-Geräteupdate kann beta.14 für Bridge und S3 abrufen.

### PW-UPD-004: Bridge-Aktionen fehlten nach dem Kunden-OTA
Der kombinierte Updater lädt den ESPHome-Bridge-Eintrag zwischen Bridge und S3 neu; die umbenannten API-Aktionen sind dadurch sofort registriert.

### PW-WEATHER-001: Forecast-Anfrage konnte beim Neustart verloren gehen
Die Bridge wiederholt eine unbeantwortete Forecast-Anfrage alle zehn Sekunden; nach gültiger Tagesprognose endet der Retry automatisch.

### PW-UPD-003: Firmware fragte einen nicht auflösbaren Update-Host ab
`www.passion-wave.com` besaß kein DNS-Ziel; beide Chips verwenden nun direkt die veröffentlichte Passion-Wave-Site für ihre OTA-Manifeste.

### PW-UI-002: Screensaver startete hinter UI Next und ließ die Lichtseite blitzen
UI Next wird ausgeblendet und Seite 7 atomar gesetzt; Testgerät wechselte nach 30 s genau einmal, ohne 100-%-Wiederholung oder Encodertrigger.

### PW-LIGHT-001: Externe Lichtänderungen erschienen nicht am RotaryKnob
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
Integration `3.0.0-beta.15` vermittelt validierte Commands; beide Firmwareprofile melden `homeassistant_services: false`.

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
Managed Dual-MCU entfernt die direkten Wetter-/Template-Fetcher bereits bei
der ESPHome-Konfigurationsauflösung; Forecast, Lichtkatalog, Medienzustand und
Steuerbefehle laufen ausschließlich über Bridge und Integration. Im neu
erzeugten Managed-S3-C++ existieren keine Home-Assistant-Serviceobjekte oder
direkten State-Subscriptions mehr. Der Build ist mit 52,4 % RAM und 71,6 %
Flash erfolgreich.

### PW-FW-010: Uhrzeitpuffer konnte statisch als zu klein gelten
Der Puffer wurde von sechs auf neun Bytes erweitert; die ESPHome-Compilerwarnung ist damit beseitigt.
