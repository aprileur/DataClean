"""Botones estilizados reutilizables para acciones primarias y destructivas."""

from PySide6.QtWidgets import QPushButton, QWidget


class PrimaryButton(QPushButton):
    """Botón con estilo principal lila."""

    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setObjectName("primaryButton")


class DangerButton(QPushButton):
    """Botón para acciones destructivas con borde y texto rojo."""

    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setObjectName("dangerButton")
