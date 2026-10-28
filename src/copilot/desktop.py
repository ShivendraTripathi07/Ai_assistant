import asyncio
import html
from typing import cast

from PySide6.QtCore import QObject, QPoint, QRunnable, QSettings, Qt, QThreadPool, Signal
from PySide6.QtGui import QDesktopServices, QFont, QMouseEvent
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QSystemTrayIcon,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from copilot.application import Assistant
from copilot.config import Settings
from copilot.domain import Mode, SearchResult, TurnResult


class WorkerSignals(QObject):
    done = Signal(object)
    failed = Signal(str)
    sources = Signal(object)


class AskWorker(QRunnable):
    def __init__(self, assistant: Assistant, prompt: str, mode: Mode, screen_context: str) -> None:
        super().__init__()
        self.assistant, self.prompt, self.mode = assistant, prompt, mode
        self.screen_context = screen_context
        self.signals = WorkerSignals()

    def run(self) -> None:
        try:
            self.signals.done.emit(
                asyncio.run(
                    self.assistant.ask(
                        self.prompt,
                        self.mode,
                        self.signals.sources.emit,
                        self.screen_context,
                    )
                )
            )
        except Exception as exc:
            self.signals.failed.emit(str(exc))


class ChatWindow(QWidget):
    def __init__(self, assistant: Assistant, settings: Settings) -> None:
        super().__init__()
        self.assistant = assistant
        self.settings = settings
        self.pool = QThreadPool.globalInstance()
        self.screen_context = ""
        self.user_settings = QSettings("PersonalAICopilot", "Copilot")
        settings.gemini_model = str(self.user_settings.value("gemini_model", settings.gemini_model))
        settings.llm_timeout_seconds = float(
            str(self.user_settings.value("llm_timeout_seconds", settings.llm_timeout_seconds))
        )
        settings.search_timeout_seconds = float(
            str(self.user_settings.value("search_timeout_seconds", settings.search_timeout_seconds))
        )
        self.setWindowTitle("Personal AI Copilot")
        self.setMinimumSize(520, 620)
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint)
        self.setStyleSheet(
            "QWidget{background:#111827;color:#e5e7eb;font-size:14px} QPushButton{background:#2563eb;padding:9px;border-radius:7px} QLineEdit,QTextBrowser,QComboBox{background:#1f2937;border:1px solid #374151;padding:9px;border-radius:6px}"
        )
        layout = QVBoxLayout(self)
        title = QLabel("Copilot  ·  private desktop assistant")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.DemiBold))
        layout.addWidget(title)
        self.context_status = QLabel("No screen context attached")
        self.context_status.setStyleSheet("color:#9ca3af")
        layout.addWidget(self.context_status)
        self.transcript = QTextBrowser()
        self.transcript.setOpenLinks(False)
        self.transcript.anchorClicked.connect(QDesktopServices.openUrl)
        layout.addWidget(self.transcript, 1)
        for message in self.assistant.store.history(settings.max_context_messages * 4):
            label = "You" if message.role == "user" else "Copilot"
            color = "#93c5fd" if message.role == "user" else "#e5e7eb"
            self.transcript.append(
                f'<p style="color:{color}"><b>{label}</b><br>'
                f'{html.escape(message.text).replace(chr(10), "<br>")}</p>'
            )
        row = QHBoxLayout()
        self.mode = QComboBox()
        self.mode.addItems([m.value for m in Mode])
        self.input = QLineEdit()
        self.input.setPlaceholderText("Ask a question…")
        self.input.returnPressed.connect(self.send)
        self.send_button = QPushButton("Send")
        self.send_button.clicked.connect(self.send)
        row.addWidget(self.mode)
        row.addWidget(self.input, 1)
        row.addWidget(self.send_button)
        layout.addLayout(row)
        actions = QHBoxLayout()
        settings_button = QPushButton("Settings")
        settings_button.clicked.connect(self.show_settings)
        attach = QPushButton("Attach copied text…")
        attach.clicked.connect(self.attach_clipboard)
        remove_context = QPushButton("Remove context")
        remove_context.clicked.connect(self.remove_context)
        clear = QPushButton("New conversation")
        clear.clicked.connect(self.clear)
        actions.addWidget(attach)
        actions.addWidget(remove_context)
        actions.addWidget(QLabel("Choose Auto, AI, or Web Search"))
        actions.addStretch()
        actions.addWidget(settings_button)
        actions.addWidget(clear)
        layout.addLayout(actions)

    def send(self) -> None:
        prompt = self.input.text().strip()
        if not prompt:
            return
        self.input.clear()
        self.transcript.append(f'<p style="color:#93c5fd"><b>You</b><br>{html.escape(prompt)}</p>')
        self.send_button.setEnabled(False)
        self.send_button.setText("Working…")
        worker = AskWorker(
            self.assistant, prompt, Mode(self.mode.currentText()), self.screen_context
        )
        worker.signals.done.connect(self.show_result)
        worker.signals.failed.connect(self.show_error)
        worker.signals.sources.connect(self.show_sources)
        self.pool.start(worker)

    def show_result(self, result: TurnResult) -> None:
        self.send_button.setEnabled(True)
        self.send_button.setText("Send")
        answer = result.answer
        if answer:
            self.transcript.append(
                f"<p><b>{html.escape(result.provider)}</b><br>{html.escape(answer).replace(chr(10), '<br>')}</p>"
            )

    def show_sources(self, sources: list[SearchResult]) -> None:
        for item in sources:
            self.transcript.append(
                f'<p>🔎 <a href="{html.escape(item.url, quote=True)}">{html.escape(item.title)}</a> · {html.escape(item.domain)}<br>{html.escape(item.snippet)}</p>'
            )

    def show_error(self, message: str) -> None:
        self.send_button.setEnabled(True)
        self.send_button.setText("Send")
        self.transcript.append(
            f'<p style="color:#fca5a5"><b>Could not complete request</b><br>{html.escape(message)}</p>'
        )

    def clear(self) -> None:
        self.assistant.store.clear()
        self.transcript.clear()

    def attach_clipboard(self) -> None:
        text = QApplication.clipboard().text().strip()
        if not text:
            self.show_error("The clipboard has no text. Copy selected text first, then attach it.")
            return
        self.screen_context = text[:20_000]
        self.context_status.setText(
            f"Selected text attached ({len(self.screen_context):,} characters). It will be sent with your next request."
        )
        self.context_status.setStyleSheet("color:#93c5fd")

    def remove_context(self) -> None:
        self.screen_context = ""
        self.context_status.setText("No screen context attached")
        self.context_status.setStyleSheet("color:#9ca3af")

    def show_settings(self) -> None:
        settings = self.settings
        dialog = QDialog(self)
        dialog.setWindowTitle("Copilot Settings")
        dialog.setMinimumWidth(430)
        layout = QVBoxLayout(dialog)
        form = QFormLayout()
        model = QLineEdit(settings.gemini_model)
        llm_timeout = QDoubleSpinBox()
        llm_timeout.setRange(1, 180)
        llm_timeout.setSuffix(" seconds")
        llm_timeout.setValue(settings.llm_timeout_seconds)
        search_timeout = QDoubleSpinBox()
        search_timeout.setRange(1, 60)
        search_timeout.setSuffix(" seconds")
        search_timeout.setValue(settings.search_timeout_seconds)
        form.addRow("Gemini model", model)
        form.addRow("AI timeout", llm_timeout)
        form.addRow("Search timeout", search_timeout)
        form.addRow(
            "Gemini API key",
            QLabel(
                "Configured"
                if settings.gemini_api_key
                else "Missing — set COPILOT_GEMINI_API_KEY in .env"
            ),
        )
        form.addRow(
            "Tavily API key",
            QLabel(
                "Configured"
                if settings.tavily_api_key
                else "Missing — set COPILOT_TAVILY_API_KEY in .env"
            ),
        )
        form.addRow("Conversation database", QLabel(str(settings.database_path)))
        layout.addLayout(form)
        layout.addWidget(
            QLabel("API keys are read from .env or environment variables and are never saved here.")
        )
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            settings.gemini_model = model.text().strip() or settings.gemini_model
            settings.llm_timeout_seconds = llm_timeout.value()
            settings.search_timeout_seconds = search_timeout.value()
            self.user_settings.setValue("gemini_model", settings.gemini_model)
            self.user_settings.setValue("llm_timeout_seconds", settings.llm_timeout_seconds)
            self.user_settings.setValue("search_timeout_seconds", settings.search_timeout_seconds)


