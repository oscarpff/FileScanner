# models/scanner.py

import traceback2
from pathlib import Path
from PyQt5.QtCore import QThread, pyqtSignal
from utils.file_utils import get_file_preview, hash_file

class ScannerWorker(QThread):
    # Ahora `files_counted` nos dice cuántos ficheros hay en total
    files_counted = pyqtSignal(int)
    # `progress` emite cuántos ficheros ya hemos procesado
    progress = pyqtSignal(int)
    finished = pyqtSignal(dict)

    def __init__(self, base_path, ignored_exts=None, allowed_exts=None, ioc_store=None, yara_rules=None):
        super().__init__()
        self.base_path = Path(base_path)
        self.ignored_exts = set(e.lower() for e in (ignored_exts or []))
        self.allowed_exts = set(e.lower() for e in allowed_exts) if allowed_exts else None
        self.total_files = 0
        self.processed = 0
        self.ioc_store = ioc_store
        # compiled yara rules object (or None)
        self.yara_rules = yara_rules

    def run(self):
        # 1) contar ficheros
        try:
            all_files = list(self.base_path.rglob('*'))
            self.total_files = len([f for f in all_files if f.is_file()])
        except Exception:
            self.total_files = 1

        # emitimos el total para ajustar la barra
        self.files_counted.emit(self.total_files)

        self.processed = 0

        # 2) escaneo
        tree = self.scan_folder(self.base_path)
        # Si se pidió parar, no emitimos finished con todo el árbol, podemos avisar con uno parcial o simplemente terminar
        if self.isInterruptionRequested():
            return

        # 3) al terminar, emitimos finished
        result = {
            "path": str(self.base_path),
            "scan_date": str(Path().stat().st_ctime),
            "tree": tree
        }
        
        try:
            all_files = list(self.base_path.rglob('*'))
            total = len([f for f in all_files if f.is_file()])
            self.progress.emit(0)
            self.total_files = total
            self.processed = 0
            tree = self.scan_folder(self.base_path)
            self.progress.emit(total)
            self.finished.emit({
                "path": str(self.base_path),
                "tree": tree
            })

        except Exception as e:
            # Capturamos y volcamos TODO el traceback en consola
            print("🛑 Error en ScannerWorker.run():", e)
            traceback2.print_exc()
            # También emitimos finished con un árbol vacío para que no quede colgado
            self.finished.emit({
                "path": str(self.base_path),
                "tree": {"path": str(self.base_path), "files": [], "subfolders": []}
            })

    def scan_folder(self, path: Path) -> dict:
        tree = {"path": str(path), "files": [], "subfolders": []}
        try:
            for item in path.iterdir():
                # si nos han pedido parar, salimos
                if self.isInterruptionRequested():
                    break
                # evitar seguir symlinks para no duplicar ni recorrer mounts remotos
                try:
                    if item.is_symlink():
                        continue
                except Exception:
                    pass
                if item.is_file():
                    # incrementamos y avisamos progreso
                    self.processed += 1
                    self.progress.emit(self.processed)

                    ext = item.suffix.lower()
                    if ext in self.ignored_exts:
                        continue
                    if self.allowed_exts is not None and ext not in self.allowed_exts:
                        continue

                    # Recolectamos metadatos seguros y hashes (hashing en streaming)
                    hashes = {}
                    try:
                        hashes = hash_file(item)
                    except Exception as e:
                        print(f"Error al hashear {item}: {e}")

                    try:
                        size = item.stat().st_size
                    except Exception:
                        size = None

                    try:
                        mtime = item.stat().st_mtime
                    except Exception:
                        mtime = None

                    file_entry = {
                        "name": item.name,
                        "path": str(item),
                        "size": size,
                        "mtime": mtime,
                        "hashes": hashes,
                        "preview": get_file_preview(item)
                    }

                    # Comprueba IOCs si hay store cargado
                    try:
                        matches = []
                        if self.ioc_store is not None:
                            # match hashes -> include algorithm and value
                            for alg, hexd in (hashes or {}).items():
                                if hexd and self.ioc_store.match_hash(hexd):
                                    matches.append(f"hash:{alg}:{hexd}")
                            # match filename -> include matched name
                            if self.ioc_store.match_name(item.name):
                                matches.append(f"name:{item.name}")
                            # match full path -> include matched path
                            if self.ioc_store.match_path(str(item)):
                                matches.append(f"path:{str(item)}")
                        if matches:
                            file_entry["ioc_matches"] = matches
                        # YARA matching: if compiled rules are available, run match on the file
                        try:
                            if getattr(self, 'yara_rules', None) is not None:
                                try:
                                    # use filepath match to let yara read efficiently
                                    ym = self.yara_rules.match(filepath=str(item))
                                except TypeError:
                                    # some yara builds expect keyword 'filepath' differently
                                    ym = self.yara_rules.match(str(item))
                                if ym:
                                    # append yara matches with rule names
                                    for m in ym:
                                        try:
                                            rname = getattr(m, 'rule', None) or str(m)
                                            matches.append(f"yara:{rname}")
                                        except Exception:
                                            matches.append(f"yara:unknown")
                                    file_entry["ioc_matches"] = matches
                        except Exception:
                            # do not break scan on yara errors
                            pass
                    except Exception:
                        pass

                    tree["files"].append(file_entry)

                elif item.is_dir():
                    sub = self.scan_folder(item)
                    tree["subfolders"].append(sub)

        except (PermissionError, FileNotFoundError):
            pass

        return tree
