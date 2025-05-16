from pathlib import Path

from PyQt5.QtWidgets import (
    QWidget, QApplication, QMessageBox,
    QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QLineEdit, QCheckBox, QListWidget, QProgressBar,
    QFileDialog, QShortcut
)
from PyQt5.QtGui import QIcon, QPalette, QColor, QKeySequence
from PyQt5.QtCore import Qt

class ActiveListWidget(QListWidget):
    """
    Subclase de QListWidget que maneja Supr y Backspace para eliminar ítems.
    """
    def __init__(self, parent=None):
        super().__init__(parent)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            view = self.parent()  # tu FileScannerView
            # recogemos qué había seleccionado
            to_remove = [item.text() for item in self.selectedItems()]
            for text in to_remove:
                # 1) lo quitamos de la lista visual
                items = self.findItems(text, Qt.MatchExactly)
                for itm in items:
                    self.takeItem(self.row(itm))
                # 2) lo quitamos de la lógica
                if text in view.allowed_exts:
                    view.allowed_exts.remove(text)

            # 3) Actulizamos la vista de activos
            view._refresh_active_list()

            # 4) Sincronizamos botón rápidos
            for btn, ext in view.quick_filter_buttons:
                if ext in view.allowed_exts:
                    btn.setChecked(True)
                    btn.setStyleSheet("background-color: lightgreen;")
                else:
                    btn.setChecked(False)
                    btn.setStyleSheet("background-color: lightgray;")

        else:
            super().keyPressEvent(event)


