import json
from pathlib import Path
import socket
import datetime

from PyQt5.QtCore import QObject, Qt
from PyQt5.QtWidgets import (
    QMessageBox, QListWidgetItem, QFileDialog, QDialog
)

from utils.settings import set_setting

from models.scanner import ScannerWorker
from models.favorites import load_favorites, save_favorites
from utils.file_utils import open_folder
from utils.ioc_store import IOCStore
from views.dialogs import IOCViewerDialog
from utils.location_utils import load_locations, save_locations
from views.dialogs import (
    FavoriteDialog, FileResultsDialog, LocationDialog
)


class MainController(QObject):
    def __init__(self, view):
        super().__init__()
        self.view = view
        # IOC store local (hashes, names, paths)
        self.ioc_store = IOCStore()

        # Favoritos de extensiones
        self.favorites = load_favorites()
        self.sort_asc = True

        # Favoritos de ubicaciones (colecciones y simples)
        self.location_collections = load_locations()

        # Conectar señales
        self._connect_signals()

        # Inicializar listas
        self._populate_favorites()
        self._refresh_location_list()
        self._refresh_location_collections_list()

    def _connect_signals(self):
        v = self.view
        # Escaneo
        v.scan_button.clicked.connect(self.run_scan)
        v.stop_button.clicked.connect(self.stop_scan)
        # Favoritos de extensiones
        v.sort_btn.clicked.connect(self.toggle_sort_favorites)
        v.search_fav_input.textChanged.connect(lambda _: self._populate_favorites())
        v.favorites_list.itemDoubleClicked.connect(self.load_favorite)
        v.save_fav_btn.clicked.connect(self.save_favorite)
        v.load_fav_btn.clicked.connect(self.import_favorites)
        v.delete_fav_btn.clicked.connect(self.delete_favorite)
        v.edit_fav_btn.clicked.connect(self.edit_favorite)
        # IOCs
        if hasattr(v, 'load_ioc_btn'):
            v.load_ioc_btn.clicked.connect(self.import_iocs)
        # Favoritos de ubicaciones (lista simple)
        v.add_loc_btn.clicked.connect(self.add_location)
        v.del_loc_btn.clicked.connect(self.delete_location)
        v.location_list.itemDoubleClicked.connect(self.select_location)
        # Colecciones de ubicaciones (CRUD)
        v.save_loc_coll_btn.clicked.connect(self.save_location_collection)
        v.load_loc_coll_btn.clicked.connect(self.import_location_collections)
        v.edit_loc_coll_btn.clicked.connect(self.edit_location_collection)

    # — Favoritos de ubicaciones (lista simple) —
    def _refresh_location_list(self):
        v = self.view
        v.location_list.clear()
        for name, path in self.location_collections.items():
            item = QListWidgetItem(f"{name} ➔ {path}")
            item.setData(Qt.UserRole, path)
            v.location_list.addItem(item)

    def add_location(self):
        v = self.view
        folder = QFileDialog.getExistingDirectory(v, "Seleccionar carpeta para favoritos")
        if not folder:
            return
        name = Path(folder).name
        base = name
        idx = 1
        while name in self.location_collections:
            idx += 1
            name = f"{base} {idx}"
        self.location_collections[name] = folder
        save_locations(self.location_collections)
        self._refresh_location_list()

    def delete_location(self):
        v = self.view
        sel = v.location_list.selectedItems()
        if not sel:
            return
        name = sel[0].text().split(" ➔ ")[0]
        self.location_collections.pop(name, None)
        save_locations(self.location_collections)
        self._refresh_location_list()

    def select_location(self, item):
        path = item.data(Qt.UserRole)
        self.view.path_input.setText(path)

    # — Colecciones de ubicaciones (CRUD) —
    def _refresh_location_collections_list(self):
        v = self.view
        v.location_list.clear()
        for name, path in self.location_collections.items():
            item = QListWidgetItem(f"{name} ➔ {path}")
            item.setData(Qt.UserRole, path)
            v.location_list.addItem(item)

    def save_location_collection(self):
        v = self.view
        try:
            current = v.path_input.text().strip()
            if not current or not Path(current).is_dir():
                raise ValueError("Selecciona primero una ruta válida.")
            
            dlg = LocationDialog(v, name="", path=current)
            if dlg.exec_() != QDialog.Accepted:
                return
            new_name, new_path = dlg.get_data()

            if not new_path or not Path(new_path).is_dir():
                raise ValueError("La ruta indicada no existe.")

            # Genera un nombre único
            if not new_name:
                new_name = self._generate_default_location_name()
            base = new_name
            idx = 1
            while new_name in self.location_collections:
                idx += 1
                new_name = f"{base} {idx}"

            # Guarda
            self.location_collections[new_name] = new_path
            save_locations(self.location_collections)
            self._refresh_location_collections_list()

        except Exception as e:
            # Muestra siempre el error sin crashear
            QMessageBox.critical(v, "Error al guardar colección", str(e))
            # Imprime en consola para el debug cuando hay consola
            import traceback; traceback.print_exc()


    def import_location_collections(self):
        v = self.view
        path, _ = QFileDialog.getOpenFileName(
            v, "Cargar colecciones de ubicaciones", "", "JSON Files (*.json)"
        )
        if not path:
            return
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            self.location_collections.update(data)
            save_locations(self.location_collections)
            self._refresh_location_collections_list()
        except Exception as e:
            QMessageBox.critical(v, "Error", f"No se pudo importar: {e}")

    def edit_location_collection(self):
        v = self.view
        sel = v.location_list.selectedItems()
        if not sel:
            return
        old_name = sel[0].text().split(" ➔ ")[0]
        old_path = self.location_collections[old_name]

        # Lanzamos el diálogo con nombre y ruta actuales
        dlg = LocationDialog(v, name=old_name, path=old_path)
        if dlg.exec_() != QDialog.Accepted:
            return

        new_name, new_path = dlg.get_data()
        if not new_name or not Path(new_path).is_dir():
            QMessageBox.warning(v, "Entrada inválida", "Debes indicar un nombre y una ruta válida.")
            return

        # Actualizamos: removemos la antigua key
        self.location_collections.pop(old_name, None)
        self.location_collections[new_name] = new_path
        save_locations(self.location_collections)
        self._refresh_location_collections_list()

    def _generate_default_location_name(self):
        base = "Colección de ubicaciones"
        idx = 1
        while f"{base} {idx}" in self.location_collections:
            idx += 1
        return f"{base} {idx}"

    # — Favoritos de extensiones —
    def _populate_favorites(self):
        v = self.view
        v.favorites_list.clear()
        filtro = v.search_fav_input.text().strip().lower()
        for name, data in self.favorites.items():
            exts = data.get("extensions", [])
            icon = data.get("icon", "📂")
            preview = ", ".join(exts)
            text = f"{icon} {name} [{preview}]"
            if filtro in name.lower() or filtro in preview.lower():
                item = QListWidgetItem(text)
                item.setData(Qt.UserRole, name)
                v.favorites_list.addItem(item)

    def toggle_sort_favorites(self):
        self.sort_asc = not self.sort_asc
        self.favorites = dict(
            sorted(self.favorites.items(), reverse=not self.sort_asc)
        )
        save_favorites(self.favorites)
        self._populate_favorites()

    def save_favorite(self):
        v = self.view
        exts = [v.active_list.item(i).text() for i in range(v.active_list.count())]
        if not exts:
            QMessageBox.warning(v, "Extensiones vacías", "No hay extensiones activas para guardar.")
            return
        dlg = FavoriteDialog(v, extensions=exts)
        if dlg.exec_() == QDialog.Accepted:
            name, icon, new_exts = dlg.get_data()
            if not name:
                base = "Colección de favoritos"
                idx = 1
                candidate = f"{base} {idx}"
                while candidate in self.favorites:
                    idx += 1
                    candidate = f"{base} {idx}"
                name = candidate
            self.favorites[name] = {"extensions": new_exts, "icon": icon}
            save_favorites(self.favorites)
            self._populate_favorites()

    def load_favorite(self, item):
        name = item.data(Qt.UserRole)
        data = self.favorites.get(name)
        if data:
            v = self.view
            v.allowed_exts.clear()
            v.allowed_exts.update(data["extensions"])
            v._refresh_active_list()
            
            # Sync all analyze buttons
            for btn, ext in v.quick_filter_buttons:
                btn.setChecked(ext in v.allowed_exts)
            
            # Also persist the loaded extensions
            set_setting("allowed_exts", sorted(list(v.allowed_exts)))

    def import_favorites(self):
        v = self.view
        path, _ = QFileDialog.getOpenFileName(
            v, "Importar colección de favoritos", "", "JSON Files (*.json)"
        )
        if not path:
            return
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            added = 0
            for name, dat in data.items():
                if name not in self.favorites:
                    self.favorites[name] = dat
                    added += 1
            if added:
                save_favorites(self.favorites)
                self._populate_favorites()
                QMessageBox.information(
                    v, "Importado", f"Se importaron {added} conjuntos nuevos correctamente ✅"
                )
            else:
                QMessageBox.information(
                    v, "Nada importado", "No se encontraron conjuntos nuevos para importar."
                )
        except Exception as e:
            QMessageBox.critical(v, "Error", f"No se pudo importar: {e}")

    def import_iocs(self):
        v = self.view
        path, _ = QFileDialog.getOpenFileName(
            v, "Cargar lista de IOCs (JSON/CSV)", "", "IOC Files (*.json *.csv *.txt);;All Files (*)"
        )
        if not path:
            return
        try:
            self.ioc_store.clear()
            self.ioc_store.load(Path(path))
            QMessageBox.information(v, "IOCs cargadas", "Se han cargado las IOCs correctamente.")
            # Actualizar contador en la UI si existe
            try:
                if hasattr(v, 'ioc_count_label'):
                    v.ioc_count_label.setText(f"Hash:{len(self.ioc_store.hashes)} Name:{len(self.ioc_store.names)} Path:{len(self.ioc_store.paths)}")
            except Exception:
                pass
            # Actualizar lista visual de IOCs si existe
            try:
                if hasattr(v, 'ioc_list'):
                    self._refresh_ioc_list()
            except Exception:
                pass
        except Exception as e:
            QMessageBox.critical(v, "Error IOCs", f"No se pudo cargar IOCs: {e}")

    def _refresh_ioc_list(self):
        v = self.view
        if not hasattr(v, 'ioc_list'):
            return
        v.ioc_list.clear()
        # Mostrar hashes primero, luego names, luego paths, con prefijos legibles
        for h in sorted(self.ioc_store.hashes):
            v.ioc_list.addItem(f"Hash: {h}")
        for n in sorted(self.ioc_store.names):
            v.ioc_list.addItem(f"Name: {n}")
        for p in sorted(self.ioc_store.paths):
            v.ioc_list.addItem(f"Path: {p}")

    def show_iocs(self):
        v = self.view
        try:
            dlg = IOCViewerDialog(v, self.ioc_store)
            dlg.exec_()
        except Exception as e:
            QMessageBox.critical(v, "Error", f"No se pudo abrir visor de IOCs: {e}")

    def delete_favorite(self):
        v = self.view
        sel = v.favorites_list.selectedItems()
        if not sel:
            return
        name = sel[0].data(Qt.UserRole)
        self.favorites.pop(name, None)
        save_favorites(self.favorites)
        self._populate_favorites()

    def edit_favorite(self):
        v = self.view
        sel = v.favorites_list.selectedItems()
        if not sel:
            return
        name = sel[0].data(Qt.UserRole)
        data = self.favorites[name]
        dlg = FavoriteDialog(
            v, name=name,
            icon=data.get("icon","📂"),
            extensions=data.get("extensions",[])
        )
        if dlg.exec_() == QDialog.Accepted:
            new_name, new_icon, new_exts = dlg.get_data()
            if new_name:
                self.favorites.pop(name, None)
                self.favorites[new_name] = {"extensions": new_exts, "icon": new_icon}
                save_favorites(self.favorites)
                self._populate_favorites()

    # — Escaneo —
    def run_scan(self):
        v = self.view
        base = v.path_input.text().strip()
        if not Path(base).is_dir():
            QMessageBox.critical(v, "Error", "Please enter a valid path to scan.")
            return
        ignored = v.ignored_exts if hasattr(v, 'ignored_exts') else set()
        allowed = v.allowed_exts or None
        v.progress_bar.setRange(0, 100)
        v.progress_bar.setValue(0)
        v.scan_button.setEnabled(False)
        v.stop_button.setEnabled(True)
        v.browse_button.setEnabled(False)
        v.save_browse_button.setEnabled(False)
        # Try to compile YARA rules (may return None if yara not available)
        try:
            from utils.yara_manager import compile_yara_rules
            yara_rules = compile_yara_rules()
        except Exception:
            yara_rules = None

        self.worker = ScannerWorker(
            base,
            ignored_exts=ignored,
            allowed_exts=allowed,
            ioc_store=getattr(self, 'ioc_store', None),
            yara_rules=yara_rules
        )
        self.worker.files_counted.connect(lambda total: v.progress_bar.setRange(0, total))
        self.worker.progress.connect(lambda done: v.progress_bar.setValue(done))
        self.worker.finished.connect(self.save_result)
        self.worker.start()
        
    def stop_scan(self):
        if hasattr(self, "worker") and self.worker.isRunning():
            # envío de petición segura de interrupción
            self.worker.requestInterruption()
            # deshabilito Detener y habilito Ejecutar
            v = self.view
            v.stop_button.setEnabled(False)
            v.scan_button.setEnabled(True)

    def save_result(self, result: dict):
        v = self.view
        out_dir = Path(v.save_path_input.text().strip() or str(Path.home()))
        if not out_dir.is_dir():
            out_dir = Path.home()
        v.progress_bar.setValue(v.progress_bar.maximum())
        file_paths = []
        # Además de la lista de paths, recolectamos un mapa path -> ioc_matches (si existe)
        ioc_map = {}
        def collect_paths(node):
            for f in node.get("files", []):
                p = f.get("path")
                if p:
                    file_paths.append(p)
                    if f.get("ioc_matches"):
                        ioc_map[p] = f.get("ioc_matches")
            for sub in node.get("subfolders", []):
                collect_paths(sub)
        collect_paths(result.get("tree", {}))
        # Añadimos metadatos top-level útiles para análisis
        result["preview_files"] = [Path(p).name for p in file_paths]
        result["total_files"] = len(file_paths)
        result["scan_date"] = datetime.datetime.now().astimezone().isoformat()
        try:
            result["host"] = socket.gethostname()
        except Exception:
            result["host"] = None

        # Normalizamos y enriquecemos cada entrada de fichero en el árbol:
        def enrich_node(node):
            for f in node.get("files", []):
                # Preserve epoch mtime if present and convert to ISO
                try:
                    m = f.get("mtime")
                    if m is not None:
                        f["mtime_epoch"] = m
                        try:
                            f["mtime"] = datetime.datetime.fromtimestamp(float(m)).astimezone().isoformat()
                        except Exception:
                            f["mtime"] = None
                except Exception:
                    pass

                # Hashes: no duplicamos algoritmos por archivo (se normaliza a top-level)
                # Dejamos la clave `hashes` tal cual (con los hexdigests) y
                # evitamos añadir metadatos redundantes por archivo.

            for sub in node.get("subfolders", []):
                enrich_node(sub)

        try:
            tree = result.get("tree") or {}
            enrich_node(tree)
        except Exception:
            pass

        # Eliminar posibles entradas de fichero duplicadas por `path` (mantener la última)
        def dedupe_node(node):
            files = node.get("files", [])
            if files:
                seen = {}
                for f in files:
                    p = f.get("path")
                    if p:
                        seen[p] = f
                node["files"] = list(seen.values())
            for sub in node.get("subfolders", []):
                dedupe_node(sub)

        try:
            dedupe_node(tree)
        except Exception:
            pass

        # Recopilar algoritmos de hash presentes y contar errores de hashing
        def collect_hash_stats(node, algs:set, error_counter:dict):
            for f in node.get("files", []):
                hashes = f.get("hashes") or {}
                if isinstance(hashes, dict) and hashes:
                    for k in hashes.keys():
                        algs.add(k)
                else:
                    error_counter['count'] = error_counter.get('count', 0) + 1
            for sub in node.get("subfolders", []):
                collect_hash_stats(sub, algs, error_counter)

        hash_algs = set()
        hash_errors = {'count': 0}
        try:
            collect_hash_stats(tree, hash_algs, hash_errors)
        except Exception:
            pass

        # Top-level hashes info (evita repetir algoritmos por archivo)
        result['hash_algorithms'] = sorted(list(hash_algs))
        result['hash_error_count'] = int(hash_errors.get('count', 0))

        json_file = out_dir / (Path(result.get("path", "")).name + ".json")
        json_file.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        dlg = FileResultsDialog(file_paths, str(out_dir), ioc_map)
        dlg.exec_()
        v.progress_bar.setRange(0, 100)
        v.progress_bar.setValue(0)
        v.stop_button.setEnabled(False)
        v.scan_button.setEnabled(True)
        v.browse_button.setEnabled(True)
        v.save_browse_button.setEnabled(True)
        try:
            self.worker.progress.disconnect()
            self.worker.files_counted.disconnect()
        except Exception:
            pass
