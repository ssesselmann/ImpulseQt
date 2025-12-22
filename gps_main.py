# gps_main.py (minimal)
from __future__ import annotations
import time, threading
from typing import Optional

try:
    import gps_globalsat
except Exception:
    gps_globalsat = None

POLL_FAST = 1.0
POLL_SLOW = 15.0
MISS_TO_SLOW = 3
STALE_AFTER_S = 3.5

_lock = threading.Lock()
_thread: Optional[threading.Thread] = None
_stop_evt = threading.Event()

# globals the rest of the app uses
status: bool = False      # True = has fix
connected: bool = False   # True = receiving data recently

_latest_t: float = 0.0    # last time we received anything (for staleness)


def start_gps() -> None:
    global _thread
    if gps_globalsat is None:
        return
    if _thread and _thread.is_alive():
        return
    _stop_evt.clear()
    _thread = threading.Thread(target=_worker, daemon=True)
    _thread.start()


def stop_gps() -> None:
    global status, connected
    _stop_evt.set()
    with _lock:
        status = False
        connected = False


def _worker() -> None:
    global status, connected, _latest_t

    misses = 0
    poll_s = POLL_FAST

    while not _stop_evt.is_set():
        now = time.time()

        try:
            fix = gps_globalsat.get_fix(timeout_s=1.2) if gps_globalsat else None

            if isinstance(fix, dict) and fix:
                # got data -> we're connected right now
                with _lock:
                    _latest_t = now
                    connected = True
                    status = bool(fix.get("fix") is True)  # <-- THE WHOLE POINT

                misses = 0
                poll_s = POLL_FAST

            else:
                # no data this cycle: decide stale vs just quiet
                misses += 1

                with _lock:
                    age = (now - _latest_t) if _latest_t else None
                    stale = (age is None) or (age > STALE_AFTER_S)

                    if stale:
                        # unplugged or dead -> poll FAST so we notice replug quickly
                        connected = False
                        status = False
                        poll_s = POLL_FAST
                    else:
                        # recently connected, maybe still acquiring -> can go slow after a bit
                        connected = True
                        if misses >= MISS_TO_SLOW:
                            poll_s = POLL_SLOW
                        else:
                            poll_s = POLL_FAST

        except Exception:
            # treat repeated errors like disconnected, but don't hammer the port
            with _lock:
                age = (now - _latest_t) if _latest_t else None
                if (age is None) or (age > STALE_AFTER_S):
                    connected = False
                    status = False
            poll_s = POLL_SLOW

        time.sleep(poll_s)
