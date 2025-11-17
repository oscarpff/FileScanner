from pathlib import Path
from typing import List
import json

try:
    import yara
    _HAS_YARA = True
except Exception:
    yara = None
    _HAS_YARA = False

from utils.settings import get_setting, set_setting

YARA_SETTINGS_KEY = 'yara_paths'


def load_yara_paths(paths: List[str]):
    """Store yara paths in settings and optionally compile them.
    Returns dict with status per path.
    """
    results = {}
    stored = []
    for p in paths:
        try:
            pp = str(Path(p))
            if _HAS_YARA:
                # try to compile to validate
                yara.compile(filepath=pp)
            results[pp] = {'ok': True}
            stored.append(pp)
        except Exception as e:
            results[p] = {'ok': False, 'error': str(e)}
    if stored:
        existing = get_setting(YARA_SETTINGS_KEY, [])
        merged = sorted(set(existing + stored))
        set_setting(YARA_SETTINGS_KEY, merged)
    return results


def get_loaded_yara_count():
    return len(get_setting(YARA_SETTINGS_KEY, []))


def clear_yara_paths():
    set_setting(YARA_SETTINGS_KEY, [])


def get_yara_paths():
    return list(get_setting(YARA_SETTINGS_KEY, []))


def compile_yara_rules():
    """Compile and return a combined YARA rules object for all stored paths.

    Returns compiled rules or None if yara is not available or no paths.
    """
    paths = get_yara_paths()
    if not paths:
        return None
    if not _HAS_YARA:
        return None
    # build a filepaths mapping required by yara.compile
    filemap = {f"r{i}": str(Path(p)) for i, p in enumerate(paths)}
    try:
        rules = yara.compile(filepaths=filemap)
        return rules
    except Exception:
        # if compilation fails, return None so caller can proceed without YARA
        return None
