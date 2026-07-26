# Debugging

## Media-Auswahl-Crash Analysieren

Der Debug-Stack ist im Normalbetrieb deaktiviert. Bei Bedarf schreibt er gezielte Media-Events in drei Kanäle:

- ESPHome-Logger mit Tag `media_debug`
- Home-Assistant-Entity `scrollwheel Media Debug Status`
- MQTT-Topic `passion_wave/rotaryknob/media/debug`

Zusätzlich meldet `scrollwheel Last Reset Reason`, ob der letzte Neustart zum Beispiel durch `panic`, `watchdog`, `brownout` oder einen normalen Software-Neustart ausgelöst wurde.

## Schnellster Ablauf

1. Debug einschalten:

   ```bash
   ha service call esphome passion_wave_rotaryknob_media_debug_on
   ```

2. Logs live ansehen:

   ```bash
   ./tools/logs.sh
   ```

   Wenn die IP-Adresse bekannt ist, kann der OTA/API-Logpfad direkt angesprochen werden:

   ```bash
   ./tools/logs.sh --device 192.0.2.10
   ```

3. Auf dem Gerät die Medienseite öffnen, Playlist/Podcast auswählen und den problematischen Titel starten.

4. Direkt nach einem Crash prüfen:

   ```bash
   ha service call esphome passion_wave_rotaryknob_media_debug_dump
   ```

5. Debug wieder ausschalten:

   ```bash
   ha service call esphome passion_wave_rotaryknob_media_debug_off
   ```

Falls die Home-Assistant-Service-Namen lokal anders heißen, in Home Assistant unter Entwicklerwerkzeuge > Dienste nach `media_debug` suchen. Alternativ kann der Switch `scrollwheel Media Debug` direkt im Gerätebereich aktiviert werden.

## Serielle Logs

Wenn das Gerät so früh crasht, dass es Home Assistant nicht erreicht, USB anschließen und serielle Logs öffnen:

```bash
SERIAL_PORT=/dev/cu.usbmodem14101 ./tools/serial-logs.sh
```

Die seriellen Logs sind der wichtigste Weg für Panic-/Watchdog-Auszüge, weil sie auch während Boot und Reconnect sichtbar bleiben.

## Wichtige Marker

- `esp_title_click_open_track_select`: Track-Auswahl wurde geöffnet.
- `esp_title_click_confirm_track`: Ein Track wurde bestätigt.
- `esp_track_start_enter`: Track-Start beginnt mit Index, Titel- und URI-Anzahl.
- `esp_track_start_invalid_index`: Auswahlindex passt nicht zur URI-Liste.
- `esp_track_start_empty_uri`: Track hat keine abspielbare URI.
- `esp_track_play_media_before`: Übergabe an Home Assistant startet.
- `esp_track_play_media_after_service_action`: Home-Assistant-Service wurde abgesetzt.
- `esp_tracks_response_*`: Empfang und Parsing der Trackliste.
- `esp_cover_url_changed`: Eine neue Cover-URL wurde erkannt und nur vorgemerkt.
- `esp_cover_update_deferred`: Cover-Laden wurde bewusst verschoben oder ein veralteter Download ignoriert.
- `esp_cover_update_start`: Ein einzelner, freigegebener Cover-Download startet.
- `esp_cover_update_skip_busy`: UI, Scrollen, Trackliste, Bootphase oder Netzwerk sind gerade zu aktiv.
- `esp_cover_update_skip_heap`: Freier Heap ist unter dem Sicherheitslimit.
- `esp_cover_update_failed_backoff`: Cover-Laden ist nach Fehlern im Backoff.
- `esp_cover_update_done`: Cover wurde erfolgreich geladen.

## Cover-Pipeline

Cover-Downloads laufen nicht direkt im Home-Assistant-Response-Callback. Die Firmware merkt eine neue URL nur vor und lädt sie später, wenn Wi-Fi stabil ist, keine Auswahl-/Scrollaktion läuft und genug Heap frei ist. Zuerst wird das kleine Medienseiten-Cover geladen; das größere Cover für den Media-Screensaver wird erst danach und nur bei Bedarf geladen.

Der wichtigste Crash-Test ist:

1. `scrollwheel Media Debug` einschalten.
2. Eine große Playlist öffnen.
3. Trackliste laden lassen.
4. Einen Titel auswählen.
5. In den Logs prüfen, dass nach `esp_tracks_response_parsed` kein `abort()` folgt, sondern Cover-Marker wie `esp_cover_update_deferred` oder `esp_cover_update_start`.

## Produktiver Debug-Weg

Für normale UI-Tests reicht `./tools/logs.sh`. Für harte Reboots oder lange Reconnect-Zeiten ist `./tools/serial-logs.sh` besser, weil der Reset-Grund und frühe Boot-Ausgaben nicht verloren gehen.
