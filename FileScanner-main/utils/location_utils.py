
import json
from pathlib import Path
from PyQt5.QtCore import QStandardPaths

CONFIG_DIR = Path(QStandardPaths.writableLocation(QStandardPaths.ConfigLocation)) / "FileScannerApp"
CONFIG_DIR.mkdir(parents=True, exist_ok=True)
LOCATIONS_FILE = CONFIG_DIR / "locations.json"

def load_locations():
    if LOCATIONS_FILE.exists():
        return json.loads(LOCATIONS_FILE.read_text(encoding="utf-8"))
    return {}

def save_locations(d):
    LOCATIONS_FILE.write_text(json.dumps(d, indent=2, ensure_ascii=False), encoding="utf-8")