class FileScannerView(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FileScanner")
        self.setWindowIcon(QIcon("detective_.ico"))
        self._ajustar_a_pantalla()

        self.dark_mode_active = False
        self.allowed_exts = set()
        self.ext_buttons = {}
        self.quick_filter_buttons = []

        # Llamada correcta al método que monta la UI
        self.setup_ui()
        
    def _ajustar_a_pantalla(self):
        pantalla = QApplication.primaryScreen().availableGeometry()
        self.setGeometry(pantalla)
        # Si se quiere establecer tamaño mínimo y dejar dimensionable
        # self.setMinimumSize(pantalla.width(), pantalla.height())

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
        # Botón modo oscuro/Claro
        self.toggle_dark_mode_btn = QPushButton("🌙 Modo Oscuro")
        self.toggle_dark_mode_btn.setCheckable(True)
        self.toggle_dark_mode_btn.clicked.connect(self._toggle_dark_mode_ui)
        self.left_layout.addWidget(self.toggle_dark_mode_btn)

        # Ruta a escanear
        self.left_layout.addWidget(QLabel("🔍 Ruta de la carpeta a escanear:"))
        self.path_input = QLineEdit()
        self.left_layout.addWidget(self.path_input)
        self.browse_button = QPushButton("Seleccionar carpeta para analizar")
        self.browse_button.clicked.connect(self._select_folder)
        self.left_layout.addWidget(self.browse_button)

        # Ruta de guardado JSON
        self.left_layout.addWidget(QLabel("💾 Ruta para guardar el JSON generado:"))
        self.save_path_input = QLineEdit()
        self.left_layout.addWidget(self.save_path_input)
        self.save_browse_button = QPushButton("Seleccionar carpeta de guardado")
        self.save_browse_button.clicked.connect(self._select_save_folder)
        self.left_layout.addWidget(self.save_browse_button)

        # Extensiones a ignorar
        self.left_layout.addWidget(QLabel("🚫 Extensiones a ignorar:"))
        self.ignore_checkboxes = {
            ext: QCheckBox(ext)
            for ext in [".exe", ".dll", ".log", ".tmp", ".bak", ".bat", ".bash"]
        }
        ignore_layout = QHBoxLayout()
        for cb in self.ignore_checkboxes.values():
            cb.setChecked(True)
            ignore_layout.addWidget(cb)
        self.left_layout.addLayout(ignore_layout)

        # Filtro rápido
        self.left_layout.addWidget(QLabel("📂 Filtro rápido:"))
        quick_exts = [".docx", ".pdf", ".txt", ".csv", ".xlsx", ".xml", ".json"]
        quick_layout = QHBoxLayout()
        for ext in quick_exts:
            btn = QPushButton(ext)
            btn.setCheckable(True)
            btn.setStyleSheet("background-color: lightgray;")
            btn.clicked.connect(lambda _, e=ext, b=btn: self._toggle_extension(e, b))
            quick_layout.addWidget(btn)
            self.ext_buttons[ext] = btn
            self.quick_filter_buttons.append((btn, ext))
        self.left_layout.addLayout(quick_layout)

        # Añadir extensión personalizada
        custom_layout = QHBoxLayout()
        self.custom_ext_input = QLineEdit()
        self.custom_ext_input.setPlaceholderText("Añadir extensión...")
        self.custom_ext_input.returnPressed.connect(self._add_custom_extension)
        self.add_custom_btn = QPushButton("➕ Añadir")
        self.add_custom_btn.clicked.connect(self._add_custom_extension)
        custom_layout.addWidget(self.custom_ext_input)
        custom_layout.addWidget(self.add_custom_btn)
        self.left_layout.addLayout(custom_layout)

        # Lista de extensiones activas
        self.left_layout.addWidget(QLabel("🎯 Extensiones activas:"))
        self.active_list = ActiveListWidget()
        self.left_layout.addWidget(self.active_list)
        
        # Shortcuts para eliminar selección con Supr o Backspace
        delete_shortcut = QShortcut(QKeySequence.Delete, self.active_list)
        delete_shortcut.activated.connect(self._remove_selected_active_extensions)
        backspace_shortcut = QShortcut(QKeySequence.Backspace, self.active_list)
        backspace_shortcut.activated.connect(self._remove_selected_active_extensions)

        # Botones de acción
        clear_btn = QPushButton("🧹 Limpiar filtros")
        clear_btn.clicked.connect(self._clear_extensions)
        self.left_layout.addWidget(clear_btn)

        # Botones de escaneo: iniciar / detener
        h_scan = QHBoxLayout()
        self.scan_button = QPushButton("▶️ Ejecutar escaneo")
        self.stop_button = QPushButton("⏹️ Detener escaneo")
        self.stop_button.setEnabled(False)   # deshabilitado hasta que empiece
        h_scan.addWidget(self.scan_button)
        h_scan.addWidget(self.stop_button)
        self.left_layout.addLayout(h_scan)

        self.progress_bar = QProgressBar()
        self.left_layout.addWidget(self.progress_bar)

        contact_btn = QPushButton("📩 Contacto")
        contact_btn.clicked.connect(self._show_contact_info)
        self.left_layout.addWidget(contact_btn)

    def build_right_panel(self):
        
        # Favoritos de ubicaciones
        self.right_layout.addWidget(QLabel("📁 Favoritos de ubicaciones:"))
        self.location_list = QListWidget()
        self.right_layout.addWidget(self.location_list)

        loc_btns = QHBoxLayout()
        self.add_loc_btn      = QPushButton("➕ Añadir ubicación")
        self.del_loc_btn      = QPushButton("❌ Eliminar ubicación")
        self.save_loc_coll_btn= QPushButton("📂 Guardar colección")
        self.load_loc_coll_btn= QPushButton("📥 Cargar colección")
        self.edit_loc_coll_btn= QPushButton("✏️ Editar colección")

        for w in (
            self.add_loc_btn, self.del_loc_btn,
            self.save_loc_coll_btn, self.load_loc_coll_btn, self.edit_loc_coll_btn
        ):
            loc_btns.addWidget(w)
        self.right_layout.addLayout(loc_btns)
        
        # Favoritos de extensiones
        self.right_layout.addWidget(QLabel("⭐ Favoritos de extensiones:"))

        fav_top_layout = QHBoxLayout()
        self.search_fav_input = QLineEdit()
        self.search_fav_input.setPlaceholderText("🔍 Buscar favorito...")
        fav_top_layout.addWidget(self.search_fav_input)

        self.sort_btn = QPushButton("🔃 A-Z/Z-A")
        fav_top_layout.addWidget(self.sort_btn)
        self.right_layout.addLayout(fav_top_layout)

        self.favorites_list = QListWidget()
        self.right_layout.addWidget(self.favorites_list)

        fav_btns = QHBoxLayout()
        self.save_fav_btn = QPushButton("➕ Guardar colección")
        self.load_fav_btn = QPushButton("📂 Cargar colección")
        self.delete_fav_btn = QPushButton("❌ Eliminar colección")
        self.edit_fav_btn = QPushButton("✏️ Editar colección")
        for w in (self.save_fav_btn, self.load_fav_btn, self.delete_fav_btn, self.edit_fav_btn):
            fav_btns.addWidget(w)
        self.right_layout.addLayout(fav_btns)

    # — Métodos de UI internos —————————————————————————————————————————

    def _toggle_extension(self, ext, button):
        if ext in self.allowed_exts:
            self.allowed_exts.remove(ext)
            button.setStyleSheet("background-color: lightgray;")
        else:
            self.allowed_exts.add(ext)
            button.setStyleSheet("background-color: lightgreen;")
        self._refresh_active_list()

    def _add_custom_extension(self):
        ext = self.custom_ext_input.text().strip().lower()
        if not ext.startswith("."):
            ext = "." + ext
        if ext and ext not in self.allowed_exts:
            self.allowed_exts.add(ext)
        self.custom_ext_input.clear()
        self._refresh_active_list()

    def _refresh_active_list(self):
        self.active_list.clear()
        for e in sorted(self.allowed_exts):
            self.active_list.addItem(e)

    def _clear_extensions(self):
        self.allowed_exts.clear()
        for btn, _ in self.quick_filter_buttons:
            btn.setChecked(False)
            btn.setStyleSheet("background-color: lightgray;")
        self._refresh_active_list()
        
    def _remove_selected_active_extensions(self):
        to_remove = [item.text() for item in self.active_list.selectedItems()]
        for ext in to_remove:
            if ext in self.allowed_exts:
                self.allowed_exts.remove(ext)

    def _toggle_dark_mode_ui(self):
        if not self.dark_mode_active:
            self.apply_dark_mode()
        else:
            self.apply_light_mode()

    def apply_dark_mode(self):
        app = QApplication.instance()
        dark_palette = QPalette()
        dark_palette.setColor(QPalette.Window, QColor("#1e1e1e"))
        dark_palette.setColor(QPalette.WindowText, QColor("#ffffff"))
        dark_palette.setColor(QPalette.Base, QColor("#333333"))
        dark_palette.setColor(QPalette.AlternateBase, QColor("#1e1e1e"))
        dark_palette.setColor(QPalette.ToolTipBase, QColor("#1e1e1e"))
        dark_palette.setColor(QPalette.ToolTipText, QColor("#ffffff"))
        dark_palette.setColor(QPalette.Text, QColor("#ffffff"))
        dark_palette.setColor(QPalette.Button, QColor("#333333"))
        dark_palette.setColor(QPalette.ButtonText, QColor("#ffffff"))
        dark_palette.setColor(QPalette.BrightText, QColor("#ff0000"))
        dark_palette.setColor(QPalette.Highlight, QColor("#555555"))
        dark_palette.setColor(QPalette.HighlightedText, QColor("#ffffff"))
        app.setPalette(dark_palette)

        app.setStyleSheet("""
            QLabel { color: white; font-size: 11pt; }
            QPushButton {
                background-color: #333333; color: white;
                border: 1px solid #555555; padding: 5px; border-radius: 5px;
            }
            QPushButton:hover { background-color: #444444; }
            QLineEdit, QComboBox, QListWidget, QProgressBar {
                background-color: #333333; color: white;
                border: 1px solid #555555; border-radius: 4px; padding: 2px;
            }
            QProgressBar { text-align: center; }
            QProgressBar::chunk { background-color: #00bfff; width: 20px; }
            QToolTip { background-color: #333333; color: white; border: 1px solid white; }
        """)
        self.dark_mode_active = True
        self.toggle_dark_mode_btn.setText("🌞 Modo Claro")

    def apply_light_mode(self):
        app = QApplication.instance()
        app.setPalette(QApplication.style().standardPalette())
        app.setStyleSheet("")
        self.dark_mode_active = False
        self.toggle_dark_mode_btn.setText("🌙 Modo Oscuro")

    def _select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta")
        if folder:
            self.path_input.setText(folder)

    def _select_save_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta de guardado")
        if folder:
            self.save_path_input.setText(folder)

    def _show_contact_info(self):
        QMessageBox.information(
            self,
            "Contacto",
            "📧 Contacto:\nÓscar Pérez\noscar.p.perez@renault.com"
        )
