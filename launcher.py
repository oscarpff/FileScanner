# --- IMPORTS ---
import os
import json
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QFileDialog, QLineEdit, QMessageBox, QProgressBar, QCheckBox, QListWidget,
    QListWidgetItem, QDialog, QComboBox, QInputDialog, QTextEdit
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QIcon
from docx import Document
import PyPDF2


# --- FAVORITE DIALOG ---
class FavoriteDialog(QDialog):
    def __init__(self, parent=None, name="", icon="📂", extensions=None):
        super().__init__(parent)
        self.setWindowTitle("Editar Favorito")
        self.extensions = extensions or []

        layout = QVBoxLayout()

        self.name_edit = QLineEdit(name)
        self.name_edit.setPlaceholderText("Nombre del favorito...")
        layout.addWidget(self.name_edit)

        self.icon_combo = QComboBox()
        self.icon_combo.addItems(["📂", "💻", "🎨", "📄", "🔧", "📊", "🗃️"])
        if icon:
            idx = self.icon_combo.findText(icon)
            if idx != -1:
                self.icon_combo.setCurrentIndex(idx)
        layout.addWidget(self.icon_combo)

        self.ext_list = QListWidget()
        self.ext_list.addItems(self.extensions)
        self.ext_list.itemDoubleClicked.connect(self.edit_extension)
        layout.addWidget(self.ext_list)

        ext_buttons = QHBoxLayout()
        self.add_ext_btn = QPushButton("➕ Añadir extensión")
        self.add_ext_btn.clicked.connect(self.add_extension)
        self.del_ext_btn = QPushButton("❌ Eliminar seleccionada")
        self.del_ext_btn.clicked.connect(self.delete_extension)
        ext_buttons.addWidget(self.add_ext_btn)
        ext_buttons.addWidget(self.del_ext_btn)
        layout.addLayout(ext_buttons)

        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Guardar")
        save_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancelar")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def add_extension(self):
        ext, ok = QInputDialog.getText(self, "Nueva extensión", "Introduce extensión (ej: .pdf)")
        if ok and ext:
            ext = ext.strip().lower()
            if not ext.startswith('.'):
                ext = '.' + ext
            if ext not in self.extensions:
                self.extensions.append(ext)
                self.ext_list.addItem(ext)

    def delete_extension(self):
        selected = self.ext_list.selectedItems()
        for item in selected:
            self.extensions.remove(item.text())
            self.ext_list.takeItem(self.ext_list.row(item))

    def edit_extension(self, item):
        old_ext = item.text()
        new_ext, ok = QInputDialog.getText(self, "Editar extensión", "Modificar extensión:", text=old_ext)
        if ok and new_ext:
            new_ext = new_ext.strip().lower()
            if not new_ext.startswith('.'):
                new_ext = '.' + new_ext
            self.extensions.remove(old_ext)
            self.extensions.append(new_ext)
            item.setText(new_ext)

    def get_data(self):
        return (
            self.name_edit.text().strip(),
            self.icon_combo.currentText(),
            [self.ext_list.item(i).text() for i in range(self.ext_list.count())]
        )

# --- FILE RESULTS DIALOG ---
class FileResultsDialog(QDialog):
    def __init__(self, file_paths, output_dir):
        super().__init__()
        self.setWindowTitle("Resultados del escaneo")
        self.resize(700, 500)
        self.setWindowIcon(QIcon("detective_.ico"))

        file_paths = [str(Path(p).resolve()) for p in file_paths]

        self.file_paths = file_paths
        self.output_dir = output_dir

        layout = QVBoxLayout()

        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("🔍 Buscar archivo...")
        self.search_bar.textChanged.connect(self.filter_files)
        layout.addWidget(self.search_bar)

        self.list_widget = QListWidget()
        self.list_widget.addItems(self.file_paths)
        self.list_widget.itemDoubleClicked.connect(self.open_file_location)
        layout.addWidget(self.list_widget)

        btn_layout = QHBoxLayout()

        open_folder_btn = QPushButton("Abrir carpeta de resultados")
        open_folder_btn.clicked.connect(lambda: open_folder(self.output_dir))
        btn_layout.addWidget(open_folder_btn)

        move_files_btn = QPushButton("Mover archivos...")
        move_files_btn.clicked.connect(self.move_files_to_folder)
        btn_layout.addWidget(move_files_btn)

        close_btn = QPushButton("Cerrar")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def filter_files(self, text):
        self.list_widget.clear()
        for path in self.file_paths:
            if text.lower() in os.path.basename(path).lower():
                self.list_widget.addItem(path)

    def open_file_location(self, item):
        file_path = item.text()
        folder_path = str(Path(file_path).parent)
        open_folder(folder_path)

    def move_files_to_folder(self):
        target_dir = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta destino")
        if target_dir:
            moved = 0
            for path in self.file_paths:
                try:
                    file_name = os.path.basename(path)
                    target_path = os.path.join(target_dir, file_name)
                    if not os.path.exists(target_path):
                        os.rename(path, target_path)
                        moved += 1
                except Exception as e:
                    print(f"Error moviendo {path}: {e}")

            QMessageBox.information(self, "Archivos movidos", f"Se movieron {moved} archivos exitosamente.")

