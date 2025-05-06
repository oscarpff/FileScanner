import json
from pathlib import Path

from PyQt5.QtCore import QObject, Qt
from PyQt5.QtWidgets import QMessageBox, QListWidgetItem, QFileDialog, QDialog

from models.scanner import ScannerWorker
from models.favorites import load_favorites, save_favorites
from utils.file_utils import open_folder
from views.dialogs import FavoriteDialog, FileResultsDialog


class MainController(QObject):
    def __init__(self, view):
        super().__init__()
        self.view = view
        self.favorites = load_favorites()
        self.sort_asc = True
        self._populate_favorites()
        self._connect_signals()

    def _connect_signals(self):
        v = self.view
        # Escaneo
        v.scan_button.clicked.connect(self.run_scan)
        # Favoritos
        v.sort_btn.clicked.connect(self.toggle_sort_favorites)
        v.search_fav_input.textChanged.connect(lambda _: self._populate_favorites())
        v.favorites_list.itemDoubleClicked.connect(self.load_favorite)
        v.save_fav_btn.clicked.connect(self.save_favorite)
        v.load_fav_btn.clicked.connect(self.import_favorites)
        v.delete_fav_btn.clicked.connect(self.delete_favorite)
        v.edit_fav_btn.clicked.connect(self.edit_favorite)

    # ——— Favoritos —————————————————————————————————————————————————————
    def _populate_favorites(self):
        v = self.view
        v.favorites_list.clear()
        filtro = v.search_fav_input.text().strip().lower()
        for name, data in self.favorites.items():
            exts = data.get("extensions", [])
            icon = data.get("icon", "📂")
            preview = ", ".join(exts)
            texto = f"{icon} {name} [{preview}]"
            if filtro in name.lower() or filtro in preview.lower():
                item = QListWidgetItem(texto)
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

            # Si el usuario no puso nombre, generamos uno único
            if not name:
                base = "Colección de favoritos"
                idx = 1
                candidate = f"{base} {idx}"
                # iteramos hasta encontrar un nombre que no exista
                while candidate in self.favorites:
                    idx += 1
                    candidate = f"{base} {idx}"
                name = candidate

            # Guardamos ya con nombre (sea el custom o el generado)
            self.favorites[name] = {"extensions": new_exts, "icon": icon}
            save_favorites(self.favorites)
            self._populate_favorites()

    def load_favorite(self, item):
        name = item.data(Qt.UserRole)
        data = self.favorites.get(name)
        if data:
            v = self.view
            v.allowed_exts.clear()
            v.active_list.clear()
            for ext in data["extensions"]:
                v.allowed_exts.add(ext)
                v.active_list.addItem(ext)
            # actualizar botones rápidos
            for btn, ext in v.quick_filter_buttons:
                if ext in v.allowed_exts:
                    btn.setChecked(True)
                    btn.setStyleSheet("background-color: lightgreen;")
                else:
                    btn.setChecked(False)
                    btn.setStyleSheet("background-color: lightgray;")

    def import_favorites(self):
        v = self.view
        path, _ = QFileDialog.getOpenFileName(v, "Importar colección de favoritos", "", "JSON Files (*.json)")
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
                QMessageBox.information(v, "Importado", f"Se importaron {added} conjuntos nuevos correctamente ✅")
            else:
                QMessageBox.information(v, "Nada importado", "No se encontraron conjuntos nuevos para importar.")
        except Exception as e:
            QMessageBox.critical(v, "Error", f"No se pudo importar el archivo: {e}")

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
        dlg = FavoriteDialog(v, name=name, icon=data.get("icon","📂"), extensions=data.get("extensions",[]))
        if dlg.exec_() == QDialog.Accepted:
            new_name, new_icon, new_exts = dlg.get_data()
            if new_name:
                self.favorites.pop(name, None)
                self.favorites[new_name] = {"extensions": new_exts, "icon": new_icon}
                save_favorites(self.favorites)
                self._populate_favorites()

    # ——— Escaneo —————————————————————————————————————————————————————
    def run_scan(self):
        v = self.view
        base = v.path_input.text().strip()
        if not Path(base).is_dir():
            QMessageBox.critical(v, "Error", "Por favor, introduce una ruta válida para escanear.")
            return

        ignored = {ext for ext, cb in v.ignore_checkboxes.items() if cb.isChecked()}
        allowed = v.allowed_exts or None

        # deshabilitar UI
        v.progress_bar.setRange(0, 100)
        v.progress_bar.setValue(0)
        v.scan_button.setEnabled(False)
        v.browse_button.setEnabled(False)
        v.save_browse_button.setEnabled(False)

        # creamos y arrancamos el worker
        self.worker = ScannerWorker(base, ignored_exts=ignored, allowed_exts=allowed)

        # 1) cuando sepamos el total, lo ponemos en la barra
        self.worker.files_counted.connect(lambda total: v.progress_bar.setRange(0, total))

        # 2) cada vez que procesemos un fichero, actualizamos la barra
        self.worker.progress.connect(lambda done: v.progress_bar.setValue(done))

        # 3) al terminar:
        self.worker.finished.connect(self.save_result)

        self.worker.start()

    def save_result(self, result: dict):
        v = self.view
        # Directorio de salida (o home si no es válido)
        out_dir = Path(v.save_path_input.text().strip() or str(Path.home()))
        if not out_dir.is_dir():
            out_dir = Path.home()

        v.progress_bar.setValue(v.progress_bar.maximum())

        # 1) Recojo rutas completas de todos los archivos encontrados
        file_paths = []
        def collect_paths(node):
            for f in node.get("files", []):
                # aquí uso directamente el campo "path"
                file_paths.append(f["path"])
            for sub in node.get("subfolders", []):
                collect_paths(sub)
        collect_paths(result["tree"])

        # 2) Para el JSON sigo guardando sólo nombres (preview), si lo necesitas
        result["preview_files"] = [Path(p).name for p in file_paths]

        # 3) Escribo el JSON completo
        json_file = out_dir / (Path(result["path"]).name + ".json")
        json_file.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

        # 4) Abro el diálogo con rutas correctas
        dlg = FileResultsDialog(file_paths, str(out_dir))
        dlg.exec_()

        # 5) Restauro estado de la UI
        v.progress_bar.setRange(0, 100)
        v.progress_bar.setValue(0)
        v.scan_button.setEnabled(True)
        v.browse_button.setEnabled(True)
        v.save_browse_button.setEnabled(True)
        
        # 6) desconectar señales para evitar actualizaciones inesperadas
        try:
            self.worker.progress.disconnect()
            self.worker.files_counted.disconnect()
        except Exception:
            pass
