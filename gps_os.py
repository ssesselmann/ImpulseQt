# gps_os.py

from __future__ import annotations

import sys
from typing import Optional, Dict, Any


def get_fix(timeout_s: float = 1.5) -> Optional[Dict[str, Any]]:
    """
    Try OS location services.
    Returns None if unavailable or permission denied.

    NOTE: This is a stub-friendly wrapper. We’ll flesh it out per-platform
    once you decide if you want extra deps (PyObjC on macOS, winrt on Windows).
    """
    try:
        if sys.platform == "darwin":
            return _mac_corelocation(timeout_s)
        if sys.platform.startswith("win"):
            return _win_geolocation(timeout_s)
        # Linux: could add GeoClue (DBus) later if you want
        return None
    except Exception:
        # keep it quiet and safe for the main app
        return None


def _mac_corelocation(timeout_s: float) -> Optional[Dict[str, Any]]:
    # Optional dependency; if not installed, just return None
    try:
        import time
        from CoreLocation import CLLocationManager  # type: ignore
        import objc  # type: ignore
    except Exception:
        return None

    # Minimal approach: start updates, wait briefly, read last location.
    # In a packaged app, permissions/UI prompts matter; we can refine later.
    mgr = CLLocationManager.alloc().init()
    try:
        mgr.requestWhenInUseAuthorization()
    except Exception:
        pass

    mgr.startUpdatingLocation()
    t0 = time.time()

    loc = None
    while time.time() - t0 < timeout_s:
        try:
            loc = mgr.location()
            if loc is not None:
                break
        except Exception:
            pass
        time.sleep(0.05)

    mgr.stopUpdatingLocation()

    if loc is None:
        return None

    try:
        coord = loc.coordinate()
        return {
            "lat": float(coord.latitude),
            "lon": float(coord.longitude),
            "alt_m": float(loc.altitude()) if loc.altitude() is not None else None,
            "utc": None,
            "date": None,
            "sats": None,
            "fix_quality": None,
            "source": "os",
        }
    except Exception:
        return None


def _win_geolocation(timeout_s: float) -> Optional[Dict[str, Any]]:
    # Optional dependency; if not installed, return None
    try:
        import asyncio
        from winrt.windows.devices.geolocation import Geolocator  # type: ignore
    except Exception:
        return None

    async def _get():
        g = Geolocator()
        pos = await g.get_geoposition_async()
        c = pos.coordinate
        p = c.point.position
        return {
            "lat": float(p.latitude),
            "lon": float(p.longitude),
            "alt_m": float(p.altitude) if p.altitude is not None else None,
            "utc": None,
            "date": None,
            "sats": None,
            "fix_quality": None,
            "source": "os",
        }

    try:
        return asyncio.run(_get())
    except Exception:
        return None
