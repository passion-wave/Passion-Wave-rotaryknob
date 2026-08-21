#!/usr/bin/env python3
"""Run ESPHome with deterministic generated build metadata.

ESPHome 2026.7.0 uses time.time() for build_info_data.cpp and does not honour
SOURCE_DATE_EPOCH. Patch only that narrow metadata function instead of freezing
Python's process clock, which could break compiler timeouts.
"""

from __future__ import annotations

import os
import sys
import time

from esphome import writer
from esphome.__main__ import main


ORIGINAL_GET_BUILD_INFO = writer.get_build_info


def deterministic_build_info() -> tuple[int, int, str, str]:
    epoch_text = os.environ.get("SOURCE_DATE_EPOCH")
    if epoch_text is None:
        return ORIGINAL_GET_BUILD_INFO()
    epoch = int(epoch_text)
    build_time = time.strftime("%Y-%m-%d %H:%M:%S +0000", time.gmtime(epoch))
    return writer.CORE.config_hash, epoch, build_time, writer.CORE.comment or ""


writer.get_build_info = deterministic_build_info

if __name__ == "__main__":
    sys.exit(main())
