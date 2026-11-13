"""Ventana principal de DataClean."""

import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app import __app_name__, __version__
from app.state import WorkflowController
from app.theme import apply_theme
from app.ui import texts_es


class MainWindow(QMainWindow):
    """Ventana principal con barra superior, sidebar fija y contenedor central expandible."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"{__app_name__} {__version__}")
        self.setMinimumSize(900, 600)
        self.resize(1920, 1080)

        self.controller = WorkflowController(parent=self)
        self._setup_ui()
        apply_theme(self)

    def _setup_ui(self) -> None:
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        # Layout vertical principal: Barra superior lila + Cuerpo (Sidebar + Contenido)
        main_vbox = QVBoxLayout(central_widget)
        main_vbox.setContentsMargins(0, 0, 0, 0)
        main_vbox.setSpacing(0)

        # Barra superior lila redondeada
        self.top_bar = QWidget(central_widget)
        self.top_bar.setObjectName("topBar")
        top_bar_layout = QHBoxLayout(self.top_bar)
        top_bar_layout.setContentsMargins(16, 10, 16, 10)

        self.title_label = QLabel(texts_es.APP_TITLE, self.top_bar)
        self.title_label.setObjectName("topBarTitle")
        self.subtitle_label = QLabel(f"— {texts_es.APP_SUBTITLE}", self.top_bar)
        self.subtitle_label.setObjectName("topBarSubtitle")

        top_bar_layout.addWidget(self.title_label)
        top_bar_layout.addWidget(self.subtitle_label)
        top_bar_layout.addStretch()

        main_vbox.addWidget(self.top_bar, 0)

        # Cuerpo: Sidebar izquierda + Stack de contenido
        body_container = QWidget(central_widget)
        body_layout = QHBoxLayout(body_container)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        # Sidebar izquierda fija de 240 px
        self.sidebar = QWidget(body_container)
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(240)
        self.sidebar.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)

        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(16, 20, 16, 20)
        sidebar_layout.setSpacing(12)

        self.sidebar_title = QLabel(texts_es.SIDEBAR_TITLE, self.sidebar)
        self.sidebar_title.setObjectName("sidebarTitle")
        self.sidebar_title.setAlignment(Qt.AlignmentFlag.AlignLeft)
        sidebar_layout.addWidget(self.sidebar_title)
        sidebar_layout.addStretch()

        body_layout.addWidget(self.sidebar, 0)

        # Área de contenido central expandible
        self.content_stack = QStackedWidget(body_container)
        self.content_stack.setObjectName("contentStack")
        self.content_stack.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        placeholder = QWidget()
        placeholder_layout = QVBoxLayout(placeholder)
        placeholder_layout.setContentsMargins(24, 24, 24, 24)
        placeholder_label = QLabel(f"Bienvenido a {__app_name__}", placeholder)
        placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder_layout.addWidget(placeholder_label)

        self.content_stack.addWidget(placeholder)
        body_layout.addWidget(self.content_stack, 1)

        main_vbox.addWidget(body_container, 1)


def main() -> int:
    """Punto de entrada de la interfaz gráfica."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