# --- UTILIDAD abrir carpeta ---
def open_folder(path):
    try:
        if os.path.isdir(path):
            os.startfile(path)
        elif os.path.isfile(path):
            # Abrir el explorador y seleccionar el archivo
            os.system(f'explorer /select,"{path}"')
    except Exception as e:
        QMessageBox.critical(None, "Error", f"No se pudo abrir la carpeta: {e}")

# --- SCANNER WORKER ---
class ScannerWorker(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(dict)

    def __init__(self, base_path, ignored_exts=None, allowed_exts=None):
        super().__init__()
        self.base_path = Path(base_path)
        self.ignored_exts = ignored_exts or set()
        self.allowed_exts = allowed_exts  # puede ser None
        self.processed = 0

    def run(self):
        try:
            all_files = list(self.base_path.rglob('*'))
            total_files = len([f for f in all_files if f.is_file()])
        except Exception as e:
            total_files = 1  # Evitar división por cero en caso de error raro

        self.processed = 0

        tree = self.scan_folder(self.base_path, [], total_files)

        result = {
            "path": str(self.base_path),
            "scan_date": str(Path().stat().st_ctime),
            "tree": tree
        }
        self.finished.emit(result)

    def scan_folder(self, path, file_list, total_files):
        tree = {"path": str(path), "files": [], "subfolders": []}
        for item in path.iterdir():
            if item.is_file():
                ext = item.suffix.lower()
                if ext in self.ignored_exts:
                    continue
                if self.allowed_exts and ext not in self.allowed_exts:
                    continue

                file_info = {
                    "name": item.name,
                    "extension": ext,
                    "size_kb": round(item.stat().st_size / 1024, 2),
                    "modified_date": str(item.stat().st_mtime),
                    "preview": self.generate_preview(item, ext)
                }

                tree["files"].append(file_info)

                self.processed += 1
                progress_percent = int((self.processed / total_files) * 100)
                self.progress.emit(progress_percent)

            elif item.is_dir():
                sub_tree = self.scan_folder(item, file_list, total_files)
                if sub_tree["files"] or sub_tree["subfolders"]:
                    tree["subfolders"].append(sub_tree)
        return tree
    
    def generate_preview(self, item, ext):
        try:
            if ext in [".txt", ".csv", ".json", ".md", ".py", ".html", ".xml"]:
                with open(item, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read(300)
                    return content.replace("\n", " ").replace("\r", " ")
            
            elif ext == ".docx":
                doc = Document(item)
                text = []
                for para in doc.paragraphs:
                    text.append(para.text)
                return " ".join(text)[:300]
            
            elif ext == ".pdf":
                with open(item, "rb") as f:
                    reader = PyPDF2.PdfReader(f)
                    text = ""
                    for page in reader.pages[:3]:  # Solo las primeras 3 páginas
                        text += page.extract_text()
                    return text[:300] if text else ""
            
        except Exception as e:
            return ""
        return ""


# --- INICIO FILE SCANNER APP ---
class FileScannerApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("File Scanner Launcher")
        self.setWindowIcon(QIcon("detective_.ico"))
        self.setFixedSize(1000, 720)

        self.allowed_exts = set()
        self.ext_buttons = {}
        self.quick_filter_buttons = []

        self.favorites = self.load_favorites()
        self.sort_asc = True

        self.setup_ui()

        self.refresh_favorites_list()

    def setup_ui(self):
        main_layout = QHBoxLayout()
        self.left_layout = QVBoxLayout()
        self.right_layout = QVBoxLayout()

        main_layout.addLayout(self.left_layout, 3)
        main_layout.addLayout(self.right_layout, 2)
        self.setLayout(main_layout)

        self.build_left_panel()
        self.build_right_panel()
    def build_left_panel(self):
        self.left_layout.addWidget(QLabel("🔍 Carpeta a escanear:"))
        self.path_input = QLineEdit()
        self.left_layout.addWidget(self.path_input)

        self.browse_button = QPushButton("Seleccionar carpeta")
        self.browse_button.clicked.connect(self.select_folder)
        self.left_layout.addWidget(self.browse_button)

        self.left_layout.addWidget(QLabel("💾 Carpeta de guardado:"))
        self.save_path_input = QLineEdit()
        self.left_layout.addWidget(self.save_path_input)

        self.save_browse_button = QPushButton("Seleccionar carpeta de guardado")
        self.save_browse_button.clicked.connect(self.select_save_folder)
        self.left_layout.addWidget(self.save_browse_button)

        self.left_layout.addWidget(QLabel("🚫 Extensiones a ignorar:"))
        self.ignore_checkboxes = {
            ".exe": QCheckBox(".exe"),
            ".dll": QCheckBox(".dll"),
            ".log": QCheckBox(".log"),
            ".tmp": QCheckBox(".tmp"),
            ".bak": QCheckBox(".bak")
        }
        ignore_layout = QHBoxLayout()
        for cb in self.ignore_checkboxes.values():
            cb.setChecked(True)
            ignore_layout.addWidget(cb)
        self.left_layout.addLayout(ignore_layout)

        self.left_layout.addWidget(QLabel("📂 Filtro rápido:"))
        quick_exts = [".docx", ".pdf", ".txt", ".json", ".csv", ".xlsx"]
        quick_layout = QHBoxLayout()
        for ext in quick_exts:
            btn = QPushButton(ext)
            btn.setCheckable(True)
            btn.setStyleSheet("background-color: lightgray;")
            btn.clicked.connect(lambda _, e=ext, b=btn: self.toggle_extension(e, b))
            quick_layout.addWidget(btn)
            self.ext_buttons[ext] = btn
            self.quick_filter_buttons.append((btn, ext))
        self.left_layout.addLayout(quick_layout)

        self.left_layout.addWidget(QLabel("🎯 Extensiones activas:"))
        self.active_list = QListWidget()
        self.left_layout.addWidget(self.active_list)

        custom_layout = QHBoxLayout()
        self.custom_ext_input = QLineEdit()
        self.custom_ext_input.setPlaceholderText("Escribe extensión...")
        self.custom_ext_input.returnPressed.connect(self.add_custom_extension)
        self.add_custom_btn = QPushButton("➕ Añadir")
        self.add_custom_btn.clicked.connect(self.add_custom_extension)
        custom_layout.addWidget(self.custom_ext_input)
        custom_layout.addWidget(self.add_custom_btn)
        self.left_layout.addLayout(custom_layout)

        clear_btn = QPushButton("🧹 Limpiar filtros")
        clear_btn.clicked.connect(self.clear_extensions)
        self.left_layout.addWidget(clear_btn)

        self.scan_button = QPushButton("Ejecutar escaneo")
        self.scan_button.clicked.connect(self.run_scan)
        self.left_layout.addWidget(self.scan_button)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.left_layout.addWidget(self.progress_bar)

        contact_btn = QPushButton("📩 Contacto")
        contact_btn.clicked.connect(self.show_contact_info)
        self.left_layout.addWidget(contact_btn)

    def build_right_panel(self):
        self.right_layout.addWidget(QLabel("⭐ Favoritos de extensiones:"))

        fav_top_layout = QHBoxLayout()
        self.search_fav_input = QLineEdit()
        self.search_fav_input.setPlaceholderText("🔍 Buscar favorito...")
        self.search_fav_input.textChanged.connect(self.refresh_favorites_list)

        sort_btn = QPushButton("🔃 A-Z/Z-A")
        sort_btn.clicked.connect(self.toggle_sort_favorites)

        fav_top_layout.addWidget(self.search_fav_input)
        fav_top_layout.addWidget(sort_btn)
        self.right_layout.addLayout(fav_top_layout)

        self.favorites_list = QListWidget()
        self.favorites_list.itemDoubleClicked.connect(self.load_selected_favorite)
        self.right_layout.addWidget(self.favorites_list)

        favorites_buttons = QHBoxLayout()

        save_fav_btn = QPushButton("➕ Guardar")
        save_fav_btn.clicked.connect(self.save_current_favorite)
        load_fav_btn = QPushButton("📂 Cargar")
        load_fav_btn.clicked.connect(self.load_selected_favorite)
        delete_fav_btn = QPushButton("❌ Eliminar")
        delete_fav_btn.clicked.connect(self.delete_selected_favorite)
        edit_fav_btn = QPushButton("✏️ Editar")
        edit_fav_btn.clicked.connect(self.edit_selected_favorite)

        favorites_buttons.addWidget(save_fav_btn)
        favorites_buttons.addWidget(load_fav_btn)
        favorites_buttons.addWidget(delete_fav_btn)
        favorites_buttons.addWidget(edit_fav_btn)

        self.right_layout.addLayout(favorites_buttons)

    # --- Funciones de favoritos, extensiones y escaneo las pego en el siguiente bloque porque pesan bastante ---

    # --- Funciones de favoritos ---

    def load_favorites(self):
        if os.path.exists("favorites.json"):
            with open("favorites.json", "r", encoding="utf-8") as f:
                favorites = json.load(f)
                for key, value in favorites.items():
                    if isinstance(value, list):
                        favorites[key] = {"extensions": value, "icon": "📂"}
                self.save_favorites(favorites)
        else:
            favorites = {}
            self.save_favorites(favorites)
        return favorites

    def save_favorites(self, favorites):
        with open("favorites.json", "w", encoding="utf-8") as f:
            json.dump(favorites, f, indent=2, ensure_ascii=False)

    def refresh_favorites_list(self):
        self.favorites_list.clear()
        search_text = self.search_fav_input.text().strip().lower()

        for name, data in self.favorites.items():
            exts = data.get("extensions", [])
            icon = data.get("icon", "📂")
            preview = ", ".join(exts)
            display_text = f"{icon} {name} [{preview}]"
            if search_text in name.lower() or search_text in preview.lower():
                item = QListWidgetItem(display_text)
                item.setData(Qt.UserRole, name)
                self.favorites_list.addItem(item)

    def save_current_favorite(self):
        current_exts = [self.active_list.item(i).text() for i in range(self.active_list.count())]
        if not current_exts:
            QMessageBox.warning(self, "Extensiones vacías", "No hay extensiones activas para guardar.")
            return

        dialog = FavoriteDialog(parent=self, extensions=current_exts)
        if dialog.exec_() == QDialog.Accepted:
            name, icon, exts = dialog.get_data()
            if name:
                self.favorites[name] = {"extensions": exts, "icon": icon}
                self.save_favorites(self.favorites)
                self.refresh_favorites_list()

    def load_selected_favorite(self):
        selected_items = self.favorites_list.selectedItems()
        if selected_items:
            item = selected_items[0]
            name = item.data(Qt.UserRole)
            data = self.favorites.get(name)
            if data:
                exts = data.get("extensions", [])
                self.active_list.clear()
                self.allowed_exts.clear()

                for ext in exts:
                    self.active_list.addItem(ext)
                    self.allowed_exts.add(ext)

                # Actualizar botones rápidos correctamente
                for btn, ext in self.quick_filter_buttons:
                    if ext in self.allowed_exts:
                        btn.setChecked(True)
                        btn.setStyleSheet("background-color: lightgreen;")
                    else:
                        btn.setChecked(False)
                        btn.setStyleSheet("background-color: lightgray;")

    def delete_selected_favorite(self):
        selected_items = self.favorites_list.selectedItems()
        if selected_items:
            item = selected_items[0]
            name = item.data(Qt.UserRole)
            if name in self.favorites:
                del self.favorites[name]
                self.save_favorites(self.favorites)
                self.refresh_favorites_list()

    def edit_selected_favorite(self):
        selected_items = self.favorites_list.selectedItems()
        if selected_items:
            item = selected_items[0]
            name = item.data(Qt.UserRole)
            data = self.favorites.get(name)
            if data:
                icon = data.get("icon", "📂")
                extensions = data.get("extensions", [])

                dialog = FavoriteDialog(parent=self, name=name, icon=icon, extensions=extensions)
                if dialog.exec_() == QDialog.Accepted:
                    new_name, new_icon, new_exts = dialog.get_data()
                    if new_name:
                        self.favorites.pop(name, None)
                        self.favorites[new_name] = {"extensions": new_exts, "icon": new_icon}
                        self.save_favorites(self.favorites)
                        self.refresh_favorites_list()

    def toggle_sort_favorites(self):
        self.sort_asc = not self.sort_asc
        self.favorites = dict(sorted(self.favorites.items(), reverse=not self.sort_asc))
        self.save_favorites(self.favorites)
        self.refresh_favorites_list()

    # --- Funciones de extensiones ---

    def toggle_extension(self, ext, button):
        if ext in self.allowed_exts:
            self.allowed_exts.remove(ext)
            button.setStyleSheet("background-color: lightgray;")
        else:
            self.allowed_exts.add(ext)
            button.setStyleSheet("background-color: lightgreen;")
        self.refresh_active_list()

    def add_custom_extension(self):
        ext = self.custom_ext_input.text().strip().lower()
        if not ext.startswith('.'):
            ext = "." + ext
        if ext and ext not in self.allowed_exts:
            self.allowed_exts.add(ext)
        self.refresh_active_list()
        self.custom_ext_input.clear()

    def refresh_active_list(self):
        self.active_list.clear()
        for ext in sorted(self.allowed_exts):
            self.active_list.addItem(ext)

    def clear_extensions(self):
        self.allowed_exts.clear()
        for btn, ext in self.quick_filter_buttons:
            btn.setStyleSheet("background-color: lightgray;")
        self.refresh_active_list()

    # --- Funciones de escaneo ---

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta")
        if folder:
            self.path_input.setText(folder)

    def select_save_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta de guardado")
        if folder:
            self.save_path_input.setText(folder)

    def run_scan(self):
        directory = self.path_input.text().strip()
        if not directory or not os.path.isdir(directory):
            QMessageBox.critical(self, "Error", "Por favor, introduce una ruta válida para escanear.")
            return

        ignored = {ext for ext, cb in self.ignore_checkboxes.items() if cb.isChecked()}
        allowed = self.allowed_exts if self.allowed_exts else None

        self.scan_button.setEnabled(False)
        self.browse_button.setEnabled(False)
        self.save_browse_button.setEnabled(False)
        self.progress_bar.setValue(0)

        self.worker = ScannerWorker(directory, ignored_exts=ignored, allowed_exts=allowed)
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.save_result)
        self.worker.start()

    def update_progress(self, value):
        self.progress_bar.setValue(value)

    def save_result(self, result):
        scan_folder_name = Path(result["path"]).name
        file_name = f"{scan_folder_name}.json"

        output_dir = self.save_path_input.text().strip()
        if not output_dir or not os.path.isdir(output_dir):
            output_dir = Path(__file__).parent

        output_path = Path(output_dir) / file_name

        # --- Añadir lista de nombres de archivos encontrados para preview ---
        preview_files = []

        def collect_files(tree):
            for f in tree.get("files", []):
                preview_files.append(f["name"])
            for sub in tree.get("subfolders", []):
                collect_files(sub)

        collect_files(result["tree"])

        result["preview_files"] = preview_files  # <-- Añadimos al JSON

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        self.progress_bar.setValue(100)

        # --- CORRECCIÓN AQUI ---
        file_paths = [str(Path(result["path"]) / name) for name in preview_files]
        dialog = FileResultsDialog(file_paths, output_dir)
        dialog.exec_()

        self.scan_button.setEnabled(True)
        self.browse_button.setEnabled(True)
        self.save_browse_button.setEnabled(True)

    def show_contact_info(self):
        QMessageBox.information(
            self,
            "Contacto",
            "📧 Contacto:\nÓscar Pérez\noscar.p.perez@renault.com"
        )

# --- MAIN LAUNCHER ---
if __name__ == "__main__":
    app = QApplication([])
    window = FileScannerApp()
    window.show()
    app.exec_()

