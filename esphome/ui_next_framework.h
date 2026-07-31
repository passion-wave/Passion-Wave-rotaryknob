#pragma once

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <string>

#include "esphome/components/font/font.h"
#include "lvgl.h"

namespace ui_next {

enum class View : uint8_t { WEATHER = 0, LIGHT = 1, MEDIA = 2, TIME = 3, MORE = 4 };

enum class LightDetailKind : uint8_t {
  NONE = 0,
  WLED_PRESET = 1,
  HUE_SCENE = 2,
};

static constexpr int kLightDetailMaxItems = 32;
static constexpr int kLightPopupVisibleRows = 8;

enum class Action : uint8_t {
  NONE = 0,
  NAV_WEATHER,
  NAV_LIGHT,
  NAV_MEDIA,
  NAV_TIME,
  NAV_MORE,
  WEATHER_DETAILS,
  WEATHER_RADAR,
  WEATHER_CONTEXT_CLOSE,
  LIGHT_TOGGLE,
  LIGHT_PICKER,
  LIGHT_DETAILS,
  LIGHT_PRESETS,
  LIGHT_OPTION_0,
  LIGHT_OPTION_1,
  LIGHT_OPTION_2,
  LIGHT_OPTION_3,
  LIGHT_OPTION_4,
  LIGHT_OPTION_5,
  LIGHT_OPTION_6,
  LIGHT_OPTION_7,
  LIGHT_OPTION_8,
  LIGHT_OPTION_9,
  LIGHT_OPTION_10,
  LIGHT_OPTION_11,
  LIGHT_OPTION_12,
  LIGHT_OPTION_13,
  LIGHT_OPTION_14,
  LIGHT_OPTION_15,
  LIGHT_OPTION_16,
  LIGHT_OPTION_17,
  LIGHT_OPTION_18,
  LIGHT_OPTION_19,
  LIGHT_OPTION_20,
  LIGHT_OPTION_21,
  LIGHT_OPTION_22,
  LIGHT_OPTION_23,
  LIGHT_OPTION_24,
  LIGHT_OPTION_25,
  LIGHT_OPTION_26,
  LIGHT_OPTION_27,
  LIGHT_OPTION_28,
  LIGHT_OPTION_29,
  LIGHT_OPTION_30,
  LIGHT_OPTION_31,
  LIGHT_POPUP_CLOSE,
  MEDIA_PREVIOUS,
  MEDIA_TOGGLE,
  MEDIA_NEXT,
  MEDIA_PICKER,
  MEDIA_DETAILS,
  MEDIA_SHUFFLE,
  MEDIA_REPEAT,
  MEDIA_CONTEXT_CLOSE,
  TIMER_TOGGLE,
  TIMER_RESET,
  ALARM_TOGGLE,
  MORE_RADAR,
  MORE_PHOTOS,
  MORE_HOUSE,
  MORE_SETTINGS,
};

class Framework {
 public:
  bool build(lv_obj_t *screen, esphome::font::Font *font_12,
             esphome::font::Font *font_14, esphome::font::Font *font_16,
             esphome::font::Font *font_20, esphome::font::Font *font_24,
             esphome::font::Font *font_32, esphome::font::Font *font_56,
             esphome::font::Font *font_88, esphome::font::Font *clock_font,
             esphome::font::Font *icon_20, esphome::font::Font *icon_28,
             esphome::font::Font *icon_42) {
    if (built_) return true;
    if (screen == nullptr || font_12 == nullptr || font_14 == nullptr ||
        font_16 == nullptr || font_20 == nullptr || font_24 == nullptr ||
        font_32 == nullptr || font_56 == nullptr || font_88 == nullptr ||
        clock_font == nullptr || icon_20 == nullptr || icon_28 == nullptr ||
        icon_42 == nullptr) return false;

    fonts_.small = font_12->get_lv_font();
    fonts_.body = font_14->get_lv_font();
    fonts_.body_large = font_16->get_lv_font();
    fonts_.subtitle = font_20->get_lv_font();
    fonts_.title = font_24->get_lv_font();
    fonts_.headline = font_32->get_lv_font();
    fonts_.value = font_56->get_lv_font();
    fonts_.temperature = font_88->get_lv_font();
    fonts_.clock = clock_font->get_lv_font();
    fonts_.icon_small = icon_20->get_lv_font();
    fonts_.icon = icon_28->get_lv_font();
    fonts_.icon_large = icon_42->get_lv_font();

    root_ = lv_obj_create(screen);
    lv_obj_set_pos(root_, 0, 0);
    lv_obj_set_size(root_, 360, 360);
    lv_obj_set_style_radius(root_, 0, LV_PART_MAIN);
    lv_obj_set_style_bg_opa(root_, LV_OPA_TRANSP, LV_PART_MAIN);
    lv_obj_set_style_border_width(root_, 0, LV_PART_MAIN);
    lv_obj_set_style_pad_all(root_, 0, LV_PART_MAIN);
    lv_obj_clear_flag(root_, LV_OBJ_FLAG_SCROLLABLE);
    lv_obj_clear_flag(root_, LV_OBJ_FLAG_CLICKABLE);

    build_weather_();
    build_light_();
    build_media_();
    build_time_();
    build_more_();
    build_navigation_();

    built_ = true;
    show(View::WEATHER);
    bring_to_front();
    return true;
  }

  bool built() const { return built_; }
  bool legacy_visible() const { return legacy_visible_; }
  View view() const { return current_view_; }
  bool light_popup_is_preset() const { return light_popup_preset_mode_; }
  bool light_popup_visible() const { return light_popup_visible_; }
  LightDetailKind light_detail_kind() const { return light_detail_kind_; }

  bool scroll_light_popup(int steps) {
    if (!built_ || !light_popup_visible_ || light_popup_list_ == nullptr ||
        steps == 0)
      return false;
    if (!light_popup_preset_mode_) return false;
    const int maximum_start =
      std::max(0, light_preset_count_ - kLightPopupVisibleRows);
    const int next = std::clamp(
      light_popup_window_start_ + steps, 0, maximum_start);
    if (next == light_popup_window_start_) return false;
    light_popup_window_start_ = next;
    render_light_popup_rows_();
    return true;
  }

  int light_option_index(Action action) const {
    const int row = static_cast<int>(action) -
                    static_cast<int>(Action::LIGHT_OPTION_0);
    if (row < 0 || row >= kLightPopupVisibleRows) return -1;
    return light_popup_preset_mode_
      ? light_popup_window_start_ + row : row;
  }

  void set_suspended(bool suspended) {
    if (root_ == nullptr || suspended_ == suspended) return;
    suspended_ = suspended;
    if (suspended) lv_obj_add_flag(root_, LV_OBJ_FLAG_HIDDEN);
    else {
      lv_obj_clear_flag(root_, LV_OBJ_FLAG_HIDDEN);
      bring_to_front();
    }
  }

  void bring_to_front() {
    if (root_ != nullptr) lv_obj_move_foreground(root_);
  }

  void show(View view) {
    if (!built_) return;
    if (view_initialized_ && !legacy_visible_ && current_view_ == view) return;
    const View previous = current_view_;
    if (previous == View::MEDIA && view != View::MEDIA) set_media_context_visible_(false);
    if (previous == View::WEATHER && view != View::WEATHER) set_weather_context_visible_(false);
    if (previous == View::LIGHT && view != View::LIGHT) set_light_popup_visible_(false, false);
    const bool full_style = !view_initialized_ || legacy_visible_;
    current_view_ = view;
    legacy_visible_ = false;
    set_navigation_visible(true);
    if (!view_initialized_) {
      for (size_t i = 0; i < 5; i++) {
        if (views_[i] == nullptr) continue;
        if (i == static_cast<size_t>(view)) lv_obj_clear_flag(views_[i], LV_OBJ_FLAG_HIDDEN);
        else lv_obj_add_flag(views_[i], LV_OBJ_FLAG_HIDDEN);
      }
    } else {
      if (views_[static_cast<size_t>(previous)] != nullptr)
        lv_obj_add_flag(views_[static_cast<size_t>(previous)], LV_OBJ_FLAG_HIDDEN);
      if (views_[static_cast<size_t>(view)] != nullptr)
        lv_obj_clear_flag(views_[static_cast<size_t>(view)], LV_OBJ_FLAG_HIDDEN);
    }
    if (full_style) style_navigation_();
    else {
      style_navigation_button_(static_cast<int>(previous), false);
      style_navigation_button_(static_cast<int>(view), true);
    }
    view_initialized_ = true;
  }

  void show_legacy(View selected) {
    if (!built_) return;
    current_view_ = selected;
    legacy_visible_ = true;
    for (auto *view : views_) if (view != nullptr) lv_obj_add_flag(view, LV_OBJ_FLAG_HIDDEN);
    // Auxiliary full-screen pages provide their own back/reload controls. The
    // main rail must neither remain visible nor intercept touches above them.
    set_navigation_visible(false);
    bring_to_front();
  }

  // Modal legacy overlays such as the media picker need the complete round
  // canvas. Hide the rail as one unit so its wide, edge-clipped buttons cannot
  // cover popup tabs or intercept their touch events.
  void set_navigation_visible(bool visible) {
    if (!built_ || navigation_visible_ == visible) return;
    navigation_visible_ = visible;
    for (int i = 0; i < 5; i++) {
      if (nav_buttons_[i] != nullptr) {
        if (visible) lv_obj_clear_flag(nav_buttons_[i], LV_OBJ_FLAG_HIDDEN);
        else lv_obj_add_flag(nav_buttons_[i], LV_OBJ_FLAG_HIDDEN);
      }
      if (nav_markers_[i] != nullptr)
        lv_obj_add_flag(nav_markers_[i], LV_OBJ_FLAG_HIDDEN);
    }
    if (visible) style_navigation_();
  }

