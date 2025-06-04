import sys
from PyQt6.QtWidgets import QApplication
from ytdownloader.ui.main_window import MainWindow # We'll create this next

def run_app():
    app = QApplication(sys.argv)
    main_win = MainWindow()
    main_win.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    run_app()
