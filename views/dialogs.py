import os
import platform
import subprocess
import shutil
from pathlib import Path

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLineEdit, QComboBox, QListWidget, QInputDialog,
    QPushButton, QHBoxLayout, QLabel, QFileDialog, QMessageBox, QWidget, QCheckBox, QListWidgetItem
)
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor, QFont
from PyQt5.QtCore import Qt, QSize

from utils.file_utils import open_folder  # <- IMPORT CORRECTO
from utils.quarantine import quarantine_file
from utils.ioc_store import IOCStore
from utils.settings import get_setting, set_setting


class WelcomeDialog(QDialog):
    """Welcome dialog with instructions for using FileScanner."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🔍 Welcome to FileScanner")
        self.setModal(True)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Main title
        title = QLabel("🔍 FileScanner - Forensic File Analyzer")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #2196F3; padding: 10px;")
        layout.addWidget(title)
        
        # Main description
        desc = QLabel(
            "FileScanner is a professional tool for forensic analysis of file systems "
            "that allows you to detect suspicious files using hashes, names, paths, and YARA rules."
        )
        desc.setWordWrap(True)
        desc.setAlignment(Qt.AlignCenter)
        desc.setStyleSheet("padding: 0px 10px 10px 10px; font-size: 11pt;")
        layout.addWidget(desc)
        
        # Instructions section
        instructions_label = QLabel("📖 <b>How to use FileScanner?</b>")
        instructions_label.setStyleSheet("font-size: 12pt; padding-top: 10px;")
        layout.addWidget(instructions_label)
        
        # Steps list - using plain text numbers to avoid emoji bugs
        steps = [
            ("1.", "Select folder to scan", 
             "Click 'Select folder to analyze' or use location favorites in the right panel."),
            
            ("2.", "Configure file filter", 
             "Enable the extensions you want to analyze (.pdf, .docx, etc.) or use quick filter."),
            
            ("3.", "(Optional) Load IOCs and YARA rules", 
             "In the right panel, load indicators of compromise (hashes/names) and YARA rules to detect threats."),
            
            ("4.", "Run scan", 
             "Press 'Run scan' and wait until it finishes. Results will be saved in JSON format."),
            
            ("5.", "Review results", 
             "When finished, you'll see a dialog with all found files. Those matching IOCs/YARA will be marked in red.")
        ]
        
        for num, title_text, desc_text in steps:
            step_widget = QWidget()
            step_layout = QHBoxLayout()
            step_layout.setContentsMargins(0, 5, 0, 5)
            
            # Number
            num_label = QLabel(num)
            num_label.setStyleSheet("font-size: 16pt; font-weight: bold; color: #2196F3;")
            num_label.setFixedWidth(40)
            num_label.setAlignment(Qt.AlignRight | Qt.AlignTop)
            step_layout.addWidget(num_label)
            
            # Text
            text_layout = QVBoxLayout()
            text_layout.setSpacing(2)
            
            title_step = QLabel(title_text)
            title_step.setStyleSheet("font-size: 10pt; font-weight: bold;")
            text_layout.addWidget(title_step)
            
            desc_step = QLabel(desc_text)
            desc_step.setWordWrap(True)
            desc_step.setStyleSheet("font-size: 9pt; color: #666;")
            text_layout.addWidget(desc_step)
            
            step_layout.addLayout(text_layout)
            step_widget.setLayout(step_layout)
            layout.addWidget(step_widget)
        
        # Additional tips
        tips_label = QLabel("💡 <b>Useful tips:</b>")
        tips_label.setStyleSheet("font-size: 11pt; padding-top: 15px;")
        layout.addWidget(tips_label)
        
        tips_text = QLabel(
            "• Use <b>Extension favorites</b> to save common configurations\n"
            "• Files can be <b>quarantined</b> from the results dialog\n"
            "• <b>Location collections</b> let you save frequent paths"
        )
        tips_text.setWordWrap(True)
        tips_text.setStyleSheet("font-size: 9pt; padding-left: 10px; color: #555;")
        layout.addWidget(tips_text)
        
        # "Don't show again" checkbox
        self.dont_show_checkbox = QCheckBox("Don't show this message again")
        self.dont_show_checkbox.setStyleSheet("padding-top: 15px; font-size: 10pt;")
        layout.addWidget(self.dont_show_checkbox)
        
        # Start button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        start_btn = QPushButton("✅ Got it, let's start!")
        start_btn.setProperty("role", "accent")
        start_btn.setMinimumHeight(40)
        start_btn.setStyleSheet("font-size: 11pt; padding: 10px 30px;")
        start_btn.setCursor(Qt.PointingHandCursor)
        start_btn.clicked.connect(self.accept)
        btn_layout.addWidget(start_btn)
        btn_layout.addStretch()
        
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
        self.setMinimumSize(700, 650)
        self.setMaximumSize(800, 750)
    
    def accept(self):
        """Guarda la preferencia del usuario antes de cerrar."""
        if self.dont_show_checkbox.isChecked():
            set_setting("hide_welcome_dialog", True)
        super().accept()


class LocationDialog(QDialog):
    def __init__(self, parent=None, name: str = "", path: str = ""):
        super().__init__(parent)
        self.setWindowTitle("Edit location collection")
        
        layout = QVBoxLayout()
        layout.setSpacing(8)
        layout.setContentsMargins(10, 10, 10, 10)

        # Name field
        lbl = QLabel("Collection name:")
        lbl.setStyleSheet("font-weight:600;")
        layout.addWidget(lbl)
        self.name_edit = QLineEdit(name)
        self.name_edit.setPlaceholderText("Ex: My Projects")
        layout.addWidget(self.name_edit)

        # Path field
        lbl2 = QLabel("Folder path:")
        lbl2.setStyleSheet("font-weight:600;")
        layout.addWidget(lbl2)
        h = QHBoxLayout()
        self.path_edit = QLineEdit(path)
        btn_browse = QPushButton("📂")
        btn_browse.setMaximumWidth(30)
        btn_browse.setCursor(Qt.PointingHandCursor)
        btn_browse.clicked.connect(self._browse_folder)
        h.addWidget(self.path_edit)
        h.addWidget(btn_browse)
        layout.addLayout(h)

        # Save / Cancel buttons
        btns = QHBoxLayout()
        save_btn   = QPushButton("Save")
        save_btn.setProperty("role", "primary")
        save_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setCursor(Qt.PointingHandCursor)
        save_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        btns.addWidget(save_btn)
        btns.addWidget(cancel_btn)
        layout.addLayout(btns)

        self.setLayout(layout)
        self.setMinimumSize(400, 200)   # width=400px, height=200px minimum

    def _browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select folder")
        if folder:
            self.path_edit.setText(folder)

    def get_data(self):
        """
        Returns (name, path)
        """
        return (
            self.name_edit.text().strip(),
            self.path_edit.text().strip()
        )


class FavoriteDialog(QDialog):
    
    def __init__(self, parent=None, name: str = "", icon: str = "📂", extensions: list = None):
        super().__init__(parent)
        self.setWindowTitle("Edit Favorites Collection")
        self.extensions = extensions or []
        layout = QVBoxLayout()
        layout.setSpacing(8)
        layout.setContentsMargins(10,10,10,10)

        # Collection name
        self.name_edit = QLineEdit(name)
        self.name_edit.setPlaceholderText("Collection name...")
        layout.addWidget(self.name_edit)

        # Icon selection
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

        # Editable extensions list
        self.ext_list = QListWidget()
        self.ext_list.addItems(self.extensions)
        self.ext_list.itemDoubleClicked.connect(self._edit_extension)
        layout.addWidget(self.ext_list)

        # Buttons to add / remove
        btns = QHBoxLayout()
        add_btn = QPushButton("➕ Add extension")
        add_btn.setCursor(Qt.PointingHandCursor)
        del_btn = QPushButton("❌ Remove selected")
        del_btn.setCursor(Qt.PointingHandCursor)
        add_btn.clicked.connect(self._add_extension)
        del_btn.clicked.connect(self._delete_extension)
        btns.addWidget(add_btn)
        btns.addWidget(del_btn)
        layout.addLayout(btns)

        # Save / Cancel
        ctrl_btns = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.setProperty("role", "primary")
        save_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setCursor(Qt.PointingHandCursor)
        save_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        ctrl_btns.addWidget(save_btn)
        ctrl_btns.addWidget(cancel_btn)
        layout.addLayout(ctrl_btns)

        self.setLayout(layout)

    def _add_extension(self):
        ext, ok = QInputDialog.getText(self, "New extension", "Enter extension (ex: .pdf)")
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


class IgnoreEditorDialog(QDialog):
    """Dialog to edit the list of ignored extensions and their enabled state.

    Provides a simple list editor with add/delete and the ability to toggle
    whether each extension is enabled for ignoring.
    """
    def __init__(self, parent=None, extensions=None, enabled_map=None):
        super().__init__(parent)
        self.setWindowTitle("Editar extensiones a ignorar")
        self.resize(480, 360)

        self.extensions = list(extensions or [])
        self.enabled_map = dict(enabled_map or {})

        layout = QVBoxLayout()
        layout.setSpacing(8)
        layout.setContentsMargins(10, 10, 10, 10)

        self.list_widget = QListWidget()
        self._reload_list()
        layout.addWidget(self.list_widget)

        btn_h = QHBoxLayout()
        add_btn = QPushButton("Añadir")
        add_btn.clicked.connect(self._add)
        del_btn = QPushButton("Eliminar seleccionada")
        del_btn.clicked.connect(self._delete_selected)
        toggle_btn = QPushButton("Alternar estado")
        toggle_btn.clicked.connect(self._toggle_selected)
        btn_h.addWidget(add_btn)
        btn_h.addWidget(del_btn)
        btn_h.addWidget(toggle_btn)
        layout.addLayout(btn_h)

        ctrl = QHBoxLayout()
        save_btn = QPushButton("Guardar")
        save_btn.setProperty("role", "primary")
        save_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancelar")
        cancel_btn.clicked.connect(self.reject)
        ctrl.addStretch()
        ctrl.addWidget(save_btn)
        ctrl.addWidget(cancel_btn)
        layout.addLayout(ctrl)

        self.setLayout(layout)

    def _reload_list(self):
        self.list_widget.clear()
        for e in sorted(self.extensions):
            state = self.enabled_map.get(e, True)
            it = QListWidgetItem(f"{e}  {'(habilitado)' if state else '(deshabilitado)'}")
            it.setData(Qt.UserRole, e)
            self.list_widget.addItem(it)

    def _add(self):
        text, ok = QInputDialog.getText(self, "Nueva extensión", "Introduce extensión (ej: .tmp)")
        if not ok or not text.strip():
            return
        ext = text.strip().lower()
        if not ext.startswith('.'):
            ext = '.' + ext
        if ext not in self.extensions:
            self.extensions.append(ext)
            self.enabled_map[ext] = True
            self._reload_list()

    def _delete_selected(self):
        for it in list(self.list_widget.selectedItems()):
            ext = it.data(Qt.UserRole)
            if ext in self.extensions:
                self.extensions.remove(ext)
            self.enabled_map.pop(ext, None)
            self.list_widget.takeItem(self.list_widget.row(it))

    def _toggle_selected(self):
        for it in list(self.list_widget.selectedItems()):
            ext = it.data(Qt.UserRole)
            cur = self.enabled_map.get(ext, True)
            self.enabled_map[ext] = not cur
        self._reload_list()

    def get_data(self):
        return list(self.extensions), dict(self.enabled_map)


class FileResultsDialog(QDialog):
    def __init__(self, file_paths, output_dir, ioc_map=None):
        super().__init__()
        self.setWindowTitle("Resultados del escaneo")
        self.resize(700,500)
        self.setWindowIcon(QIcon("detective_.ico"))
        self.file_paths = [str(Path(p).resolve()) for p in file_paths]
        self.output_dir = output_dir
        self.ioc_map = ioc_map or {}

        layout = QVBoxLayout()
        layout.setSpacing(8)
        layout.setContentsMargins(10,10,10,10)

        # Search bar and IOC-only toggle on the same row
        top_h = QHBoxLayout()
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("🔍 Buscar archivo...")
        self.search_bar.textChanged.connect(self.apply_list_filter)
        top_h.addWidget(self.search_bar)

        self.only_iocs_cb = QCheckBox("Mostrar sólo sospechosos")
        self.only_iocs_cb.setToolTip("Filtrar la lista para mostrar sólo archivos marcados como IOC")
        self.only_iocs_cb.toggled.connect(self.apply_list_filter)
        top_h.addWidget(self.only_iocs_cb)

        layout.addLayout(top_h)

        self.list_widget = QListWidget()
        self.list_widget.setAlternatingRowColors(True)
        self.list_widget.itemDoubleClicked.connect(self.open_file_location)
        layout.addWidget(self.list_widget)

        action_layout = QHBoxLayout()
        action_layout.addWidget(QLabel("Acción:"))
        self.action_combo = QComboBox()
        self.action_combo.addItems(["Copiar", "Mover", "Cuarentena"])
        action_layout.addWidget(self.action_combo)
        layout.addLayout(action_layout)

        btn_layout = QHBoxLayout()
        open_btn = QPushButton("Abrir carpeta de resultados")
        open_btn.clicked.connect(lambda: open_folder(self.output_dir))  # ahora sí importado
        proc_btn = QPushButton("Procesar archivos…")
        proc_btn.setProperty("role", "primary")
        proc_btn.clicked.connect(self.process_files_to_folder)
        close_btn = QPushButton("Cerrar")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(open_btn)
        btn_layout.addWidget(proc_btn)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

        # Si hay IOCs, mostrar un resumen emergente y ofrecer filtrar
        if self.ioc_map:
            summary_lines = []
            for path, matches in list(self.ioc_map.items())[:10]:
                summary_lines.append(f"{Path(path).name}: {', '.join(matches)}")
            summary = "\n".join(summary_lines)
            if len(self.ioc_map) > 10:
                summary += f"\n... y {len(self.ioc_map)-10} más"

            resp = QMessageBox.question(self, "IOCs detectadas",
                f"Se han detectado {len(self.ioc_map)} archivos sospechosos:\n\n{summary}\n\n¿Filtrar la lista para mostrar sólo los sospechosos?",
                QMessageBox.Yes | QMessageBox.No)
            if resp == QMessageBox.Yes:
                # toggle the checkbox to the 'on' position and refresh
                self.only_iocs_cb.setChecked(True)
                self.apply_list_filter()
        # Ensure the list is populated according to current filter/search state
        self.apply_list_filter()

        # Conectar selección para mostrar detalles
        self.list_widget.itemSelectionChanged.connect(self._on_selection_changed)

        # Detalles del archivo seleccionado
        self.details_label = QLabel("")
        layout.addWidget(self.details_label)

        # Botón para mover selección a cuarentena
        self.quarantine_selected_btn = QPushButton("Mover seleccionados a cuarentena")
        self.quarantine_selected_btn.setProperty("role", "primary")
        self.quarantine_selected_btn.clicked.connect(self.move_selected_to_quarantine)
        layout.addWidget(self.quarantine_selected_btn)

    def apply_list_filter(self, _=None):
        """Repoblates the list_widget according to search text and IOC-only toggle."""
        txt = self.search_bar.text().lower().strip()
        show_only_iocs = self.only_iocs_cb.isChecked()
        self.list_widget.clear()
        for p in self.file_paths:
            if txt and txt not in p.lower():
                continue
            if show_only_iocs and p not in self.ioc_map:
                continue
            display = p
            if p in self.ioc_map:
                display = f"{p} [IOC]"
            item = QListWidgetItem(display)
            # dynamic sizing based on font metrics so items don't appear cramped
            try:
                fm = self.list_widget.fontMetrics()
                height = max(36, fm.height() + 14)
                item.setSizeHint(QSize(0, height))
            except Exception:
                try:
                    item.setSizeHint(QSize(0, 36))
                except Exception:
                    pass

            # set an icon based on file extension
            try:
                icon = self._icon_for_path(p)
                if icon:
                    item.setIcon(icon)
            except Exception:
                pass

            item.setData(Qt.UserRole, p)
            self.list_widget.addItem(item)
            if p in self.ioc_map:
                try:
                    item.setForeground(QColor('red'))
                except Exception:
                    pass

    def filter_only_iocs(self):
        # Mostrar sólo ficheros que aparecen en ioc_map
        self.list_widget.clear()
        for p in self.file_paths:
            if p in self.ioc_map:
                self.list_widget.addItem(p)

    def _on_selection_changed(self):
        sels = self.list_widget.selectedItems()
        if not sels:
            self.details_label.setText("")
            return
        # usamos el dato guardado para obtener la ruta real
        item = sels[0]
        path = item.data(Qt.UserRole) or item.text()
        matches = self.ioc_map.get(path) or []
        lines = [f"Path: {path}"]
        if matches:
            lines.append("IOC matches:")
            for m in matches:
                lines.append(f" - {m}")
        self.details_label.setText("\n".join(lines))

    def open_file_location(self, item):
        """Open the folder containing the selected file item."""
        # try to use the stored path (Qt.UserRole) if present
        try:
            path = item.data(Qt.UserRole) or item.text()
        except Exception:
            path = item.text()
        folder = str(Path(path).parent)
        open_folder(folder)

    def process_files_to_folder(self):
        """Copy/Move selected files to a chosen folder (used by Results dialog)."""
        dst = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta destino")
        if not dst:
            return

        action = self.action_combo.currentText()  # "Copiar" o "Mover"
        count_ok = 0
        errors = []

        # iterate over currently selected items to respect user choice
        sources = [it.data(Qt.UserRole) or it.text() for it in list(self.list_widget.selectedItems())]
        if not sources:
            # fallback: operate over all files
            sources = list(self.file_paths)

        for src in sources:
            # Sólo tratamos ficheros
            if not os.path.isfile(src):
                continue

            fn = os.path.basename(src)
            tgt = os.path.join(dst, fn)

            try:
                if action == "Copiar":
                    # Si ya existe, sobreescribir:
                    shutil.copy2(src, tgt)
                elif action == "Mover":
                    shutil.move(src, tgt)
                else:  # Cuarentena
                    # Confirmación adicional por seguridad
                    ans = QMessageBox.question(self, "Confirmar cuarentena",
                        f"Vas a mover {fn} a la cuarentena en: {dst}\n¿Continuar?",
                        QMessageBox.Yes | QMessageBox.No)
                    if ans != QMessageBox.Yes:
                        continue
                    # Mover con renombrado seguro y log
                    try:
                        quarantine_file(src, dst, reason="manual from UI")
                    except Exception:
                        raise

                count_ok += 1

            except Exception as e:
                errors.append(f"{fn}: {e}")

        # Preparamos mensaje de respuesta
        verbo = "copiaron" if action == "Copiar" else "movieron"
        msg = f"Se {verbo} {count_ok} archivos."

        if errors:
            msg += "\n\nErrores en algunos archivos:\n" + "\n".join(errors)

        QMessageBox.information(self, "Operación completada", msg)

    def move_selected_to_quarantine(self):
        sels = self.list_widget.selectedItems()
        if not sels:
            QMessageBox.information(self, "Nada seleccionado", "Selecciona al menos un fichero para mover a cuarentena.")
            return

        # Preguntar carpeta de cuarentena
        qdir = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta de cuarentena", self.output_dir)
        if not qdir:
            return

        count = 0
        errors = []
        for item in list(sels):
            path = item.data(Qt.UserRole) or item.text()
            try:
                quarantine_file(path, qdir, reason="manual from Results dialog")
                count += 1
                # eliminar del listado y del mapa
                if path in self.file_paths:
                    self.file_paths.remove(path)
                if path in self.ioc_map:
                    self.ioc_map.pop(path, None)
                self.list_widget.takeItem(self.list_widget.row(item))
            except Exception as e:
                errors.append(f"{path}: {e}")

        msg = f"Se movieron {count} archivos a la cuarentena."
        if errors:
            msg += "\n\nErrores:\n" + "\n".join(errors)
        QMessageBox.information(self, "Cuarentena", msg)


class IOCViewerDialog(QDialog):
    """Diálogo simple para ver y gestionar las IOCs cargadas en memoria.

    Muestra tres listas: hashes, names y paths. Permite eliminar selecciones y vaciar todo.
    """
    def __init__(self, parent=None, ioc_store: IOCStore = None):
        super().__init__(parent)
        self.setWindowTitle("IOCs cargadas")
        self.resize(600, 400)
        self.ioc_store = ioc_store or IOCStore()

        layout = QVBoxLayout()

        # Counts
        counts_lbl = QLabel(self._counts_text())
        layout.addWidget(counts_lbl)

        lists_layout = QHBoxLayout()

        # Hashes list
        self.hash_list = QListWidget()
        self.hash_list.addItems(sorted(self.ioc_store.hashes))
        lists_layout.addWidget(self._wrap_list_with_label("Hashes", self.hash_list))

        # Names list
        self.name_list = QListWidget()
        self.name_list.addItems(sorted(self.ioc_store.names))
        lists_layout.addWidget(self._wrap_list_with_label("Names", self.name_list))

        # Paths list
        self.path_list = QListWidget()
        self.path_list.addItems(sorted(self.ioc_store.paths))
        lists_layout.addWidget(self._wrap_list_with_label("Paths", self.path_list))

        layout.addLayout(lists_layout)

        btns = QHBoxLayout()
        remove_btn = QPushButton("Eliminar seleccionados")
        remove_btn.clicked.connect(self._remove_selected)
        clear_btn = QPushButton("Vaciar IOCs")
        clear_btn.clicked.connect(self._clear_all)
        close_btn = QPushButton("Cerrar")
        close_btn.clicked.connect(self.accept)
        btns.addWidget(remove_btn)
        btns.addWidget(clear_btn)
        btns.addStretch()
        btns.addWidget(close_btn)
        layout.addLayout(btns)

        self.setLayout(layout)

    def _counts_text(self):
        return f"Hashes: {len(self.ioc_store.hashes)}  —  Names: {len(self.ioc_store.names)}  —  Paths: {len(self.ioc_store.paths)}"

    def _wrap_list_with_label(self, label_text, widget):
        w = QVBoxLayout()
        w.addWidget(QLabel(label_text))
        w.addWidget(widget)
        container = QWidget()
        container.setLayout(w)
        return container

    def _remove_selected(self):
        # Remove from store and update lists
        for lst, kind in ((self.hash_list, 'hashes'), (self.name_list, 'names'), (self.path_list, 'paths')):
            for it in list(lst.selectedItems()):
                val = it.text()
                if kind == 'hashes':
                    self.ioc_store.hashes.discard(val)
                elif kind == 'names':
                    self.ioc_store.names.discard(val)
                else:
                    self.ioc_store.paths.discard(val)
                lst.takeItem(lst.row(it))
        # Update counts label
        # find counts label (first widget)
        if isinstance(self.layout().itemAt(0).widget(), QLabel):
            self.layout().itemAt(0).widget().setText(self._counts_text())

    def _clear_all(self):
        self.ioc_store.clear()
        self.hash_list.clear(); self.name_list.clear(); self.path_list.clear()
        if isinstance(self.layout().itemAt(0).widget(), QLabel):
            self.layout().itemAt(0).widget().setText(self._counts_text())

    def _icon_for_path(self, path: str) -> QIcon:
        """Generate a small colored icon for a file based on its extension.

        Uses a deterministic color derived from the extension and draws
        a short label (e.g. "PDF", "DOC") on a colored square pixmap.
        """
        try:
            ext = Path(path).suffix.lower().lstrip('.')
            if not ext:
                label = "FILE"
            else:
                label = ext.upper()[:3]

            # simple color map by hashing extension
            h = sum(ord(c) for c in ext) if ext else 0
            colors = [QColor('#4f83ff'), QColor('#6aa0ff'), QColor('#ff8a65'), QColor('#9ccc65'), QColor('#ffca28'), QColor('#b39ddb')]
            color = colors[h % len(colors)]

            size = 24
            pix = QPixmap(size, size)
            pix.fill(Qt.transparent)
            p = QPainter(pix)
            p.setRenderHint(QPainter.Antialiasing)
            p.setBrush(color)
            p.setPen(Qt.NoPen)
            p.drawRoundedRect(0, 0, size, size, 6, 6)
            f = QFont()
            f.setPointSize(8)
            f.setBold(True)
            p.setFont(f)
            p.setPen(QColor('#ffffff'))
            rect = pix.rect()
            # draw centered text (short label)
            p.drawText(rect, Qt.AlignCenter, label)
            p.end()
            return QIcon(pix)
        except Exception:
            return QIcon()

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
                elif action == "Mover":
                    shutil.move(src, tgt)
                else:  # Cuarentena
                    # Confirmación adicional por seguridad
                    ans = QMessageBox.question(self, "Confirmar cuarentena",
                        f"Vas a mover {fn} a la cuarentena en: {dst}\n¿Continuar?",
                        QMessageBox.Yes | QMessageBox.No)
                    if ans != QMessageBox.Yes:
                        continue
                    # Mover con renombrado seguro y log
                    try:
                        quarantine_file(src, dst, reason="manual from UI")
                    except Exception as e:
                        raise

                count_ok += 1

            except Exception as e:
                errors.append(f"{fn}: {e}")

        # Preparamos mensaje de respuesta
        verbo = "copiaron" if action == "Copiar" else "movieron"
        msg = f"Se {verbo} {count_ok} archivos."

        if errors:
            msg += "\n\nErrores en algunos archivos:\n" + "\n".join(errors)

        QMessageBox.information(self, "Operación completada", msg)

