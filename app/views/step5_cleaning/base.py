"""Utilidades compartidas por las vistas del Paso 5 (limpieza A–E).

Cada sub-vista expone la señal `step_done` (que el contenedor usa para
habilitar la pestaña siguiente) y delega toda la lógica de datos en
`app.services.cleaning`. Esta clase base concentra el registro en el
historial, la invalidación en cascada y la confirmación de "Omitir".
"""

from __future__ import annotations

import pandas as pd
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QLabel, QMessageBox, QVBoxLayout, QWidget

from app.state import Step, WorkflowController
from app.ui import texts_es
from app.widgets import StepHeader


class CleaningStepView(QWidget):
    """Base común de las cinco sub-vistas de limpieza.

    Attributes:
        step: Paso del flujo que representa la vista (`Step.CLEAN_A`…`CLEAN_E`).
        step_letter: Letra mostrada en el círculo del encabezado ("A"…"E").
        step_title: Título en español del sub-paso.
    """

    step_done = Signal()

    step: Step
    step_letter: str
    step_title: str

    def __init__(self, controller: WorkflowController, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.controller = controller

        self.body_layout = QVBoxLayout(self)
        self.body_layout.setContentsMargins(16, 16, 16, 16)
        self.body_layout.setSpacing(12)

        self.header = StepHeader(self.step_letter, self.step_title, self)
        self.status_label = QLabel("", self)
        self.status_label.setObjectName("cleanStatusLabel")
        self.status_label.setWordWrap(True)
        self.status_label.setVisible(False)

        self.body_layout.addWidget(self.header)
        self.body_layout.addWidget(self.status_label)

    # -- API pública ------------------------------------------------------- #

    @property
    def dataframe(self) -> pd.DataFrame | None:
        """Dataset de trabajo actual (nunca el original)."""
        return self.controller.state.working_df

    @property
    def is_completed(self) -> bool:
        """Indica si el sub-paso ya fue resuelto."""
        return self.controller.state.is_completed(self.step)

    def refresh(self) -> None:
        """Recalcula el diagnóstico y repinta la vista. Implementado por cada sub-vista."""
        raise NotImplementedError

    def reset_diagnostics(self) -> None:
        """Limpia el estado interno de la vista (se llama al reiniciar el flujo)."""
        self.show_status("")

    def show_status(self, message: str) -> None:
        """Muestra (o esconde) un mensaje de estado bajo el encabezado."""
        self.status_label.setText(message)
        self.status_label.setVisible(bool(message))

    def mark_completed(self) -> None:
        """Marca el sub-paso como resuelto y notifica al contenedor."""
        self.controller.complete(self.step)
        self.step_done.emit()

    def skip(self) -> bool:
        """Pide confirmación y omite el sub-paso, registrándolo en el historial.

        Returns:
            `True` si el usuario confirmó la omisión; `False` si canceló.
        """
        answer = QMessageBox.question(
            self,
            texts_es.CLEAN_SKIP_CONFIRM_TITLE,
            texts_es.CLEAN_SKIP_CONFIRM_MSG,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return False

        df = self.dataframe
        if df is not None:
            self.controller.state.history.push(
                texts_es.CLEAN_HISTORY_SKIP.format(step_name=self.step_title), df
            )
        self.show_status(texts_es.CLEAN_STEP_SKIPPED)
        self.mark_completed()
        return True

    # -- Utilidades para las sub-vistas ------------------------------------ #

    def apply_result(self, new_df: pd.DataFrame, description: str) -> None:
        """Guarda el snapshot, actualiza el dataset, invalida y completa el sub-paso.

        Args:
            new_df: DataFrame resultante de la operación (nunca se muta el actual).
            description: Texto en español que describe la acción para el historial.
        """
        state = self.controller.state
        state.history.push(description, new_df)
        state.working_df = new_df
        self.controller.invalidate_from(self.step, inclusive=False)
        self.mark_completed()
        self.show_status("")
        self.refresh()

    def complete_if_no_issues(self, has_issues: bool) -> None:
        """Completa el sub-paso automáticamente cuando el diagnóstico está vacío."""
        if self.dataframe is None or has_issues or self.is_completed:
            return
        self.show_status(texts_es.CLEAN_NO_ISSUES_FOUND)
        self.mark_completed()
