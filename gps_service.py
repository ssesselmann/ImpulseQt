# gps_service.py
from __future__ import annotations

import threading
import time
from typing import Optional, Dict, Any

try:
    import gps_os
except Exception:
    gps_os = None

try:
    import gps_globalsat
except Exception:
    gps_globalsat = None


_lock = threading.Lock()
_latest: Optional[Dict[str, Any]] = None

_stop = threading.Event()
_thread: Optional[threading.Thread] = None


def start() -> None:
    """Start GPS polling thread if GPS backends exist. Safe to call multiple times."""
    global _thread
    if _thread and _thread.is_alive():
        return

    if gps_os is None and gps_globalsat is None:
        return  # Rule 1: no GPS available -> do nothing

    _stop.clear()
    _thread = threading.Thread(target=_worker, name="GPSWorker", daemon=True)
    _thread.start()


def stop() -> None:
    _stop.set()


def latest() -> Optional[Dict[str, Any]]:
    """Instant, non-blocking. Returns last fix dict or None."""
    with _lock:
        return dict(_latest) if isinstance(_latest, dict) else None


def _set_latest(fix: Dict[str, Any]) -> None:
    with _lock:
        global _latest
        _latest = fix


def _worker() -> None:
    """Runs in background. Blocking calls are fine here (Rule 2)."""
    while not _stop.is_set():
        fix = None

        # 1) OS GPS (if present)
        if gps_os is not None:
            try:
                # NOTE: don't pass return_acquiring unless your gps_os supports it
                fix = gps_os.get_fix(timeout_s=1.2)
                if fix:
                    fix.setdefault("source", "os")
            except Exception:
                fix = None

        # 2) USB GPS (if present)
        if not fix and gps_globalsat is not None:
            try:
                fix = gps_globalsat.get_fix(timeout_s=1.2)
                if fix:
                    fix.setdefault("source", "globalsat")
            except Exception:
                fix = None

        if fix:
            fix["epoch"] = time.time()
            _set_latest(fix)

        # poll rate (slow enough to be cheap; change if you want)
        time.sleep(1.0)
