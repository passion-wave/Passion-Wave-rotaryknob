#pragma once

#include <algorithm>
#include <array>
#include <cstdint>
#include <cstring>
#include <string>
#include <vector>

#include "dual_mcu_link.h"

namespace dual_mcu {

enum class LibraryKind : uint8_t {
  PLAYLISTS = 1,
  RADIOS = 2,
  PODCASTS = 3,
  PLAYLIST_PAGE = 4,
  PLAYLIST_TRACKS = 5,
};

struct LibraryEntry {
  std::string name;
  std::string uri;
  std::string item_id;
  std::string media_type;
};

struct LibraryPageInfo {
  uint16_t total{0};
  uint16_t offset{0};
  uint16_t next_offset{0};
  uint16_t context{0};
  bool paged{false};
  bool has_more{false};
};

static constexpr size_t LIBRARY_MAX_BYTES = 48 * 1024;
static constexpr size_t LIBRARY_CHUNK_BYTES = MAX_PAYLOAD - 6;
static constexpr size_t LIBRARY_MAX_ENTRIES = 64;

inline uint32_t library_crc32_update(uint32_t crc, const uint8_t *data, size_t length) {
  crc = ~crc;
  for (size_t index = 0; index < length; index++) {
    crc ^= data[index];
    for (uint8_t bit = 0; bit < 8; bit++)
      crc = (crc >> 1) ^ (0xEDB88320UL & static_cast<uint32_t>(-(static_cast<int32_t>(crc & 1U))));
  }
  return ~crc;
}

inline void library_write_u16(uint8_t *data, uint16_t value) {
  data[0] = static_cast<uint8_t>(value & 0xFF);
  data[1] = static_cast<uint8_t>((value >> 8) & 0xFF);
}

inline void library_write_u32(uint8_t *data, uint32_t value) {
  data[0] = static_cast<uint8_t>(value & 0xFF);
  data[1] = static_cast<uint8_t>((value >> 8) & 0xFF);
  data[2] = static_cast<uint8_t>((value >> 16) & 0xFF);
  data[3] = static_cast<uint8_t>((value >> 24) & 0xFF);
}

inline uint16_t library_read_u16(const uint8_t *data) {
  return static_cast<uint16_t>(data[0]) | (static_cast<uint16_t>(data[1]) << 8);
}

inline uint32_t library_read_u32(const uint8_t *data) {
  return static_cast<uint32_t>(data[0]) |
         (static_cast<uint32_t>(data[1]) << 8) |
         (static_cast<uint32_t>(data[2]) << 16) |
         (static_cast<uint32_t>(data[3]) << 24);
}

class LibraryProxyServer {
 public:
  bool set(LibraryKind kind, const std::vector<LibraryEntry> &entries) {
    const size_t slot = static_cast<size_t>(kind);
    if (slot == 0 || slot >= this->cache_.size()) return false;
    std::vector<uint8_t> blob;
    blob.reserve(std::min<size_t>(LIBRARY_MAX_BYTES, 4 + entries.size() * 96));
    blob.push_back(1);
    blob.push_back(static_cast<uint8_t>(kind));
    blob.push_back(0);
    blob.push_back(0);
    uint16_t count = 0;
    const size_t entry_count = std::min(entries.size(), LIBRARY_MAX_ENTRIES);
    for (size_t index = 0; index < entry_count; index++) {
      const LibraryEntry &entry = entries[index];
      const size_t entry_start = blob.size();
      if (!this->append_string_(blob, entry.name, 96) ||
          !this->append_string_(blob, entry.uri, 192) ||
          !this->append_string_(blob, entry.item_id, 96) ||
          !this->append_string_(blob, entry.media_type, 24)) {
        blob.resize(entry_start);
        break;
      }
      count++;
    }
    library_write_u16(&blob[2], count);
    this->cache_[slot] = std::move(blob);
    this->contexts_[slot] = 0;
    auto &canonical_entries = this->paged_entries_[slot];
    canonical_entries.assign(entries.begin(), entries.begin() + count);
    this->ready_[slot] = true;
    return true;
  }

