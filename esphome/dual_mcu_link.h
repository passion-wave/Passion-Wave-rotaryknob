#pragma once

#include <algorithm>
#include <array>
#include <cctype>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <string>
#include <vector>

#include "esphome/components/uart/uart.h"

namespace dual_mcu {

static constexpr uint8_t PROTOCOL_VERSION = 3;
// Keep a complete COBS frame below 254 bytes while carrying substantially
// more bulk data per acknowledged frame. At 2 Mbit/s this cuts a 320x320
// radar image from about 189 stop-and-wait chunks to roughly 43 without
// increasing the four-millisecond traffic cadence used to protect controls.
static constexpr size_t MAX_PAYLOAD = 192;
static constexpr size_t MAX_RAW_FRAME = 8 + MAX_PAYLOAD;
static constexpr size_t MAX_WIRE_FRAME = MAX_RAW_FRAME + 2;
// Radar data may arrive while LVGL briefly occupies the S3 main loop. 64
// frames buffer roughly 250 ms of the deliberately throttled bulk stream,
// without affecting the latency of encoder and control frames.
static constexpr size_t FRAME_QUEUE_SIZE = 64;

enum class MessageType : uint8_t {
  HELLO = 1,
  HEARTBEAT = 2,
  ENCODER_DELTA = 3,
  ENCODER_DIAG = 4,
  PING = 5,
  PONG = 6,
  RESET_COUNTERS = 7,
  BRIDGE_STATUS = 8,
  SNAPSHOT_REQUEST = 9,
  MEDIA_STATE = 10,
  MEDIA_TEXT = 11,
  LIGHT_STATE = 12,
  HA_ACTION = 13,
  WEATHER_STATE = 14,
  WEATHER_TEXT = 15,
  WEATHER_FORECAST = 16,
  RADAR_REQUEST = 17,
  RADAR_BEGIN = 18,
  RADAR_CHUNK = 19,
  RADAR_END = 20,
  RADAR_ERROR = 21,
  RADAR_ACK = 22,
  LIBRARY_REQUEST = 23,
  LIBRARY_BEGIN = 24,
  LIBRARY_CHUNK = 25,
  LIBRARY_END = 26,
  LIBRARY_ERROR = 27,
  LIBRARY_ACK = 28,
  LIBRARY_CHANGED = 29,
  WLED_PRESET_ITEM = 30,
  WLED_PRESET_META = 31,
  MEDIA_LIBRARY_PLAY = 32,
  MEDIA_LIBRARY_PLAY_RESULT = 33,
  LIBRARY_PAGE_FETCH = 34,
  LIBRARY_PAGE_FETCH_RESULT = 35,
  LATENCY_PROBE = 36,
  LATENCY_BRIDGE_ACK = 37,
  LATENCY_RESULT = 38,
  VOLUME_SET = 39,
  VOLUME_BRIDGE_ACK = 40,
  VOLUME_RESULT = 41,
  RADAR_META = 42,
  TIME_STATE = 43,
  DEVICE_STATUS = 44,
  LIBRARY_CLIENT_STATUS = 45,
  MEDIA_COVER_URL_BEGIN = 46,
  MEDIA_COVER_URL_CHUNK = 47,
  MEDIA_COVER_URL_END = 48,
  MEDIA_COVER_URL_ACK = 49,
  LIGHT_DETAIL_STATE = 50,
  LIGHT_PRESET_TEXT = 51,
  FLOORPLAN_INVALIDATED = 52,
  LIGHT_DETAIL_CATALOG_ITEM = 53,
  LIGHT_DETAIL_CATALOG_META = 54,
};

enum class HAAction : uint8_t {
  MEDIA_PREVIOUS = 1,
  MEDIA_PLAY_PAUSE = 2,
  MEDIA_NEXT = 3,
  MEDIA_VOLUME = 4,
  MEDIA_SHUFFLE = 5,
  MEDIA_REPEAT_ONE = 6,
  LIGHT_OFF = 10,
  LIGHT_ON = 11,
  LIGHT_BRIGHTNESS = 12,
  WLED_PRESET = 13,
  SCENE_ACTIVATE = 14,
  SELECT_OPTION = 15,
  LIGHT_DETAIL_ACTIVATE = 16,
};

enum class MediaTextField : uint8_t {
  TITLE = 1,
  ARTIST = 2,
  FRIENDLY_NAME = 3,
  ALBUM_ARTIST = 4,
};
enum class WeatherTextField : uint8_t { CONDITION = 1, LOCATION = 2 };

static constexpr size_t WLED_PRESET_MAX_ITEMS = 9;
static constexpr size_t LIGHT_DETAIL_MAX_ITEMS = 32;

// Home Assistant forwards list-valued attributes through the ESPHome API as
// their Python string representation, for example "['Warm', 'Police']".
// Parse only a bounded list of quoted strings; malformed input yields an empty
// result instead of allocating or forwarding untrusted data indefinitely.
inline std::vector<std::string> parse_home_assistant_string_list(
    const std::string &input, size_t maximum = WLED_PRESET_MAX_ITEMS) {
  std::vector<std::string> result;
  result.reserve(std::min(maximum, WLED_PRESET_MAX_ITEMS));
  size_t position = 0;
  while (position < input.size() && isspace(static_cast<unsigned char>(input[position]))) position++;
  if (position >= input.size() || input[position] != '[') return result;
  position++;
  while (position < input.size() && result.size() < maximum) {
    while (position < input.size() &&
           (isspace(static_cast<unsigned char>(input[position])) || input[position] == ',')) position++;
    if (position >= input.size() || input[position] == ']') break;
    const char quote = input[position];
    if (quote != '\'' && quote != '"') {
      result.clear();
      return result;
    }
    position++;
    std::string value;
    value.reserve(24);
    bool closed = false;
    while (position < input.size()) {
      char character = input[position++];
      if (character == '\\' && position < input.size()) {
        character = input[position++];
        if (character == 'n') character = '\n';
        else if (character == 'r') character = '\r';
        else if (character == 't') character = '\t';
        value.push_back(character);
      } else if (character == quote) {
        closed = true;
        break;
      } else {
        value.push_back(character);
      }
      if (value.size() > MAX_PAYLOAD - 3) value.resize(MAX_PAYLOAD - 3);
    }
    if (!closed) {
      result.clear();
      return result;
    }
    if (!value.empty()) result.push_back(value);
    while (position < input.size() && isspace(static_cast<unsigned char>(input[position]))) position++;
    if (position < input.size() && input[position] == ']') break;
    if (position >= input.size() || input[position] != ',') {
      result.clear();
      return result;
    }
  }
  return result;
}

struct MediaState {
  uint8_t state{1};
  uint8_t volume_pct{0};
  bool shuffle{false};
  bool repeat_one{false};
  uint32_t position_seconds{0};
  uint32_t duration_seconds{0};
};

struct WeatherState {
  bool temperature_valid{false};
  bool humidity_valid{false};
  bool wind_valid{false};
  bool precipitation_valid{false};
  int16_t temperature_tenths{0};
  uint8_t humidity_pct{0};
  uint16_t wind_tenths{0};
  uint8_t precipitation_probability{0};
};

enum class WeatherCondition : uint8_t {
  UNKNOWN = 0,
  CLEAR_NIGHT = 1,
  CLOUDY = 2,
  EXCEPTIONAL = 3,
  FOG = 4,
  HAIL = 5,
  LIGHTNING = 6,
  LIGHTNING_RAINY = 7,
  PARTLY_CLOUDY = 8,
  POURING = 9,
  RAINY = 10,
  SNOWY = 11,
  SNOWY_RAINY = 12,
  SUNNY = 13,
  WINDY = 14,
  WINDY_VARIANT = 15,
};

struct ForecastState {
  uint8_t daily_valid_mask{0};
  uint8_t hourly_valid_mask{0};
  uint8_t precipitation_probability{0};
  int16_t rain_minutes{-1};
  std::array<int16_t, 5> daily_min_tenths{};
  std::array<int16_t, 5> daily_max_tenths{};
  std::array<uint8_t, 5> daily_condition{};
  std::array<int16_t, 4> hourly_temperature_tenths{};
  std::array<uint8_t, 4> hourly_condition{};
};

struct RadarMeta {
  bool eta_valid{false};
  bool direction_valid{false};
  bool speed_valid{false};
  bool raining{false};
  int16_t eta_minutes{-1};
  uint16_t direction_tenths{0};
  uint16_t speed_tenths{0};
};

inline ForecastState bridge_forecast_cache{};

inline uint8_t weather_condition_code(const std::string &condition) {
  if (condition == "clear-night") return static_cast<uint8_t>(WeatherCondition::CLEAR_NIGHT);
  if (condition == "cloudy") return static_cast<uint8_t>(WeatherCondition::CLOUDY);
  if (condition == "exceptional") return static_cast<uint8_t>(WeatherCondition::EXCEPTIONAL);
  if (condition == "fog") return static_cast<uint8_t>(WeatherCondition::FOG);
  if (condition == "hail") return static_cast<uint8_t>(WeatherCondition::HAIL);
  if (condition == "lightning") return static_cast<uint8_t>(WeatherCondition::LIGHTNING);
  if (condition == "lightning-rainy") return static_cast<uint8_t>(WeatherCondition::LIGHTNING_RAINY);
  if (condition == "partlycloudy") return static_cast<uint8_t>(WeatherCondition::PARTLY_CLOUDY);
  if (condition == "pouring") return static_cast<uint8_t>(WeatherCondition::POURING);
  if (condition == "rainy") return static_cast<uint8_t>(WeatherCondition::RAINY);
  if (condition == "snowy") return static_cast<uint8_t>(WeatherCondition::SNOWY);
  if (condition == "snowy-rainy") return static_cast<uint8_t>(WeatherCondition::SNOWY_RAINY);
  if (condition == "sunny") return static_cast<uint8_t>(WeatherCondition::SUNNY);
  if (condition == "windy") return static_cast<uint8_t>(WeatherCondition::WINDY);
  if (condition == "windy-variant") return static_cast<uint8_t>(WeatherCondition::WINDY_VARIANT);
  return static_cast<uint8_t>(WeatherCondition::UNKNOWN);
}

inline const char *weather_condition_name(uint8_t code) {
  switch (static_cast<WeatherCondition>(code)) {
    case WeatherCondition::CLEAR_NIGHT: return "clear-night";
    case WeatherCondition::CLOUDY: return "cloudy";
    case WeatherCondition::EXCEPTIONAL: return "exceptional";
    case WeatherCondition::FOG: return "fog";
    case WeatherCondition::HAIL: return "hail";
    case WeatherCondition::LIGHTNING: return "lightning";
    case WeatherCondition::LIGHTNING_RAINY: return "lightning-rainy";
    case WeatherCondition::PARTLY_CLOUDY: return "partlycloudy";
    case WeatherCondition::POURING: return "pouring";
    case WeatherCondition::RAINY: return "rainy";
    case WeatherCondition::SNOWY: return "snowy";
    case WeatherCondition::SNOWY_RAINY: return "snowy-rainy";
    case WeatherCondition::SUNNY: return "sunny";
    case WeatherCondition::WINDY: return "windy";
    case WeatherCondition::WINDY_VARIANT: return "windy-variant";
    default: return "unknown";
  }
}

struct Frame {
  MessageType type{MessageType::HELLO};
  uint8_t flags{0};
  uint16_t sequence{0};
  uint8_t length{0};
  std::array<uint8_t, MAX_PAYLOAD> payload{};
};

struct Stats {
  uint32_t received{0};
  uint32_t sent{0};
  uint32_t crc_errors{0};
  uint32_t decode_errors{0};
  uint32_t version_errors{0};
  uint32_t queue_overflows{0};
};

class Link {
 public:
  void setup(esphome::uart::UARTComponent *uart) {
    this->uart_ = uart;
    // A peer may already be transmitting while this MCU boots. Discard the
    // possible partial COBS frame up to the first delimiter, then count only
    // complete frames received after synchronization.
    this->rx_synchronized_ = false;
    this->rx_length_ = 0;
  }

