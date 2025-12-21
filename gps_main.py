# gps_main.py

from __future__ import annotations

import time
from typing import Optional, Dict, Any

import gps_os
import gps_globalsat  # or gps_bu353n5, depending on your current filename


# ---- Tuning knobs ----
FAST_INTERVAL_S = 1.0
SLOW_INTERVAL_S = 30.0
MISS_LIMIT = 5            # number of consecutive misses before going slow
CACHE_MAX_AGE_S = 1.0      # optional: don't re-poll more often than this


# ---- Internal state ----
_last_result: Optional[Dict[str, Any]] = None
_last_poll_t: float = 0.0
_next_poll_t: float = 0.0
_miss_count: int = 0
_mode: str = "FAST"  # "FAST" or "SLOW"


def gpsloc() -> Optional[Dict[str, Any]]:
    """
    Returns:
      - dict from a provider (fix or acquiring), OR
      - None if nothing available.
    Polling policy:
      - FAST: poll every 1s
      - after MISS_LIMIT consecutive None results: switch to SLOW (30s)
      - any successful response switches back to FAST
    """
    global _last_result, _last_poll_t, _next_poll_t, _miss_count, _mode

    now = time.time()

    # Optional: cache to avoid being called multiple times per second by UI
    if _last_result is not None and (now - _last_poll_t) < CACHE_MAX_AGE_S:
        return _last_result

    # Respect next scheduled poll
    if now < _next_poll_t:
        return _last_result  # could be None, could be last known

    _last_poll_t = now

    # 1) OS provider (optional; if you don’t want OS fallback, remove this block)
    fix = gps_os.get_fix(timeout_s=1.2)
    if fix:
        fix.setdefault("source", "os")
        _on_success(fix)
        return fix

    # 2) External GPS (GlobalSat BU-353 family etc.)
    fix = gps_globalsat.get_fix(timeout_s=1.2, return_acquiring=True)
    if fix:
        _on_success(fix)
        return fix

    # Nothing found this poll
    _on_miss()
    _last_result = None
    return {"state": "absent"}


def _on_success(fix: Dict[str, Any]) -> None:
    """Any reply => go FAST and reset miss counter."""
    global _last_result, _next_poll_t, _miss_count, _mode

    _last_result = fix
    _miss_count = 0
    _mode = "FAST"
    _next_poll_t = time.time() + FAST_INTERVAL_S


def _on_miss() -> None:
    """Consecutive misses => eventually go SLOW."""
    global _next_poll_t, _miss_count, _mode

    _miss_count += 1

    if _miss_count >= MISS_LIMIT:
        _mode = "SLOW"
        _next_poll_t = time.time() + SLOW_INTERVAL_S
    else:
        _mode = "FAST"
        _next_poll_t = time.time() + FAST_INTERVAL_S
