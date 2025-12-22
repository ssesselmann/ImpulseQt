# gps_main.py
from __future__ import annotations

import time
import threading
from typing import Optional, Dict, Any

import gps_globalsat
from shared import logger

# Public: True only when we have a *fresh* fix with lat/lon
status: bool = False

POLL_INTERVAL_FAST = 1.0
POLL_INTERVAL_SLOW = 15.0
MISS_TO_SLOW = 3

# If we haven't received *any* dict update for this long, consider it stale/unplugged
STALE_AFTER_S = 4.0

_lock = threading.Lock()

_latest_fix: Optional[Dict[str, Any]] = None   # last dict returned from device
_latest_t: float = 0.0                         # when _latest_fix was updated
_state: str = "absent"                         # absent | acquiring | fix | error
_last_err: Optional[str] = None

_thread: Optional[threading.Thread] = None
_stop_evt = threading.Event()


def start_gps() -> None:
    """Safe to call repeatedly."""
    global _thread
    if _thread and _thread.is_alive():
        return
    _stop_evt.clear()
    _thread = threading.Thread(target=_worker, name="gps-worker", daemon=True)
    _thread.start()
    logger.info("✅ GPS thread started")


def stop_gps() -> None:
    _stop_evt.set()


def get_fix_cached(allow_stale: bool = True) -> Dict[str, Any]:
    """
    Returns a normalized dict with at least:
      state: absent|acquiring|fix|stale|error
      age_s: float|None
      error: str|None
      lat/lon if known
    Also updates module-level `status`.
    """
    global status

    now = time.time()
    with _lock:
        fix = _latest_fix.copy() if isinstance(_latest_fix, dict) else None
        last_t = _latest_t
        st = _state
        err = _last_err

    age = (now - last_t) if last_t else None

    # No cached data yet
    if not fix:
        status = False
        return {"state": "absent", "age_s": None, "error": err}

    # Stale detection (covers unplug / no updates)
    if age is not None and age > STALE_AFTER_S:
        status = False
        out = fix.copy()
        out["state"] = "stale"
        out["age_s"] = age
        out["error"] = err
        if not allow_stale:
            # explicitly refuse stale coords
            out.pop("lat", None)
            out.pop("lon", None)
        return out

    # Fresh update exists; compute "good fix now"
    lat = fix.get("lat")
    lon = fix.get("lon")
    is_fix = (fix.get("fix") is True) or (st == "fix") or (fix.get("state") == "fix")
    has_coords = (lat is not None) and (lon is not None)

    status = bool(is_fix and has_coords)

    out = fix.copy()
    out["state"] = "fix" if status else st  # keep acquiring/absent/error if not a true fix
    out["age_s"] = age
    out["error"] = err
    return out


def make_gps_row(index: int) -> Dict[str, Any]:
    """
    Convenience for spectrum rows:
    always returns a small dict that won't crash callers.
    """
    fix = get_fix_cached(allow_stale=False)
    return {
        "i": int(index),
        "state": fix.get("state"),
        "lat": fix.get("lat"),
        "lon": fix.get("lon"),
        "epoch": time.time(),
        "age_s": fix.get("age_s"),
        "error": fix.get("error"),
        "source": fix.get("source", "globalsat"),
    }


def _publish(*, fix: Optional[Dict[str, Any]] = None, state: Optional[str] = None, err: Optional[str] = None, touch: bool = False) -> None:
    global _latest_fix, _latest_t, _state, _last_err
    with _lock:
        if isinstance(fix, dict) and fix:
            _latest_fix = fix
        if touch:
            _latest_t = time.time()
        if state:
            _state = state
        _last_err = err


def _worker() -> None:
    misses = 0
    poll_s = POLL_INTERVAL_FAST

    while not _stop_evt.is_set():
        try:
            fix = gps_globalsat.get_fix(timeout_s=1.2)

            if isinstance(fix, dict) and fix:
                fix = fix.copy()
                fix.setdefault("source", "globalsat")

                # Determine state from the device dict
                lat = fix.get("lat")
                lon = fix.get("lon")
                got_coords = (lat is not None) and (lon is not None)
                got_fix = (fix.get("fix") is True) and got_coords

                fix["state"] = "fix" if got_fix else "acquiring"

                _publish(fix=fix, state=fix["state"], err=None, touch=True)

                misses = 0
                poll_s = POLL_INTERVAL_FAST

            else:
                # No dict returned (timeout / no sentence). Don't clobber a previous good fix.
                misses += 1
                if misses >= MISS_TO_SLOW:
                    poll_s = POLL_INTERVAL_SLOW

                # If we have never seen anything, say "absent"; otherwise "acquiring"
                with _lock:
                    ever = bool(_latest_t)

                _publish(state=("acquiring" if ever else "absent"), err=None, touch=False)

        except Exception as e:
            misses += 1
            if misses >= MISS_TO_SLOW:
                poll_s = POLL_INTERVAL_SLOW
            _publish(state="error", err=str(e), touch=False)

        time.sleep(poll_s)
