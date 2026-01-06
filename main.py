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
    # 1) Crear la aplicación
    app = QApplication(sys.argv)
    # Cargar hoja de estilos global (si existe)
    try:
        here = os.path.dirname(__file__)
        qss_path = os.path.join(here, "styles", "style.qss")
        if os.path.isfile(qss_path):
            with open(qss_path, "r", encoding="utf-8") as f:
                app.setStyleSheet(f.read())
    except Exception:
        pass

    # 2) Instanciar la vista y ponerle el icono
    view = FileScannerView()
    view.setWindowIcon(QIcon(resource_path("detective_.ico")))

    # 3) Conectar el controlador
    ctrl = MainController(view)

    # 4) Mostrar la ventana maximizada (respetando la barra de tareas)
    view.showMaximized()

    # 5) Entrar al bucle de eventos
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