  void poll() {
    if (this->uart_ == nullptr) return;

    uint8_t byte = 0;
    while (this->uart_->available() && this->uart_->read_byte(&byte)) {
      if (!this->rx_synchronized_) {
        if (byte == 0) this->rx_synchronized_ = true;
        continue;
      }
      if (byte == 0) {
        if (this->rx_length_ > 0) this->decode_received_frame_();
        this->rx_length_ = 0;
        continue;
      }

      if (this->rx_length_ >= this->rx_wire_.size()) {
        this->stats_.decode_errors++;
        this->rx_length_ = 0;
        continue;
      }
      this->rx_wire_[this->rx_length_++] = byte;
    }
  }

  bool pop(Frame *frame) {
    if (frame == nullptr || this->queue_count_ == 0) return false;
    *frame = this->queue_[this->queue_head_];
    this->queue_head_ = (this->queue_head_ + 1) % this->queue_.size();
    this->queue_count_--;
    return true;
  }

  // Keep bulk transfer ordering intact, but never let radar/library chunks
  // head-of-line block an encoder, UI action, state update, or latency frame.
  // This is intentionally done at dequeue time so an already buffered bulk
  // burst cannot delay a newly arrived control frame.
  bool pop_priority(Frame *frame) {
    if (frame == nullptr || this->queue_count_ == 0) return false;
    size_t selected_offset = 0;
    bool found_control = false;
    for (size_t offset = 0; offset < this->queue_count_; offset++) {
      const size_t index = (this->queue_head_ + offset) % this->queue_.size();
      if (is_control_frame_(this->queue_[index].type)) {
        selected_offset = offset;
        found_control = true;
        break;
      }
    }
    if (!found_control || selected_offset == 0) return this->pop(frame);

    const size_t selected =
      (this->queue_head_ + selected_offset) % this->queue_.size();
    *frame = this->queue_[selected];
    for (size_t offset = selected_offset; offset + 1 < this->queue_count_; offset++) {
      const size_t current = (this->queue_head_ + offset) % this->queue_.size();
      const size_t next = (this->queue_head_ + offset + 1) % this->queue_.size();
      this->queue_[current] = this->queue_[next];
    }
    this->queue_tail_ =
      (this->queue_tail_ + this->queue_.size() - 1) % this->queue_.size();
    this->queue_count_--;
    return true;
  }

