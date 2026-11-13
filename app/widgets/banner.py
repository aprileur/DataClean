"""Banner visual para avisos y advertencias de impacto."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QWidget


class WarningBanner(QFrame):
    """Banner de advertencia con fondo amarillo y mensaje descriptivo."""

    def __init__(self, message: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("warningBanner")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(10)

        self.icon_label = QLabel("⚠️", self)
        self.icon_label.setObjectName("bannerIcon")
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.message_label = QLabel(message, self)
        self.message_label.setObjectName("bannerMessage")
        self.message_label.setWordWrap(True)

        layout.addWidget(self.icon_label, 0)
        layout.addWidget(self.message_label, 1)

    def set_message(self, message: str) -> None:
        """Actualiza el texto del mensaje en el banner."""
        self.message_label.setText(message)
