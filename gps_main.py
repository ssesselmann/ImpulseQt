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
STALE_AFTER_S = 3.5  # if no fresh data recently, treat as disconnected / no-fix

_lock = threading.Lock()
_latest_fix: Optional[Dict[str, Any]] = None
_latest_t: float = 0.0
_last_err: Optional[str] = None

_thread: Optional[threading.Thread] = None
_stop_evt = threading.Event()

# Simple booleans you can use anywhere
connected: bool = False   # "we're receiving data recently"
status: bool = False      # == has_fix (fresh + coords)


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
    global connected, status
    _stop_evt.set()
    with _lock:
        connected = False
        status = False


def get_fix_cached(allow_stale: bool = True) -> Dict[str, Any]:
    """
    Always returns a dict (never None).

    NOTE: also refreshes the module-level booleans (connected/status) based on staleness,
    so the UI dot changes even if the GPS gets unplugged and no new messages arrive.
    """
    global connected, status

    now = time.time()
    with _lock:
        fix = _latest_fix.copy() if isinstance(_latest_fix, dict) else None
        age = (now - _latest_t) if _latest_t else None
        err = _last_err

    fresh = bool(age is not None and age <= STALE_AFTER_S)

    # derive booleans from "fresh" + fix content (DO NOT require fix['connected'])
    has_fix = bool(
        fresh
        and isinstance(fix, dict)
        and (fix.get("fix") is True)
        and (fix.get("lat") is not None)
        and (fix.get("lon") is not None)
    )

    # keep your simple globals up to date
    with _lock:
        connected = fresh
        status = has_fix

    if not isinstance(fix, dict):
        return {
            "connected": connected,
            "fix": False,
            "lat": None,
            "lon": None,
            "age_s": age,
            "error": err,
        }

    # optionally downgrade stale
    if (not allow_stale) and (not fresh):
        out = fix.copy()
        out["connected"] = False
        out["fix"] = False
        out["age_s"] = age
        out["error"] = "stale" if err is None else err
        return out

    out = fix.copy()
    out["connected"] = connected
    out["age_s"] = age
    out["error"] = err
    return out


def _set_latest(fix: Dict[str, Any], err: Optional[str]) -> None:
    global _latest_fix, _latest_t, _last_err, connected, status

    now = time.time()

    # normalize minimal schema
    fix = dict(fix)
    fix.setdefault("source", "globalsat")
    fix.setdefault("fix", False)
    fix.setdefault("lat", None)
    fix.setdefault("lon", None)

    # we just received data -> fresh
    _latest_fix = fix
    _latest_t = now
    _last_err = err

    # compute booleans (fresh by definition here)
    connected = True
    status = bool(
        (fix.get("fix") is True)
        and (fix.get("lat") is not None)
        and (fix.get("lon") is not None)
    )


def _worker() -> None:
    misses = 0
    poll_s = POLL_INTERVAL_FAST

    while not _stop_evt.is_set():
        try:
            fix = gps_globalsat.get_fix(timeout_s=1.2) if gps_globalsat is not None else None

            if isinstance(fix, dict) and fix:
                misses = 0
                poll_s = POLL_INTERVAL_FAST
                with _lock:
                    _set_latest(fix, err=None)
            else:
                # no message this cycle (NOT an exception)
                misses += 1
                if misses >= MISS_TO_SLOW:
                    poll_s = POLL_INTERVAL_SLOW
                with _lock:
                    # don't overwrite last fix; staleness logic will flip status/connected
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