  bool send(MessageType type, const uint8_t *payload = nullptr, uint8_t length = 0,
            uint8_t flags = 0) {
    if (this->uart_ == nullptr || length > MAX_PAYLOAD ||
        (length > 0 && payload == nullptr)) return false;

    std::array<uint8_t, MAX_RAW_FRAME> raw{};
    raw[0] = PROTOCOL_VERSION;
    raw[1] = static_cast<uint8_t>(type);
    raw[2] = flags;
    raw[3] = static_cast<uint8_t>(this->tx_sequence_ & 0xFF);
    raw[4] = static_cast<uint8_t>((this->tx_sequence_ >> 8) & 0xFF);
    raw[5] = length;
    if (length > 0 && payload != nullptr) std::memcpy(&raw[6], payload, length);

    const uint16_t crc = crc16_(raw.data(), 6 + length);
    raw[6 + length] = static_cast<uint8_t>(crc & 0xFF);
    raw[7 + length] = static_cast<uint8_t>((crc >> 8) & 0xFF);

    std::array<uint8_t, MAX_WIRE_FRAME> wire{};
    const size_t encoded = cobs_encode_(raw.data(), 8 + length, wire.data(), wire.size() - 1);
    if (encoded == 0) return false;
    wire[encoded] = 0;
    this->uart_->write_array(wire.data(), encoded + 1);
    this->tx_sequence_++;
    this->stats_.sent++;
    return true;
  }

  bool send_i32(MessageType type, int32_t value) {
    uint8_t payload[4];
    write_u32_(payload, static_cast<uint32_t>(value));
    return this->send(type, payload, sizeof(payload));
  }

