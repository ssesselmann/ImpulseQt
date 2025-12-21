# gps_main.py
from __future__ import annotations

import time
import threading
import inspect
from typing import Optional, Dict, Any

import gps_globalsat
from shared import logger

# ---- Tuning knobs ----
POLL_INTERVAL_S = 1.0          # how often the GPS thread polls
GLOBALSAT_TIMEOUT_S = 1.2      # serial can be slower; thread isolates it
STALE_AFTER_S = 10.0           # if last fix older than this, treat as stale

# ---- Thread state ----
_lock = threading.Lock()
_latest_fix: Optional[Dict[str, Any]] = None
_latest_t: float = 0.0
_last_err: Optional[str] = None

_thread: Optional[threading.Thread] = None
_stop_evt = threading.Event()


def _call_get_fix(mod, timeout_s: float, return_acquiring: bool = True) -> Optional[Dict[str, Any]]:
    """Call mod.get_fix with only the kwargs it actually supports."""
    fn = getattr(mod, "get_fix", None)
    if fn is None:
        return None

    sig = inspect.signature(fn)
    kwargs = {}
    if "timeout_s" in sig.parameters:
        kwargs["timeout_s"] = timeout_s
    if return_acquiring and "return_acquiring" in sig.parameters:
        kwargs["return_acquiring"] = True

    return fn(**kwargs)


def start_gps() -> None:
    """Start background GPS polling (safe to call multiple times)."""
    global _thread
    if _thread and _thread.is_alive():
        return

    _stop_evt.clear()
    _thread = threading.Thread(target=_worker, name="gps-worker", daemon=True)
    _thread.start()
    logger.info("✅ GPS thread started (globalsat only)")


def stop_gps() -> None:
    _stop_evt.set()


def get_fix_cached(allow_stale: bool = True) -> Dict[str, Any]:
    """Return last known fix instantly (never blocks)."""
    now = time.time()
    with _lock:
        fix = _latest_fix.copy() if isinstance(_latest_fix, dict) else None
        age = (now - _latest_t) if _latest_t else None
        err = _last_err

    if not fix:
        return {"state": "absent", "fix": False, "age_s": None, "error": err}

    # If your UI expects fix['fix'] == True, ensure it exists.
    if "fix" not in fix:
        fix["fix"] = (fix.get("lat") is not None and fix.get("lon") is not None)

    fix["age_s"] = age
    fix["error"] = err

    if (not allow_stale) and (age is not None) and (age > STALE_AFTER_S):
        fix["state"] = "stale"

    return fix


def _publish(fix: Optional[Dict[str, Any]] = None, err: Optional[str] = None) -> None:
    global _latest_fix, _latest_t, _last_err
    with _lock:
        if fix:
            _latest_fix = fix
            _latest_t = time.time()
        _last_err = err


def _worker() -> None:
    consecutive_failures = 0

    while not _stop_evt.is_set():
        t0 = time.time()
        try:
            fix = None
            try:
                fix = _call_get_fix(gps_globalsat, timeout_s=GLOBALSAT_TIMEOUT_S, return_acquiring=True)
                if fix:
                    fix.setdefault("source", "globalsat")
            except Exception as e:
                _publish(err=str(e))

            if fix:
                consecutive_failures = 0
                _publish(fix=fix, err=None)
            else:
                consecutive_failures += 1
                if consecutive_failures % 5 == 0:
                    logger.warning(f"GPS: no fix (fails={consecutive_failures})")

        except Exception as e:
            _publish(err=f"gps worker loop error: {e}")

        dt = time.time() - t0
        time.sleep(max(0.05, POLL_INTERVAL_S - dt))



def make_gps_row(i: int) -> dict:
    """Non-blocking: returns latest cached GPS info for interval index i."""
    fix = get_fix_cached()  # never blocks, just reads worker cache

    return {
        "i": i,
        "t": time.time(),
        "lat": fix.get("lat"),
        "lon": fix.get("lon"),
        "state": fix.get("state", "absent"),
        "source": fix.get("source"),
    }
