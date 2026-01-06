import json
import shutil
from pathlib import Path
from datetime import datetime
from uuid import uuid4


def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)


def quarantine_file(src: str, quarantine_dir: str, reason: str = None) -> dict:
    """Move `src` into `quarantine_dir` with a unique name and log the action.

    Returns an entry dict with details saved into `quarantine_log.json` inside `quarantine_dir`.
    """
    src_p = Path(src)
    qdir = Path(quarantine_dir)
    ensure_dir(qdir)

    if not src_p.exists():
        raise FileNotFoundError(str(src_p))

    # Build a unique filename to avoid collisions
    unique = uuid4().hex
    tgt_name = f"{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}_{unique}_{src_p.name}"
    tgt = qdir / tgt_name

    # Move the file
    shutil.move(str(src_p), str(tgt))

    # Prepare log entry
    entry = {
        "original_path": str(src_p),
        "quarantine_path": str(tgt),
        "timestamp": datetime.utcnow().isoformat() + 'Z',
        "reason": reason,
        "id": unique
    }

    # Append to log
    log_file = qdir / "quarantine_log.json"
    try:
        if log_file.exists():
            data = json.loads(log_file.read_text(encoding='utf-8') or '[]')
        else:
            data = []
    except Exception:
        data = []

    data.append(entry)
    log_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')

    return entry
