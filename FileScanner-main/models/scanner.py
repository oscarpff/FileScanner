# models/scanner.py

import traceback2
from pathlib import Path
from PyQt5.QtCore import QThread, pyqtSignal
from utils.file_utils import get_file_preview

class ScannerWorker(QThread):
    # Ahora `files_counted` nos dice cuántos ficheros hay en total
    files_counted = pyqtSignal(int)
    # `progress` emite cuántos ficheros ya hemos procesado
    progress = pyqtSignal(int)
    finished = pyqtSignal(dict)

    def __init__(self, base_path, ignored_exts=None, allowed_exts=None):
        super().__init__()
        self.base_path = Path(base_path)
        self.ignored_exts = set(e.lower() for e in (ignored_exts or []))
        self.allowed_exts = set(e.lower() for e in allowed_exts) if allowed_exts else None
        self.total_files = 0
        self.processed = 0

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
                if item.is_file():
                    # incrementamos y avisamos progreso
                    self.processed += 1
                    self.progress.emit(self.processed)

                    ext = item.suffix.lower()
                    if ext in self.ignored_exts:
                        continue
                    if self.allowed_exts is not None and ext not in self.allowed_exts:
                        continue

                    tree["files"].append({
                        "name": item.name,
                        "path": str(item),
                        "preview": get_file_preview(item)
                    })

                elif item.is_dir():
                    sub = self.scan_folder(item)
                    tree["subfolders"].append(sub)

        except (PermissionError, FileNotFoundError):
            pass

        return tree
