# gps_globalsat.py
from __future__ import annotations

import time
from typing import Optional, Dict, Any

try:
    import serial  # pyserial
    from serial.tools import list_ports
except Exception:
    serial = None
    list_ports = None


_SER = None
_PORT = None
_BAUD = 4800
_LAST_SCAN_T = 0.0
SCAN_EVERY_S = 5.0


def _score_port(p) -> int:
    desc = (getattr(p, "description", "") or "").lower()
    hwid = (getattr(p, "hwid", "") or "").lower()
    dev = (getattr(p, "device", "") or "")

    score = 0
    # Prolific PL2303 (your BU-353N5)
    if "pl2303" in desc or "pl2303" in hwid:
        score += 50
    if "prolific" in desc or "prolific" in hwid:
        score += 30
    if "067b" in hwid:
        score += 20
    if dev.startswith("/dev/cu."):
        score += 5
    return score


def _find_best_port() -> Optional[str]:
    if list_ports is None:
        return None
    ports = list(list_ports.comports())
    if not ports:
        return None
    ports.sort(key=_score_port, reverse=True)
    return getattr(ports[0], "device", None)


def _dm_to_deg(dm: str, hemi: str) -> Optional[float]:
    # dm like "3348.5096" (ddmm.mmmm) or "15113.1800" (dddmm.mmmm)
    try:
        if not dm:
            return None
        v = float(dm)
        deg = int(v // 100)
        minutes = v - (deg * 100)
        out = deg + minutes / 60.0
        if hemi in ("S", "W"):
            out = -out
        return out
    except Exception:
        return None


def _parse_nmea(line: str) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    if not line.startswith("$"):
        return out

    parts = line.strip().split(",")
    if len(parts) < 2:
        return out

    t = parts[0]

    # $GPRMC,hhmmss.sss,A,llll.ll,a,yyyyy.yy,a,...
    if t.endswith("RMC") and len(parts) >= 7:
        status = parts[2]  # A=valid
        lat = _dm_to_deg(parts[3], parts[4])
        lon = _dm_to_deg(parts[5], parts[6])
        out["rmc_valid"] = (status == "A")
        if lat is not None and lon is not None:
            out["lat"] = lat
            out["lon"] = lon
        out["utc"] = parts[1] or None

    # $GPGGA,hhmmss.sss,llll.ll,a,yyyyy.yy,a,fixq,sats,hdop,alt,M,...
    if t.endswith("GGA") and len(parts) >= 10:
        fixq = parts[6]
        sats = parts[7]
        hdop = parts[8]
        alt = parts[9]
        out["fix_quality"] = int(fixq) if fixq.isdigit() else 0
        out["sats"] = int(sats) if sats.isdigit() else None
        try:
            out["hdop"] = float(hdop) if hdop else None
        except Exception:
            out["hdop"] = None
        try:
            out["alt_m"] = float(alt) if alt else None
        except Exception:
            out["alt_m"] = None
        out["utc"] = parts[1] or out.get("utc")

    return out


def _close_serial():
    global _SER, _PORT
    try:
        if _SER:
            _SER.close()
    except Exception:
        pass
    _SER = None
    _PORT = None

def reset():
    """Force close so next get_fix() will rescan + reopen."""
    global _LAST_SCAN_T
    _LAST_SCAN_T = 0.0
    _close_serial()


def get_fix(timeout_s: float = 1.2) -> Dict[str, Any]:
    """
    Returns a dict ALWAYS:
      connected: bool
      fix: bool
      lat/lon (optional)
      epoch
      error (optional)
    """
    global _SER, _PORT, _LAST_SCAN_T

    now = time.time()

    if serial is None or list_ports is None:
        return {
            "connected": False,
            "fix": False,
            "lat": None,
            "lon": None,
            "epoch": now,
            "error": "pyserial not available",
        }

    # ensure serial connected
    if _SER is None or not getattr(_SER, "is_open", False):
        if (now - _LAST_SCAN_T) >= SCAN_EVERY_S:
            _LAST_SCAN_T = now
            _PORT = _find_best_port()

        if not _PORT:
            _close_serial()
            return {
                "connected": False,
                "fix": False,
                "lat": None,
                "lon": None,
                "epoch": now,
                "error": None,
            }

        try:
            _SER = serial.Serial(_PORT, _BAUD, timeout=0.2)
        except Exception as e:
            _close_serial()
            return {
                "connected": False,
                "fix": False,
                "lat": None,
                "lon": None,
                "epoch": now,
                "error": str(e),
            }

    # read until timeout, parse NMEA
    best: Dict[str, Any] = {}
    deadline = now + float(max(0.2, timeout_s))
    got_any_bytes = False


    try:
        while time.time() < deadline:
            raw = _SER.readline()
            if not raw:
                continue
            got_any_bytes = True

            if not raw:
                continue
            try:
                line = raw.decode("ascii", errors="ignore").strip()
            except Exception:
                continue
            d = _parse_nmea(line)
            if d:
                best.update(d)

            # If we got valid coords + valid fix indicator, we can return early
            lat = best.get("lat")
            lon = best.get("lon")
            fixq = best.get("fix_quality", 0)
            rmc_valid = best.get("rmc_valid", False)
            if lat is not None and lon is not None and (fixq > 0 or rmc_valid):
                break
        # If we got ZERO bytes for the whole window, the port is effectively dead.
        # This is the common "unplug/replug" macOS behavior: no exception, just silence.
        if not got_any_bytes:
            _close_serial()
            return {
                "connected": bool(got_any_bytes),
                "fix": False,
                "lat": None,
                "lon": None,
                "epoch": time.time(),
                "error": None,
            }

    except Exception as e:
        _close_serial()
        return {
            "connected": False,
            "fix": False,
            "lat": None,
            "lon": None,
            "epoch": time.time(),
            "error": str(e),
        }

    lat = best.get("lat")
    lon = best.get("lon")
    fixq = best.get("fix_quality", 0)
    rmc_valid = best.get("rmc_valid", False)

    has_fix = (lat is not None and lon is not None and (fixq > 0 or rmc_valid))

    return {
        "source": "globalsat",
        "port": _PORT,
        "baud": _BAUD,
        "connected": True,
        "fix": bool(has_fix),
        "lat": lat,
        "lon": lon,
        "alt_m": best.get("alt_m"),
        "sats": best.get("sats"),
        "hdop": best.get("hdop"),
        "utc": best.get("utc"),
        "epoch": time.time(),
        "error": None,
    }
