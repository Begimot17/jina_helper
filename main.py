import sys

from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QMessageBox

from ui.main_window import JinaMDProcessor


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Установка иконки приложения для Windows (также работает на других платформах)
    app.setWindowIcon(
        QIcon("resources/icon.png")
    )  # Убедитесь, что файл icon.png находится в том же каталоге

    try:
        window = JinaMDProcessor()
        window.show()
        sys.exit(app.exec_())
    except Exception as e:
        QMessageBox.critical(
            None, "Fatal Error", f"Application failed to start: {str(e)}"
        )
        sys.exit(1)
