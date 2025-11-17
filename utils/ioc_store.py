import json
import csv
from pathlib import Path


class IOCStore:
    """Almacena IOCs simples: hashes, filenames y paths.

    Formatos aceptados:
    - JSON con claves `hashes`, `names`, `paths` (listas)
    - CSV con columna `hash` o `name` o `path` (detecta la cabecera)
    """
    def __init__(self):
        self.hashes = set()
        self.names = set()
        self.paths = set()

    def clear(self):
        self.hashes.clear(); self.names.clear(); self.paths.clear()

    def load_json(self, path: Path):
        data = json.loads(Path(path).read_text(encoding='utf-8'))
        if isinstance(data, dict):
            for k in ('hashes', 'names', 'paths'):
                vals = data.get(k) or []
                for v in vals:
                    self._add_value(k, v)
        elif isinstance(data, list):
            # asumimos lista de hashes
            for v in data:
                self.hashes.add(str(v).lower())

    def load_csv(self, path: Path):
        with open(path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            # si no hay cabecera, intentamos leer por columna única
            if reader.fieldnames:
                for row in reader:
                    for fld in ('hash', 'name', 'path'):
                        if fld in row and row[fld]:
                            self._add_value({'hash': 'hashes', 'name': 'names', 'path': 'paths'}[fld], row[fld])
            else:
                f.seek(0)
                for line in f:
                    val = line.strip()
                    if val:
                        self.hashes.add(val.lower())

    def _add_value(self, kind, value):
        if value is None:
            return
        v = str(value).strip()
        if not v:
            return
        if kind == 'hashes':
            self.hashes.add(v.lower())
        elif kind == 'names':
            self.names.add(v)
        elif kind == 'paths':
            self.paths.add(v)

    def load(self, path: Path):
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(str(p))
        if p.suffix.lower() in ('.json',):
            self.load_json(p)
        elif p.suffix.lower() in ('.csv', '.txt'):
            self.load_csv(p)
        else:
            # intento leer como JSON, si falla, como lista de líneas
            try:
                self.load_json(p)
            except Exception:
                self.load_csv(p)

    # Consultas
    def match_hash(self, h: str) -> bool:
        if not h:
            return False
        return h.lower() in self.hashes

    def match_name(self, name: str) -> bool:
        if not name:
            return False
        return name in self.names

    def match_path(self, path: str) -> bool:
        if not path:
            return False
        return path in self.paths