  // Accumulate a bounded paginated result on the network processor and send
  // one complete snapshot to the S3. Replacing from `offset` also makes a
  // repeated page response idempotent.
  bool set_page(LibraryKind kind, const std::vector<LibraryEntry> &entries,
                uint16_t offset, uint16_t total, bool has_more,
                uint16_t context = 0) {
    const size_t slot = static_cast<size_t>(kind);
    if (slot == 0 || slot >= this->cache_.size()) return false;
    auto &all = this->paged_entries_[slot];
    const bool stream_page_only = kind == LibraryKind::PLAYLIST_TRACKS;
    if (stream_page_only) {
      // Track lists can contain hundreds of items. Keeping the growing list,
      // rebuilding its complete blob and copying that blob for every UART
      // transfer caused quadratic work and exhausted the classic ESP32 heap
      // on page two. The S3 owns the UI cache, so the network processor only
      // needs to retain and transfer the current delta page.
      all.clear();
      const size_t remaining =
        offset < LIBRARY_MAX_ENTRIES ? LIBRARY_MAX_ENTRIES - offset : 0;
      const size_t page_count = std::min(entries.size(), remaining);
      all.assign(entries.begin(), entries.begin() + page_count);
    } else {
      // Playlist pages stay cumulative because the ESP32 resolves a selected
      // playlist index locally when the S3 requests its tracks.
      if (offset == 0) {
        all.clear();
      } else if (offset > all.size()) {
        return false;
      } else if (offset < all.size()) {
        all.resize(offset);
      }
      for (const auto &entry : entries) {
        if (all.size() >= LIBRARY_MAX_ENTRIES) break;
        all.push_back(entry);
      }
    }

    std::vector<uint8_t> blob;
    blob.reserve(std::min<size_t>(LIBRARY_MAX_BYTES, 9 + all.size() * 96));
    blob.push_back(2);
    blob.push_back(static_cast<uint8_t>(kind));
    blob.push_back(0);
    blob.push_back(0);
    blob.push_back(0);
    blob.push_back(0);
    blob.push_back(0);
    blob.push_back(0);
    blob.push_back(0);
    uint16_t count = 0;
    for (const auto &entry : all) {
      const size_t entry_start = blob.size();
      if (!this->append_string_(blob, entry.name, 96) ||
          !this->append_string_(blob, entry.uri, 192) ||
          !this->append_string_(blob, entry.item_id, 96) ||
          !this->append_string_(blob, entry.media_type, 24)) {
        blob.resize(entry_start);
        break;
      }
      count++;
    }
    library_write_u16(&blob[2], count);
    library_write_u16(&blob[4], total);
    const uint16_t next_offset = static_cast<uint16_t>(
      std::min<size_t>(
        stream_page_only ? static_cast<size_t>(offset) + count : all.size(),
        UINT16_MAX));
    library_write_u16(&blob[6], next_offset);
    blob[8] = (has_more && next_offset < LIBRARY_MAX_ENTRIES) ? 0x01 : 0x00;
    this->cache_[slot] = std::move(blob);
    this->contexts_[slot] = context;
    this->ready_[slot] = true;
    return true;
  }

  bool handle_request(Link &link, const Frame &frame) {
    if (frame.type != MessageType::LIBRARY_REQUEST || frame.length != 1) return false;
    const uint8_t kind = frame.payload[0];
    if (kind == 0 || kind >= this->cache_.size() || !this->ready_[kind]) {
      const uint8_t error[] = {kind, 1};
      link.send(MessageType::LIBRARY_ERROR, error, sizeof(error));
      return false;
    }
    if (this->active_) {
      const uint8_t error[] = {kind, 2};
      link.send(MessageType::LIBRARY_ERROR, error, sizeof(error));
      return false;
    }
    this->kind_ = kind;
    this->active_context_ = this->contexts_[kind];
    // Freeze the selected cache for this transfer. MQTT may refresh the
    // retained list while chunks are still in flight.
    this->active_blob_ = this->cache_[kind];
    this->transfer_id_++;
    if (this->transfer_id_ == 0) this->transfer_id_ = 1;
    this->offset_ = 0;
    this->last_chunk_length_ = 0;
    this->phase_ = Phase::BEGIN;
    this->awaiting_ack_ = false;
    this->active_ = true;
    return true;
  }

