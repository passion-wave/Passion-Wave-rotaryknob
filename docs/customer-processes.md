# Kundenprozesse

## Onboarding

1. PassionWave über HACS installieren und Home Assistant neu starten.
2. Für eine eindeutige Erstzuordnung immer nur einen neuen RotaryKnob
   einschalten; beide Prozessoren verbinden sich mit demselben WLAN.
3. Unter **Einstellungen → Geräte & Dienste → Entdeckt** genau eine
   `PassionWave RotaryKnob`-Kachel pro physischem Gerät öffnen.
4. Den vorausgewählten S3 und die einzige neue Bridge bestätigen. Erst danach
   das nächste Kundengerät einschalten und denselben Ablauf wiederholen.
5. Music Assistant, Wiedergabegerät und bis zu vier Lichtplätze auswählen.
6. PassionWave richtet beide verschlüsselten technischen Verbindungen ein.
   API-Schlüssel oder ESPHome-Geräte muss der Kunde nicht bearbeiten.

## Update

1. Home Assistant meldet ein HACS-Update für die PassionWave-Integration oder
   ein Geräteupdate `PassionWave RotaryKnob Firmware`.
2. Falls beide angeboten werden, zuerst die Integration über HACS aktualisieren
   und Home Assistant wie von HACS verlangt neu starten.
3. Danach beim RotaryKnob **Installieren** wählen. Das ist die einzige
   Kundenaktion für beide Firmwares; technische ESPHome-Updates erscheinen ab
   Beta.16 nicht mehr.
4. PassionWave aktualisiert zuerst die Bridge und wartet auf deren bestätigte
   Rückkehr mit der Zielversion.
5. Nur bei erfolgreicher Bridge aktualisiert PassionWave anschließend den S3
   und prüft auch dessen Rückkehr.
6. Schläft ein Prozessor, bleibt der Auftrag als `Wartet auf RotaryKnob`
   gespeichert und läuft nach dem Aufwecken weiter.
7. Bei einem Fehler bleibt der Ablauf stehen und nennt die betroffene Phase.
   Ein Neustart von Home Assistant verliert einen laufenden Auftrag nicht.

## Änderungsabnahme im Home-Assistant-Updatefenster

Dieser Ablauf ist nach jeder Änderung an Integration, Update-Logik, Firmware,
Manifesten oder Veröffentlichung aus Kundensicht auszuführen. Ein API-Test
ersetzt ihn nicht. Integration, Timo und Marco werden strikt nacheinander
aktualisiert; ein zweiter Auftrag darf nie parallel laufen.

### Vorbereitung

1. Unter **Einstellungen → System → Updates** die angebotene und installierte
   Version der PassionWave-Integration sowie der logischen Firmware-Updates
   von Timo und Marco festhalten.
2. Sicherstellen, dass beide RotaryKnobs erreichbar sind und kein Update läuft.
   Für jedes Produkt Bridge-/S3-Version, Verbindungsstatus, Phase und letzten
   Fehler als technische Baseline erfassen.
3. Einen angemeldeten Home-Assistant-Browser mit sichtbarer Update-Seite
   bereitstellen. Fehlt diese Browser-Sitzung, lautet das UI-Ergebnis
   `BLOCKIERT`; Remote- oder API-Zustände dürfen nicht als UI-Erfolg gelten.

### Integration

1. Die PassionWave-Integrationskachel öffnen. Installierte und angebotene
   Version sowie Release-Hinweise müssen eindeutig sein.
2. **Aktualisieren** genau einmal betätigen. Der Dialog muss danach einen
   dauerhaften Fortschritts- oder Beschäftigtzustand zeigen; ein kurzes
   Aufblitzen mit sofort wieder aktivem Knopf ist ein Fehlerbefund.
3. Bis Erfolg oder verständlicher Fehlermeldung warten. Mehrfachklicks dürfen
   keinen zweiten Auftrag starten.
4. Einen verlangten Home-Assistant-Neustart ausführen und bis zum Core-Zustand
   `RUNNING` warten. Danach müssen HACS- und geladene Integrationsversion dem
   Ziel entsprechen.

### Geräte

1. Zuerst nur Timo aktualisieren. Auf der Kachel müssen Zielversion und ein
   verständlicher Hinweis auf das zweistufige Geräteupdate sichtbar sein.
2. **Aktualisieren** genau einmal betätigen. Während Bridge, Rückkehrprüfung,
   S3 und Abschluss muss ein dauerhafter Status sichtbar sein; der Benutzer
   darf das Gerät nicht ausschalten und keinen zweiten Auftrag auslösen können.
3. Erfolg erst annehmen, wenn die Kachel keinen offenen Updatezustand mehr
   zeigt und technisch `phase=complete`, Bridge und S3 auf der Zielversion,
   beide Verbindungen aktiv und `last_error=null` bestätigt sind.
4. Erst danach denselben Ablauf vollständig für Marco wiederholen.
5. Beide Entitäten erneut aktualisieren. Die Zielversion darf nicht nochmals
   angeboten werden.

### Protokoll und Bewertung

Für jeden der drei Schritte werden Start-/Endzeit, installierte und angebotene
Version, sichtbare Texte, Knopfzustände, Fortschritt, Ergebnis und Screenshot
notiert. Evidenz erhält genau eine Herkunft: `UI-beobachtet`, `remote
beobachtet` oder `automatisiert`. Ein Fehler nennt Produkt und Phase sowie den
sicheren Wiederaufnahmepunkt. Die Abnahme ist nur `BESTANDEN`, wenn alle drei
UI-Abläufe und ihre technischen Endzustände übereinstimmen; andernfalls ist
sie `FEHLGESCHLAGEN` oder bei fehlendem Browser `BLOCKIERT`.

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
