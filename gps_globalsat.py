# gps_bu353n5.py

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Optional, Dict, Any

try:
    import serial  # pyserial
    from serial.tools import list_ports
except Exception:
    serial = None
    list_ports = None


def get_fix(
    timeout_s: float = 1.5,
    baud: Optional[int] = None,
    return_acquiring: bool = True,
) -> Optional[Dict[str, Any]]:
    """
    Read BU-353N5 (or similar NMEA over PL2303) and return a dict.
    - If a valid fix is obtained: returns dict with fix=True and lat/lon.
    - If NMEA is flowing but no fix yet: returns dict with fix=False if return_acquiring=True.
    - If device not present / cannot read: returns None.
    """
    if serial is None or list_ports is None:
        return None

    port = _find_candidate_port()
    if not port:
        return None

    bauds = (baud,) if isinstance(baud, int) else (4800, 9600)

    for b in bauds:
        try:
            with serial.Serial(port, baudrate=b, timeout=0.2) as ser:
                out = _read_and_parse(ser, timeout_s=timeout_s, port=port, baud=b)
                if out is None:
                    continue
                if out.get("fix") is True:
                    return out
                # acquiring
                if return_acquiring and out.get("has_nmea"):
                    return out
        except Exception:
            continue

    return None


def _find_candidate_port() -> Optional[str]:
    # Prefer ports that look like Prolific PL2303
    candidates = []
    for p in list_ports.comports():
        desc = (p.description or "").lower()
        hwid = (p.hwid or "").lower()
        device = (p.device or "")
        score = 0

        if "pl2303" in desc or "pl2303" in hwid:
            score += 50
        if "prolific" in desc or "prolific" in hwid:
            score += 30
        if "067b" in hwid:
            score += 20

        if device.startswith("/dev/cu."):
            score += 5

        if score > 0 and device:
            candidates.append((score, device))

    if not candidates:
        ports = [p.device for p in list_ports.comports() if p.device]
        return ports[0] if ports else None

    candidates.sort(reverse=True)
    return candidates[0][1]


def _read_and_parse(ser, timeout_s: float, port: str, baud: int) -> Optional[Dict[str, Any]]:
    t0 = time.time()

    best: Dict[str, Any] = {
        "source": "globalsat",
        "model": "bu353n5",          # code-friendly
        "model_name": "BU-353N5",    # optional display field
        "port": port,
        "baud": baud,
        "connected": False,          # flips true once we see any $... sentence
        "fix": False,
        "lat": None,
        "lon": None,
        "alt_m": None,
        "sats": None,
        "sats_in_view": None,
        "hdop": None,
        "fix_quality": None,
        "utc": None,
        "date": None,
        "timestamp_utc": None,
    }


    while time.time() - t0 < timeout_s:
        try:
            line = ser.readline().decode("ascii", errors="ignore").strip()
        except Exception:
            continue

        if not line.startswith("$"):
            continue

        best["connected"] = True

        msg = _parse_nmea(line)
        if not msg:
            continue

        mtype = msg.get("type")

        if mtype == "RMC":
            best["utc"] = msg.get("utc") or best["utc"]
            best["date"] = msg.get("date") or best["date"]

            # Only accept lat/lon if status A (active)
            if msg.get("status") == "A":
                best["lat"] = msg.get("lat")
                best["lon"] = msg.get("lon")

        elif mtype == "GGA":
            best["utc"] = msg.get("utc") or best["utc"]
            # Note: GGA doesn't contain date

            if msg.get("lat") is not None:
                best["lat"] = msg.get("lat")
            if msg.get("lon") is not None:
                best["lon"] = msg.get("lon")

            best["fix_quality"] = msg.get("fix_quality")
            best["sats"] = msg.get("sats")
            best["hdop"] = msg.get("hdop")
            best["alt_m"] = msg.get("alt_m")

            if isinstance(best["fix_quality"], int) and best["fix_quality"] > 0:
                best["fix"] = True

        elif mtype == "GSV":
            # take max seen during the window
            siv = msg.get("sats_in_view")
            if isinstance(siv, int):
                cur = best.get("sats_in_view")
                best["sats_in_view"] = siv if cur is None else max(cur, siv)

        # If we can build a timestamp, do it (even while acquiring)
        if best.get("timestamp_utc") is None and best.get("date") and best.get("utc"):
            best["timestamp_utc"] = _make_timestamp_utc(best["date"], best["utc"])

        # Return early if we have a real fix (lat/lon + fix_quality > 0 OR RMC active)
        if best.get("fix") is True and best.get("lat") is not None and best.get("lon") is not None:
            if best.get("timestamp_utc") is None and best.get("date") and best.get("utc"):
                best["timestamp_utc"] = _make_timestamp_utc(best["date"], best["utc"])
            return best

    # If we saw NMEA but no fix, still return acquiring status
    if best.get("has_nmea"):
        if best.get("timestamp_utc") is None and best.get("date") and best.get("utc"):
            best["timestamp_utc"] = _make_timestamp_utc(best["date"], best["utc"])
        return best

    return None


