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


class FileScannerView(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FileScanner")
        self.setWindowIcon(QIcon("detective_.ico"))
        self._ajustar_a_pantalla()

        # load persisted settings
        self.dark_mode_active = bool(get_setting("theme_dark", False))
        # Start with empty sets by default
        self.allowed_exts = set()
        self.ignored_exts = set()
        self.ext_buttons = {}
        self.quick_filter_buttons = []
        self.ignore_buttons = []

        # Llamada correcta al método que monta la UI
        self.setup_ui()
        # Apply persisted theme (no toggle button shown)
        if self.dark_mode_active:
            self.apply_dark_mode()
        else:
            self.apply_light_mode()
        
        # Set hand cursor for all buttons
        self._set_hand_cursor_for_buttons()
        
        # Mostrar diálogo de bienvenida si es la primera vez o si el usuario no lo desactivó
        self._show_welcome_dialog()
    
    def _set_hand_cursor_for_buttons(self):
        """Set pointing hand cursor for all buttons in the application."""
        from PyQt5.QtCore import Qt
        # Find all QPushButton widgets recursively
        for button in self.findChildren(QPushButton):
            button.setCursor(Qt.PointingHandCursor)
        
    def _show_welcome_dialog(self):
        """Muestra el diálogo de bienvenida si no ha sido desactivado por el usuario."""
        from PyQt5.QtCore import QTimer
        
        # Verificar si el usuario desactivó el diálogo
        if get_setting("hide_welcome_dialog", False):
            return
        
        # Usar QTimer para mostrar el diálogo después de que la ventana esté completamente renderizada
        QTimer.singleShot(200, self._display_welcome)
    
    def _display_welcome(self):
        """Muestra el diálogo de bienvenida."""
        try:
            from views.dialogs import WelcomeDialog
            dialog = WelcomeDialog(self)
            dialog.exec_()
        except Exception as e:
            print(f"Error mostrando diálogo de bienvenida: {e}")
        
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

        # Scan path
        self.left_layout.addWidget(QLabel("🔍 Folder path to scan:"))
        self.path_input = QLineEdit()
        # Do not focus the path input automatically; only focus on click
        self.path_input.setFocusPolicy(Qt.ClickFocus)
        self.left_layout.addWidget(self.path_input)
        self.browse_button = QPushButton("Select folder to analyze")
        self.browse_button.clicked.connect(self._select_folder)
        self.browse_button.setProperty("role", "secondary")
        self.left_layout.addWidget(self.browse_button)

        # JSON save path
        self.left_layout.addWidget(QLabel("💾 Path to save generated JSON:"))
        self.save_path_input = QLineEdit()
        self.left_layout.addWidget(self.save_path_input)
        self.save_browse_button = QPushButton("Select save folder")
        self.save_browse_button.clicked.connect(self._select_save_folder)
        self.save_browse_button.setProperty("role", "secondary")
        self.left_layout.addWidget(self.save_browse_button)

        # Spacing before ignore section
        self.left_layout.addSpacing(20)

        # Extensions to IGNORE (red theme to differentiate)
        self.left_layout.addWidget(QLabel("🚫 Extensions to IGNORE (skip these files):"))
        ignore_exts = [".exe", ".dll", ".log", ".tmp", ".bak", ".cache", ".pyc", ".bin"]
        ignore_layout = QHBoxLayout()
        # Initialize with empty set by default
        self.ignored_exts = set()
        self.ignore_buttons = {}
        for ext in ignore_exts:
            btn = QPushButton(ext)
            btn.setCheckable(True)
            btn.setProperty("role", "ignore")
            btn.setChecked(False)  # Start unchecked
            btn.clicked.connect(lambda _, e=ext, b=btn: self._toggle_ignore_extension(e, b))
            ignore_layout.addWidget(btn)
            self.ignore_buttons[ext] = btn
        self.left_layout.addLayout(ignore_layout)

        # Add custom ignore extension
        ignore_custom_layout = QHBoxLayout()
        self.custom_ignore_input = QLineEdit()
        self.custom_ignore_input.setPlaceholderText("Add extension to ignore...")
        self.custom_ignore_input.returnPressed.connect(self._add_custom_ignore_extension)
        self.add_ignore_btn = QPushButton("➕ Add to ignore")
        self.add_ignore_btn.clicked.connect(self._add_custom_ignore_extension)
        self.add_ignore_btn.setProperty("role", "ignore")
        self.delete_ignore_btn = QPushButton("🗑️ Clear all")
        self.delete_ignore_btn.clicked.connect(self._delete_custom_ignore_extension)
        self.delete_ignore_btn.setProperty("role", "danger")
        ignore_custom_layout.addWidget(self.custom_ignore_input)
        ignore_custom_layout.addWidget(self.add_ignore_btn)
        ignore_custom_layout.addWidget(self.delete_ignore_btn)
        self.left_layout.addLayout(ignore_custom_layout)

        # List of ignored extensions
        self.left_layout.addWidget(QLabel("🔴 Active ignored extensions:"))
        self.ignored_list = QListWidget()
        self.ignored_list.setMaximumHeight(100)
        self.ignored_list.setFlow(QListWidget.LeftToRight)
        self.ignored_list.setWrapping(True)
        self.ignored_list.setResizeMode(QListWidget.Adjust)
        self.ignored_list.setSpacing(3)
        self.left_layout.addWidget(self.ignored_list)
        self._refresh_ignored_list()
        
        # Shortcuts to delete selection with Delete or Backspace
        delete_ignore_shortcut = QShortcut(QKeySequence.Delete, self.ignored_list)
        delete_ignore_shortcut.activated.connect(self._remove_selected_ignored_extensions)
        backspace_ignore_shortcut = QShortcut(QKeySequence.Backspace, self.ignored_list)
        backspace_ignore_shortcut.activated.connect(self._remove_selected_ignored_extensions)

        # Spacing before analyze section
        self.left_layout.addSpacing(20)

        # Extensions to ANALYZE (green theme)
        self.left_layout.addWidget(QLabel("📂 Extensions to ANALYZE (quick filter):"))
        quick_exts = [".docx", ".pdf", ".txt", ".csv", ".xlsx", ".xml", ".json"]
        quick_layout = QHBoxLayout()
        # Pre-select all analyze extensions by default
        self.allowed_exts = set(quick_exts)
        for ext in quick_exts:
            btn = QPushButton(ext)
            btn.setCheckable(True)
            btn.setProperty("role", "secondary")
            btn.setChecked(True)  # Start checked
            btn.clicked.connect(lambda _, e=ext, b=btn: self._toggle_extension(e, b))
            quick_layout.addWidget(btn)
            self.ext_buttons[ext] = btn
            self.quick_filter_buttons.append((btn, ext))
        self.left_layout.addLayout(quick_layout)

        # Add custom extension
        custom_layout = QHBoxLayout()
        self.custom_ext_input = QLineEdit()
        self.custom_ext_input.setPlaceholderText("Add extension to analyze...")
        self.custom_ext_input.returnPressed.connect(self._add_custom_extension)
        self.add_custom_btn = QPushButton("➕ Add to analyze")
        self.add_custom_btn.clicked.connect(self._add_custom_extension)
        self.add_custom_btn.setProperty("role", "secondary")
        self.delete_custom_btn = QPushButton("🗑️ Clear all")
        self.delete_custom_btn.clicked.connect(self._delete_custom_extension)
        self.delete_custom_btn.setProperty("role", "danger")
        custom_layout.addWidget(self.custom_ext_input)
        custom_layout.addWidget(self.add_custom_btn)
        custom_layout.addWidget(self.delete_custom_btn)
        self.left_layout.addLayout(custom_layout)

        # Active extensions list
        self.left_layout.addWidget(QLabel("🟢 Active analyzed extensions:"))
        self.active_list = QListWidget()
        self.active_list.setMaximumHeight(100)
        self.active_list.setFlow(QListWidget.LeftToRight)
        self.active_list.setWrapping(True)
        self.active_list.setResizeMode(QListWidget.Adjust)
        self.active_list.setSpacing(3)
        self.left_layout.addWidget(self.active_list)
        self._refresh_active_list()  # Update list to show pre-selected extensions
        
        # Shortcuts to delete selection with Delete or Backspace
        delete_shortcut = QShortcut(QKeySequence.Delete, self.active_list)
        delete_shortcut.activated.connect(self._remove_selected_active_extensions)
        backspace_shortcut = QShortcut(QKeySequence.Backspace, self.active_list)
        backspace_shortcut.activated.connect(self._remove_selected_active_extensions)

        # Add spacing before scan buttons
        self.left_layout.addSpacing(15)

        # Scan buttons: start / stop
        h_scan = QHBoxLayout()
        self.scan_button = QPushButton("▶️ Run scan")
        self.scan_button.setProperty("role", "accent")
        # Give default focus to scan button so the path input does not show a cursor on startup
        self.scan_button.setFocus()
        self.stop_button = QPushButton("⏹️ Stop scan")
        self.stop_button.setProperty("role", "danger")
        self.stop_button.setEnabled(False)   # disabled until scan starts
        h_scan.addWidget(self.scan_button)
        h_scan.addWidget(self.stop_button)
        self.left_layout.addLayout(h_scan)

        self.progress_bar = QProgressBar()
        self.left_layout.addWidget(self.progress_bar)

        # Help and contact buttons in the same row
        help_layout = QHBoxLayout()
        
        help_btn = QPushButton("❓ Help")
        help_btn.clicked.connect(self._show_help)
        help_btn.setProperty("role", "secondary")
        help_btn.setToolTip("View FileScanner tutorial")
        help_layout.addWidget(help_btn)
        
        contact_btn = QPushButton("📩 Contact")
        contact_btn.clicked.connect(self._show_contact_info)
        contact_btn.setProperty("role", "secondary")
        contact_btn.setToolTip("Developer contact information")
        help_layout.addWidget(contact_btn)
        
        self.left_layout.addLayout(help_layout)

    def build_right_panel(self):
        # Layout adjustments: reduce spacing and margins to bring titles closer to boxes
        self.right_layout.setSpacing(4)
        self.right_layout.setContentsMargins(6, 6, 6, 6)

        # Location favorites
        loc_label = QLabel("📁 Location favorites:")
        loc_label.setContentsMargins(0, 0, 0, 0)
        self.right_layout.addWidget(loc_label)
        self.location_list = QListWidget()
        # Reduced height for better space distribution
        self.location_list.setMaximumHeight(180)
        self.right_layout.addWidget(self.location_list)

        loc_btns = QHBoxLayout()
        self.add_loc_btn      = QPushButton("➕ Add location")
        self.del_loc_btn      = QPushButton("❌ Remove location")
        self.save_loc_coll_btn= QPushButton("📂 Save collection")
        self.load_loc_coll_btn= QPushButton("📥 Load collection")
        self.edit_loc_coll_btn= QPushButton("✏️ Edit collection")

        for w in (
            self.add_loc_btn, self.del_loc_btn,
            self.save_loc_coll_btn, self.load_loc_coll_btn, self.edit_loc_coll_btn
        ):
            loc_btns.addWidget(w)
        self.right_layout.addLayout(loc_btns)
        
        # Extension favorites
        fav_label = QLabel("⭐ Extension favorites:")
        fav_label.setContentsMargins(0, 0, 0, 0)
        self.right_layout.addWidget(fav_label)

        fav_top_layout = QHBoxLayout()
        self.search_fav_input = QLineEdit()
        self.search_fav_input.setPlaceholderText("🔍 Search favorite...")
        fav_top_layout.addWidget(self.search_fav_input)

        self.sort_btn = QPushButton("🔃 A-Z/Z-A")
        fav_top_layout.addWidget(self.sort_btn)
        self.right_layout.addLayout(fav_top_layout)

        self.favorites_list = QListWidget()
        # Reduced height for better space distribution
        self.favorites_list.setMaximumHeight(180)
        self.right_layout.addWidget(self.favorites_list)

        fav_btns = QHBoxLayout()
        self.save_fav_btn = QPushButton("➕ Save collection")
        self.load_fav_btn = QPushButton("📂 Load collection")
        self.delete_fav_btn = QPushButton("❌ Delete collection")
        self.edit_fav_btn = QPushButton("✏️ Edit collection")
        for w in (self.save_fav_btn, self.load_fav_btn, self.delete_fav_btn, self.edit_fav_btn):
            fav_btns.addWidget(w)
        self.right_layout.addLayout(fav_btns)

        # IOCs section (reorganized in vertical layout)
        self.right_layout.addSpacing(15)
        
        ioc_label = QLabel("🛡️ Loaded IOCs:")
        ioc_label.setContentsMargins(0, 0, 0, 0)
        self.right_layout.addWidget(ioc_label)
        
        ioc_h = QHBoxLayout()
        self.ioc_count_label = QLabel("0")
        ioc_h.addWidget(self.ioc_count_label)
        self.load_ioc_btn = QPushButton('Load IOCs')
        self.load_ioc_btn.setToolTip('Load indicators (hashes, names, paths) from files')
        ioc_h.addWidget(self.load_ioc_btn)
        self.right_layout.addLayout(ioc_h)
        
        # YARA section (now in separate row)
        self.right_layout.addSpacing(10)
        
        yara_label = QLabel("📋 YARA Rules:")
        yara_label.setContentsMargins(0, 0, 0, 0)
        self.right_layout.addWidget(yara_label)
        
        yara_h = QHBoxLayout()
        self.yara_count_label = QLabel('0')
        yara_h.addWidget(self.yara_count_label)
        self.load_yara_btn = QPushButton('Load YARA')
        self.load_yara_btn.clicked.connect(self._load_yara_rules)
        yara_h.addWidget(self.load_yara_btn)
        self.right_layout.addLayout(yara_h)

        # Visual IOCs list (same structure as locations and favorites)
        self.ioc_list = QListWidget()
        self.ioc_list.setMaximumHeight(240)
        self.right_layout.addWidget(self.ioc_list)

    # — Internal UI methods —————————————————————————————————————————

    def _toggle_ignore_extension(self, ext, button):
        """Toggle extension in ignore list."""
        if ext in self.ignored_exts:
            self.ignored_exts.remove(ext)
            button.setChecked(False)
        else:
            self.ignored_exts.add(ext)
            button.setChecked(True)
        self._refresh_ignored_list()
        set_setting("ignored_exts", sorted(list(self.ignored_exts)))

    def _add_custom_ignore_extension(self):
        """Add custom extension to ignore list."""
        ext = self.custom_ignore_input.text().strip().lower()
        if not ext.startswith("."):
            ext = "." + ext
        if ext and ext not in self.ignored_exts:
            self.ignored_exts.add(ext)
            # Update button if it exists
            if ext in self.ignore_buttons:
                self.ignore_buttons[ext].setChecked(True)
            set_setting("ignored_exts", sorted(list(self.ignored_exts)))
        self.custom_ignore_input.clear()
        self._refresh_ignored_list()

    def _refresh_ignored_list(self):
        """Refresh the list of ignored extensions."""
        self.ignored_list.clear()
        for e in sorted(self.ignored_exts):
            self.ignored_list.addItem(e)

    def _remove_selected_ignored_extensions(self):
        """Remove selected extensions from ignore list."""
        to_remove = [item.text() for item in self.ignored_list.selectedItems()]
        for ext in to_remove:
            if ext in self.ignored_exts:
                self.ignored_exts.remove(ext)
            # Update button if it exists
            if ext in self.ignore_buttons:
                self.ignore_buttons[ext].setChecked(False)
        self._refresh_ignored_list()
        set_setting("ignored_exts", sorted(list(self.ignored_exts)))

    def _toggle_extension(self, ext, button):
        if ext in self.allowed_exts:
            self.allowed_exts.remove(ext)
            button.setChecked(False)
        else:
            self.allowed_exts.add(ext)
            button.setChecked(True)
        self._refresh_active_list()
        set_setting("allowed_exts", sorted(list(self.allowed_exts)))

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
        
    def _remove_selected_active_extensions(self):
        """Remove selected extensions from analyze list."""
        to_remove = [item.text() for item in self.active_list.selectedItems()]
        for ext in to_remove:
            if ext in self.allowed_exts:
                self.allowed_exts.remove(ext)
            # Update button if it exists
            if ext in self.ext_buttons:
                self.ext_buttons[ext].setChecked(False)
        self._refresh_active_list()
        set_setting("allowed_exts", sorted(list(self.allowed_exts)))

    def _delete_custom_extension(self):
        """Delete ALL active analyzed extensions."""
        self.allowed_exts.clear()
        # Uncheck all analyze buttons
        for btn, _ in self.quick_filter_buttons:
            btn.setChecked(False)
        self._refresh_active_list()
        set_setting("allowed_exts", [])
        self.custom_ext_input.clear()

    def _delete_custom_ignore_extension(self):
        """Delete ALL active ignored extensions."""
        self.ignored_exts.clear()
        # Uncheck all ignore buttons
        for ext, btn in self.ignore_buttons.items():
            btn.setChecked(False)
        self._refresh_ignored_list()
        set_setting("ignored_exts", [])
        self.custom_ignore_input.clear()

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

    def _select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select folder")
        if folder:
            self.path_input.setText(folder)

    def _select_save_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select save folder")
        if folder:
            self.save_path_input.setText(folder)

    def _show_contact_info(self):
        QMessageBox.information(
            self,
            "Contact",
            "📧 Contact:\nÓscar Pérez\npefer.oscar@gmail.com"
        )
    
    def _show_help(self):
        """Show help/tutorial dialog."""
        try:
            from views.dialogs import WelcomeDialog
            dialog = WelcomeDialog(self)
            dialog.setWindowTitle("❓ Help - FileScanner")
            dialog.exec_()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not open tutorial: {e}")

    def _load_yara_rules(self):
        """Open a file dialog to load YARA rule files and register them via yara_manager."""
        try:
            from utils.yara_manager import load_yara_paths, get_loaded_yara_count
        except Exception:
            QMessageBox.warning(self, "YARA not available", "YARA module is not available in this environment.")
            return

        files, _ = QFileDialog.getOpenFileNames(self, "Select YARA rules", filter="YARA files (*.yar *.yara);;All files (*)")
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

        msg = f"{ok} YARA rules loaded."
        if bad:
            msg += "\nErrors: " + ", ".join(bad[:5])
        QMessageBox.information(self, "YARA loaded", msg)
