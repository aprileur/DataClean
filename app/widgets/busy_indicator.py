"""Indicador visual de operaciones en segundo plano (tarea T21).

`BusyIndicator` es una etiqueta más una barra de progreso indeterminada. El
widget no ejecuta nada: las vistas lo muestran y lo ocultan desde el hilo de
interfaz mientras un `app.workers.Worker` realiza el trabajo pesado.
"""

from __future__ import annotations

from PySide6.QtWidgets import QLabel, QProgressBar, QVBoxLayout, QWidget


class BusyIndicator(QWidget):
    """Etiqueta y barra indeterminada que indican que hay una tarea en curso.

    Args:
        message: Texto en español que se muestra durante la operación.
        parent: Widget padre opcional.
    """

    def __init__(self, message: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("busyIndicator")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.label = QLabel(message, self)
        self.label.setObjectName("loadProgressLabel")
        self.label.setWordWrap(True)

        self.bar = QProgressBar(self)
        self.bar.setObjectName("loadProgress")
        # Rango 0–0: Qt dibuja la barra en modo indeterminado (animación continua).
        self.bar.setRange(0, 0)
        self.bar.setTextVisible(False)

        layout.addWidget(self.label)
        layout.addWidget(self.bar)
        self.setVisible(False)

    @property
    def is_busy(self) -> bool:
        """Indica si el indicador está mostrándose explícitamente."""
        return not self.isHidden()

    def set_busy(self, busy: bool) -> None:
        """Muestra u oculta el indicador (siempre desde el hilo de interfaz)."""
        self.setVisible(busy)