  bool poll_send(Link &link) {
    if (!this->active_) return false;
    if (this->awaiting_ack_ && millis() - this->last_send_ms_ < 40) return false;
    const std::vector<uint8_t> &blob = this->active_blob_;
    uint8_t payload[MAX_PAYLOAD]{};
    bool sent = false;
    if (this->phase_ == Phase::BEGIN) {
      payload[0] = this->kind_;
      library_write_u16(&payload[1], this->transfer_id_);
      library_write_u32(&payload[3], static_cast<uint32_t>(blob.size()));
      library_write_u16(&payload[7], this->active_context_);
      sent = link.send(MessageType::LIBRARY_BEGIN, payload, 9);
    } else if (this->phase_ == Phase::CHUNK) {
      library_write_u16(payload, this->transfer_id_);
      library_write_u32(&payload[2], this->offset_);
      this->last_chunk_length_ = static_cast<uint8_t>(
        std::min<size_t>(LIBRARY_CHUNK_BYTES, blob.size() - this->offset_));
      std::memcpy(&payload[6], &blob[this->offset_], this->last_chunk_length_);
      sent = link.send(MessageType::LIBRARY_CHUNK, payload,
                       static_cast<uint8_t>(6 + this->last_chunk_length_));
    } else if (this->phase_ == Phase::END) {
      library_write_u16(payload, this->transfer_id_);
      library_write_u32(&payload[2], static_cast<uint32_t>(blob.size()));
      library_write_u32(&payload[6], library_crc32_update(0, blob.data(), blob.size()));
      sent = link.send(MessageType::LIBRARY_END, payload, 10);
    }
    if (!sent) return false;
    this->last_send_ms_ = millis();
    this->awaiting_ack_ = true;
    return true;
  }

  bool acknowledge(const Frame &frame) {
    if (!this->active_ || !this->awaiting_ack_ ||
        frame.type != MessageType::LIBRARY_ACK || frame.length != 6) return false;
    if (library_read_u16(frame.payload.data()) != this->transfer_id_) return false;
    const uint32_t next_offset = library_read_u32(&frame.payload[2]);
    uint32_t expected = 0;
    if (this->phase_ == Phase::CHUNK) expected = this->offset_ + this->last_chunk_length_;
    else if (this->phase_ == Phase::END) expected = this->active_blob_.size();
    if (next_offset != expected) return false;
    this->awaiting_ack_ = false;
    if (this->phase_ == Phase::BEGIN) {
      this->phase_ = this->active_blob_.empty() ? Phase::END : Phase::CHUNK;
    } else if (this->phase_ == Phase::CHUNK) {
      this->offset_ = next_offset;
      if (this->offset_ >= this->active_blob_.size()) this->phase_ = Phase::END;
    } else {
      this->active_ = false;
      this->phase_ = Phase::IDLE;
      this->active_blob_.clear();
    }
    return true;
  }

  bool busy() const { return this->active_; }
  void reset_transfer() {
    this->active_ = false;
    this->awaiting_ack_ = false;
    this->phase_ = Phase::IDLE;
    this->active_blob_.clear();
    this->offset_ = 0;
    this->last_chunk_length_ = 0;
  }
  LibraryKind current_kind() const { return static_cast<LibraryKind>(this->kind_); }

  uint16_t count(LibraryKind kind) const {
    const size_t slot = static_cast<size_t>(kind);
    if (slot == 0 || slot >= this->cache_.size() || !this->ready_[slot] ||
        this->cache_[slot].size() < 4) return 0;
    return library_read_u16(&this->cache_[slot][2]);
  }

  bool entry(LibraryKind kind, uint16_t index, LibraryEntry *result) const {
    if (result == nullptr) return false;
    const size_t slot = static_cast<size_t>(kind);
    if (slot == 0 || slot >= this->paged_entries_.size() ||
        !this->ready_[slot] || index >= this->paged_entries_[slot].size()) return false;
    *result = this->paged_entries_[slot][index];
    return true;
  }

 private:
  enum class Phase : uint8_t { IDLE, BEGIN, CHUNK, END };

