# gps_main.py
from __future__ import annotations

import time
import threading
from typing import Optional, Dict, Any

import gps_globalsat
from shared import logger

POLL_INTERVAL_FAST = 1.0
POLL_INTERVAL_SLOW = 15.0
MISS_TO_SLOW = 3  # after 3 consecutive misses, go slow

_lock = threading.Lock()
_latest_fix: Optional[Dict[str, Any]] = None
_latest_t: float = 0.0
_last_err: Optional[str] = None

_thread: Optional[threading.Thread] = None
_stop_evt = threading.Event()


def start_gps() -> None:
    global _thread
    if _thread and _thread.is_alive():
        return
    _stop_evt.clear()
    _thread = threading.Thread(target=_worker, name="gps-worker", daemon=True)
    _thread.start()
    logger.info("✅ GPS thread started")

def stop_gps() -> None:
    _stop_evt.set()



def get_fix_cached() -> Dict[str, Any]:
    now = time.time()
    with _lock:
        fix = _latest_fix.copy() if isinstance(_latest_fix, dict) else None
        age = now - _latest_t if _latest_t else None
        err = _last_err

    if not fix:
        return {"state": "absent", "age_s": age, "error": err}

    fix["age_s"] = age
    fix["error"] = err
    return fix


def _publish(fix: Optional[Dict[str, Any]] = None, err: Optional[str] = None) -> None:
    global _latest_fix, _latest_t, _last_err
    with _lock:
        if isinstance(fix, dict):
            _latest_fix = fix
            _latest_t = time.time()
        _last_err = err


def _worker() -> None:
    misses = 0
    poll_s = POLL_INTERVAL_FAST

    while not _stop_evt.is_set():
        try:
            # Keep this call inside the thread so it can block without hurting UI
            fix = gps_globalsat.get_fix(timeout_s=1.2)  # keep your preferred timeout

            if isinstance(fix, dict) and fix:
                misses = 0
                poll_s = POLL_INTERVAL_FAST
                fix.setdefault("source", "globalsat")
                _publish(fix=fix, err=None)
            else:
                misses += 1
                if misses >= MISS_TO_SLOW:
                    poll_s = POLL_INTERVAL_SLOW
                _publish(err="no fix")

        except Exception as e:
            misses += 1
            if misses >= MISS_TO_SLOW:
                poll_s = POLL_INTERVAL_SLOW
            _publish(err=str(e))

        time.sleep(poll_s)
