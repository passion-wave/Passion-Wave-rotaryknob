# Firmware and integration 3.0.1-beta.17

Playlist-track pages reuse one bounded browse snapshot instead of retrieving
the complete playlist for every 16 tracks. Exact provider URIs, logical devices,
Music Assistant instances and selected players remain isolated, supporting
playlists from multiple Spotify accounts.

Slow starts retain their Bridge and S3 callback after the picker closes.
Two-second progress acknowledgements keep quiet watchdogs alive without a new
Music Assistant playback call. Provider waiting is bounded to 120 seconds;
progress, HA confirmation and audible sound are separate observations.

## Validation and rollout

The current Home Assistant fast suite passed 136 tests and 56 subtests.
Full channel qualification and the immutable Hosted-CI receipt remain required.
Install the integration before Bridge, then S3. Physical cold/warm playlist
starts, rapid changed selections and both-device UI acceptance remain pending.
The receipt owns all source OIDs, toolchain and artifact hashes.
