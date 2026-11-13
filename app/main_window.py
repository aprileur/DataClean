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


class MainWindow(QMainWindow):
    """Ventana principal con sidebar fija y contenedor central expandible."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"{__app_name__} {__version__}")
        self.setMinimumSize(900, 600)
        self.resize(1920, 1080)

        self._setup_ui()

    def _setup_ui(self) -> None:
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        root_layout = QHBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Sidebar izquierda fija de 240 px
        self.sidebar = QWidget(central_widget)
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(240)
        self.sidebar.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)

        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(16, 20, 16, 20)
        sidebar_layout.setSpacing(12)

        self.sidebar_title = QLabel("Pasos del flujo", self.sidebar)
        self.sidebar_title.setObjectName("sidebarTitle")
        self.sidebar_title.setAlignment(Qt.AlignmentFlag.AlignLeft)
        sidebar_layout.addWidget(self.sidebar_title)
        sidebar_layout.addStretch()

        root_layout.addWidget(self.sidebar, 0)

        # Área de contenido central expandible
        self.content_stack = QStackedWidget(central_widget)
        self.content_stack.setObjectName("contentStack")
        self.content_stack.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # Placeholder inicial para T01
        placeholder = QWidget()
        placeholder_layout = QVBoxLayout(placeholder)
        placeholder_layout.setContentsMargins(24, 24, 24, 24)
        placeholder_label = QLabel(f"Bienvenido a {__app_name__}", placeholder)
        placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder_layout.addWidget(placeholder_label)

        self.content_stack.addWidget(placeholder)
        root_layout.addWidget(self.content_stack, 1)


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
