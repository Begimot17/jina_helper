import os
import sys
import threading

import requests
from dotenv import load_dotenv
from PyQt5.QtCore import QObject, Qt, pyqtSignal
from PyQt5.QtGui import QFont, QIcon, QTextCursor
from PyQt5.QtWidgets import (
    QApplication,
    QCheckBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStatusBar,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

load_dotenv()


class SignalEmitter(QObject):
    update_text_signal = pyqtSignal(str, QTextEdit)
    update_status_signal = pyqtSignal(str, bool)
    enable_button_signal = pyqtSignal(bool)


class JinaMDProcessor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Jina.ai MD Processor")
        self.resize(1000, 900)

        # Установка иконки приложения
        self.setWindowIcon(QIcon(self.get_icon_path()))

        # Load configuration
        self.api_key = os.getenv("JINA_API_KEY")
        self.proxy_url = os.getenv("PROXY_URL")

        if not self.api_key:
            QMessageBox.critical(self, "Error", "JINA_API_KEY not found in .env file")
            sys.exit(1)

        # Default system prompt
        self.default_system_prompt = """You are a professional data extractor. 
Analyze the provided markdown content and extract all important fields in a structured way. 
Include all relevant details like product name, specifications, features, price, etc."""

        self.signal_emitter = SignalEmitter()
        self.signal_emitter.update_text_signal.connect(self.update_text)
        self.signal_emitter.update_status_signal.connect(self.update_status)
        self.signal_emitter.enable_button_signal.connect(self.enable_button)

        self.init_ui()

    def get_icon_path(self):
        """Возвращает путь к иконке в зависимости от платформы"""
        # Попробуем найти иконку в нескольких возможных местах
        possible_paths = [
            os.path.join(os.path.dirname(__file__), "icon.png"),
            os.path.join(os.path.dirname(__file__), "resources", "icon.png"),
            os.path.join(os.path.dirname(__file__), "..", "resources", "icon.png"),
            "/usr/share/pixmaps/jina_md_processor.png",  # Для Linux
            os.path.join(
                os.getenv("ProgramFiles"), "JinaMDProcessor", "icon.png"
            ),  # Для Windows
        ]

        for path in possible_paths:
            if os.path.exists(path):
                return path

        # Если иконка не найдена, можно сгенерировать простую иконку программно
        # или вернуть путь к стандартной иконке Qt
        return ":/icons/default_icon"  # Это сработает только если у вас есть ресурсы Qt

    def init_ui(self):
        # Main widget and layout
        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)
        self.main_layout = QVBoxLayout(self.main_widget)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(10)

        # Header
        self.header = QLabel("Jina.ai Markdown Processor")
        self.header.setFont(QFont("Segoe UI", 14, QFont.Bold))
        self.header.setStyleSheet("color: #343a40;")
        self.main_layout.addWidget(self.header, alignment=Qt.AlignCenter)

        # URL input
        self.url_layout = QHBoxLayout()
        self.url_label = QLabel("Listing URL:")
        self.url_entry = QLineEdit()
        self.url_entry.setMinimumHeight(30)
        self.url_layout.addWidget(self.url_label)
        self.url_layout.addWidget(self.url_entry)
        self.main_layout.addLayout(self.url_layout)

        # Proxy settings
        self.proxy_layout = QHBoxLayout()
        self.use_proxy_check = QCheckBox("Use Proxy")
        self.use_proxy_check.setChecked(bool(self.proxy_url))
        self.use_proxy_check.stateChanged.connect(self.toggle_proxy_entry)
        self.proxy_label = QLabel("Proxy:")
        self.proxy_entry = QLineEdit()
        self.proxy_entry.setMinimumHeight(30)
        if self.proxy_url:
            self.proxy_entry.setText(self.proxy_url)

        self.proxy_layout.addWidget(self.use_proxy_check)
        self.proxy_layout.addWidget(self.proxy_label)
        self.proxy_layout.addWidget(self.proxy_entry)
        self.main_layout.addLayout(self.proxy_layout)

        # System Prompt Group
        self.prompt_group = QGroupBox("System Prompt")
        self.prompt_layout = QVBoxLayout()

        self.system_prompt_edit = QTextEdit()
        self.system_prompt_edit.setPlainText(self.default_system_prompt)
        self.system_prompt_edit.setFont(QFont("Consolas", 10))
        self.system_prompt_edit.setMinimumHeight(100)

        self.reset_prompt_btn = QPushButton("Reset to Default")
        self.reset_prompt_btn.setIcon(QIcon.fromTheme("view-refresh"))
        self.reset_prompt_btn.clicked.connect(self.reset_system_prompt)

        self.prompt_layout.addWidget(self.system_prompt_edit)
        self.prompt_layout.addWidget(self.reset_prompt_btn)
        self.prompt_group.setLayout(self.prompt_layout)
        self.main_layout.addWidget(self.prompt_group)

        # Process button
        self.process_btn = QPushButton("Process Listing")
        self.process_btn.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.process_btn.setStyleSheet("padding: 6px;")
        self.process_btn.setIcon(QIcon.fromTheme("system-run"))  # Иконка для кнопки
        self.process_btn.clicked.connect(self.start_fetch_thread)
        self.main_layout.addWidget(self.process_btn, alignment=Qt.AlignCenter)

        # Tabs
        self.tabs = QTabWidget()
        self.main_layout.addWidget(self.tabs)

        # Raw MD tab
        self.raw_tab = QWidget()
        self.raw_md_area = QTextEdit()
        self.raw_md_area.setFont(QFont("Consolas", 10))
        self.raw_md_area.setLineWrapMode(QTextEdit.WidgetWidth)
        self.raw_layout = QVBoxLayout(self.raw_tab)
        self.raw_layout.addWidget(self.raw_md_area)
        self.tabs.addTab(self.raw_tab, "Original Markdown")

        # Processed tab
        self.processed_tab = QWidget()
        self.processed_area = QTextEdit()
        self.processed_area.setFont(QFont("Consolas", 10))
        self.processed_area.setLineWrapMode(QTextEdit.WidgetWidth)
        self.processed_layout = QVBoxLayout(self.processed_tab)
        self.processed_layout.addWidget(self.processed_area)
        self.tabs.addTab(self.processed_tab, "Processed Content")

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

        # Initialize proxy state
        self.toggle_proxy_entry()

    def reset_system_prompt(self):
        self.system_prompt_edit.setPlainText(self.default_system_prompt)

    def toggle_proxy_entry(self):
        enabled = self.use_proxy_check.isChecked()
        self.proxy_label.setEnabled(enabled)
        self.proxy_entry.setEnabled(enabled)

    def start_fetch_thread(self):
        self.status_bar.showMessage("Processing...")
        self.process_btn.setEnabled(False)

        thread = threading.Thread(target=self.fetch_md, daemon=True)
        thread.start()

    def fetch_md(self):
        listing_url = self.url_entry.text().strip()

        if not listing_url:
            self.signal_emitter.update_status_signal.emit(
                "Error: Please enter listing URL", True
            )
            return

        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            if self.use_proxy_check.isChecked():
                proxy = self.proxy_entry.text().strip()
                if proxy:
                    headers["X-Proxy-Url"] = proxy
                    headers["X-Proxy"] = "auto"

            response = requests.get(
                f"https://r.jina.ai/{listing_url}",
                headers=headers,
                timeout=30,
                verify=False,
            )

            if response.status_code == 200:
                md_content = response.text
                self.signal_emitter.update_text_signal.emit(
                    md_content, self.raw_md_area
                )

                processed_text = self.process_md(md_content)
                self.signal_emitter.update_text_signal.emit(
                    processed_text, self.processed_area
                )

                self.signal_emitter.update_status_signal.emit(
                    "Completed successfully", False
                )
            else:
                error_msg = f"API Error {response.status_code}: {response.text}"
                self.signal_emitter.update_status_signal.emit(error_msg, True)
                self.signal_emitter.update_text_signal.emit(error_msg, self.raw_md_area)

        except requests.exceptions.RequestException as e:
            error_msg = f"Request failed: {str(e)}"
            self.signal_emitter.update_status_signal.emit(error_msg, True)
            self.signal_emitter.update_text_signal.emit(error_msg, self.raw_md_area)
        finally:
            self.signal_emitter.enable_button_signal.emit(True)

    def process_md(self, raw_md):
        from g4f.client import Client

        client = Client()
        system_prompt = self.system_prompt_edit.toPlainText().strip()

        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"Please analyze and extract information from this markdown content:\n\n{raw_md}",
            },
        ]

        response = client.chat.completions.create(
            model="gpt-4o-mini", messages=messages, web_search=False
        )
        return response.choices[0].message.content

    def update_text(self, content, widget):
        widget.clear()
        widget.setPlainText(content)
        cursor = widget.textCursor()
        cursor.movePosition(QTextCursor.Start)
        widget.setTextCursor(cursor)

    def update_status(self, message, is_error):
        self.status_bar.showMessage(message)
        if is_error:
            self.status_bar.setStyleSheet("background-color: #dc3545; color: white;")
        else:
            self.status_bar.setStyleSheet("background-color: #6c757d; color: white;")

    def enable_button(self, enabled):
        self.process_btn.setEnabled(enabled)


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Установка иконки приложения для Windows (также работает на других платформах)
    app.setWindowIcon(
        QIcon("icon.png")
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