  bool send_u32(MessageType type, uint32_t value) {
    uint8_t payload[4];
    write_u32_(payload, value);
    return this->send(type, payload, sizeof(payload));
  }

  bool send_pair_i32(MessageType type, int32_t first, int32_t second) {
    uint8_t payload[8];
    write_u32_(&payload[0], static_cast<uint32_t>(first));
    write_u32_(&payload[4], static_cast<uint32_t>(second));
    return this->send(type, payload, sizeof(payload));
  }

  bool send_pair_u32(MessageType type, uint32_t first, uint32_t second,
                     uint8_t status = 0) {
    uint8_t payload[9];
    write_u32_(&payload[0], first);
    write_u32_(&payload[4], second);
    payload[8] = status;
    return this->send(type, payload, sizeof(payload));
  }

  bool send_ha_action(HAAction action, uint8_t value, const char *entity_id) {
    if (entity_id == nullptr) return false;
    const size_t entity_length = std::min(std::strlen(entity_id), MAX_PAYLOAD - 2);
    uint8_t payload[MAX_PAYLOAD]{};
    payload[0] = static_cast<uint8_t>(action);
    payload[1] = value;
    if (entity_length > 0) std::memcpy(&payload[2], entity_id, entity_length);
    return this->send(MessageType::HA_ACTION, payload,
                      static_cast<uint8_t>(entity_length + 2));
  }

  bool send_ha_text_action(HAAction action, const char *entity_id,
                           const char *value) {
    if (entity_id == nullptr || value == nullptr) return false;
    const size_t entity_length = std::strlen(entity_id);
    const size_t value_length = std::strlen(value);
    if (entity_length == 0 || value_length == 0 ||
        entity_length > 255 || entity_length + value_length + 3 > MAX_PAYLOAD)
      return false;
    uint8_t payload[MAX_PAYLOAD]{};
    payload[0] = static_cast<uint8_t>(action);
    payload[1] = static_cast<uint8_t>(entity_length);
    std::memcpy(&payload[2], entity_id, entity_length);
    payload[2 + entity_length] = 0;
    std::memcpy(&payload[3 + entity_length], value, value_length);
    return this->send(MessageType::HA_ACTION, payload,
                      static_cast<uint8_t>(entity_length + value_length + 3));
  }

  // Dedicated low-latency volume path. The configured bridge target remains
  // authoritative, while the sequence correlates local paint, UART receipt,
  // HA state confirmation, and the final S3 render.
  bool send_volume_set(uint32_t sequence, uint8_t volume_pct) {
    uint8_t payload[5];
    write_u32_(&payload[0], sequence);
    payload[4] = std::min<uint8_t>(volume_pct, 100);
    return this->send(MessageType::VOLUME_SET, payload, sizeof(payload));
  }

  bool send_media_library_play(uint8_t kind, uint16_t index) {
    const uint8_t payload[] = {
      kind,
      static_cast<uint8_t>(index & 0xFF),
      static_cast<uint8_t>((index >> 8) & 0xFF),
    };
    return this->send(MessageType::MEDIA_LIBRARY_PLAY, payload, sizeof(payload));
  }

  // Request a paginated library operation on the network MCU.
  // kind 4 requests playlists; kind 5 requests tracks for playlist_index.
  bool send_library_page_fetch(uint8_t kind, uint16_t offset, uint8_t limit,
                               uint16_t playlist_index = UINT16_MAX,
                               uint16_t context = 0) {
    const uint8_t payload[] = {
      kind,
      static_cast<uint8_t>(offset & 0xFF),
      static_cast<uint8_t>((offset >> 8) & 0xFF),
      limit,
      static_cast<uint8_t>(playlist_index & 0xFF),
      static_cast<uint8_t>((playlist_index >> 8) & 0xFF),
      static_cast<uint8_t>(context & 0xFF),
      static_cast<uint8_t>((context >> 8) & 0xFF),
    };
    return this->send(MessageType::LIBRARY_PAGE_FETCH, payload, sizeof(payload));
  }

  bool send_wled_preset_item(uint8_t slot, uint8_t generation, uint8_t index,
                             const std::string &name) {
    const size_t name_length = std::min(name.size(), MAX_PAYLOAD - 3);
    uint8_t payload[MAX_PAYLOAD]{};
    payload[0] = slot;
    payload[1] = generation;
    payload[2] = index;
    if (name_length > 0) std::memcpy(&payload[3], name.data(), name_length);
    return this->send(MessageType::WLED_PRESET_ITEM, payload,
                      static_cast<uint8_t>(name_length + 3));
  }

  bool send_wled_preset_meta(uint8_t slot, uint8_t generation, uint8_t count,
                             uint8_t selected) {
    const uint8_t payload[] = {slot, generation, count, selected};
    return this->send(MessageType::WLED_PRESET_META, payload, sizeof(payload));
  }

  bool send_light_detail_item(uint8_t slot, uint8_t generation, uint8_t index,
                              const std::string &label) {
    if (slot >= 4 || index >= LIGHT_DETAIL_MAX_ITEMS) return false;
    const size_t label_length = std::min(label.size(), MAX_PAYLOAD - 3);
    uint8_t payload[MAX_PAYLOAD]{};
    payload[0] = slot;
    payload[1] = generation;
    payload[2] = index;
    if (label_length > 0)
      std::memcpy(&payload[3], label.data(), label_length);
    return this->send(MessageType::LIGHT_DETAIL_CATALOG_ITEM, payload,
                      static_cast<uint8_t>(label_length + 3));
  }