class Launcher(QWidget):
    def __init__(self, window: ChatWindow) -> None:
        super().__init__()
        self.chat_window = window
        self.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.button = QPushButton("✦")
        self.button.setToolTip("Open Personal AI Copilot · drag to move")
        self.button.setFixedSize(52, 52)
        self.button.setStyleSheet(
            "QPushButton{background:#2563eb;color:white;border-radius:26px;font-size:24px}"
        )
        self.button.clicked.connect(self.open_chat)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.button)
        self._drag_offset: QPoint | None = None
        self.move(40, 220)

    def open_chat(self) -> None:
        self.chat_window.show()
        self.chat_window.raise_()
        self.chat_window.activateWindow()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if event.buttons() & Qt.MouseButton.LeftButton and self._drag_offset is not None:
            self.move(event.globalPosition().toPoint() - self._drag_offset)


def run_desktop(assistant: Assistant, settings: Settings) -> int:
    app = cast(QApplication | None, QApplication.instance())
    if app is None:
        app = QApplication([])
    app.setQuitOnLastWindowClosed(False)
    chat = ChatWindow(assistant, settings)
    launcher = Launcher(chat)
    launcher.show()
    tray = QSystemTrayIcon(app)
    tray.setToolTip("Personal AI Copilot")
    menu = QMenu()
    menu.addAction("Open Assistant", launcher.open_chat)
    menu.addAction("Settings", chat.show_settings)
    menu.addAction("Hide launcher", launcher.hide)
    menu.addAction("Show launcher", launcher.show)
    menu.addSeparator()
    menu.addAction("Exit", app.quit)
    tray.setContextMenu(menu)
    tray.activated.connect(
        lambda reason: (
            launcher.open_chat() if reason == QSystemTrayIcon.ActivationReason.Trigger else None
        )
    )
    tray.show()
    return app.exec()
