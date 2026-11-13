"""Tarjetas reutilizables para métricas y datos informativos."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget


class StatCard(QFrame):
    """Tarjeta para mostrar una estadística clave con título superior y valor destacado."""

    def __init__(self, title: str, value: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("statCard")
        self.setProperty("class", "StatCard")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(4)

        self.title_label = QLabel(title, self)
        self.title_label.setObjectName("cardTitle")

        self.value_label = QLabel(value, self)
        self.value_label.setObjectName("cardValue")

        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)

    def set_value(self, value: str) -> None:
        """Actualiza el texto del valor en la tarjeta."""
        self.value_label.setText(value)


class InfoCard(QFrame):
    """Tarjeta informativa con título y cuerpo de texto flexible."""

    def __init__(self, title: str, content: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("infoCard")
        self.setProperty("class", "InfoCard")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(8)

        self.title_label = QLabel(title, self)
        self.title_label.setObjectName("cardTitle")

        self.content_label = QLabel(content, self)
        self.content_label.setObjectName("cardContent")
        self.content_label.setWordWrap(True)
        self.content_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        layout.addWidget(self.title_label)
        layout.addWidget(self.content_label)

    def set_content(self, content: str) -> None:
        """Actualiza el contenido textual de la tarjeta."""
        self.content_label.setText(content)