  bool send_light_detail_meta(uint8_t slot, uint8_t generation, uint8_t kind,
                              uint8_t count, int selected) {
    if (slot >= 4 || count > LIGHT_DETAIL_MAX_ITEMS) return false;
    const uint8_t payload[] = {
      slot, generation, kind, count,
      static_cast<uint8_t>(
        selected >= 0 && selected < count ? selected : 0xFF),
    };
    return this->send(MessageType::LIGHT_DETAIL_CATALOG_META, payload,
                      sizeof(payload));
  }

  bool send_light_detail_activate(uint8_t slot, uint8_t index) {
    if (slot >= 4 || index >= LIGHT_DETAIL_MAX_ITEMS) return false;
    const uint8_t payload[] = {
      static_cast<uint8_t>(HAAction::LIGHT_DETAIL_ACTIVATE), slot, index,
    };
    return this->send(MessageType::HA_ACTION, payload, sizeof(payload));
  }

  bool send_media_text(MediaTextField field, const std::string &text) {
    const size_t text_length = std::min(text.size(), MAX_PAYLOAD - 1);
    uint8_t payload[MAX_PAYLOAD]{};
    payload[0] = static_cast<uint8_t>(field);
    if (text_length > 0) std::memcpy(&payload[1], text.data(), text_length);
    return this->send(MessageType::MEDIA_TEXT, payload,
                      static_cast<uint8_t>(text_length + 1));
  }

  bool send_media_state(const MediaState &state) {
    uint8_t payload[11]{};
    payload[0] = state.state;
    payload[1] = std::min<uint8_t>(state.volume_pct, 100);
    payload[2] = static_cast<uint8_t>((state.shuffle ? 0x01 : 0x00) |
                                      (state.repeat_one ? 0x02 : 0x00));
    write_u32_(&payload[3], state.position_seconds);
    write_u32_(&payload[7], state.duration_seconds);
    return this->send(MessageType::MEDIA_STATE, payload, sizeof(payload));
  }

  bool send_weather_state(const WeatherState &state) {
    uint8_t payload[7]{};
    payload[0] = static_cast<uint8_t>((state.temperature_valid ? 0x01 : 0x00) |
                                      (state.humidity_valid ? 0x02 : 0x00) |
                                      (state.wind_valid ? 0x04 : 0x00) |
                                      (state.precipitation_valid ? 0x08 : 0x00));
    const uint16_t temperature = static_cast<uint16_t>(state.temperature_tenths);
    payload[1] = static_cast<uint8_t>(temperature & 0xFF);
    payload[2] = static_cast<uint8_t>((temperature >> 8) & 0xFF);
    payload[3] = std::min<uint8_t>(state.humidity_pct, 100);
    payload[4] = static_cast<uint8_t>(state.wind_tenths & 0xFF);
    payload[5] = static_cast<uint8_t>((state.wind_tenths >> 8) & 0xFF);
    payload[6] = std::min<uint8_t>(state.precipitation_probability, 100);
    return this->send(MessageType::WEATHER_STATE, payload, sizeof(payload));
  }

  bool send_weather_text(WeatherTextField field, const std::string &text) {
    const size_t text_length = std::min(text.size(), MAX_PAYLOAD - 1);
    uint8_t payload[MAX_PAYLOAD]{};
    payload[0] = static_cast<uint8_t>(field);
    if (text_length > 0) std::memcpy(&payload[1], text.data(), text_length);
    return this->send(MessageType::WEATHER_TEXT, payload,
                      static_cast<uint8_t>(text_length + 1));
  }

  bool send_weather_forecast(const ForecastState &state) {
    uint8_t payload[42]{};
    payload[0] = state.daily_valid_mask;
    payload[1] = state.hourly_valid_mask;
    payload[2] = std::min<uint8_t>(state.precipitation_probability, 100);
    write_i16_(&payload[3], state.rain_minutes);
    size_t offset = 5;
    for (size_t index = 0; index < 5; index++) {
      write_i16_(&payload[offset], state.daily_min_tenths[index]);
      write_i16_(&payload[offset + 2], state.daily_max_tenths[index]);
      payload[offset + 4] = state.daily_condition[index];
      offset += 5;
    }
    for (size_t index = 0; index < 4; index++) {
      write_i16_(&payload[offset], state.hourly_temperature_tenths[index]);
      payload[offset + 2] = state.hourly_condition[index];
      offset += 3;
    }
    return this->send(MessageType::WEATHER_FORECAST, payload, sizeof(payload));
  }

  bool send_radar_meta(const RadarMeta &state) {
    uint8_t payload[7]{};
    payload[0] = static_cast<uint8_t>(
      (state.eta_valid ? 0x01 : 0x00) |
      (state.direction_valid ? 0x02 : 0x00) |
      (state.speed_valid ? 0x04 : 0x00) |
      (state.raining ? 0x08 : 0x00));
    write_i16_(&payload[1], state.eta_minutes);
    write_u16_(&payload[3], state.direction_tenths);
    write_u16_(&payload[5], state.speed_tenths);
    return this->send(MessageType::RADAR_META, payload, sizeof(payload));
  }