  Action take_action() {
    const Action action = pending_action_;
    pending_action_ = Action::NONE;
    return action;
  }

  // The right rail changes views on touch-down. Discrete controls still wait
  // for release so a swipe cannot accidentally trigger an action.
  bool handle_navigation_touch(int x, int y) {
    if (!built_ || suspended_ || legacy_visible_ || !navigation_visible_) return false;
    const Action action = navigation_action_at_(x, y);
    if (action == Action::NONE) return false;
    activate_(action);
    return true;
  }

  // Fallback input path for CST816 releases. ESPHome still forwards the same
  // touch to LVGL, but this coordinate map keeps the interface operable if a
  // screen/page reorder cancels LVGL's CLICKED event between press and release.
  bool handle_touch(int x, int y) {
    if (!built_ || suspended_ || legacy_visible_) return false;
    if (!navigation_visible_) return true;

    Action action = Action::NONE;
    if (weather_context_visible_) {
      if (inside_(x, y, 62, 300, 162, 340)) action = Action::WEATHER_RADAR;
      else if (inside_(x, y, 170, 300, 226, 340)) action = Action::WEATHER_CONTEXT_CLOSE;
      if (action == Action::NONE) return true;
      activate_(action);
      return true;
    }
    if (media_context_visible_) {
      if (inside_(x, y, 62, 139, 226, 191)) action = Action::MEDIA_SHUFFLE;
      else if (inside_(x, y, 62, 197, 226, 249)) action = Action::MEDIA_REPEAT;
      else if (inside_(x, y, 95, 260, 193, 307)) action = Action::MEDIA_CONTEXT_CLOSE;
      if (action == Action::NONE) return true;
      activate_(action);
      return true;
    }
    if (light_popup_visible_) {
      if (inside_(x, y, 192, 34, 238, 82)) action = Action::LIGHT_POPUP_CLOSE;
      else if (inside_(x, y, 62, 82, 226, 316)) {
        const int row = (y - 82) / 44;
        if (row >= 0 && row < (light_popup_preset_mode_ ? light_preset_count_ : 4))
          action = static_cast<Action>(static_cast<int>(Action::LIGHT_OPTION_0) + row);
      }
      if (action == Action::NONE) return true;
      activate_(action);
      return true;
    }
    action = navigation_action_at_(x, y);
    if (action == Action::NONE) {
      switch (current_view_) {
        case View::WEATHER:
          if (inside_(x, y, 58, 58, 236, 183)) action = Action::WEATHER_DETAILS;
          break;
        case View::LIGHT:
          if (inside_(x, y, 93, 82, 240, 136)) action = Action::LIGHT_PICKER;
          else if (inside_(x, y, 45, 137, 240, 211)) action = Action::LIGHT_TOGGLE;
          else if (inside_(x, y, 45, 245, 142, 315)) action = Action::LIGHT_TOGGLE;
          else if (inside_(x, y, 140, 245, 245, 315)) action = Action::LIGHT_DETAILS;
          break;
        case View::MEDIA:
          if (inside_(x, y, 55, 150, 120, 222)) action = Action::MEDIA_PREVIOUS;
          else if (inside_(x, y, 116, 150, 188, 224)) action = Action::MEDIA_TOGGLE;
          else if (inside_(x, y, 183, 150, 246, 222)) action = Action::MEDIA_NEXT;
          else if (inside_(x, y, 88, 258, 150, 328)) action = Action::MEDIA_PICKER;
          else if (inside_(x, y, 150, 258, 212, 328)) action = Action::MEDIA_DETAILS;
          break;
        case View::TIME:
          if (inside_(x, y, 45, 165, 145, 226)) action = Action::TIMER_TOGGLE;
          else if (inside_(x, y, 140, 165, 232, 226)) action = Action::TIMER_RESET;
          else if (inside_(x, y, 155, 252, 250, 316)) action = Action::ALARM_TOGGLE;
          break;
        case View::MORE:
          if (inside_(x, y, 42, 93, 145, 197)) action = Action::MORE_RADAR;
          else if (inside_(x, y, 140, 93, 242, 197)) action = Action::MORE_PHOTOS;
          else if (inside_(x, y, 42, 192, 145, 296)) action = Action::MORE_HOUSE;
          else if (inside_(x, y, 140, 192, 242, 296)) action = Action::MORE_SETTINGS;
          break;
      }
    }

    if (action == Action::NONE) return false;
    activate_(action);
    return true;
  }

  void update_status(const char *time, int battery_percent) {
    set_text_(status_time_label_, empty_fallback_(time, "--:--"));
    set_text_fmt_(status_battery_label_, "%d %%",
                  std::clamp(battery_percent, 0, 100));
  }

  void update_weather(float temperature, float minimum, float maximum,
                      int humidity, float wind_speed, const char *condition,
                      const char *condition_text,
                      const char *morning_condition, float morning_temperature,
                      const char *noon_condition, float noon_temperature,
                      const char *evening_condition, float evening_temperature,
                      const char *overnight_condition, float overnight_temperature,
                      const char *tomorrow_condition, float tomorrow_minimum,
                      float tomorrow_maximum, const char *day_after_condition,
                      float day_after_minimum, float day_after_maximum) {
    if (!built_) return;
    const bool daily_range_valid =
      std::isfinite(minimum) && std::isfinite(maximum) &&
      minimum >= -60.0f && maximum <= 60.0f &&
      maximum - minimum >= 1.0f;
    const float scale_minimum = daily_range_valid ? minimum : -10.0f;
    const float scale_maximum = daily_range_valid ? maximum : 40.0f;

    // Apparent-temperature formula. The bridge supplies wind in km/h, while
    // the calculation expects m/s.
    const float safe_temperature = std::isfinite(temperature) ? temperature : 0.0f;
    const float safe_humidity = static_cast<float>(std::clamp(humidity, 0, 100));
    const float safe_wind_ms = std::isfinite(wind_speed)
      ? std::max(0.0f, wind_speed) / 3.6f
      : 0.0f;
    const float vapour_pressure = safe_humidity * 0.01f * 6.105f *
      expf(17.27f * safe_temperature / (237.7f + safe_temperature));
    const float apparent_temperature = safe_temperature +
      0.33f * vapour_pressure - 0.70f * safe_wind_ms - 4.0f;

    set_text_fmt_(weather_temperature_, "%d°", static_cast<int>(lroundf(temperature)));
    set_weather_visual_(weather_condition_, condition);
    set_text_(weather_summary_, empty_fallback_(condition_text, "Wetter"));
    set_text_fmt_(weather_apparent_, "Gefühlt %d°",
                  static_cast<int>(lroundf(apparent_temperature)));
    set_weather_visual_(weather_context_current_icon_, condition);
    set_text_fmt_(weather_context_current_temp_, "%d°", static_cast<int>(lroundf(temperature)));
    set_weather_visual_(weather_context_morning_icon_, morning_condition);
    set_weather_visual_(weather_context_noon_icon_, noon_condition);
    set_weather_visual_(weather_context_evening_icon_, evening_condition);
    set_weather_visual_(weather_context_overnight_icon_, overnight_condition);
    set_text_fmt_(weather_context_morning_temp_, "%d°", static_cast<int>(lroundf(morning_temperature)));
    set_text_fmt_(weather_context_noon_temp_, "%d°", static_cast<int>(lroundf(noon_temperature)));
    set_text_fmt_(weather_context_evening_temp_, "%d°", static_cast<int>(lroundf(evening_temperature)));
    set_text_fmt_(weather_context_overnight_temp_, "%d°", static_cast<int>(lroundf(overnight_temperature)));
    set_weather_visual_(weather_context_tomorrow_icon_, tomorrow_condition);
    set_weather_visual_(weather_context_day_after_icon_, day_after_condition);
    set_text_fmt_(weather_context_tomorrow_range_, "%d/%d°",
                  static_cast<int>(lroundf(tomorrow_minimum)),
                  static_cast<int>(lroundf(tomorrow_maximum)));
    set_text_fmt_(weather_context_day_after_range_, "%d/%d°",
                  static_cast<int>(lroundf(day_after_minimum)),
                  static_cast<int>(lroundf(day_after_maximum)));
    set_text_fmt_(weather_maximum_, "%d°",
                  static_cast<int>(lroundf(scale_maximum)));
    set_text_fmt_(weather_minimum_, "%d°",
                  static_cast<int>(lroundf(scale_minimum)));
    set_text_fmt_(weather_humidity_, "%d%%", std::clamp(humidity, 0, 100));
    set_text_fmt_(weather_wind_, "%d km/h",
                  std::max(0, static_cast<int>(lroundf(wind_speed))));
    const float span = scale_maximum - scale_minimum;
    const int value = std::isfinite(temperature)
      ? static_cast<int>(lroundf((temperature - scale_minimum) * 100.0f / span))
      : 0;
    // Keep the lowest segment active at or below the daily minimum so the
    // current temperature never disappears completely from the bezel.
    const int display_value = std::isfinite(temperature)
      ? std::clamp(value, 1, 100)
      : 0;
    update_arc_(weather_arc_, display_value, &weather_arc_value_);
  }

