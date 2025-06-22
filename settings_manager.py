import json
from pathlib import Path
from shared import DATA_DIR

APP_NAME = "ImpulseQt"
settings_path = Path(DATA_DIR / "settings.json")
settings_path.parent.mkdir(parents=True, exist_ok=True)  # Ensure path exists

def load_settings():
    if settings_path.exists():
        try:
            with open(settings_path, "r") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
                else:
                    print("[load_settings] WARNING: settings.json is not a dict.")
        except Exception as e:
            print(f"[load_settings] ERROR: {e}")
    return {}  # fallback


def save_settings(settings: dict):
    try:
        with open(settings_path, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)
    except Exception as e:
        print(f"[Error saving settings] {e}")
