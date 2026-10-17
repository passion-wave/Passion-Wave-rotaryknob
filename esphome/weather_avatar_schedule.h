#pragma once

#include <cstdint>
#include <ctime>

namespace weather_avatar {

// Wall-clock scheduling and monotonic interaction timing intentionally have
// separate inputs: a DST change must not count as an input or extend 10:00.
inline bool morning_window(bool enabled, bool valid_time, int local_hour) {
  return enabled && valid_time && local_hour >= 6 && local_hour < 10;
}

enum class MorningAction : uint8_t { NONE, ENTER, LEAVE };

inline MorningAction morning_action(bool window, bool blocked, bool visible,
                                    bool automatic, uint32_t idle_ms,
                                    uint32_t idle_threshold_ms) {
  if (visible && automatic && (!window || blocked)) return MorningAction::LEAVE;
  if (window && !blocked && !visible && idle_ms >= idle_threshold_ms)
    return MorningAction::ENTER;
  return MorningAction::NONE;
}

// The ESPHome time components configure libc's local zone. mktime with
// tm_isdst=-1 computes tomorrow's local 06:00 across 23/25-hour DST days.
// A device without a synchronized clock periodically wakes to retry sync.
inline uint32_t next_morning_wake_seconds(std::time_t epoch) {
  if (epoch < 1609459200) return 15U * 60U;
  std::tm local{};
  if (localtime_r(&epoch, &local) == nullptr) return 15U * 60U;
  if (local.tm_hour >= 6) ++local.tm_mday;
  local.tm_hour = 6;
  local.tm_min = 0;
  local.tm_sec = 0;
  local.tm_isdst = -1;
  const std::time_t wake = std::mktime(&local);
  if (wake <= epoch) return 15U * 60U;
  return static_cast<uint32_t>(wake - epoch);
}

}  // namespace weather_avatar