  void update_light(const char *name, int brightness, bool on) {
    if (!built_) return;
    set_text_(light_name_, empty_fallback_(name, "Licht"));
    set_text_fmt_(light_value_, "%d %%", std::clamp(brightness, 0, 100));
    set_text_(light_state_, on ? "Eingeschaltet" : "Ausgeschaltet");
    set_text_(light_toggle_label_, on ? "AUS" : "EIN");
    if (!light_state_valid_ || last_light_on_ != on) {
      style_action_button_(light_toggle_button_, on ? kCyan : kPanel,
                           on ? kAccentForeground : kWhite);
      last_light_on_ = on;
      light_state_valid_ = true;
    }
  }

  void update_light_options(const char *const light_names[4], int selected_light,
                            LightDetailKind detail_kind,
                            const char *const detail_names[kLightDetailMaxItems],
                            int detail_count, int selected_detail) {
    if (!built_) return;
    light_detail_kind_ = detail_kind;
    light_selected_source_ = std::clamp(selected_light, 0, 3);
    light_preset_count_ = std::clamp(detail_count, 0, kLightDetailMaxItems);
    light_selected_preset_ = light_preset_count_ > 0
      ? std::clamp(selected_detail, -1, light_preset_count_ - 1)
      : -1;
    for (int i = 0; i < 4; i++) {
      const char *value =
        empty_fallback_(light_names[i], "Nicht konfiguriert");
      if (light_names_[i] != value) light_names_[i] = value;
    }
    for (int i = 0; i < kLightDetailMaxItems; i++) {
      if (i < light_preset_count_) {
        const char *value =
          empty_fallback_(detail_names[i], "Nicht konfiguriert");
        if (light_detail_names_[i] != value)
          light_detail_names_[i] = value;
      } else {
        light_detail_names_[i].clear();
      }
    }
    light_popup_window_start_ = std::clamp(
      light_popup_window_start_, 0,
      std::max(0, light_preset_count_ - kLightPopupVisibleRows));
    render_light_popup_rows_();
    if (light_popup_empty_ != nullptr) {
      if (light_popup_preset_mode_ && light_preset_count_ == 0)
        lv_obj_clear_flag(light_popup_empty_, LV_OBJ_FLAG_HIDDEN);
      else lv_obj_add_flag(light_popup_empty_, LV_OBJ_FLAG_HIDDEN);
    }
    if (light_popup_visible_ && light_popup_preset_mode_)
      set_text_(light_popup_title_, light_detail_title_());
  }

  void update_media(const char *title, const char *artist, int volume, bool playing,
                    int position_seconds, int duration_seconds, bool shuffle,
                    bool repeat_one) {
    if (!built_) return;
    set_text_(media_title_, empty_fallback_(title, "Keine Wiedergabe"));
    set_text_(media_artist_, empty_fallback_(artist, "Home Assistant"));
    set_text_fmt_(media_volume_, "%d %%", std::clamp(volume, 0, 100));
    set_text_(media_play_icon_, playing ? "\U0000E034" : "\U0000E037");
    update_arc_(media_arc_, std::clamp(volume, 0, 100), &media_arc_value_);
    const int safe_duration = std::max(0, duration_seconds);
    const int source_position = std::clamp(position_seconds, 0, safe_duration > 0 ? safe_duration : 0);
    const uint32_t now = lv_tick_get();
    if (!media_position_valid_ || source_position != media_source_position_ ||
        playing != media_position_playing_) {
      media_source_position_ = source_position;
      media_position_anchor_ = source_position;
      media_position_anchor_tick_ = now;
      media_position_playing_ = playing;
      media_position_valid_ = true;
    }
    int safe_position = media_position_anchor_;
    if (playing && safe_duration > 0) {
      safe_position = std::min(safe_duration,
                               media_position_anchor_ +
                               static_cast<int>((now - media_position_anchor_tick_) / 1000U));
    }
    const int progress = safe_duration > 0
      ? std::clamp(static_cast<int>(lroundf(safe_position * 100.0f / safe_duration)), 0, 100)
      : 0;
    if (media_progress_fill_ != nullptr && progress != media_progress_value_) {
      if (progress <= 0) {
        lv_obj_add_flag(media_progress_fill_, LV_OBJ_FLAG_HIDDEN);
      } else {
        lv_obj_set_width(media_progress_fill_, std::max(3, progress * kMediaContentWidth / 100));
        lv_obj_clear_flag(media_progress_fill_, LV_OBJ_FLAG_HIDDEN);
      }
      media_progress_value_ = progress;
    }
    set_text_fmt_(media_progress_elapsed_, "%d:%02d", safe_position / 60, safe_position % 60);
    set_text_fmt_(media_progress_duration_, "%d:%02d", safe_duration / 60, safe_duration % 60);
    if (!media_mode_valid_ || shuffle != last_media_shuffle_) {
      style_action_button_(media_shuffle_button_, shuffle ? kCyan : kPanel,
                           shuffle ? kAccentForeground : kWhite);
      last_media_shuffle_ = shuffle;
    }
    if (!media_mode_valid_ || repeat_one != last_media_repeat_) {
      style_action_button_(media_repeat_button_, repeat_one ? kCyan : kPanel,
                           repeat_one ? kAccentForeground : kWhite);
      last_media_repeat_ = repeat_one;
    }
    media_mode_valid_ = true;
  }

  // Encoder hot path: touch only the two LVGL objects whose pixels change.
  // This avoids re-laying out title, artist, transport and progress widgets
  // for every detent.
  void update_media_volume(int volume) {
    if (!built_) return;
    const int safe_volume = std::clamp(volume, 0, 100);
    set_text_fmt_(media_volume_, "%d %%", safe_volume);
    update_arc_(media_arc_, safe_volume, &media_arc_value_);
  }

  void update_time(int remaining_seconds, bool timer_running, bool timer_finished,
                   int alarm_hour, int alarm_minute, bool alarm_enabled) {
    if (!built_) return;
    const int remaining = std::clamp(remaining_seconds, 0, 5999);
    set_text_fmt_(timer_value_, "%02d:%02d", remaining / 60, remaining % 60);
    set_text_(timer_state_, timer_finished ? "Fertig" : (timer_running ? "Läuft" : "Bereit"));
    set_text_(timer_toggle_label_, timer_running ? "PAUSE" : "START");
    set_text_fmt_(alarm_value_, "%02d:%02d", alarm_hour, alarm_minute);
    set_text_(alarm_toggle_label_, alarm_enabled ? "ALARM EIN" : "ALARM AUS");
    if (!alarm_state_valid_ || last_alarm_enabled_ != alarm_enabled) {
      style_action_button_(alarm_toggle_button_, alarm_enabled ? kCyan : kPanel,
                           alarm_enabled ? kAccentForeground : kWhite);
      last_alarm_enabled_ = alarm_enabled;
      alarm_state_valid_ = true;
    }
  }

 private:
  // Restrained, cool-neutral palette. Cyan is reserved for active state and
  // progress; all informational content stays neutral.
  static constexpr uint32_t kBlack = 0x07090B;
  static constexpr uint32_t kPanel = 0x111519;
  static constexpr uint32_t kTrack = 0x292F33;
  static constexpr uint32_t kWhite = 0xF2F1EE;
  static constexpr uint32_t kMuted = 0x899297;
  static constexpr uint32_t kSubtle = 0x596268;
  static constexpr uint32_t kCyan = 0x68B8BA;
  static constexpr uint32_t kAccentForeground = 0x071012;
  static constexpr int kMediaContentWidth = 166;

  struct Fonts {
    const lv_font_t *small{nullptr};
    const lv_font_t *body{nullptr};
    const lv_font_t *body_large{nullptr};
    const lv_font_t *subtitle{nullptr};
    const lv_font_t *title{nullptr};
    const lv_font_t *headline{nullptr};
    const lv_font_t *value{nullptr};
    const lv_font_t *temperature{nullptr};
    const lv_font_t *clock{nullptr};
    const lv_font_t *icon_small{nullptr};
    const lv_font_t *icon{nullptr};
    const lv_font_t *icon_large{nullptr};
  } fonts_;

  struct Binding {
    Framework *owner{nullptr};
    Action action{Action::NONE};
  };

  static void event_cb_(lv_event_t *event) {
    if (lv_event_get_code(event) != LV_EVENT_CLICKED) return;
    auto *binding = static_cast<Binding *>(lv_event_get_user_data(event));
    if (binding == nullptr || binding->owner == nullptr) return;
    binding->owner->activate_(binding->action);
  }

  static bool inside_(int x, int y, int left, int top, int right, int bottom) {
    return x >= left && x <= right && y >= top && y <= bottom;
  }

  static Action navigation_action_at_(int x, int y) {
    if (x < 205) return Action::NONE;
    const int centers[] = {78, 127, 180, 233, 282};
    const Action actions[] = {Action::NAV_WEATHER, Action::NAV_LIGHT,
                              Action::NAV_MEDIA, Action::NAV_TIME,
                              Action::NAV_MORE};
    int nearest = -1;
    int nearest_distance = 1000;
    for (int i = 0; i < 5; i++) {
      const int distance = std::abs(y - centers[i]);
      if (distance < nearest_distance) {
        nearest = i;
        nearest_distance = distance;
      }
    }
    return nearest >= 0 && nearest_distance <= 28 ? actions[nearest] : Action::NONE;
  }

