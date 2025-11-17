from pathlib import Path
import os

from utils.settings import get_setting, set_setting

from PyQt5.QtWidgets import (
    QWidget, QApplication, QMessageBox, QDialog,
    QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QGridLayout,
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
                else:
                    btn.setChecked(False)

        else:
            super().keyPressEvent(event)


class FileScannerView(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FileScanner")
        self.setWindowIcon(QIcon("detective_.ico"))
        self._ajustar_a_pantalla()

        # load persisted settings
        self.dark_mode_active = bool(get_setting("theme_dark", False))
        self.allowed_exts = set(get_setting("allowed_exts", []))
        self.ext_buttons = {}
        self.quick_filter_buttons = []

        # Llamada correcta al método que monta la UI
        self.setup_ui()
        # Apply persisted theme (no toggle button shown)
        if self.dark_mode_active:
            self.apply_dark_mode()
        else:
            self.apply_light_mode()
        
    def _ajustar_a_pantalla(self):
        pantalla = QApplication.primaryScreen().availableGeometry()
        self.setGeometry(pantalla)
        # Si se quiere establecer tamaño mínimo y dejar dimensionable
        # self.setMinimumSize(pantalla.width(), pantalla.height())

    def setup_ui(self):
        main_layout = QHBoxLayout()
        self.left_layout = QVBoxLayout()
        self.right_layout = QVBoxLayout()

        # Create panels (QWidget) for left and right areas so QSS .sectionPanel can style them
        self.left_panel = QWidget()
        self.left_panel.setProperty("class", "sectionPanel")
        self.left_panel.setProperty("panel", "left")
        self.left_panel.setLayout(self.left_layout)

        self.right_panel = QWidget()
        self.right_panel.setProperty("class", "sectionPanel")
        self.right_panel.setProperty("panel", "right")
        self.right_panel.setLayout(self.right_layout)

        main_layout.addWidget(self.left_panel, 3)
        main_layout.addWidget(self.right_panel, 2)
        self.setLayout(main_layout)

        self.build_left_panel()
        self.build_right_panel()

    def build_left_panel(self):
        # (Removed dark-mode toggle button per user preference)

        # Ruta a escanear
        self.left_layout.addWidget(QLabel("🔍 Ruta de la carpeta a escanear:"))
        self.path_input = QLineEdit()
        # Do not focus the path input automatically; only focus on click
        self.path_input.setFocusPolicy(Qt.ClickFocus)
        self.left_layout.addWidget(self.path_input)
        self.browse_button = QPushButton("Seleccionar carpeta para analizar")
        self.browse_button.clicked.connect(self._select_folder)
        self.browse_button.setProperty("role", "secondary")
        self.left_layout.addWidget(self.browse_button)

        # Ruta de guardado JSON
        self.left_layout.addWidget(QLabel("💾 Ruta para guardar el JSON generado:"))
        self.save_path_input = QLineEdit()
        self.left_layout.addWidget(self.save_path_input)
        self.save_browse_button = QPushButton("Seleccionar carpeta de guardado")
        self.save_browse_button.clicked.connect(self._select_save_folder)
        self.save_browse_button.setProperty("role", "secondary")
        self.left_layout.addWidget(self.save_browse_button)

        # Extensiones a ignorar (configurable)
        self.left_layout.addWidget(QLabel("🚫 Extensiones a ignorar:"))
        # small button to open ignore editor dialog
        try:
            icon_folder = Path(__file__).parent.parent / 'resources' / 'icons'
            edit_icon = QIcon(str(icon_folder / 'add.svg'))
        except Exception:
            edit_icon = QIcon()
        self.edit_ignores_btn = QPushButton()
        self.edit_ignores_btn.setIcon(edit_icon)
        self.edit_ignores_btn.setToolTip('Editar lista de extensiones a ignorar')
        self.edit_ignores_btn.clicked.connect(self._open_ignore_editor)
        self.left_layout.addWidget(self.edit_ignores_btn)
        # Defaults: common binary/temporary/cache files to ignore
        default_ignores = [
            ".exe", ".dll", ".log", ".tmp", ".bak", ".bat", ".cache", ".o", ".pyc",
            ".bin", ".iso", ".msi"
        ]
        saved_ignores = get_setting("ignore_extensions", default_ignores)
        self.ignore_checkboxes = {}
        # Use a grid so checkboxes wrap into multiple rows instead of a single long row
        # Expose container/grid so we can rebuild from the IgnoreEditor
        self.ignore_container = QWidget()
        self.ignore_grid = QGridLayout()
        self.ignore_grid.setSpacing(8)
        cols = 4
        row = 0
        col = 0
        checked_map = get_setting("ignore_enabled", {})
        for ext in saved_ignores:
            cb = QCheckBox(ext)
            cb.setChecked(checked_map.get(ext, True))
            cb.toggled.connect(lambda state, e=ext: self._on_ignore_toggled(e, state))
            self.ignore_checkboxes[ext] = cb
            self.ignore_grid.addWidget(cb, row, col)
            col += 1
            if col >= cols:
                col = 0
                row += 1
        self.ignore_container.setLayout(self.ignore_grid)
        self.left_layout.addWidget(self.ignore_container)

        # Filtro rápido
        self.left_layout.addWidget(QLabel("📂 Filtro rápido:"))
        quick_exts = [".docx", ".pdf", ".txt", ".csv", ".xlsx", ".xml", ".json"]
        quick_layout = QHBoxLayout()
        for ext in quick_exts:
            btn = QPushButton(ext)
            btn.setCheckable(True)
            btn.setProperty("role", "secondary")
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
        self.add_custom_btn.setProperty("role", "secondary")
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
        clear_btn.setProperty("role", "secondary")
        self.left_layout.addWidget(clear_btn)

        # Botones de escaneo: iniciar / detener
        h_scan = QHBoxLayout()
        self.scan_button = QPushButton("▶️ Ejecutar escaneo")
        self.scan_button.setProperty("role", "accent")
        # Give default focus to scan button so the path input does not show a cursor on startup
        self.scan_button.setFocus()
        self.stop_button = QPushButton("⏹️ Detener escaneo")
        self.stop_button.setProperty("role", "danger")
        self.stop_button.setEnabled(False)   # deshabilitado hasta que empiece
        h_scan.addWidget(self.scan_button)
        h_scan.addWidget(self.stop_button)
        self.left_layout.addLayout(h_scan)

        self.progress_bar = QProgressBar()
        self.left_layout.addWidget(self.progress_bar)

        contact_btn = QPushButton("📩 Contacto")
        contact_btn.clicked.connect(self._show_contact_info)
        contact_btn.setProperty("role", "secondary")
        self.left_layout.addWidget(contact_btn)

    def build_right_panel(self):
        # Ajustes de layout: reducir espacios y márgenes para acercar títulos a cuadros
        self.right_layout.setSpacing(4)
        self.right_layout.setContentsMargins(6, 6, 6, 6)

        # Favoritos de ubicaciones
        loc_label = QLabel("📁 Favoritos de ubicaciones:")
        loc_label.setContentsMargins(0, 0, 0, 0)
        self.right_layout.addWidget(loc_label)
        self.location_list = QListWidget()
        # Aumentar el tamaño del cuadro para reducir visualmente la separación
        self.location_list.setMaximumHeight(240)
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
        fav_label = QLabel("⭐ Favoritos de extensiones:")
        fav_label.setContentsMargins(0, 0, 0, 0)
        self.right_layout.addWidget(fav_label)

        fav_top_layout = QHBoxLayout()
        self.search_fav_input = QLineEdit()
        self.search_fav_input.setPlaceholderText("🔍 Buscar favorito...")
        fav_top_layout.addWidget(self.search_fav_input)

        self.sort_btn = QPushButton("🔃 A-Z/Z-A")
        fav_top_layout.addWidget(self.sort_btn)
        self.right_layout.addLayout(fav_top_layout)

        self.favorites_list = QListWidget()
        self.favorites_list.setMaximumHeight(240)
        self.right_layout.addWidget(self.favorites_list)

        fav_btns = QHBoxLayout()
        self.save_fav_btn = QPushButton("➕ Guardar colección")
        self.load_fav_btn = QPushButton("📂 Cargar colección")
        self.delete_fav_btn = QPushButton("❌ Eliminar colección")
        self.edit_fav_btn = QPushButton("✏️ Editar colección")
        for w in (self.save_fav_btn, self.load_fav_btn, self.delete_fav_btn, self.edit_fav_btn):
            fav_btns.addWidget(w)
        self.right_layout.addLayout(fav_btns)

        # Sección IOCs (debajo de Favoritos de extensiones)
        ioc_label = QLabel("🛡️ IOCs cargadas:")
        ioc_label.setContentsMargins(0, 0, 0, 0)
        self.right_layout.addWidget(ioc_label)
        # (Leyenda removida a petición del usuario)
        ioc_h = QHBoxLayout()
        self.ioc_count_label = QLabel("0")
        ioc_h.addWidget(self.ioc_count_label)
        # Botón para cargar IOCs (usar texto para claridad)
        self.load_ioc_btn = QPushButton('Cargar IOCs')
        self.load_ioc_btn.setToolTip('Cargar indicadores (hashes, nombres, rutas) desde archivos')
        ioc_h.addWidget(self.load_ioc_btn)
        # YARA loader button
        self.load_yara_btn = QPushButton('Cargar YARA')
        ioc_h.addWidget(self.load_yara_btn)
        self.load_yara_btn.clicked.connect(self._load_yara_rules)
        self.yara_count_label = QLabel('YARA: 0')
        ioc_h.addWidget(self.yara_count_label)
        self.right_layout.addLayout(ioc_h)

        # Lista visual de IOCs (igual estructura que ubicaciones y favoritos)
        self.ioc_list = QListWidget()
        self.ioc_list.setMaximumHeight(240)
        self.right_layout.addWidget(self.ioc_list)

    # — Métodos de UI internos —————————————————————————————————————————

    def _toggle_extension(self, ext, button):
        if ext in self.allowed_exts:
            self.allowed_exts.remove(ext)
            button.setChecked(False)
        else:
            self.allowed_exts.add(ext)
            button.setChecked(True)
        self._refresh_active_list()

    def _add_custom_extension(self):
        ext = self.custom_ext_input.text().strip().lower()
        if not ext.startswith("."):
            ext = "." + ext
        if ext and ext not in self.allowed_exts:
            self.allowed_exts.add(ext)
            # persist
            set_setting("allowed_exts", sorted(list(self.allowed_exts)))
        self.custom_ext_input.clear()
        self._refresh_active_list()

    def _refresh_active_list(self):
        self.active_list.clear()
        for e in sorted(self.allowed_exts):
            self.active_list.addItem(e)
        # persist
        set_setting("allowed_exts", sorted(list(self.allowed_exts)))

    def _clear_extensions(self):
        self.allowed_exts.clear()
        for btn, _ in self.quick_filter_buttons:
            btn.setChecked(False)
        self._refresh_active_list()
        set_setting("allowed_exts", [])
        
    def _remove_selected_active_extensions(self):
        to_remove = [item.text() for item in self.active_list.selectedItems()]
        for ext in to_remove:
            if ext in self.allowed_exts:
                self.allowed_exts.remove(ext)

    def _toggle_dark_mode_ui(self):
        # toggle and persist
        if not self.dark_mode_active:
            self.apply_dark_mode()
            set_setting("theme_dark", True)
        else:
            self.apply_light_mode()
            set_setting("theme_dark", False)

    def apply_dark_mode(self):
        # Load dark QSS if available; fall back to palette adjustments
        app = QApplication.instance()
        dark_qss_path = Path(__file__).parent.parent / "styles" / "style-dark.qss"
        if dark_qss_path.exists():
            try:
                with open(dark_qss_path, 'r', encoding='utf-8') as f:
                    q = f.read()
                app.setStyleSheet(q)
            except Exception:
                pass
        else:
            # minimal palette fallback
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
            app.setPalette(dark_palette)

        self.dark_mode_active = True
        # toggle button removed: do not try to set text

    def apply_light_mode(self):
        # Load light QSS to restore the modern look
        app = QApplication.instance()
        light_qss_path = Path(__file__).parent.parent / "styles" / "style.qss"
        if light_qss_path.exists():
            try:
                with open(light_qss_path, 'r', encoding='utf-8') as f:
                    q = f.read()
                app.setStyleSheet(q)
            except Exception:
                app.setPalette(QApplication.style().standardPalette())
        else:
            app.setPalette(QApplication.style().standardPalette())

        self.dark_mode_active = False
        # toggle button removed: do not try to set text

    def _on_ignore_toggled(self, ext, state):
        # persist the enabled/disabled state of ignore checkboxes
        m = get_setting("ignore_enabled", {})
        m[ext] = bool(state)
        set_setting("ignore_enabled", m)

    def _clear_layout(self, layout):
        """Remove all widgets from a layout."""
        if layout is None:
            return
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)

    def _rebuild_ignore_checkboxes(self, extensions, enabled_map=None):
        """Rebuild the grid of ignore checkboxes from the given list."""
        enabled_map = enabled_map or {}
        # clear old widgets
        self._clear_layout(self.ignore_grid)
        self.ignore_checkboxes = {}
        cols = 4
        row = 0
        col = 0
        for ext in extensions:
            cb = QCheckBox(ext)
            cb.setChecked(enabled_map.get(ext, True))
            cb.toggled.connect(lambda state, e=ext: self._on_ignore_toggled(e, state))
            self.ignore_checkboxes[ext] = cb
            self.ignore_grid.addWidget(cb, row, col)
            col += 1
            if col >= cols:
                col = 0
                row += 1
        # persist the full list of ignore extensions
        set_setting('ignore_extensions', sorted(list(extensions)))

    def _open_ignore_editor(self):
        try:
            from views.dialogs import IgnoreEditorDialog
        except Exception:
            QMessageBox.warning(self, "Error", "No se puede abrir el editor de ignores.")
            return

        current_exts = get_setting('ignore_extensions', [])
        current_enabled = get_setting('ignore_enabled', {})
        dlg = IgnoreEditorDialog(self, extensions=current_exts, enabled_map=current_enabled)
        if dlg.exec_() == QDialog.Accepted:
            exts, enabled = dlg.get_data()
            # persist settings
            set_setting('ignore_extensions', sorted(list(exts)))
            set_setting('ignore_enabled', enabled)
            # rebuild UI
            self._rebuild_ignore_checkboxes(exts, enabled)

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
            "📧 Contacto:\nÓscar Pérez\npefer.oscar@gmail.com"
        )

    def _load_yara_rules(self):
        """Open a file dialog to load YARA rule files and register them via yara_manager."""
        try:
            from utils.yara_manager import load_yara_paths, get_loaded_yara_count
        except Exception:
            QMessageBox.warning(self, "YARA no disponible", "El módulo de YARA no está disponible en este entorno.")
            return

        files, _ = QFileDialog.getOpenFileNames(self, "Seleccionar reglas YARA", filter="YARA files (*.yar *.yara);;All files (*)")
        if not files:
            return
        res = load_yara_paths(files)
        ok = sum(1 for v in res.values() if v.get('ok'))
        bad = [p for p, v in res.items() if not v.get('ok')]
        # update UI count
        try:
            cnt = get_loaded_yara_count()
            self.yara_count_label.setText(f"YARA: {cnt}")
        except Exception:
            pass

        msg = f"Se cargaron {ok} reglas YARA."
        if bad:
            msg += "\nErrores: " + ", ".join(bad[:5])
        QMessageBox.information(self, "YARA cargadas", msg)
