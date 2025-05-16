import os
import platform
import subprocess
import shutil
from pathlib import Path

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLineEdit, QComboBox, QListWidget, QInputDialog,
    QPushButton, QHBoxLayout, QLabel, QFileDialog, QMessageBox
)
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt

from utils.file_utils import open_folder  # <- IMPORT CORRECTO

class LocationDialog(QDialog):
    def __init__(self, parent=None, name: str = "", path: str = ""):
        super().__init__(parent)
        self.setWindowTitle("Editar colección de ubicaciones")

        layout = QVBoxLayout()

        # Campo nombre
        layout.addWidget(QLabel("Nombre de la colección:"))
        self.name_edit = QLineEdit(name)
        self.name_edit.setPlaceholderText("Ej: Mis Proyectos")
        layout.addWidget(self.name_edit)

        # Campo ruta
        layout.addWidget(QLabel("Ruta de la carpeta:"))
        h = QHBoxLayout()
        self.path_edit = QLineEdit(path)
        btn_browse = QPushButton("📂")
        btn_browse.setMaximumWidth(30)
        btn_browse.clicked.connect(self._browse_folder)
        h.addWidget(self.path_edit)
        h.addWidget(btn_browse)
        layout.addLayout(h)

        # Botones Guardar / Cancelar
        btns = QHBoxLayout()
        save_btn   = QPushButton("Guardar")
        cancel_btn = QPushButton("Cancelar")
        save_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        btns.addWidget(save_btn)
        btns.addWidget(cancel_btn)
        layout.addLayout(btns)

        self.setLayout(layout)
        self.setMinimumSize(400, 200)   # ancho=400px, alto=200px como mínimo

    def _browse_folder(self):
        carpeta = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta")
        if carpeta:
            self.path_edit.setText(carpeta)

    def get_data(self):
        """
        Devuelve (nombre, ruta)
        """
        return (
            self.name_edit.text().strip(),
            self.path_edit.text().strip()
        )


class FavoriteDialog(QDialog):
    
    def __init__(self, parent=None, name: str = "", icon: str = "📂", extensions: list = None):
        super().__init__(parent)
        self.setWindowTitle("Editar Colección de Favoritos")
        self.extensions = extensions or []

        layout = QVBoxLayout()

        # Nombre de la colección
        self.name_edit = QLineEdit(name)
        self.name_edit.setPlaceholderText("Nombre de la colección...")
        layout.addWidget(self.name_edit)

        # Selección de icono
        self.icon_combo = QComboBox()
        self.icon_combo.addItems([
            "⭐", "📂", "💻", "🎨", "📄", "🔧",
            "📊", "🗃️", "🎵", "🖼️", "🎥", "🚀",
            "🛠️", "🧩"
        ])
        if icon:
            idx = self.icon_combo.findText(icon)
            if idx != -1:
                self.icon_combo.setCurrentIndex(idx)
        layout.addWidget(self.icon_combo)

        # Lista editable de extensiones
        self.ext_list = QListWidget()
        self.ext_list.addItems(self.extensions)
        self.ext_list.itemDoubleClicked.connect(self._edit_extension)
        layout.addWidget(self.ext_list)

        # Botones para añadir / eliminar
        btns = QHBoxLayout()
        add_btn = QPushButton("➕ Añadir extensión")
        del_btn = QPushButton("❌ Eliminar seleccionada")
        add_btn.clicked.connect(self._add_extension)
        del_btn.clicked.connect(self._delete_extension)
        btns.addWidget(add_btn)
        btns.addWidget(del_btn)
        layout.addLayout(btns)

        # Guardar / Cancelar
        ctrl_btns = QHBoxLayout()
        save_btn = QPushButton("Guardar")
        cancel_btn = QPushButton("Cancelar")
        save_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        ctrl_btns.addWidget(save_btn)
        ctrl_btns.addWidget(cancel_btn)
        layout.addLayout(ctrl_btns)

        self.setLayout(layout)

    def _add_extension(self):
        ext, ok = QInputDialog.getText(self, "Nueva extensión", "Introduce extensión (ej: .pdf)")
        if not ok or not ext.strip():
            return
        ext = ext.strip().lower()
        if not ext.startswith("."):
            ext = "." + ext
        if ext not in self.extensions:
            self.extensions.append(ext)
            self.ext_list.addItem(ext)

    def _delete_extension(self):
        for item in self.ext_list.selectedItems():
            self.extensions.remove(item.text())
            self.ext_list.takeItem(self.ext_list.row(item))

    def _edit_extension(self, item):
        old = item.text()
        new_ext, ok = QInputDialog.getText(self, "Editar extensión", "Modificar extensión:", text=old)
        if not ok or not new_ext.strip():
            return
        new_ext = new_ext.strip().lower()
        if not new_ext.startswith("."):
            new_ext = "." + new_ext
        idx = self.extensions.index(old)
        self.extensions[idx] = new_ext
        item.setText(new_ext)

    def get_data(self):
        """
        Devuelve una tupla (name, icon, extensions)
        """
        return (
            self.name_edit.text().strip(),
            self.icon_combo.currentText(),
            list(self.extensions)
        )


class FileResultsDialog(QDialog):
    def __init__(self, file_paths, output_dir):
        super().__init__()
        self.setWindowTitle("Resultados del escaneo")
        self.resize(700,500)
        self.setWindowIcon(QIcon("detective_.ico"))
        self.file_paths = [str(Path(p).resolve()) for p in file_paths]
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

        action_layout = QHBoxLayout()
        action_layout.addWidget(QLabel("Acción:"))
        self.action_combo = QComboBox()
        self.action_combo.addItems(["Copiar","Mover"])
        action_layout.addWidget(self.action_combo)
        layout.addLayout(action_layout)

        btn_layout = QHBoxLayout()
        open_btn = QPushButton("Abrir carpeta de resultados")
        open_btn.clicked.connect(lambda: open_folder(self.output_dir))  # ahora sí importado
        proc_btn = QPushButton("Procesar archivos…")
        proc_btn.clicked.connect(self.process_files_to_folder)
        close_btn = QPushButton("Cerrar")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(open_btn)
        btn_layout.addWidget(proc_btn)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def filter_files(self, txt):
        self.list_widget.clear()
        for p in self.file_paths:
            if txt.lower() in p.lower():
                self.list_widget.addItem(p)

    def open_file_location(self, item):
        folder = str(Path(item.text()).parent)
        open_folder(folder)

    def process_files_to_folder(self):
        dst = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta destino")
        if not dst:
            return

        action = self.action_combo.currentText()  # "Copiar" o "Mover"
        count_ok = 0
        errors = []

        for src in self.file_paths:
            # Sólo tratamos ficheros
            if not os.path.isfile(src):
                continue

            fn = os.path.basename(src)
            tgt = os.path.join(dst, fn)

            try:
                if action == "Copiar":
                    # Si ya existe, sobreescribir:
                    shutil.copy2(src, tgt)
                else:
                    shutil.move(src, tgt)
                count_ok += 1

            except Exception as e:
                errors.append(f"{fn}: {e}")

        # Preparamos mensaje de respuesta
        verbo = "copiaron" if action == "Copiar" else "movieron"
        msg = f"Se {verbo} {count_ok} archivos."

        if errors:
            msg += "\n\nErrores en algunos archivos:\n" + "\n".join(errors)

        QMessageBox.information(self, "Operación completada", msg)

