import time
from gps_main import gpsloc


def fmt_fix(fix: dict | None) -> str:
    if not fix:
        return "GPS: absent"

    # Prefer your fields if present
    if fix.get("fix") is True and fix.get("lat") is not None and fix.get("lon") is not None:
        lat = fix["lat"]
        lon = fix["lon"]
        alt = fix.get("alt_m")
        sats = fix.get("sats")
        hdop = fix.get("hdop")
        ts = fix.get("timestamp_utc") or ""
        parts = [
            f"GPS: FIX",
            f"{lat:.6f},{lon:.6f}",
            f"alt={alt:.1f}m" if isinstance(alt, (int, float)) else "alt=?",
            f"sats={sats}" if sats is not None else "sats=?",
            f"hdop={hdop:.2f}" if isinstance(hdop, (int, float)) else "hdop=?",
            ts,
        ]
        return " | ".join([p for p in parts if p])

    # Connected but acquiring (or partial)
    src = fix.get("source", "?")
    model = fix.get("model") or fix.get("model_name") or ""
    siv = fix.get("sats_in_view")
    return f"GPS: acquiring | {src} {model} | sats_in_view={siv if siv is not None else '?'}"


def main():
    while True:
        fix = gpsloc()
        print(fmt_fix(fix))
        time.sleep(1)


if __name__ == "__main__":
    main()