  void activate_(Action action) {
    const uint32_t now = lv_tick_get();
    if (action == last_action_ && now - last_action_tick_ < 180) return;
    last_action_ = action;
    last_action_tick_ = now;
    pending_action_ = action;
    switch (action) {
      case Action::NAV_WEATHER: show(View::WEATHER); break;
      case Action::NAV_LIGHT: show(View::LIGHT); break;
      case Action::NAV_MEDIA: show(View::MEDIA); break;
      case Action::NAV_TIME: show(View::TIME); break;
      case Action::NAV_MORE: show(View::MORE); break;
      case Action::WEATHER_DETAILS:
        set_weather_context_visible_(!weather_context_visible_);
        break;
      case Action::WEATHER_RADAR:
      case Action::WEATHER_CONTEXT_CLOSE:
        set_weather_context_visible_(false);
        break;
      case Action::LIGHT_PICKER:
        set_light_popup_visible_(true, false);
        break;
      case Action::LIGHT_DETAILS:
        pending_action_ = Action::LIGHT_PRESETS;
        set_light_popup_visible_(true, true);
        break;
      case Action::LIGHT_PRESETS:
        set_light_popup_visible_(true, true);
        break;
      case Action::LIGHT_POPUP_CLOSE:
        set_light_popup_visible_(false, light_popup_preset_mode_);
        break;
      case Action::LIGHT_OPTION_0:
      case Action::LIGHT_OPTION_1:
      case Action::LIGHT_OPTION_2:
      case Action::LIGHT_OPTION_3:
      case Action::LIGHT_OPTION_4:
      case Action::LIGHT_OPTION_5:
      case Action::LIGHT_OPTION_6:
      case Action::LIGHT_OPTION_7:
      case Action::LIGHT_OPTION_8:
      case Action::LIGHT_OPTION_9:
      case Action::LIGHT_OPTION_10:
      case Action::LIGHT_OPTION_11:
      case Action::LIGHT_OPTION_12:
      case Action::LIGHT_OPTION_13:
      case Action::LIGHT_OPTION_14:
      case Action::LIGHT_OPTION_15:
      case Action::LIGHT_OPTION_16:
      case Action::LIGHT_OPTION_17:
      case Action::LIGHT_OPTION_18:
      case Action::LIGHT_OPTION_19:
      case Action::LIGHT_OPTION_20:
      case Action::LIGHT_OPTION_21:
      case Action::LIGHT_OPTION_22:
      case Action::LIGHT_OPTION_23:
      case Action::LIGHT_OPTION_24:
      case Action::LIGHT_OPTION_25:
      case Action::LIGHT_OPTION_26:
      case Action::LIGHT_OPTION_27:
      case Action::LIGHT_OPTION_28:
      case Action::LIGHT_OPTION_29:
      case Action::LIGHT_OPTION_30:
      case Action::LIGHT_OPTION_31:
        set_light_popup_visible_(false, light_popup_preset_mode_);
        break;
      case Action::MEDIA_DETAILS:
        set_media_context_visible_(!media_context_visible_);
        break;
      case Action::MEDIA_CONTEXT_CLOSE:
        set_media_context_visible_(false);
        break;
      default: break;
    }
  }

  Binding *binding_(Action action) {
    if (binding_count_ >= sizeof(bindings_) / sizeof(bindings_[0])) return nullptr;
    Binding *binding = &bindings_[binding_count_++];
    binding->owner = this;
    binding->action = action;
    return binding;
  }

  lv_obj_t *make_view_(View view) {
    lv_obj_t *panel = lv_obj_create(root_);
    lv_obj_set_pos(panel, 0, 0);
    lv_obj_set_size(panel, 360, 360);
    lv_obj_set_style_radius(panel, 0, LV_PART_MAIN);
    lv_obj_set_style_bg_color(panel, lv_color_hex(kBlack), LV_PART_MAIN);
    lv_obj_set_style_bg_opa(panel, LV_OPA_COVER, LV_PART_MAIN);
    lv_obj_set_style_border_width(panel, 0, LV_PART_MAIN);
    lv_obj_set_style_pad_all(panel, 0, LV_PART_MAIN);
    lv_obj_clear_flag(panel, LV_OBJ_FLAG_SCROLLABLE);
    lv_obj_clear_flag(panel, LV_OBJ_FLAG_CLICKABLE);
    views_[static_cast<size_t>(view)] = panel;
    return panel;
  }

  lv_obj_t *make_label_(lv_obj_t *parent, int x, int y, int width, int height,
                        const char *text, const lv_font_t *font, uint32_t color,
                        lv_text_align_t align = LV_TEXT_ALIGN_LEFT) {
    lv_obj_t *label = lv_label_create(parent);
    lv_obj_set_pos(label, x, y);
    lv_obj_set_size(label, width, height);
    lv_label_set_text(label, text);
    lv_label_set_long_mode(label, LV_LABEL_LONG_CLIP);
    lv_obj_set_style_text_font(label, font, LV_PART_MAIN);
    lv_obj_set_style_text_color(label, lv_color_hex(color), LV_PART_MAIN);
    lv_obj_set_style_text_align(label, align, LV_PART_MAIN);
    return label;
  }

  lv_obj_t *make_button_(lv_obj_t *parent, int x, int y, int width, int height,
                         Action action, uint32_t background = kPanel,
                         uint32_t foreground = kWhite, int radius = 22) {
    lv_obj_t *button = lv_button_create(parent);
    lv_obj_set_pos(button, x, y);
    lv_obj_set_size(button, width, height);
    lv_obj_set_style_radius(button, radius, LV_PART_MAIN);
    lv_obj_set_style_bg_color(button, lv_color_hex(background), LV_PART_MAIN);
    lv_obj_set_style_bg_opa(button, LV_OPA_COVER, LV_PART_MAIN);
    lv_obj_set_style_border_width(button, 0, LV_PART_MAIN);
    lv_obj_set_style_shadow_width(button, 0, LV_PART_MAIN);
    lv_obj_set_style_pad_all(button, 0, LV_PART_MAIN);
    if (Binding *binding = binding_(action)) {
      lv_obj_add_event_cb(button, event_cb_, LV_EVENT_CLICKED, binding);
    }
    return button;
  }

  lv_obj_t *button_label_(lv_obj_t *button, const char *text, const lv_font_t *font,
                          uint32_t color = kWhite) {
    lv_obj_t *label = lv_label_create(button);
    lv_label_set_text(label, text);
    lv_obj_set_style_text_font(label, font, LV_PART_MAIN);
    lv_obj_set_style_text_color(label, lv_color_hex(color), LV_PART_MAIN);
    lv_obj_center(label);
    return label;
  }

  lv_obj_t *make_arc_(lv_obj_t *parent) {
    lv_obj_t *arc = lv_arc_create(parent);
    lv_obj_set_pos(arc, 6, 6);
    lv_obj_set_size(arc, 348, 348);
    lv_obj_remove_style(arc, nullptr, LV_PART_KNOB);
    lv_obj_clear_flag(arc, LV_OBJ_FLAG_CLICKABLE);
    lv_obj_set_style_bg_opa(arc, LV_OPA_TRANSP, LV_PART_MAIN);
    lv_obj_set_style_arc_width(arc, 7, LV_PART_MAIN);
    lv_obj_set_style_arc_width(arc, 7, LV_PART_INDICATOR);
    lv_obj_set_style_arc_rounded(arc, true, LV_PART_MAIN);
    lv_obj_set_style_arc_rounded(arc, true, LV_PART_INDICATOR);
    lv_obj_set_style_arc_color(arc, lv_color_hex(kTrack), LV_PART_MAIN);
    lv_obj_set_style_arc_color(arc, lv_color_hex(kCyan), LV_PART_INDICATOR);
    lv_obj_set_style_arc_opa(arc, LV_OPA_TRANSP, LV_PART_INDICATOR);
    lv_arc_set_range(arc, 0, 100);
    lv_arc_set_rotation(arc, 105);
    lv_arc_set_bg_angles(arc, 0, 132);
    lv_arc_set_value(arc, 0);
    return arc;
  }

  void update_arc_(lv_obj_t *arc, int value, int *cached_value) {
    if (arc == nullptr) return;
    const int clamped = std::clamp(value, 0, 100);
    if (cached_value != nullptr && *cached_value == clamped) return;
    lv_arc_set_value(arc, clamped);
    lv_obj_set_style_arc_opa(arc, clamped > 0 ? LV_OPA_COVER : LV_OPA_TRANSP,
                             LV_PART_INDICATOR);
    if (cached_value != nullptr) *cached_value = clamped;
  }