  static bool append_string_(std::vector<uint8_t> &blob, const std::string &value,
                             size_t limit) {
    const size_t length = std::min(value.size(), limit);
    if (blob.size() + 2 + length > LIBRARY_MAX_BYTES) return false;
    const size_t offset = blob.size();
    blob.resize(offset + 2 + length);
    library_write_u16(&blob[offset], static_cast<uint16_t>(length));
    if (length > 0) std::memcpy(&blob[offset + 2], value.data(), length);
    return true;
  }

  std::array<std::vector<uint8_t>, 6> cache_{};
  std::array<std::vector<LibraryEntry>, 6> paged_entries_{};
  std::array<uint16_t, 6> contexts_{};
  std::vector<uint8_t> active_blob_{};
  std::array<bool, 6> ready_{};
  bool active_{false};
  bool awaiting_ack_{false};
  uint8_t kind_{0};
  uint16_t transfer_id_{0};
  uint16_t active_context_{0};
  uint32_t offset_{0};
  uint32_t last_send_ms_{0};
  uint8_t last_chunk_length_{0};
  Phase phase_{Phase::IDLE};
};

class LibraryProxyClient {
 public:
  void set_available(bool available) {
    this->available_ = available;
    if (!available) this->reset_();
  }
  bool available() const { return this->available_; }
  bool active() const { return this->waiting_ || this->receiving_; }

  bool request(Link &link, LibraryKind kind) {
    if (!this->available_ || this->active() || millis() < this->retry_after_ms_) return false;
    const uint8_t payload[] = {static_cast<uint8_t>(kind)};
    if (!link.send(MessageType::LIBRARY_REQUEST, payload, sizeof(payload))) return false;
    this->requested_kind_ = static_cast<uint8_t>(kind);
    this->waiting_ = true;
    this->receiving_ = false;
    this->finished_ = false;
    this->started_ms_ = millis();
    return true;
  }

  bool begin(const Frame &frame) {
    if (frame.length != 7 && frame.length != 9) return false;
    const uint8_t kind = frame.payload[0];
    const uint16_t id = library_read_u16(&frame.payload[1]);
    if (this->receiving_ && id == this->transfer_id_) return true;
    if (!this->waiting_ || kind != this->requested_kind_) return false;
    const uint32_t total = library_read_u32(&frame.payload[3]);
    if (total > LIBRARY_MAX_BYTES) return this->fail_(3);
    this->kind_ = kind;
    this->transfer_id_ = id;
    this->expected_total_ = total;
    this->context_ = frame.length == 9
      ? library_read_u16(&frame.payload[7]) : 0;
    this->bytes_.clear();
    this->bytes_.reserve(total);
    this->waiting_ = false;
    this->receiving_ = true;
    this->started_ms_ = millis();
    return true;
  }

  bool append(const Frame &frame) {
    if (!this->receiving_ || frame.length < 7) return false;
    const uint16_t id = library_read_u16(frame.payload.data());
    const uint32_t offset = library_read_u32(&frame.payload[2]);
    const size_t length = frame.length - 6;
    if (id != this->transfer_id_ || offset + length > LIBRARY_MAX_BYTES) return this->fail_(4);
    if (offset < this->bytes_.size()) {
      if (offset + length <= this->bytes_.size() &&
          std::memcmp(&this->bytes_[offset], &frame.payload[6], length) == 0) return true;
      return false;
    }
    if (offset != this->bytes_.size()) return false;
    this->bytes_.insert(this->bytes_.end(), &frame.payload[6], &frame.payload[frame.length]);
    this->started_ms_ = millis();
    return true;
  }

  bool finish(const Frame &frame) {
    if (frame.length != 10) return false;
    const uint16_t id = library_read_u16(frame.payload.data());
    const uint32_t total = library_read_u32(&frame.payload[2]);
    if (this->finished_) return id == this->transfer_id_ && total == this->bytes_.size();
    if (!this->receiving_) return false;
    const uint32_t expected_crc = library_read_u32(&frame.payload[6]);
    const uint32_t actual_crc = library_crc32_update(0, this->bytes_.data(), this->bytes_.size());
    if (id != this->transfer_id_ || total != this->bytes_.size() ||
        total != this->expected_total_ || expected_crc != actual_crc) return this->fail_(5);
    this->receiving_ = false;
    this->finished_ = true;
    this->completed_ = true;
    return true;
  }

