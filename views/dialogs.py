import os
import platform
import subprocess
import shutil
from pathlib import Path

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLineEdit, QComboBox, QListWidget,
    QPushButton, QHBoxLayout, QLabel, QFileDialog, QMessageBox
)
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt

from utils.file_utils import open_folder  # <- IMPORT CORRECTO


class FavoriteDialog(QDialog):
    # (sin cambios respecto a la versión anterior)
    ...


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