  void build_weather_() {
    lv_obj_t *view = make_view_(View::WEATHER);
    weather_arc_ = make_arc_(view);
    // Continue the circular flow beyond the final segments. The labels sit at
    // roughly 246° (upper end) and 96° (lower end) and follow the local tangent.
    weather_maximum_ = make_label_(view, 89, 15, 42, 16, "--°", fonts_.small,
                                   kMuted, LV_TEXT_ALIGN_CENTER);
    weather_minimum_ = make_label_(view, 141, 337, 42, 16, "--°", fonts_.small,
                                   kMuted, LV_TEXT_ALIGN_CENTER);
    lv_obj_set_style_transform_pivot_x(weather_maximum_, 21, LV_PART_MAIN);
    lv_obj_set_style_transform_pivot_y(weather_maximum_, 8, LV_PART_MAIN);
    lv_obj_set_style_transform_angle(weather_maximum_, -240, LV_PART_MAIN);
    lv_obj_set_style_transform_pivot_x(weather_minimum_, 21, LV_PART_MAIN);
    lv_obj_set_style_transform_pivot_y(weather_minimum_, 8, LV_PART_MAIN);
    lv_obj_set_style_transform_angle(weather_minimum_, 60, LV_PART_MAIN);
    // The 88 px font overhangs its nominal advance at the degree glyph. Keep
    // extra transparent space on the right so two-digit values never clip.
    weather_temperature_ = make_label_(view, 66, 68, 142, 96, "18°", fonts_.temperature, kWhite);
    // The condition symbol shares the temperature baseline. The dynamic
    // summary below takes over the former standalone-symbol position.
    weather_condition_ = make_label_(view, 210, 128, 32, 32, "\U0000E430", fonts_.icon,
                                     kMuted, LV_TEXT_ALIGN_CENTER);
    weather_summary_ = make_label_(view, 76, 166, 160, 22,
                                   "Teilweise wolkig", fonts_.body_large,
                                   kWhite, LV_TEXT_ALIGN_LEFT);
    lv_label_set_long_mode(weather_summary_, LV_LABEL_LONG_SCROLL_CIRCULAR);
    weather_apparent_ = make_label_(view, 76, 191, 160, 18,
                                    "Gefühlt 18°", fonts_.small,
                                    kMuted, LV_TEXT_ALIGN_LEFT);

    auto *weather_details = make_button_(view, 58, 58, 178, 158, Action::WEATHER_DETAILS,
                                         kBlack, kWhite, 0);
    lv_obj_set_style_bg_opa(weather_details, LV_OPA_TRANSP, LV_PART_MAIN);

    make_label_(view, 76, 229, 22, 24, "\U0000E798", fonts_.icon_small, kMuted,
                LV_TEXT_ALIGN_CENTER);
    weather_humidity_ = make_label_(view, 102, 230, 43, 22, "--%", fonts_.body_large,
                                    kWhite, LV_TEXT_ALIGN_LEFT);
    weather_metric_divider_ = lv_obj_create(view);
    lv_obj_set_pos(weather_metric_divider_, 145, 230);
    lv_obj_set_size(weather_metric_divider_, 1, 20);
    lv_obj_set_style_bg_color(weather_metric_divider_, lv_color_hex(kTrack), LV_PART_MAIN);
    lv_obj_set_style_bg_opa(weather_metric_divider_, LV_OPA_COVER, LV_PART_MAIN);
    lv_obj_set_style_border_width(weather_metric_divider_, 0, LV_PART_MAIN);
    lv_obj_set_style_pad_all(weather_metric_divider_, 0, LV_PART_MAIN);
    lv_obj_clear_flag(weather_metric_divider_, LV_OBJ_FLAG_SCROLLABLE);
    lv_obj_clear_flag(weather_metric_divider_, LV_OBJ_FLAG_CLICKABLE);
    make_label_(view, 151, 229, 22, 24, "\U0000EFD8", fonts_.icon_small, kMuted,
                LV_TEXT_ALIGN_CENTER);
    // Keep the complete unit visible for values up to 999 km/h. The former
    // 53 px / 16 px combination clipped the final "h" on two-digit values.
    weather_wind_ = make_label_(view, 176, 231, 62, 20, "-- km/h", fonts_.body,
                                kWhite, LV_TEXT_ALIGN_LEFT);

    build_weather_context_(view);
  }

  void build_weather_context_(lv_obj_t *view) {
    weather_context_ = lv_obj_create(view);
    lv_obj_set_pos(weather_context_, 50, 22);
    lv_obj_set_size(weather_context_, 188, 326);
    lv_obj_set_style_radius(weather_context_, 24, LV_PART_MAIN);
    lv_obj_set_style_bg_color(weather_context_, lv_color_hex(kPanel), LV_PART_MAIN);
    lv_obj_set_style_bg_opa(weather_context_, LV_OPA_COVER, LV_PART_MAIN);
    lv_obj_set_style_border_width(weather_context_, 1, LV_PART_MAIN);
    lv_obj_set_style_border_color(weather_context_, lv_color_hex(kTrack), LV_PART_MAIN);
    lv_obj_set_style_pad_all(weather_context_, 0, LV_PART_MAIN);
    lv_obj_clear_flag(weather_context_, LV_OBJ_FLAG_SCROLLABLE);

    make_label_(weather_context_, 14, 9, 160, 18, "HEUTE", fonts_.small,
                kMuted, LV_TEXT_ALIGN_CENTER);
    weather_context_current_icon_ = make_label_(weather_context_, 24, 29, 32, 32,
                                                "\U0000E430", fonts_.icon, kMuted,
                                                LV_TEXT_ALIGN_CENTER);
    weather_context_current_temp_ = make_label_(weather_context_, 66, 27, 92, 40,
                                                "--°", fonts_.headline, kWhite);
    make_separator_(weather_context_, 14, 68, 160);

    make_weather_forecast_row_(weather_context_, 76, "08 Uhr", &weather_context_morning_icon_,
                               &weather_context_morning_temp_);
    make_weather_forecast_row_(weather_context_, 102, "13 Uhr", &weather_context_noon_icon_,
                               &weather_context_noon_temp_);
    make_weather_forecast_row_(weather_context_, 128, "19 Uhr", &weather_context_evening_icon_,
                               &weather_context_evening_temp_);
    make_weather_forecast_row_(weather_context_, 154, "23 Uhr", &weather_context_overnight_icon_,
                               &weather_context_overnight_temp_);
    make_separator_(weather_context_, 14, 184, 160);
    make_label_(weather_context_, 14, 191, 160, 18, "NÄCHSTE TAGE", fonts_.small,
                kMuted, LV_TEXT_ALIGN_CENTER);
    make_weather_daily_row_(weather_context_, 212, "Morgen", &weather_context_tomorrow_icon_,
                            &weather_context_tomorrow_range_);
    make_weather_daily_row_(weather_context_, 238, "+2 Tage", &weather_context_day_after_icon_,
                            &weather_context_day_after_range_);

    auto *radar = make_button_(weather_context_, 12, 280, 100, 34,
                               Action::WEATHER_RADAR, kPanel, kWhite, 17);
    button_label_(radar, "RADAR", fonts_.small, kWhite);
    auto *close = make_button_(weather_context_, 120, 280, 56, 34,
                               Action::WEATHER_CONTEXT_CLOSE, kBlack, kMuted, 17);
    button_label_(close, "\U0000E88A", fonts_.icon, kMuted);
    lv_obj_add_flag(weather_context_, LV_OBJ_FLAG_HIDDEN);
  }

  void make_weather_forecast_row_(lv_obj_t *parent, int y, const char *name,
                                  lv_obj_t **icon_out, lv_obj_t **temp_out) {
    make_label_(parent, 14, y + 4, 72, 20, name, fonts_.body, kWhite);
    *icon_out = make_label_(parent, 91, y, 28, 28, "\U0000E2BD", fonts_.icon,
                            kMuted, LV_TEXT_ALIGN_CENTER);
    *temp_out = make_label_(parent, 126, y + 4, 46, 20, "--°", fonts_.body_large,
                            kWhite, LV_TEXT_ALIGN_RIGHT);
  }

  void make_weather_daily_row_(lv_obj_t *parent, int y, const char *name,
                               lv_obj_t **icon_out, lv_obj_t **range_out) {
    make_label_(parent, 14, y + 3, 72, 20, name, fonts_.body, kWhite);
    *icon_out = make_label_(parent, 87, y, 28, 28, "\U0000E2BD", fonts_.icon,
                           kMuted, LV_TEXT_ALIGN_CENTER);
    *range_out = make_label_(parent, 116, y + 3, 58, 20, "--/--°", fonts_.body,
                            kWhite, LV_TEXT_ALIGN_RIGHT);
  }

  void make_separator_(lv_obj_t *parent, int x, int y, int width) {
    lv_obj_t *line = lv_obj_create(parent);
    lv_obj_set_pos(line, x, y);
    lv_obj_set_size(line, width, 1);
    lv_obj_set_style_bg_color(line, lv_color_hex(kTrack), LV_PART_MAIN);
    lv_obj_set_style_bg_opa(line, LV_OPA_COVER, LV_PART_MAIN);
    lv_obj_set_style_border_width(line, 0, LV_PART_MAIN);
    lv_obj_set_style_pad_all(line, 0, LV_PART_MAIN);
    lv_obj_clear_flag(line, LV_OBJ_FLAG_SCROLLABLE);
    lv_obj_clear_flag(line, LV_OBJ_FLAG_CLICKABLE);
  }

  lv_obj_t *make_metric_panel_(lv_obj_t *parent, int x, int y, int width, int height) {
    lv_obj_t *panel = lv_obj_create(parent);
    lv_obj_set_pos(panel, x, y);
    lv_obj_set_size(panel, width, height);
    lv_obj_set_style_radius(panel, 16, LV_PART_MAIN);
    lv_obj_set_style_bg_color(panel, lv_color_hex(kPanel), LV_PART_MAIN);
    lv_obj_set_style_bg_opa(panel, LV_OPA_COVER, LV_PART_MAIN);
    lv_obj_set_style_border_width(panel, 0, LV_PART_MAIN);
    lv_obj_set_style_pad_all(panel, 0, LV_PART_MAIN);
    lv_obj_clear_flag(panel, LV_OBJ_FLAG_SCROLLABLE);
    lv_obj_clear_flag(panel, LV_OBJ_FLAG_CLICKABLE);
    return panel;
  }