def _parse_nmea(line: str) -> Optional[Dict[str, Any]]:
    """
    Minimal NMEA parsing for RMC, GGA, GSV.
    Accepts GN talkers too ($GNRMC, $GNGGA, $GPGSV, $GNGSV).
    """
    if "*" in line:
        body, _chk = line.split("*", 1)
    else:
        body = line

    parts = body.split(",")
    if not parts:
        return None

    head = parts[0].lstrip("$")
    if len(head) < 5:
        return None

    msg_type = head[-3:]

    if msg_type == "RMC":
        # $GNRMC,hhmmss.sss,A,llll.ll,a,yyyyy.yy,a,...,ddmmyy,...
        if len(parts) < 10:
            return None
        utc = parts[1] or None
        status = parts[2] or None
        lat = _parse_lat(parts[3], parts[4])
        lon = _parse_lon(parts[5], parts[6])
        date = parts[9] or None
        return {"type": "RMC", "utc": utc, "status": status, "lat": lat, "lon": lon, "date": date}

    if msg_type == "GGA":
        # $GNGGA,hhmmss.sss,lat,N,lon,E,fix,nsats,hdop,alt,M,...
        if len(parts) < 10:
            return None
        utc = parts[1] or None
        lat = _parse_lat(parts[2], parts[3])
        lon = _parse_lon(parts[4], parts[5])
        fix_quality = _to_int(parts[6])
        sats = _to_int(parts[7])
        hdop = _to_float(parts[8])
        alt_m = _to_float(parts[9])
        return {
            "type": "GGA",
            "utc": utc,
            "lat": lat,
            "lon": lon,
            "fix_quality": fix_quality,
            "sats": sats,
            "hdop": hdop,
            "alt_m": alt_m,
        }

    if msg_type == "GSV":
        # $GPGSV,total_msgs,msg_num,sats_in_view, ...
        if len(parts) < 4:
            return None
        sats_in_view = _to_int(parts[3])
        return {"type": "GSV", "sats_in_view": sats_in_view}

    return None


def _make_timestamp_utc(date_ddmmyy: str, utc_hhmmss: str) -> Optional[str]:
    """
    Convert NMEA ddmmyy + hhmmss.sss to ISO-8601 UTC string ending in 'Z'.
    Example: '201225' + '034954.000' -> '2025-12-20T03:49:54.000Z'
    """
    try:
        if len(date_ddmmyy) != 6:
            return None
        dd = int(date_ddmmyy[0:2])
        mm = int(date_ddmmyy[2:4])
        yy = int(date_ddmmyy[4:6])
        year = 2000 + yy  # good enough for modern GNSS logs

        # utc can be hhmmss or hhmmss.sss
        if len(utc_hhmmss) < 6:
            return None
        hh = int(utc_hhmmss[0:2])
        mi = int(utc_hhmmss[2:4])
        ss = float(utc_hhmmss[4:])  # includes .sss if present
        sec = int(ss)
        ms = int(round((ss - sec) * 1000.0))

        dt = datetime(year, mm, dd, hh, mi, sec, ms * 1000, tzinfo=timezone.utc)
        return dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    except Exception:
        return None


def _parse_lat(v: str, hemi: str) -> Optional[float]:
    if not v or not hemi:
        return None
    try:
        deg = int(v[0:2])
        minutes = float(v[2:])
        out = deg + minutes / 60.0
        if hemi.upper() == "S":
            out = -out
        return out
    except Exception:
        return None


def _parse_lon(v: str, hemi: str) -> Optional[float]:
    if not v or not hemi:
        return None
    try:
        deg = int(v[0:3])
        minutes = float(v[3:])
        out = deg + minutes / 60.0
        if hemi.upper() == "W":
            out = -out
        return out
    except Exception:
        return None


def _to_int(s: str) -> Optional[int]:
    try:
        return int(s) if s != "" else None
    except Exception:
        return None


def _to_float(s: str) -> Optional[float]:
    try:
        return float(s) if s != "" else None
    except Exception:
        return None
