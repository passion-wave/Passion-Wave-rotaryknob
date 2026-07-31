# Kundenprozesse

## Onboarding

1. PassionWave über HACS installieren und Home Assistant neu starten.
2. Für eine eindeutige Erstzuordnung immer nur einen neuen Rotaryknob
   einschalten; beide Prozessoren verbinden sich mit demselben WLAN.
3. Unter **Einstellungen → Geräte & Dienste → Entdeckt** genau eine
   `PassionWave Rotaryknob`-Kachel pro physischem Gerät öffnen.
4. Den vorausgewählten S3 und die einzige neue Bridge bestätigen. Erst danach
   das nächste Kundengerät einschalten und denselben Ablauf wiederholen.
5. Music Assistant, Wiedergabegerät und bis zu vier Lichtplätze auswählen.
6. PassionWave richtet beide verschlüsselten technischen Verbindungen ein.
   API-Schlüssel oder ESPHome-Geräte muss der Kunde nicht bearbeiten.

## Update

1. Home Assistant meldet ein HACS-Update für die PassionWave-Integration oder
   ein Geräteupdate `PassionWave Rotaryknob Firmware`.
2. Falls beide angeboten werden, zuerst die Integration über HACS aktualisieren
   und Home Assistant wie von HACS verlangt neu starten.
3. Danach beim Rotaryknob **Installieren** wählen. Das ist eine Kundenaktion
   für beide Firmwares.
4. PassionWave aktualisiert zuerst die Bridge und wartet auf deren bestätigte
   Rückkehr mit der Zielversion.
5. Nur bei erfolgreicher Bridge aktualisiert PassionWave anschließend den S3
   und prüft auch dessen Rückkehr.
6. Bei einem Fehler bleibt der Ablauf stehen und nennt die betroffene Phase.
   Die verborgenen Einzelupdates dienen Support und Wiederherstellung.

## Konfiguration

1. **Einstellungen → Geräte & Dienste → PassionWave → Konfigurieren** öffnen.
2. Display/Bridge-Zuordnung, Music-Assistant-Instanz und Wiedergabegerät prüfen
   oder ändern.
3. Bis zu vier Lichter in der gewünschten Display-Reihenfolge zuweisen;
   `Nicht belegt` lässt einen Platz frei.
4. Playlists, Radios und Podcasts optional auf einzelne Einträge begrenzen.
   `Alle automatisch` folgt der vollständigen Music-Assistant-Bibliothek.
5. Speichern. PassionWave überträgt Ziele, Namen und Zustände automatisch an
   beide Prozessoren; YAML, Blueprint und erneutes Flashen sind nicht nötig.