  bool send_ack(Link &link) const {
    if (!this->receiving_ && !this->finished_) return false;
    uint8_t payload[6]{};
    library_write_u16(payload, this->transfer_id_);
    library_write_u32(&payload[2], static_cast<uint32_t>(this->bytes_.size()));
    return link.send(MessageType::LIBRARY_ACK, payload, sizeof(payload));
  }

  void remote_error(const Frame &frame) {
    this->fail_(frame.length >= 2 ? frame.payload[1] : 6);
  }

  void tick() {
    if (this->active() && millis() - this->started_ms_ > 12000) this->fail_(7);
  }

  bool take_completed(LibraryKind *kind, std::vector<LibraryEntry> *entries,
                      LibraryPageInfo *page_info = nullptr) {
    if (!this->completed_ || kind == nullptr || entries == nullptr) return false;
    this->completed_ = false;
    *kind = static_cast<LibraryKind>(this->kind_);
    if (!decode_(this->bytes_, this->kind_, entries, page_info)) {
      this->fail_(8);
      return false;
    }
    if (page_info != nullptr) page_info->context = this->context_;
    return true;
  }

  bool take_failure(uint8_t *error) {
    if (!this->failure_pending_) return false;
    this->failure_pending_ = false;
    if (error != nullptr) *error = this->last_error_;
    return true;
  }

  uint8_t kind() const { return this->kind_; }
  size_t bytes() const { return this->bytes_.size(); }

 private:
  static bool decode_(const std::vector<uint8_t> &blob, uint8_t expected_kind,
                      std::vector<LibraryEntry> *entries,
                      LibraryPageInfo *page_info) {
    if (blob.size() < 4 || (blob[0] != 1 && blob[0] != 2) ||
        blob[1] != expected_kind) return false;
    const uint16_t count = library_read_u16(&blob[2]);
    size_t offset = 4;
    if (page_info != nullptr) {
      *page_info = LibraryPageInfo{};
      page_info->total = count;
      page_info->next_offset = count;
    }
    if (blob[0] == 2) {
      if (blob.size() < 9) return false;
      if (page_info != nullptr) {
        page_info->paged = true;
        page_info->total = library_read_u16(&blob[4]);
        page_info->next_offset = library_read_u16(&blob[6]);
        page_info->offset =
          page_info->next_offset >= count ? page_info->next_offset - count : 0;
        page_info->has_more = (blob[8] & 0x01) != 0;
      }
      offset = 9;
    }
    entries->clear();
    entries->reserve(count);
    for (uint16_t index = 0; index < count; index++) {
      LibraryEntry entry;
      std::string *fields[] = {&entry.name, &entry.uri, &entry.item_id, &entry.media_type};
      for (std::string *field : fields) {
        if (offset + 2 > blob.size()) return false;
        const uint16_t length = library_read_u16(&blob[offset]);
        offset += 2;
        if (offset + length > blob.size()) return false;
        field->assign(reinterpret_cast<const char *>(&blob[offset]), length);
        offset += length;
      }
      entries->push_back(std::move(entry));
    }
    return offset == blob.size();
  }

  bool fail_(uint8_t error) {
    this->last_error_ = error;
    this->waiting_ = false;
    this->receiving_ = false;
    this->finished_ = false;
    this->completed_ = false;
    this->failure_pending_ = true;
    this->retry_after_ms_ = millis() + 10000;
    this->bytes_.clear();
    return false;
  }

  void reset_() {
    this->waiting_ = false;
    this->receiving_ = false;
    this->finished_ = false;
    this->completed_ = false;
    this->bytes_.clear();
  }

  bool available_{false};
  bool waiting_{false};
  bool receiving_{false};
  bool finished_{false};
  bool completed_{false};
  bool failure_pending_{false};
  uint8_t requested_kind_{0};
  uint8_t kind_{0};
  uint8_t last_error_{0};
  uint16_t transfer_id_{0};
  uint16_t context_{0};
  uint32_t expected_total_{0};
  uint32_t started_ms_{0};
  uint32_t retry_after_ms_{0};
  std::vector<uint8_t> bytes_{};
};

inline LibraryProxyServer library_server;
inline LibraryProxyClient library_client;

}  // namespace dual_mcu
