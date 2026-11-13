"""Encabezado de paso con círculo lila numerado y título."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget


class StepHeader(QWidget):
    """Componente de encabezado consistente con badge numérico lila y título del paso."""

    def __init__(self, step_number: str | int, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("stepHeaderWidget")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 8)
        layout.setSpacing(10)

        self.badge = QLabel(str(step_number), self)
        self.badge.setObjectName("stepBadge")
        self.badge.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.title_label = QLabel(title, self)
        self.title_label.setObjectName("stepTitle")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        layout.addWidget(self.badge, 0)
        layout.addWidget(self.title_label, 1)

    def set_title(self, title: str) -> None:
        """Actualiza el título del paso."""
        self.title_label.setText(title)
