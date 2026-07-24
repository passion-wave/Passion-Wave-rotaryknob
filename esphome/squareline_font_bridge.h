#pragma once

#ifdef __cplusplus
extern "C" {
#endif

#include <lvgl.h>
#if __has_include(<src/widgets/arc/lv_arc.h>)
#include <src/widgets/arc/lv_arc.h>
#elif __has_include(<src/widgets/lv_arc.h>)
#include <src/widgets/lv_arc.h>
#endif

LV_FONT_DECLARE(ui_font_Number);

#ifdef __cplusplus
}
#endif