  static bool decode_media_state(const Frame &frame, MediaState *state) {
    if (state == nullptr || frame.type != MessageType::MEDIA_STATE || frame.length < 2) {
      return false;
    }
    state->state = frame.payload[0];
    state->volume_pct = std::min<uint8_t>(frame.payload[1], 100);
    if (frame.length >= 11) {
      state->shuffle = (frame.payload[2] & 0x01) != 0;
      state->repeat_one = (frame.payload[2] & 0x02) != 0;
      state->position_seconds = read_u32(&frame.payload[3]);
      state->duration_seconds = read_u32(&frame.payload[7]);
    }
    return true;
  }

  static bool decode_weather_state(const Frame &frame, WeatherState *state) {
    if (state == nullptr || frame.type != MessageType::WEATHER_STATE ||
        (frame.length != 6 && frame.length != 7)) {
      return false;
    }
    state->temperature_valid = (frame.payload[0] & 0x01) != 0;
    state->humidity_valid = (frame.payload[0] & 0x02) != 0;
    state->wind_valid = (frame.payload[0] & 0x04) != 0;
    state->temperature_tenths = static_cast<int16_t>(
      static_cast<uint16_t>(frame.payload[1]) |
      (static_cast<uint16_t>(frame.payload[2]) << 8));
    state->humidity_pct = std::min<uint8_t>(frame.payload[3], 100);
    state->wind_tenths = static_cast<uint16_t>(frame.payload[4]) |
                         (static_cast<uint16_t>(frame.payload[5]) << 8);
    state->precipitation_valid =
      frame.length >= 7 && (frame.payload[0] & 0x08) != 0;
    state->precipitation_probability =
      frame.length >= 7 ? std::min<uint8_t>(frame.payload[6], 100) : 0;
    return true;
  }

  static bool decode_weather_forecast(const Frame &frame, ForecastState *state) {
    if (state == nullptr || frame.type != MessageType::WEATHER_FORECAST || frame.length != 42) {
      return false;
    }
    state->daily_valid_mask = frame.payload[0];
    state->hourly_valid_mask = frame.payload[1];
    state->precipitation_probability = std::min<uint8_t>(frame.payload[2], 100);
    state->rain_minutes = read_i16_(&frame.payload[3]);
    size_t offset = 5;
    for (size_t index = 0; index < 5; index++) {
      state->daily_min_tenths[index] = read_i16_(&frame.payload[offset]);
      state->daily_max_tenths[index] = read_i16_(&frame.payload[offset + 2]);
      state->daily_condition[index] = frame.payload[offset + 4];
      offset += 5;
    }
    for (size_t index = 0; index < 4; index++) {
      state->hourly_temperature_tenths[index] = read_i16_(&frame.payload[offset]);
      state->hourly_condition[index] = frame.payload[offset + 2];
      offset += 3;
    }
    return true;
  }

  static bool decode_radar_meta(const Frame &frame, RadarMeta *state) {
    if (state == nullptr || frame.type != MessageType::RADAR_META ||
        frame.length != 7) {
      return false;
    }
    state->eta_valid = (frame.payload[0] & 0x01) != 0;
    state->direction_valid = (frame.payload[0] & 0x02) != 0;
    state->speed_valid = (frame.payload[0] & 0x04) != 0;
    state->raining = (frame.payload[0] & 0x08) != 0;
    state->eta_minutes = read_i16_(&frame.payload[1]);
    state->direction_tenths = read_u16(&frame.payload[3]);
    state->speed_tenths = read_u16(&frame.payload[5]);
    return true;
  }

  static std::string read_string(const uint8_t *data, size_t length) {
    return data == nullptr || length == 0
             ? std::string()
             : std::string(reinterpret_cast<const char *>(data), length);
  }

  static uint32_t read_u32(const uint8_t *data) {
    return static_cast<uint32_t>(data[0]) |
           (static_cast<uint32_t>(data[1]) << 8) |
           (static_cast<uint32_t>(data[2]) << 16) |
           (static_cast<uint32_t>(data[3]) << 24);
  }

  static uint16_t read_u16(const uint8_t *data) {
    return static_cast<uint16_t>(data[0]) |
           (static_cast<uint16_t>(data[1]) << 8);
  }

  static int32_t read_i32(const uint8_t *data) {
    return static_cast<int32_t>(read_u32(data));
  }

  const Stats &stats() const { return this->stats_; }

  void reset_stats() { this->stats_ = {}; }

 private:
  static bool is_control_frame_(MessageType type) {
    switch (type) {
      case MessageType::RADAR_BEGIN:
      case MessageType::RADAR_CHUNK:
      case MessageType::RADAR_END:
      case MessageType::RADAR_ACK:
      case MessageType::LIBRARY_BEGIN:
      case MessageType::LIBRARY_CHUNK:
      case MessageType::LIBRARY_END:
      case MessageType::LIBRARY_ACK:
        return false;
      default:
        return true;
    }
  }

  static void write_i16_(uint8_t *data, int16_t value) {
    const uint16_t raw = static_cast<uint16_t>(value);
    data[0] = static_cast<uint8_t>(raw & 0xFF);
    data[1] = static_cast<uint8_t>((raw >> 8) & 0xFF);
  }

  static void write_u16_(uint8_t *data, uint16_t value) {
    data[0] = static_cast<uint8_t>(value & 0xFF);
    data[1] = static_cast<uint8_t>((value >> 8) & 0xFF);
  }

