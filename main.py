import sys
import os

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui     import QIcon

from views.main_view        import FileScannerView
from controllers.main_controller import MainController


def resource_path(relpath):
    """
    Devuelve la ruta absoluta en modo PyInstaller (sys._MEIPASS)
    o en modo desarrollo (dirname(__file__)).
    """
    base = getattr(sys, "_MEIPASS", os.path.dirname(__file__))
    return os.path.join(base, relpath)


def main():

    app = QApplication(sys.argv)
    
    view = FileScannerView()
    view.setWindowIcon(QIcon(resource_path("detective_.ico")))

    ctrl = MainController(view)

    view.showMaximized()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
