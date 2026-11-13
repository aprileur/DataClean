"""Vista del Paso 3 del flujo: vista previa (`head`) del dataset.

Permite elegir cuántos registros mostrar con un `QSpinBox` y presenta las
primeras N filas en una tabla de solo lectura. Cambiar N no recarga el
archivo: la tabla se actualiza a partir del `working_df` en memoria.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.state import Step, WorkflowController
from app.ui import texts_es
from app.widgets import PrimaryButton, StepHeader
from app.widgets.dataframe_table import DataFrameTable

#: Cantidad de registros mostrados por defecto al entrar a la vista previa.
DEFAULT_PREVIEW_ROWS = 5


class Step3PreviewView(QWidget):
    """Vista del paso 3: primeras N filas del dataset con N configurable."""

    def __init__(self, controller: WorkflowController, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.controller = controller
        #: Indica si el usuario ya eligió un valor propio en el spinbox; si no,
        #: `refresh()` aplica el valor por defecto cuando llega un dataset nuevo.
        self._limit_chosen = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        self.header = StepHeader(step_number=3, title=texts_es.STEP_3_NAME, parent=self)

        # Fila de control: etiqueta + spinbox + total de registros.
        control_row = QHBoxLayout()
        control_row.setContentsMargins(0, 0, 0, 0)
        control_row.setSpacing(10)

        self.control_label = QLabel(texts_es.PREVIEW_CONTROL_LABEL, self)

        self.spinbox = QSpinBox(self)
        self.spinbox.setObjectName("previewSpinBox")
        self.spinbox.setMinimum(1)
        self.spinbox.setMaximum(1)
        self.spinbox.setValue(DEFAULT_PREVIEW_ROWS)

        self.total_label = QLabel("", self)
        self.total_label.setObjectName("previewTotalLabel")

        control_row.addWidget(self.control_label)
        control_row.addWidget(self.spinbox)
        control_row.addWidget(self.total_label)
        control_row.addStretch()

        self.table = DataFrameTable(parent=self)

        # Barra inferior de navegación.
        nav_row = QHBoxLayout()
        nav_row.setContentsMargins(0, 0, 0, 0)
        nav_row.setSpacing(10)

        self.back_button = QPushButton(texts_es.BTN_BACK, self)
        self.back_button.clicked.connect(self._on_back)

        self.understood_button = PrimaryButton(texts_es.BTN_UNDERSTOOD, self)
        self.understood_button.clicked.connect(self._on_understood)

        nav_row.addWidget(self.back_button)
        nav_row.addStretch()
        nav_row.addWidget(self.understood_button)

        layout.addWidget(self.header)
        layout.addLayout(control_row)
        layout.addWidget(self.table, 1)
        layout.addLayout(nav_row)

        self.spinbox.valueChanged.connect(self._on_limit_changed)
        self.refresh()

    # -- API pública ------------------------------------------------------- #

    def refresh(self) -> None:
        """Sincroniza el spinbox, la etiqueta de total y la tabla con el dataset."""
        df = self.controller.state.working_df
        total = 0 if df is None else int(len(df))

        self.spinbox.blockSignals(True)
        try:
            if total > 0:
                # `setMaximum` recorta el valor actual si excede el nuevo máximo.
                self.spinbox.setMaximum(total)
                if not self._limit_chosen:
                    self.spinbox.setValue(min(DEFAULT_PREVIEW_ROWS, total))
            else:
                # Sin filas no hay nada que previsualizar: un único valor válido.
                self.spinbox.setMaximum(1)
                self.spinbox.setValue(1)
                self._limit_chosen = False
        finally:
            self.spinbox.blockSignals(False)

        self.total_label.setText(texts_es.PREVIEW_TOTAL_LABEL.format(total=total))
        self._update_table()

    # -- Utilidades internas ----------------------------------------------- #

    def _update_table(self) -> None:
        """Muestra las primeras N filas del dataset actual (sin recargar archivo)."""
        df = self.controller.state.working_df
        if df is None:
            self.table.set_dataframe(None)
            return
        self.table.set_dataframe(df.head(self.spinbox.value()))

    # -- Navegación -------------------------------------------------------- #

    def _on_limit_changed(self, _value: int) -> None:
        """Actualiza la tabla cuando el usuario cambia la cantidad de registros."""
        self._limit_chosen = True
        self._update_table()

    def _on_back(self) -> None:
        """Regresa al paso de información general (retroceder siempre es libre)."""
        self.controller.go_to(Step.INFO)

    def _on_understood(self) -> None:
        """Marca el paso como consultado y avanza a los tipos de columnas."""
        self.controller.complete(Step.PREVIEW)
        self.controller.go_to(Step.TYPES)
