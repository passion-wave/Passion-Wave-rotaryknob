#pragma once

#include <string>

namespace scrollwheel_targets {

inline int clamp_index(int index, int count) {
  if (count <= 0) return 0;
  if (index < 0) return 0;
  if (index >= count) return count - 1;
  return index;
}

constexpr int MEDIA_TARGET_COUNT = 5;

inline const char *media_name(int index) {
  static const char *names[MEDIA_TARGET_COUNT] = {
    "Media 1",
    "Media 2",
    "Media 3",
    "Media 4",
    "Media 5",
  };
  return names[clamp_index(index, MEDIA_TARGET_COUNT)];
}

inline const char *media_entity(int index) {
  static const char *entities[MEDIA_TARGET_COUNT] = {
    "media_player.passion_wave_media_1",
    "media_player.passion_wave_media_2",
    "media_player.passion_wave_media_3",
    "media_player.passion_wave_media_4",
    "media_player.passion_wave_media_5",
  };
  return entities[clamp_index(index, MEDIA_TARGET_COUNT)];
}

inline int media_index_from_name(const std::string &name) {
  for (int index = 0; index < MEDIA_TARGET_COUNT; index++) {
    if (name == media_name(index)) return index;
  }
  return 3;
}

constexpr int SCENE_SLOT_COUNT = 3;

inline const char *scene_slot_name(int index) {
  static const char *names[SCENE_SLOT_COUNT] = {
    "Scene Light",
    "WLED Light 1",
    "WLED Light 2",
  };
  return names[clamp_index(index, SCENE_SLOT_COUNT)];
}

inline const char *scene_slot_entity(int index) {
  static const char *entities[SCENE_SLOT_COUNT] = {
    "light.passion_wave_light_1",
    "light.passion_wave_wled_1",
    "light.passion_wave_wled_2",
  };
  return entities[clamp_index(index, SCENE_SLOT_COUNT)];
}

inline bool scene_slot_is_wled(int index) {
  return clamp_index(index, SCENE_SLOT_COUNT) != 0;
}

inline int scene_slot_index_from_name(const std::string &name) {
  for (int index = 0; index < SCENE_SLOT_COUNT; index++) {
    if (name == scene_slot_name(index)) return index;
  }
  return 0;
}

inline int scene_value_count(int scene_slot_index) {
  const int slot = clamp_index(scene_slot_index, SCENE_SLOT_COUNT);
  if (slot == 1) return 2;
  if (slot == 2) return 9;
  return 5;
}

inline const char *scene_value_name(int scene_slot_index, int value_index) {
  static const char *ambiente_names[5] = {
    "Entspannen",
    "Energie",
    "Gedimmt",
    "Goldstern",
    "Hell",
  };
  static const char *wled_1_names[2] = {
    "Police",
    "Warmwhite",
  };
  static const char *wled_2_names[9] = {
    "Bouncing Balls",
    "Chase Rainbow",
    "Colorloop",
    "Fire 2012",
    "Oben_Solid ",
    "Rainbow",
    "Solid",
    "Unten_Solid",
    "test",
  };

  const int slot = clamp_index(scene_slot_index, SCENE_SLOT_COUNT);
  if (slot == 1) return wled_1_names[clamp_index(value_index, 2)];
  if (slot == 2) return wled_2_names[clamp_index(value_index, 9)];
  return ambiente_names[clamp_index(value_index, 5)];
}

inline const char *ambiente_scene_entity(int value_index) {
  static const char *entities[5] = {
    "scene.passion_wave_scene_1",
    "scene.passion_wave_scene_2",
    "scene.passion_wave_scene_3",
    "scene.passion_wave_scene_4",
    "scene.passion_wave_scene_5",
  };
  return entities[clamp_index(value_index, 5)];
}

inline const char *wled_preset_entity(int scene_slot_index) {
  static const char *entities[SCENE_SLOT_COUNT] = {
    "",
    "select.passion_wave_wled_preset_1",
    "select.passion_wave_wled_preset_2",
  };
  return entities[clamp_index(scene_slot_index, SCENE_SLOT_COUNT)];
}

constexpr int LIGHT_TARGET_COUNT = 12;

inline const char *light_target_name(int index) {
  static const char *names[LIGHT_TARGET_COUNT] = {
    "Light 1",
    "Light 2",
    "Light 3",
    "Light 4",
    "Light 5",
    "Light 6",
    "Light 7",
    "Light 8",
    "Light 9",
    "Light 10",
    "Light 11",
    "Light 12",
  };
  return names[clamp_index(index, LIGHT_TARGET_COUNT)];
}

inline const char *light_target_entity(int index) {
  static const char *entities[LIGHT_TARGET_COUNT] = {
    "light.passion_wave_light_1",
    "light.passion_wave_light_2",
    "light.passion_wave_light_3",
    "light.passion_wave_light_4",
    "light.passion_wave_light_5",
    "light.passion_wave_light_6",
    "light.passion_wave_light_7",
    "light.passion_wave_light_8",
    "light.passion_wave_light_9",
    "light.passion_wave_light_10",
    "light.passion_wave_light_11",
    "light.passion_wave_light_12",
  };
  return entities[clamp_index(index, LIGHT_TARGET_COUNT)];
}

inline int light_target_index_from_name(const std::string &name) {
  for (int index = 0; index < LIGHT_TARGET_COUNT; index++) {
    if (name == light_target_name(index)) return index;
  }
  return 0;
}

inline const char *light_slot_name(int slot, int scene_slot_index, int slot_2_index, int slot_3_index, int slot_4_index) {
  if (slot == 0) return scene_slot_name(scene_slot_index);
  if (slot == 1) return light_target_name(slot_2_index);
  if (slot == 2) return light_target_name(slot_3_index);
  return light_target_name(slot_4_index);
}

inline const char *light_slot_entity(int slot, int scene_slot_index, int slot_2_index, int slot_3_index, int slot_4_index) {
  if (slot == 0) return scene_slot_entity(scene_slot_index);
  if (slot == 1) return light_target_entity(slot_2_index);
  if (slot == 2) return light_target_entity(slot_3_index);
  return light_target_entity(slot_4_index);
}

}  // namespace scrollwheel_targets