  void build_light_() {
    lv_obj_t *view = make_view_(View::LIGHT);
    make_label_(view, 55, 78, 42, 42, "\U0000E0F0", fonts_.icon_large, kMuted);
    light_name_ = make_label_(view, 103, 82, 135, 32, "Licht", fonts_.title, kWhite);
    auto *name_target = make_button_(view, 96, 72, 145, 55, Action::LIGHT_PICKER,
                                     kBlack, kWhite, 0);
    lv_obj_set_style_bg_opa(name_target, LV_OPA_TRANSP, LV_PART_MAIN);
    light_value_ = make_label_(view, 55, 145, 180, 64, "100 %", fonts_.value, kWhite);
    auto *value_target = make_button_(view, 48, 137, 192, 76, Action::LIGHT_TOGGLE,
                                      kBlack, kWhite, 0);
    lv_obj_set_style_bg_opa(value_target, LV_OPA_TRANSP, LV_PART_MAIN);
    light_state_ = make_label_(view, 57, 211, 180, 22, "Eingeschaltet", fonts_.body, kMuted);
    light_toggle_button_ = make_button_(view, 55, 255, 82, 46, Action::LIGHT_TOGGLE,
                                        kCyan, kAccentForeground, 23);
    light_toggle_label_ = button_label_(light_toggle_button_, "AUS", fonts_.body_large,
                                        kAccentForeground);
    auto *details = make_button_(view, 145, 255, 92, 46, Action::LIGHT_DETAILS, kPanel, kWhite, 23);
    button_label_(details, "DETAILS", fonts_.small, kWhite);

    light_popup_ = lv_obj_create(view);
    lv_obj_set_pos(light_popup_, 50, 28);
    lv_obj_set_size(light_popup_, 188, 304);
    lv_obj_set_style_radius(light_popup_, 28, LV_PART_MAIN);
    lv_obj_set_style_bg_color(light_popup_, lv_color_hex(kPanel), LV_PART_MAIN);
    lv_obj_set_style_bg_opa(light_popup_, LV_OPA_COVER, LV_PART_MAIN);
    lv_obj_set_style_border_width(light_popup_, 1, LV_PART_MAIN);
    lv_obj_set_style_border_color(light_popup_, lv_color_hex(kTrack), LV_PART_MAIN);
    lv_obj_set_style_pad_all(light_popup_, 0, LV_PART_MAIN);
    lv_obj_clear_flag(light_popup_, LV_OBJ_FLAG_SCROLLABLE);
    light_popup_title_ = make_label_(light_popup_, 14, 16, 128, 20, "LEUCHTEN",
                                     fonts_.body, kWhite);
    auto *close = make_button_(light_popup_, 140, 8, 36, 36,
                               Action::LIGHT_POPUP_CLOSE, 0x1A2024, kMuted, 18);
    button_label_(close, "\U0000E88A", fonts_.icon_small, kMuted);
    light_popup_list_ = lv_obj_create(light_popup_);
    lv_obj_set_pos(light_popup_list_, 12, 52);
    lv_obj_set_size(light_popup_list_, 164, 238);
    lv_obj_set_style_bg_opa(light_popup_list_, LV_OPA_TRANSP, LV_PART_MAIN);
    lv_obj_set_style_border_width(light_popup_list_, 0, LV_PART_MAIN);
    lv_obj_set_style_pad_all(light_popup_list_, 0, LV_PART_MAIN);
    lv_obj_set_scroll_dir(light_popup_list_, LV_DIR_VER);
    lv_obj_set_scrollbar_mode(light_popup_list_, LV_SCROLLBAR_MODE_AUTO);
    lv_obj_set_style_bg_color(light_popup_list_, lv_color_hex(kTrack), LV_PART_SCROLLBAR);
    lv_obj_set_style_width(light_popup_list_, 3, LV_PART_SCROLLBAR);
    const Action option_actions[] = {
      Action::LIGHT_OPTION_0, Action::LIGHT_OPTION_1, Action::LIGHT_OPTION_2,
      Action::LIGHT_OPTION_3, Action::LIGHT_OPTION_4, Action::LIGHT_OPTION_5,
      Action::LIGHT_OPTION_6, Action::LIGHT_OPTION_7,
    };
    for (int i = 0; i < kLightPopupVisibleRows; i++) {
      light_popup_rows_[i] = make_button_(light_popup_list_, 0, i * 44, 158, 40,
                                          option_actions[i], 0x171C20, kWhite, 14);
      light_popup_labels_[i] = button_label_(light_popup_rows_[i], "", fonts_.body, kWhite);
      lv_obj_add_flag(light_popup_rows_[i], LV_OBJ_FLAG_HIDDEN);
    }
    light_popup_empty_ = make_label_(light_popup_list_, 8, 74, 145, 42,
                                     "Keine Details\nverfügbar", fonts_.body,
                                     kMuted, LV_TEXT_ALIGN_CENTER);
    lv_obj_add_flag(light_popup_empty_, LV_OBJ_FLAG_HIDDEN);
    lv_obj_add_flag(light_popup_, LV_OBJ_FLAG_HIDDEN);
  }

  void build_media_() {
    lv_obj_t *view = make_view_(View::MEDIA);
    media_arc_ = make_arc_(view);
    media_title_ = make_label_(view, 69, 63, kMediaContentWidth, 38,
                               "Keine Wiedergabe", fonts_.headline, kWhite);
    lv_label_set_long_mode(media_title_, LV_LABEL_LONG_SCROLL_CIRCULAR);
    media_artist_ = make_label_(view, 69, 102, kMediaContentWidth, 23,
                                "Home Assistant", fonts_.body_large, kMuted);

    media_progress_track_ = lv_obj_create(view);
    lv_obj_set_pos(media_progress_track_, 69, 139);
    lv_obj_set_size(media_progress_track_, kMediaContentWidth, 6);
    lv_obj_set_style_radius(media_progress_track_, 3, LV_PART_MAIN);
    lv_obj_set_style_bg_color(media_progress_track_, lv_color_hex(kTrack), LV_PART_MAIN);
    lv_obj_set_style_bg_opa(media_progress_track_, LV_OPA_COVER, LV_PART_MAIN);
    lv_obj_set_style_border_width(media_progress_track_, 0, LV_PART_MAIN);
    lv_obj_set_style_pad_all(media_progress_track_, 0, LV_PART_MAIN);
    lv_obj_clear_flag(media_progress_track_, LV_OBJ_FLAG_SCROLLABLE);
    lv_obj_clear_flag(media_progress_track_, LV_OBJ_FLAG_CLICKABLE);
    media_progress_fill_ = lv_obj_create(media_progress_track_);
    lv_obj_set_pos(media_progress_fill_, 0, 0);
    lv_obj_set_size(media_progress_fill_, 3, 6);
    lv_obj_set_style_radius(media_progress_fill_, 3, LV_PART_MAIN);
    lv_obj_set_style_bg_color(media_progress_fill_, lv_color_hex(kCyan), LV_PART_MAIN);
    lv_obj_set_style_bg_opa(media_progress_fill_, LV_OPA_COVER, LV_PART_MAIN);
    lv_obj_set_style_border_width(media_progress_fill_, 0, LV_PART_MAIN);
    lv_obj_set_style_pad_all(media_progress_fill_, 0, LV_PART_MAIN);
    lv_obj_clear_flag(media_progress_fill_, LV_OBJ_FLAG_SCROLLABLE);
    lv_obj_clear_flag(media_progress_fill_, LV_OBJ_FLAG_CLICKABLE);
    lv_obj_add_flag(media_progress_fill_, LV_OBJ_FLAG_HIDDEN);
    media_progress_elapsed_ = make_label_(view, 69, 149, 66, 16, "0:00", fonts_.small, kMuted);
    media_progress_duration_ = make_label_(view, 169, 149, 66, 16, "0:00", fonts_.small,
                                          kMuted, LV_TEXT_ALIGN_RIGHT);

    auto *previous = make_button_(view, 65, 172, 48, 48, Action::MEDIA_PREVIOUS, kBlack, kWhite, 24);
    button_label_(previous, "\U0000E045", fonts_.icon, kWhite);
    auto *toggle = make_button_(view, 124, 168, 56, 56, Action::MEDIA_TOGGLE,
                                kCyan, kAccentForeground, 28);
    media_play_icon_ = button_label_(toggle, "\U0000E037", fonts_.icon_large,
                                     kAccentForeground);
    auto *next = make_button_(view, 191, 172, 48, 48, Action::MEDIA_NEXT, kBlack, kWhite, 24);
    button_label_(next, "\U0000E044", fonts_.icon, kWhite);

    media_volume_ = make_label_(view, 141, 337, 42, 16, "-- %", fonts_.small,
                                kMuted, LV_TEXT_ALIGN_CENTER);
    lv_obj_set_style_transform_pivot_x(media_volume_, 21, LV_PART_MAIN);
    lv_obj_set_style_transform_pivot_y(media_volume_, 8, LV_PART_MAIN);
    lv_obj_set_style_transform_angle(media_volume_, 60, LV_PART_MAIN);
    auto *picker = make_button_(view, 96, 270, 48, 48,
                                Action::MEDIA_PICKER, kPanel, kWhite, 24);
    button_label_(picker, "\U0000E8B6", fonts_.icon, kWhite);
    auto *details = make_button_(view, 156, 270, 48, 48,
                                 Action::MEDIA_DETAILS, kPanel, kWhite, 24);
    button_label_(details, "\U0000E5D3", fonts_.icon, kMuted);

    media_context_ = lv_obj_create(view);
    lv_obj_set_pos(media_context_, 50, 76);
    lv_obj_set_size(media_context_, 188, 238);
    lv_obj_set_style_radius(media_context_, 26, LV_PART_MAIN);
    lv_obj_set_style_bg_color(media_context_, lv_color_hex(kPanel), LV_PART_MAIN);
    lv_obj_set_style_bg_opa(media_context_, LV_OPA_COVER, LV_PART_MAIN);
    lv_obj_set_style_border_width(media_context_, 1, LV_PART_MAIN);
    lv_obj_set_style_border_color(media_context_, lv_color_hex(kTrack), LV_PART_MAIN);
    lv_obj_set_style_pad_all(media_context_, 0, LV_PART_MAIN);
    lv_obj_clear_flag(media_context_, LV_OBJ_FLAG_SCROLLABLE);
    make_label_(media_context_, 14, 18, 160, 24, "MEDIENOPTIONEN", fonts_.body, kMuted,
                LV_TEXT_ALIGN_CENTER);
    media_shuffle_button_ = make_button_(media_context_, 12, 63, 164, 48,
                                         Action::MEDIA_SHUFFLE, kPanel, kWhite, 20);
    button_label_(media_shuffle_button_, "SHUFFLE", fonts_.body_large, kWhite);
    media_repeat_button_ = make_button_(media_context_, 12, 121, 164, 48,
                                        Action::MEDIA_REPEAT, kPanel, kWhite, 20);
    button_label_(media_repeat_button_, "REPEAT ONE", fonts_.body_large, kWhite);
    auto *close = make_button_(media_context_, 70, 184, 48, 38,
                               Action::MEDIA_CONTEXT_CLOSE, kBlack, kMuted, 19);
    button_label_(close, "\U0000E88A", fonts_.icon_small, kMuted);
    lv_obj_add_flag(media_context_, LV_OBJ_FLAG_HIDDEN);
  }

