import sys
from PyQt5.QtWidgets import QApplication
from views.main_view import FileScannerView
from controllers.main_controller import MainController

def main():
    app = QApplication(sys.argv)
    view = FileScannerView()
    ctrl = MainController(view)
    view.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
