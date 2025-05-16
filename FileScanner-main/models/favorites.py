import json
from pathlib import Path
from PyQt5.QtCore import QStandardPaths

_CFG_DIR = Path(QStandardPaths.writableLocation(QStandardPaths.ConfigLocation)) / "FileScannerApp"
_FAV_FILE = _CFG_DIR / "favorites.json"
_CFG_DIR.mkdir(parents=True, exist_ok=True)

def load_favorites() -> dict:
    if _FAV_FILE.exists():
        return json.loads(_FAV_FILE.read_text(encoding="utf-8"))
    return {}

def save_favorites(favs: dict):
    _FAV_FILE.write_text(
        json.dumps(favs, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
