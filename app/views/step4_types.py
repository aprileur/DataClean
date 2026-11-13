"""Vista del Paso 4 del flujo: tipos de columnas del dataset.

Clasifica las columnas con `app.services.profiling.classify_columns` y las
presenta en tarjetas: numéricas, categóricas y (solo si existen) fecha/otras.
Si una columna parece identificador se informa, sin reclasificarla.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QHBoxLayout,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.services import profiling
from app.state import Step, WorkflowController
from app.ui import texts_es
from app.widgets import InfoCard, PrimaryButton, StepHeader, WarningBanner


class Step4TypesView(QWidget):
    """Vista del paso 4: clasificación informativa de los tipos de columna."""

    def __init__(self, controller: WorkflowController, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.controller = controller

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        self.header = StepHeader(step_number=4, title=texts_es.STEP_4_NAME, parent=self)

        self.id_banner = WarningBanner(parent=self)
        self.id_banner.setVisible(False)

        self.numeric_card = InfoCard(texts_es.TYPES_NUMERIC_TITLE, parent=self)
        self.categorical_card = InfoCard(texts_es.TYPES_CATEGORICAL_TITLE, parent=self)
        self.other_card = InfoCard(texts_es.TYPES_OTHER_TITLE, parent=self)
        self.other_card.setVisible(False)

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
        layout.addWidget(self.id_banner)
        layout.addWidget(self.numeric_card)
        layout.addWidget(self.categorical_card)
        layout.addWidget(self.other_card)
        layout.addStretch(1)
        layout.addLayout(nav_row)

        # Las tarjetas se estiran horizontalmente y encogen sin romper el layout.
        for card in (self.numeric_card, self.categorical_card, self.other_card):
            card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        self.refresh()

    # -- API pública ------------------------------------------------------- #

    def refresh(self) -> None:
        """Recalcula la clasificación de columnas y actualiza las tarjetas."""
        df = self.controller.state.working_df
        if df is None:
            self._show_classification(None)
            return

        types = profiling.classify_columns(df)
        self._show_classification(types)

    # -- Utilidades internas ----------------------------------------------- #

    def _show_classification(self, types: profiling.ColumnTypes | None) -> None:
        """Pinta las tarjetas a partir de la clasificación (o vacía sin datos)."""
        numeric: list[str] = []
        categorical: list[str] = []
        other: list[str] = []

        if types is not None:
            numeric = types.numeric
            categorical = types.categorical
            other = [*types.datetime, *types.other]

        self.numeric_card.set_content(", ".join(numeric))
        self.categorical_card.set_content(", ".join(categorical))

        has_other = bool(other)
        self.other_card.setVisible(has_other)
        if has_other:
            self.other_card.set_content(", ".join(other))

        self._update_id_banner()

    def _update_id_banner(self) -> None:
        """Muestra un aviso por cada columna que parece identificador."""
        df = self.controller.state.working_df
        if df is None or df.empty:
            self.id_banner.setVisible(False)
            return

        id_columns = [str(col) for col in df.columns if profiling.looks_like_id(df[col])]
        has_warnings = bool(id_columns)
        self.id_banner.setVisible(has_warnings)
        if has_warnings:
            message = "\n".join(texts_es.TYPES_ID_WARNING.format(col=col) for col in id_columns)
            self.id_banner.set_message(message)

    # -- Navegación -------------------------------------------------------- #

    def _on_back(self) -> None:
        """Regresa al paso de vista previa (retroceder siempre es libre)."""
        self.controller.go_to(Step.PREVIEW)

    def _on_understood(self) -> None:
        """Marca el paso como consultado y avanza a la limpieza de datos."""
        self.controller.complete(Step.TYPES)
        self.controller.go_to(Step.CLEAN_A)
