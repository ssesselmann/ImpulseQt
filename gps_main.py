# gps_main.py
from __future__ import annotations

import time
import threading
from typing import Optional, Dict, Any

from shared import logger

try:
    import gps_globalsat
except Exception:
    gps_globalsat = None  # GPS optional

# ---- tuning ----
POLL_INTERVAL_FAST = 1.0
POLL_INTERVAL_SLOW = 15.0
MISS_TO_SLOW = 3
STALE_AFTER_S = 3.5  # if we haven't seen fresh data in this long, treat as not connected

_lock = threading.Lock()
_latest_fix: Optional[Dict[str, Any]] = None
_latest_t: float = 0.0
_last_err: Optional[str] = None

_thread: Optional[threading.Thread] = None
_stop_evt = threading.Event()

# Simple booleans you can use anywhere
connected: bool = False
status: bool = False   # == has_fix


def start_gps() -> None:
    global _thread
    if gps_globalsat is None:
        return
    if _thread and _thread.is_alive():
        return
    _stop_evt.clear()
    _thread = threading.Thread(target=_worker, name="gps-worker", daemon=True)
    _thread.start()
    logger.info("✅ GPS thread started")


def stop_gps() -> None:
    _stop_evt.set()


def get_fix_cached(allow_stale: bool = True) -> Dict[str, Any]:
    """Always returns a dict (never None)."""
    now = time.time()
    with _lock:
        fix = _latest_fix.copy() if isinstance(_latest_fix, dict) else None
        age = (now - _latest_t) if _latest_t else None
        err = _last_err

    if not fix:
        return {"connected": False, "fix": False, "lat": None, "lon": None, "age_s": None, "error": err}

    # If we want fresh-only and it's stale, downgrade
    if (not allow_stale) and (age is not None) and (age > STALE_AFTER_S):
        out = fix.copy()
        out["connected"] = False
        out["fix"] = False
        out["age_s"] = age
        out["error"] = "stale" if err is None else err
        return out

    fix["age_s"] = age
    fix["error"] = err
    return fix


def _set_latest(fix: Dict[str, Any], err: Optional[str]) -> None:
    global _latest_fix, _latest_t, _last_err, connected, status
    now = time.time()

    # derive booleans directly from the fix dict
    is_conn = bool(fix.get("connected") is True)
    has_fix = bool(
        is_conn
        and (fix.get("fix") is True)
        and (fix.get("lat") is not None)
        and (fix.get("lon") is not None)
    )

    with _lock:
        _latest_fix = fix
        _latest_t = now
        _last_err = err
        connected = is_conn
        status = has_fix


def _worker() -> None:
    global _last_err  # <-- declare global ONCE, at top of function

    misses = 0
    poll_s = POLL_INTERVAL_FAST

    while not _stop_evt.is_set():
        try:
            fix = gps_globalsat.get_fix(timeout_s=1.2) if gps_globalsat is not None else None

            if isinstance(fix, dict) and fix:
                misses = 0
                poll_s = POLL_INTERVAL_FAST
                fix.setdefault("source", "globalsat")
                _set_latest(fix, err=None)
            else:
                # normal "no fix yet"
                misses += 1
                if misses >= MISS_TO_SLOW:
                    poll_s = POLL_INTERVAL_SLOW

                # "no fix" is not an error; don't overwrite _latest_fix
                with _lock:
                    _last_err = None

        except Exception as e:
            misses += 1
            if misses >= MISS_TO_SLOW:
                poll_s = POLL_INTERVAL_SLOW
            with _lock:
                _last_err = str(e)

        time.sleep(poll_s)



def debug_status() -> dict:
    with _lock:
        alive = bool(_thread and _thread.is_alive())
        return {
            "thread_alive": alive,
            "latest_t": _latest_t,
            "latest_fix": _latest_fix,
            "last_err": _last_err,
            "connected": connected,
            "status": status,
        }