  static int16_t read_i16_(const uint8_t *data) {
    return static_cast<int16_t>(static_cast<uint16_t>(data[0]) |
                                (static_cast<uint16_t>(data[1]) << 8));
  }

  static void write_u32_(uint8_t *data, uint32_t value) {
    data[0] = static_cast<uint8_t>(value & 0xFF);
    data[1] = static_cast<uint8_t>((value >> 8) & 0xFF);
    data[2] = static_cast<uint8_t>((value >> 16) & 0xFF);
    data[3] = static_cast<uint8_t>((value >> 24) & 0xFF);
  }

  static uint16_t crc16_(const uint8_t *data, size_t length) {
    uint16_t crc = 0xFFFF;
    for (size_t i = 0; i < length; i++) {
      crc ^= static_cast<uint16_t>(data[i]) << 8;
      for (uint8_t bit = 0; bit < 8; bit++) {
        crc = (crc & 0x8000) ? static_cast<uint16_t>((crc << 1) ^ 0x1021)
                             : static_cast<uint16_t>(crc << 1);
      }
    }
    return crc;
  }

  static size_t cobs_encode_(const uint8_t *input, size_t length, uint8_t *output,
                             size_t capacity) {
    if (capacity == 0) return 0;
    size_t read_index = 0;
    size_t write_index = 1;
    size_t code_index = 0;
    uint8_t code = 1;

    while (read_index < length) {
      if (input[read_index] == 0) {
        if (code_index >= capacity) return 0;
        output[code_index] = code;
        code = 1;
        code_index = write_index++;
        if (write_index > capacity) return 0;
        read_index++;
      } else {
        if (write_index >= capacity) return 0;
        output[write_index++] = input[read_index++];
        code++;
        if (code == 0xFF) {
          output[code_index] = code;
          code = 1;
          code_index = write_index++;
          if (write_index > capacity) return 0;
        }
      }
    }
    if (code_index >= capacity) return 0;
    output[code_index] = code;
    return write_index;
  }

  static size_t cobs_decode_(const uint8_t *input, size_t length, uint8_t *output,
                             size_t capacity) {
    size_t read_index = 0;
    size_t write_index = 0;

    while (read_index < length) {
      const uint8_t code = input[read_index++];
      if (code == 0) return 0;
      for (uint8_t i = 1; i < code; i++) {
        if (read_index >= length || write_index >= capacity) return 0;
        output[write_index++] = input[read_index++];
      }
      if (code != 0xFF && read_index < length) {
        if (write_index >= capacity) return 0;
        output[write_index++] = 0;
      }
    }
    return write_index;
  }

  void decode_received_frame_() {
    std::array<uint8_t, MAX_RAW_FRAME> raw{};
    const size_t raw_length = cobs_decode_(this->rx_wire_.data(), this->rx_length_,
                                           raw.data(), raw.size());
    if (raw_length < 8) {
      this->stats_.decode_errors++;
      return;
    }
    if (raw[0] != PROTOCOL_VERSION) {
      this->stats_.version_errors++;
      return;
    }

    const uint8_t payload_length = raw[5];
    if (payload_length > MAX_PAYLOAD || raw_length != static_cast<size_t>(8 + payload_length)) {
      this->stats_.decode_errors++;
      return;
    }

    const uint16_t received_crc = static_cast<uint16_t>(raw[6 + payload_length]) |
                                  (static_cast<uint16_t>(raw[7 + payload_length]) << 8);
    if (received_crc != crc16_(raw.data(), 6 + payload_length)) {
      this->stats_.crc_errors++;
      return;
    }
    if (this->queue_count_ >= this->queue_.size()) {
      this->stats_.queue_overflows++;
      return;
    }

    Frame &frame = this->queue_[this->queue_tail_];
    frame.type = static_cast<MessageType>(raw[1]);
    frame.flags = raw[2];
    frame.sequence = static_cast<uint16_t>(raw[3]) |
                     (static_cast<uint16_t>(raw[4]) << 8);
    frame.length = payload_length;
    if (payload_length > 0) std::memcpy(frame.payload.data(), &raw[6], payload_length);
    this->queue_tail_ = (this->queue_tail_ + 1) % this->queue_.size();
    this->queue_count_++;
    this->stats_.received++;
  }

  esphome::uart::UARTComponent *uart_{nullptr};
  uint16_t tx_sequence_{0};
  std::array<uint8_t, MAX_WIRE_FRAME> rx_wire_{};
  size_t rx_length_{0};
  bool rx_synchronized_{false};
  std::array<Frame, FRAME_QUEUE_SIZE> queue_{};
  size_t queue_head_{0};
  size_t queue_tail_{0};
  size_t queue_count_{0};
  Stats stats_{};
};

static constexpr size_t MEDIA_COVER_URL_MAX_LENGTH = 512;

class CoverUrlSender {
 public:
  bool queue(const std::string &url) {
    if (url.size() > MEDIA_COVER_URL_MAX_LENGTH) return false;
    this->url_ = url;
    this->transfer_id_++;
    if (this->transfer_id_ == 0) this->transfer_id_ = 1;
    this->offset_ = 0;
    this->phase_ = 1;
    this->waiting_ack_ = false;
    return true;
  }

