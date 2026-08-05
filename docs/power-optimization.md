# Power and runtime optimization

This analysis describes the Beta.13 dual-MCU implementation. Current values
are code and vendor-reference values, not whole-device measurements. Display,
backlight, regulators, haptics and the second MCU must be measured on the real
product before publishing a battery-runtime claim.

## Current power behavior

- S3 and Bridge are fixed at 240 MHz and use `wifi.power_save_mode: none`.
- The visible LVGL UI updates every 33 ms. The backlight normally runs at 70%.
- On battery, the S3 dims after 15 seconds by default, switches the display off
  after 60 seconds without playback or 180 seconds during playback, and enters
  deep sleep after 90 seconds of inactivity if no timer or alarm blocks sleep.
- Display-off turns off the backlight and pauses LVGL. GPIO9 wakes the S3.
- Runtime and diagnostic traffic is event-driven with a 15-minute full-state
  fallback. Support mode alone restores high-frequency diagnostics.
- The Bridge remains awake and connected. If both processors use the same
  battery rail, Bridge consumption can dominate after the S3 enters deep sleep.

## Recommended order

1. Measure S3 and Bridge separately in five repeatable states: UI at 70%, dim
   UI, display off before deep sleep, S3 deep sleep, and network asset download.
   Record voltage, average current and peak current for at least five minutes
   per state. Runtime estimate: `usable battery mAh / average mA`, then apply a
   conservative 0.8–0.9 derating factor.
2. Change both Wi-Fi clients from `none` to modem power save and benchmark the
   existing command-latency probes. The Bridge should remain continuously
   connected; a battery-dependent `esp_wifi_set_ps()` policy can retain `none`
   on external power and use modem sleep on battery. This is the strongest
   low-risk firmware lever because central visual content is unchanged.
3. Enable ESP-IDF dynamic frequency scaling with 240 MHz maximum and 80 MHz
   minimum, initially without automatic light sleep. Re-run UART at 2 Mbit/s,
   touch, encoder, QSPI display, cover decode and WLED latest-command-wins tests.
4. Shorten the battery-only delay between display-off and S3 deep sleep from
   90 seconds to 15–30 seconds. The display is already black and LVGL paused, so
   this removes invisible awake time without removing information. Validate
   GPIO9 wake and full Bridge snapshot restoration first.
5. Keep central information visible while reducing backlight cost: use 70% for
   active interaction, 25–35% after roughly 10–15 seconds, and 10–15% for a
   still-visible screensaver. Do not lower cover, title, weather or alarm update
   frequency while the display is active.
6. Reduce work during the short display-off window: suspend the 10 ms UI loop
   and nonessential touch/render timers immediately, and sample battery voltage
   every 60 seconds instead of every 15 seconds. Publish immediately on a
   meaningful percentage or external-power transition, plus every 15 minutes.
7. Optimize the always-on Bridge last. Test 160 or 80 MHz plus modem power save
   and remove millisecond polling where UART/API callbacks can signal work. If
   the Bridge shares the battery, a hardware power gate or explicitly designed
   low-power Bridge state offers the largest product-level gain, but requires a
   proven wake and resynchronization design.

## Acceptance gates

An optimization is accepted only when the 95th-percentile light/media command
latency does not regress materially, every visible page remains current,
cover/radar/floorplan downloads still succeed, UART errors stay at zero, and
touch/encoder wake restores the complete state. Compare battery energy per
hour, not only instantaneous current.

## Marco experiment branch

The branch `agent/extreme-power-responsiveness` contains the first isolated
implementation tranche. It is enabled only by Marco's
`managed-production-{s3,esp32}.yaml` overlays; Timo, factory builds and the
Beta.14 release remain unchanged.

- Both processors retain `WIFI_PS_NONE` on external power and for the first
  three seconds after a local interaction. On battery idle they switch to
  `WIFI_PS_MIN_MODEM`, which keeps the association alive.
- S3 image/radar/floorplan activity holds the responsive Wi-Fi policy until
  the transfer and decode are complete.
- The Bridge treats encoder deltas and actionable S3 control frames as user
  activity, so the next command does not wait for the idle policy window.
- Marco's non-playing, battery-only display-off window now enters deep sleep
  at 75 seconds of inactivity instead of 90 seconds. With the existing
  60-second display-off point, this removes 15 seconds of invisible awake time.
- Automatic light sleep and CPU frequency scaling are deliberately not part
  of this first tranche: the 2 Mbit/s inter-MCU UART and active LVGL path first
  need current and P95-latency measurements under the modem-sleep policy.

This branch must not be flashed before both managed configs compile and the
test plan is reviewed. The intended first hardware target is Marco only.

Pre-flash verification on 2026-08-05:

- ESPHome 2026.7.0 configuration and full compilation succeeded for Marco S3
  and Bridge.
- S3 uses 52.5% RAM and 71.6% flash; Bridge uses 39.9% RAM and 62.5% flash.
- The Home Assistant 2026.7.4 test environment passes 43 tests and four
  subtests.
- No binary from this branch has been flashed, uploaded to a device or placed
  in a customer update manifest.

## Reference basis

- Espressif documents that Wi-Fi modem sleep retains the connection, while
  disabling power save prioritizes minimum receive latency at higher power.
- ESP-IDF dynamic frequency scaling adjusts CPU/APB clocks and coordinates
  peripheral performance through power-management locks.
- Espressif's idealized ESP32-S3 Wi-Fi measurements show approximately
  38–40 mA for modem sleep without DFS, 19.5–20.7 mA with DFS, and below 3 mA
  with automatic light sleep depending on DTIM. These are silicon/reference
  conditions and must not be treated as Rotaryknob measurements.

Sources:

- <https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/api-guides/wifi-driver/wifi-performance-and-power-save.html>
- <https://docs.espressif.com/projects/esp-idf/en/v6.0/esp32s3/api-reference/system/power_management.html>
- <https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/api-guides/low-power-mode/low-power-mode-wifi.html>