  void build_time_() {
    lv_obj_t *view = make_view_(View::TIME);
    make_label_(view, 55, 51, 180, 24, "TIMER", fonts_.body, kMuted);
    timer_value_ = make_label_(view, 54, 78, 185, 65, "01:00", fonts_.value, kWhite);
    timer_state_ = make_label_(view, 57, 143, 100, 22, "Bereit", fonts_.body, kMuted);
    auto *toggle = make_button_(view, 55, 173, 86, 42, Action::TIMER_TOGGLE,
                                kCyan, kAccentForeground, 21);
    timer_toggle_label_ = button_label_(toggle, "START", fonts_.body,
                                        kAccentForeground);
    auto *reset = make_button_(view, 150, 173, 72, 42, Action::TIMER_RESET, kPanel, kWhite, 21);
    button_label_(reset, "RESET", fonts_.small, kWhite);

    make_label_(view, 55, 237, 70, 22, "WECKER", fonts_.body, kMuted);
    alarm_value_ = make_label_(view, 54, 264, 112, 42, "07:00", fonts_.headline, kWhite);
    alarm_toggle_button_ = make_button_(view, 164, 263, 78, 42, Action::ALARM_TOGGLE, kPanel, kWhite, 21);
    alarm_toggle_label_ = button_label_(alarm_toggle_button_, "ALARM AUS", fonts_.small, kWhite);
  }

  void build_more_() {
    lv_obj_t *view = make_view_(View::MORE);
    make_label_(view, 55, 52, 180, 30, "MEHR", fonts_.title, kWhite);
    struct Item { int x; int y; Action action; const char *icon; const char *text; };
    const Item items[] = {
      {52, 103, Action::MORE_RADAR, "\U0000F176", "Radar"},
      {148, 103, Action::MORE_PHOTOS, "\U0000E413", "Fotos"},
      {52, 202, Action::MORE_HOUSE, "\U0000E88A", "Haus"},
      {148, 202, Action::MORE_SETTINGS, "\U0000E8B8", "Setup"},
    };
    for (const auto &item : items) {
      auto *button = make_button_(view, item.x, item.y, 84, 84, item.action, kPanel, kWhite, 26);
      auto *icon = make_label_(button, 0, 10, 84, 37, item.icon, fonts_.icon,
                               kMuted, LV_TEXT_ALIGN_CENTER);
      (void) icon;
      make_label_(button, 0, 52, 84, 18, item.text, fonts_.small, kWhite, LV_TEXT_ALIGN_CENTER);
    }
  }

  void build_navigation_() {
    // Both labels are centered on the physical 360 px display, not merely on
    // the content column to the left of the navigation rail.
    status_time_label_ = make_label_(root_, 112, 8, 136, 34, "--:--", fonts_.clock,
                                     kWhite, LV_TEXT_ALIGN_CENTER);
    status_battery_label_ = make_label_(root_, 140, 41, 80, 16, "-- %", fonts_.small,
                                        kMuted, LV_TEXT_ALIGN_CENTER);
    // Symbol centers follow a 150 px radius around the 180/180 display
    // center. The middle item is furthest right; upper and lower entries move
    // inward with the physical circle. Each text field ends exactly 7 px
    // before its symbol and is right-aligned.
    const int x[] = {210, 234, 244, 234, 210};
    const int y[] = {55, 104, 157, 210, 259};
    const int width[] = {150, 126, 116, 126, 150};
    const Action actions[] = {Action::NAV_WEATHER, Action::NAV_LIGHT, Action::NAV_MEDIA,
                              Action::NAV_TIME, Action::NAV_MORE};
    const char *icons[] = {"\U0000E2BD", "\U0000E0F0", "\U0000E405", "\U0000E425", "\U0000E5D3"};
    const char *names[] = {"Wetter", "Licht", "Medien", "Zeit", "Mehr"};
    for (int i = 0; i < 5; i++) {
      lv_obj_t *button = make_button_(root_, x[i], y[i], width[i], 46, actions[i], kBlack, kSubtle, 0);
      nav_buttons_[i] = button;
      lv_obj_t *icon = make_label_(button, 75, 11, 22, 24, icons[i], fonts_.icon_small,
                                   kSubtle, LV_TEXT_ALIGN_CENTER);
      nav_icon_labels_[i] = icon;
      lv_obj_t *name = make_label_(button, 0, 15, 68, 16, names[i], fonts_.small,
                                   kSubtle, LV_TEXT_ALIGN_RIGHT);
      nav_name_labels_[i] = name;
    }
  }

  void style_navigation_() {
    for (int i = 0; i < 5; i++) {
      const bool active = i == static_cast<int>(current_view_);
      style_navigation_button_(i, active);
    }
  }

  void style_navigation_button_(int index, bool active) {
    if (index < 0 || index >= 5 || nav_buttons_[index] == nullptr) return;
    lv_obj_set_style_bg_color(nav_buttons_[index], lv_color_hex(kBlack), LV_PART_MAIN);
    lv_obj_set_style_border_width(nav_buttons_[index], 0, LV_PART_MAIN);
    // The button remains a full-size invisible touch target. Only its icon
    // and right-aligned label are rendered over the active page.
    lv_obj_set_style_bg_opa(nav_buttons_[index], LV_OPA_TRANSP, LV_PART_MAIN);
    if (nav_icon_labels_[index] != nullptr)
      lv_obj_set_style_text_color(nav_icon_labels_[index],
                                  lv_color_hex(active ? kCyan : kSubtle), LV_PART_MAIN);
    if (nav_name_labels_[index] != nullptr)
      lv_obj_set_style_text_color(nav_name_labels_[index],
                                  lv_color_hex(active ? kWhite : kSubtle), LV_PART_MAIN);
    // Icon and label color are the complete active indication. A separate
    // edge marker would break the radial rhythm and previously appeared as an
    // unrelated vertical line on Media and Time.
  }

  void style_action_button_(lv_obj_t *button, uint32_t background, uint32_t foreground) {
    if (button == nullptr) return;
    lv_obj_set_style_bg_color(button, lv_color_hex(background), LV_PART_MAIN);
    const uint32_t count = lv_obj_get_child_count(button);
    for (uint32_t child = 0; child < count; child++) {
      lv_obj_set_style_text_color(lv_obj_get_child(button, static_cast<int32_t>(child)),
                                  lv_color_hex(foreground), LV_PART_MAIN);
    }
  }

  struct WeatherVisual {
    const char *icon;
    uint32_t color;
  };

  static WeatherVisual weather_visual_(const char *condition) {
    const char *value = empty_fallback_(condition, "partlycloudy");
    if (std::strcmp(value, "sunny") == 0) return {"\U0000E430", kMuted};
    if (std::strcmp(value, "clear-night") == 0) return {"\U0000E51C", kMuted};
    if (std::strcmp(value, "cloudy") == 0) return {"\U0000E2BD", kMuted};
    if (std::strcmp(value, "partlycloudy") == 0) return {"\U0000F172", kMuted};
    if (std::strcmp(value, "fog") == 0) return {"\U0000E818", kMuted};
    if (std::strcmp(value, "windy") == 0 ||
        std::strcmp(value, "windy-variant") == 0)
      return {"\U0000EFD8", kMuted};
    if (std::strcmp(value, "rainy") == 0 || std::strcmp(value, "pouring") == 0 ||
        std::strcmp(value, "hail") == 0 || std::strcmp(value, "snowy-rainy") == 0)
      return {"\U0000F176", kMuted};
    if (std::strcmp(value, "lightning") == 0 ||
        std::strcmp(value, "lightning-rainy") == 0 ||
        std::strcmp(value, "exceptional") == 0)
      return {"\U0000EBDB", kMuted};
    if (std::strcmp(value, "snowy") == 0) return {"\U0000EB3B", kMuted};
    return {"\U0000E8FD", kMuted};
  }

  static void set_weather_visual_(lv_obj_t *label, const char *condition) {
    if (label == nullptr) return;
    const WeatherVisual visual = weather_visual_(condition);
    const char *current = lv_label_get_text(label);
    if (current == nullptr || std::strcmp(current, visual.icon) != 0)
      lv_label_set_text(label, visual.icon);
    lv_obj_set_style_text_color(label, lv_color_hex(visual.color), LV_PART_MAIN);
  }