  bool poll_send(Link &target) {
    if (this->phase_ == 0) return false;
    if (this->phase_ == 1) {
      const uint16_t length = static_cast<uint16_t>(this->url_.size());
      const uint8_t payload[] = {
        static_cast<uint8_t>(this->transfer_id_ & 0xFF),
        static_cast<uint8_t>((this->transfer_id_ >> 8) & 0xFF),
        static_cast<uint8_t>(length & 0xFF),
        static_cast<uint8_t>((length >> 8) & 0xFF),
      };
      if (!target.send(MessageType::MEDIA_COVER_URL_BEGIN, payload,
                       sizeof(payload))) return false;
      this->phase_ = this->url_.empty() ? 3 : 2;
      return true;
    }
    if (this->phase_ == 2) {
      const size_t length = std::min<size_t>(
        MAX_PAYLOAD - 4, this->url_.size() - this->offset_);
      uint8_t payload[MAX_PAYLOAD]{};
      payload[0] = static_cast<uint8_t>(this->transfer_id_ & 0xFF);
      payload[1] = static_cast<uint8_t>((this->transfer_id_ >> 8) & 0xFF);
      payload[2] = static_cast<uint8_t>(this->offset_ & 0xFF);
      payload[3] = static_cast<uint8_t>((this->offset_ >> 8) & 0xFF);
      std::memcpy(&payload[4], this->url_.data() + this->offset_, length);
      if (!target.send(MessageType::MEDIA_COVER_URL_CHUNK, payload,
                       static_cast<uint8_t>(length + 4))) return false;
      this->offset_ += static_cast<uint16_t>(length);
      if (this->offset_ >= this->url_.size()) this->phase_ = 3;
      return true;
    }
    const uint8_t payload[] = {
      static_cast<uint8_t>(this->transfer_id_ & 0xFF),
      static_cast<uint8_t>((this->transfer_id_ >> 8) & 0xFF),
    };
    if (!target.send(MessageType::MEDIA_COVER_URL_END, payload,
                     sizeof(payload))) return false;
    this->phase_ = 0;
    this->waiting_ack_ = true;
    return true;
  }

  bool acknowledge(const Frame &frame, uint8_t *result = nullptr) {
    if (frame.type != MessageType::MEDIA_COVER_URL_ACK ||
        frame.length != 3 || !this->waiting_ack_) return false;
    const uint16_t id = static_cast<uint16_t>(frame.payload[0]) |
                        (static_cast<uint16_t>(frame.payload[1]) << 8);
    if (id != this->transfer_id_) return false;
    this->waiting_ack_ = false;
    if (result != nullptr) *result = frame.payload[2];
    return true;
  }

  bool busy() const { return this->phase_ != 0; }
  bool waiting_ack() const { return this->waiting_ack_; }
  uint16_t transfer_id() const { return this->transfer_id_; }

 private:
  std::string url_;
  uint16_t transfer_id_{0};
  uint16_t offset_{0};
  uint8_t phase_{0};
  bool waiting_ack_{false};
};

class CoverUrlReceiver {
 public:
  bool begin(const Frame &frame) {
    if (frame.type != MessageType::MEDIA_COVER_URL_BEGIN ||
        frame.length != 4) return false;
    const uint16_t length = static_cast<uint16_t>(frame.payload[2]) |
                            (static_cast<uint16_t>(frame.payload[3]) << 8);
    if (length > MEDIA_COVER_URL_MAX_LENGTH) return false;
    this->transfer_id_ = static_cast<uint16_t>(frame.payload[0]) |
                         (static_cast<uint16_t>(frame.payload[1]) << 8);
    this->total_ = length;
    this->url_.clear();
    this->url_.reserve(length);
    this->active_ = true;
    return true;
  }

  bool append(const Frame &frame) {
    if (!this->active_ || frame.type != MessageType::MEDIA_COVER_URL_CHUNK ||
        frame.length < 4) return false;
    const uint16_t id = static_cast<uint16_t>(frame.payload[0]) |
                        (static_cast<uint16_t>(frame.payload[1]) << 8);
    const uint16_t offset = static_cast<uint16_t>(frame.payload[2]) |
                            (static_cast<uint16_t>(frame.payload[3]) << 8);
    const size_t length = frame.length - 4;
    if (id != this->transfer_id_ || offset != this->url_.size() ||
        this->url_.size() + length > this->total_) {
      this->active_ = false;
      return false;
    }
    this->url_.append(reinterpret_cast<const char *>(&frame.payload[4]), length);
    return true;
  }

  bool finish(const Frame &frame, std::string *url, Link &target) {
    if (frame.type != MessageType::MEDIA_COVER_URL_END ||
        frame.length != 2) return false;
    const uint16_t id = static_cast<uint16_t>(frame.payload[0]) |
                        (static_cast<uint16_t>(frame.payload[1]) << 8);
    const uint8_t result =
      this->active_ && id == this->transfer_id_ &&
      this->url_.size() == this->total_ ? 0 : 1;
    const uint8_t payload[] = {
      frame.payload[0], frame.payload[1], result,
    };
    target.send(MessageType::MEDIA_COVER_URL_ACK, payload, sizeof(payload));
    if (result != 0) {
      this->active_ = false;
      return false;
    }
    if (url != nullptr) *url = this->url_;
    this->active_ = false;
    return true;
  }

 private:
  std::string url_;
  uint16_t transfer_id_{0};
  uint16_t total_{0};
  bool active_{false};
};

inline Link link;
inline CoverUrlSender cover_url_sender;
inline CoverUrlReceiver cover_url_receiver;

}  // namespace dual_mcu
