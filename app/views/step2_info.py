"""Vista del Paso 2 del flujo: información general del dataset.

Muestra tarjetas con la forma del dataset, conteo de filas y columnas,
uso de memoria aproximado y el archivo de origen. La lógica de datos vive
en `app.services.profiling`; la vista solo consulta y presenta resultados.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.services import profiling
from app.state import Step, WorkflowController
from app.ui import texts_es
from app.widgets import PrimaryButton, StatCard, StepHeader


class Step2InfoView(QWidget):
    """Vista del paso 2: resumen informativo del dataset cargado."""

    def __init__(self, controller: WorkflowController, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.controller = controller

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        self.header = StepHeader(step_number=2, title=texts_es.STEP_2_NAME, parent=self)

        # Fila superior de tarjetas: se reacomoda con la ventana (nunca se corta).
        cards_grid = QGridLayout()
        cards_grid.setContentsMargins(0, 0, 0, 0)
        cards_grid.setSpacing(12)

        self.shape_card = StatCard(texts_es.INFO_SHAPE_TITLE, parent=self)
        self.rows_card = StatCard(texts_es.INFO_ROWS_TITLE, parent=self)
        self.cols_card = StatCard(texts_es.INFO_COLS_TITLE, parent=self)
        self.memory_card = StatCard(texts_es.INFO_MEMORY_TITLE, parent=self)
        self.file_card = StatCard(texts_es.INFO_FILENAME_TITLE, parent=self)

        cards_grid.addWidget(self.shape_card, 0, 0)
        cards_grid.addWidget(self.rows_card, 0, 1)
        cards_grid.addWidget(self.cols_card, 0, 2)
        cards_grid.addWidget(self.memory_card, 1, 0)
        cards_grid.addWidget(self.file_card, 1, 1, 1, 2)

        # Barra inferior de navegación.
        nav_row = QHBoxLayout()
        nav_row.setContentsMargins(0, 0, 0, 0)
        nav_row.setSpacing(10)

        self.back_button = QPushButton(texts_es.BTN_BACK, self)
        self.back_button.clicked.connect(self._on_back)

        self.understood_button = PrimaryButton(texts_es.BTN_UNDERSTOOD, self)
        self.understood_button.clicked.connect(self._on_understood)

        nav_row.addWidget(self.back_button)
        nav_row.addWidget(self.understood_button)
        nav_row.addStretch()

        layout.addWidget(self.header)
        layout.addLayout(cards_grid)
        layout.addStretch(1)
        layout.addLayout(nav_row)

        # Las tarjetas crecen con el espacio disponible y se encogen sin romperse.
        for card in (
            self.shape_card,
            self.rows_card,
            self.cols_card,
            self.memory_card,
            self.file_card,
        ):
            card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        self.refresh()

    # -- API pública ------------------------------------------------------- #

    def refresh(self) -> None:
        """Recalcula y actualiza las tarjetas con el dataset actual."""
        df = self.controller.state.working_df
        if df is None:
            self.shape_card.set_value("")
            self.rows_card.set_value("")
            self.cols_card.set_value("")
            self.memory_card.set_value("")
            self.file_card.set_value("")
            return

        rows, cols = profiling.dataset_shape(df)
        self.shape_card.set_value(f"({rows}, {cols})")
        self.rows_card.set_value(f"{rows:,}")
        self.cols_card.set_value(f"{cols:,}")
        self.memory_card.set_value(profiling.memory_usage(df))

        file_path = self.controller.state.file_path
        self.file_card.set_value(file_path.name if file_path is not None else "")

    # -- Navegación -------------------------------------------------------- #

    def _on_back(self) -> None:
        """Regresa al paso de carga de datos (retroceder siempre es libre)."""
        self.controller.go_to(Step.LOAD)

    def _on_understood(self) -> None:
        """Marca el paso como consultado y avanza a la vista previa."""
        self.controller.complete(Step.INFO)
        self.controller.go_to(Step.PREVIEW)