  void set_weather_context_visible_(bool visible) {
    if (weather_context_ == nullptr) return;
    weather_context_visible_ = visible;
    if (visible) {
      lv_obj_clear_flag(weather_context_, LV_OBJ_FLAG_HIDDEN);
      lv_obj_move_foreground(weather_context_);
    } else {
      lv_obj_add_flag(weather_context_, LV_OBJ_FLAG_HIDDEN);
    }
  }

  void set_media_context_visible_(bool visible) {
    if (media_context_ == nullptr) return;
    media_context_visible_ = visible;
    if (visible) {
      lv_obj_clear_flag(media_context_, LV_OBJ_FLAG_HIDDEN);
      lv_obj_move_foreground(media_context_);
    } else {
      lv_obj_add_flag(media_context_, LV_OBJ_FLAG_HIDDEN);
    }
  }

  void set_light_popup_visible_(bool visible, bool preset_mode) {
    if (light_popup_ == nullptr) return;
    const bool mode_changed = light_popup_preset_mode_ != preset_mode;
    light_popup_visible_ = visible;
    light_popup_preset_mode_ = preset_mode;
    if (visible) {
      if (mode_changed) {
        light_popup_window_start_ =
          preset_mode && light_selected_preset_ >= 0
            ? std::clamp(
                light_selected_preset_ - (kLightPopupVisibleRows / 2), 0,
                std::max(
                  0, light_preset_count_ - kLightPopupVisibleRows))
            : 0;
      }
      // Never reveal the rows from the previously used popup mode. The
      // current catalog is painted by update_light_options() on the next UI
      // tick, keeping the modal reveal atomic instead of briefly showing the
      // light picker underneath a preset/scene list (or vice versa).
      if (mode_changed) {
        for (auto *row : light_popup_rows_) {
          if (row != nullptr) lv_obj_add_flag(row, LV_OBJ_FLAG_HIDDEN);
        }
      }
      set_text_(light_popup_title_, preset_mode ? light_detail_title_() : "LEUCHTEN");
      render_light_popup_rows_();
      lv_obj_clear_flag(light_popup_, LV_OBJ_FLAG_HIDDEN);
      lv_obj_move_foreground(light_popup_);
      lv_obj_scroll_to_y(light_popup_list_, 0, LV_ANIM_OFF);
    } else {
      lv_obj_add_flag(light_popup_, LV_OBJ_FLAG_HIDDEN);
    }
  }

  const char *light_detail_title_() const {
    if (light_detail_kind_ == LightDetailKind::WLED_PRESET) return "WLED PRESETS";
    if (light_detail_kind_ == LightDetailKind::HUE_SCENE) return "HUE SZENEN";
    return "DETAILS";
  }

  void render_light_popup_rows_() {
    for (int row = 0; row < kLightPopupVisibleRows; row++) {
      if (light_popup_rows_[row] == nullptr ||
          light_popup_labels_[row] == nullptr)
        continue;
      const int option = light_popup_preset_mode_
        ? light_popup_window_start_ + row : row;
      const bool available = light_popup_preset_mode_
        ? option >= 0 && option < light_preset_count_
        : option >= 0 && option < 4;
      if (!available) {
        lv_obj_add_flag(light_popup_rows_[row], LV_OBJ_FLAG_HIDDEN);
        continue;
      }
      lv_obj_clear_flag(light_popup_rows_[row], LV_OBJ_FLAG_HIDDEN);
      const std::string &text = light_popup_preset_mode_
        ? light_detail_names_[option] : light_names_[option];
      set_text_(light_popup_labels_[row],
                empty_fallback_(text.c_str(), "Nicht konfiguriert"));
      const bool active = light_popup_preset_mode_
        ? option == light_selected_preset_
        : option == light_selected_source_;
      style_action_button_(
        light_popup_rows_[row], active ? kCyan : 0x171C20,
        active ? kAccentForeground : kWhite);
    }
  }

  static const char *empty_fallback_(const char *value, const char *fallback) {
    return value == nullptr || value[0] == '\0' ? fallback : value;
  }

  static void set_text_(lv_obj_t *label, const char *text) {
    if (label == nullptr || text == nullptr) return;
    const char *current = lv_label_get_text(label);
    if (current != nullptr && std::strcmp(current, text) == 0) return;
    lv_label_set_text(label, text);
  }

  template<typename... Args>
  static void set_text_fmt_(lv_obj_t *label, const char *format, Args... args) {
    char buffer[96];
    std::snprintf(buffer, sizeof(buffer), format, args...);
    set_text_(label, buffer);
  }

  bool built_{false};
  bool view_initialized_{false};
  bool legacy_visible_{false};
  bool suspended_{false};
  View current_view_{View::WEATHER};
  Action pending_action_{Action::NONE};
  Action last_action_{Action::NONE};
  uint32_t last_action_tick_{0};
  int weather_arc_value_{-1};
  int media_arc_value_{-1};
  bool light_state_valid_{false};
  bool last_light_on_{false};
  bool alarm_state_valid_{false};
  bool last_alarm_enabled_{false};
  bool weather_context_visible_{false};
  bool media_context_visible_{false};
  bool light_popup_visible_{false};
  bool light_popup_preset_mode_{false};
  LightDetailKind light_detail_kind_{LightDetailKind::NONE};
  int light_selected_source_{0};
  int light_selected_preset_{0};
  int light_preset_count_{0};
  int light_popup_window_start_{0};
  std::array<std::string, 4> light_names_{};
  std::array<std::string, kLightDetailMaxItems> light_detail_names_{};
  bool media_mode_valid_{false};
  bool last_media_shuffle_{false};
  bool last_media_repeat_{false};
  int media_progress_value_{-1};
  bool media_position_valid_{false};
  bool media_position_playing_{false};
  bool navigation_visible_{true};
  int media_source_position_{0};
  int media_position_anchor_{0};
  uint32_t media_position_anchor_tick_{0};
  lv_obj_t *root_{nullptr};
  lv_obj_t *views_[5]{};
  lv_obj_t *nav_buttons_[5]{};
  lv_obj_t *nav_icon_labels_[5]{};
  lv_obj_t *nav_name_labels_[5]{};
  lv_obj_t *nav_markers_[5]{};
  Binding bindings_[96]{};
  size_t binding_count_{0};

  lv_obj_t *status_time_label_{nullptr};
  lv_obj_t *status_battery_label_{nullptr};
  lv_obj_t *weather_arc_{nullptr};
  lv_obj_t *weather_temperature_{nullptr};
  lv_obj_t *weather_condition_{nullptr};
  lv_obj_t *weather_summary_{nullptr};
  lv_obj_t *weather_apparent_{nullptr};
  lv_obj_t *weather_metric_divider_{nullptr};
  lv_obj_t *weather_maximum_{nullptr};
  lv_obj_t *weather_minimum_{nullptr};
  lv_obj_t *weather_humidity_{nullptr};
  lv_obj_t *weather_wind_{nullptr};
  lv_obj_t *weather_context_{nullptr};
  lv_obj_t *weather_context_current_icon_{nullptr};
  lv_obj_t *weather_context_current_temp_{nullptr};
  lv_obj_t *weather_context_morning_icon_{nullptr};
  lv_obj_t *weather_context_morning_temp_{nullptr};
  lv_obj_t *weather_context_noon_icon_{nullptr};
  lv_obj_t *weather_context_noon_temp_{nullptr};
  lv_obj_t *weather_context_evening_icon_{nullptr};
  lv_obj_t *weather_context_evening_temp_{nullptr};
  lv_obj_t *weather_context_overnight_icon_{nullptr};
  lv_obj_t *weather_context_overnight_temp_{nullptr};
  lv_obj_t *weather_context_tomorrow_icon_{nullptr};
  lv_obj_t *weather_context_tomorrow_range_{nullptr};
  lv_obj_t *weather_context_day_after_icon_{nullptr};
  lv_obj_t *weather_context_day_after_range_{nullptr};
  lv_obj_t *light_name_{nullptr};
  lv_obj_t *light_value_{nullptr};
  lv_obj_t *light_state_{nullptr};
  lv_obj_t *light_toggle_button_{nullptr};
  lv_obj_t *light_toggle_label_{nullptr};
  lv_obj_t *light_popup_{nullptr};
  lv_obj_t *light_popup_title_{nullptr};
  lv_obj_t *light_popup_list_{nullptr};
  lv_obj_t *light_popup_rows_[kLightPopupVisibleRows]{};
  lv_obj_t *light_popup_labels_[kLightPopupVisibleRows]{};
  lv_obj_t *light_popup_empty_{nullptr};
  lv_obj_t *media_arc_{nullptr};
  lv_obj_t *media_title_{nullptr};
  lv_obj_t *media_artist_{nullptr};
  lv_obj_t *media_volume_{nullptr};
  lv_obj_t *media_play_icon_{nullptr};
  lv_obj_t *media_progress_track_{nullptr};
  lv_obj_t *media_progress_fill_{nullptr};
  lv_obj_t *media_progress_elapsed_{nullptr};
  lv_obj_t *media_progress_duration_{nullptr};
  lv_obj_t *media_context_{nullptr};
  lv_obj_t *media_shuffle_button_{nullptr};
  lv_obj_t *media_repeat_button_{nullptr};
  lv_obj_t *timer_value_{nullptr};
  lv_obj_t *timer_state_{nullptr};
  lv_obj_t *timer_toggle_label_{nullptr};
  lv_obj_t *alarm_value_{nullptr};
  lv_obj_t *alarm_toggle_button_{nullptr};
  lv_obj_t *alarm_toggle_label_{nullptr};
};

inline Framework framework;

}  // namespace ui_next
