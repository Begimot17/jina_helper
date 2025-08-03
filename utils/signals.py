from PyQt5.QtCore import QObject, pyqtSignal


class SignalEmitter(QObject):
    update_text_signal = pyqtSignal(str, str)  # content, widget_id
    update_status_signal = pyqtSignal(str, bool)  # message, is_error
    enable_button_signal = pyqtSignal(bool)
