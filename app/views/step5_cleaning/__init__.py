"""Contenedor del Paso 5: pestañas de limpieza A–E con progreso y navegación.

La pestaña A siempre está disponible; cada pestaña siguiente se habilita
cuando la anterior emite `step_done` (o ya estaba completada en el estado).
El botón "Siguiente" solo se habilita al resolver E y solicita avanzar a la
vista de exportación.
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.state import Step, StepLockedError, WorkflowController
from app.ui import texts_es
from app.views.step5_cleaning.base import CleaningStepView
from app.views.step5_cleaning.duplicates import DuplicatesView
from app.views.step5_cleaning.irrelevant import IrrelevantView
from app.views.step5_cleaning.missing import MissingView
from app.views.step5_cleaning.outliers import OutliersView
from app.views.step5_cleaning.typos import TyposView
from app.widgets import PrimaryButton, StepHeader


class Step5CleaningView(QWidget):
    """Contenedor con las cinco sub-vistas del paso de limpieza."""

    export_requested = Signal()

    def __init__(self, controller: WorkflowController, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.controller = controller
        self._syncing = False

        self.steps: tuple[Step, ...] = (
            Step.CLEAN_A,
            Step.CLEAN_B,
            Step.CLEAN_C,
            Step.CLEAN_D,
            Step.CLEAN_E,
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        self.header = StepHeader("5", texts_es.STEP_5_NAME, self)
        self.progress_label = QLabel("", self)
        self.progress_label.setObjectName("cleanProgressLabel")

        self.tabs = QTabWidget(self)
        self.tabs.setObjectName("cleaningTabs")
        self.views: list[CleaningStepView] = [
            MissingView(controller, self.tabs),
            IrrelevantView(controller, self.tabs),
            DuplicatesView(controller, self.tabs),
            OutliersView(controller, self.tabs),
            TyposView(controller, self.tabs),
        ]
        for step, view in zip(self.steps, self.views, strict=True):
            self.tabs.addTab(view, step.display_name)
            view.step_done.connect(self._on_step_done)

        nav_row = QHBoxLayout()
        nav_row.setContentsMargins(0, 0, 0, 0)
        nav_row.setSpacing(10)

        self.back_button = QPushButton(texts_es.BTN_BACK, self)
        self.back_button.clicked.connect(self._on_back)

        self.skip_button = QPushButton(texts_es.BTN_SKIP_STEP, self)
        self.skip_button.clicked.connect(self._on_skip)

        self.next_button = PrimaryButton(texts_es.BTN_NEXT, self)
        self.next_button.setEnabled(False)
        self.next_button.clicked.connect(self._on_next)

        nav_row.addWidget(self.back_button)
        nav_row.addWidget(self.skip_button)
        nav_row.addStretch()
        nav_row.addWidget(self.next_button)

        layout.addWidget(self.header)
        layout.addWidget(self.progress_label)
        layout.addWidget(self.tabs, 1)
        layout.addLayout(nav_row)

        self.tabs.currentChanged.connect(self._on_tab_changed)
        self.controller.step_completed.connect(self._on_step_completed)
        self.controller.steps_invalidated.connect(self._on_steps_invalidated)
        self.controller.step_changed.connect(self._on_step_changed)
        self.controller.state_reset.connect(self._on_state_reset)

        self._update_tab_states()
        self._restore_current_tab()

    # -- API pública ------------------------------------------------------- #

    @property
    def current_view(self) -> CleaningStepView:
        """Sub-vista activa del contenedor."""
        return self.views[self.tabs.currentIndex()]

    def refresh(self) -> None:
        """Actualiza el progreso, las pestañas y la sub-vista activa."""
        self._update_tab_states()
        self._update_progress()
        self.current_view.refresh()

    # -- Estado y pestañas -------------------------------------------------- #

    def _update_tab_states(self) -> None:
        """Habilita cada pestaña según el estado de la anterior y marca las completadas."""
        state = self.controller.state
        for index, step in enumerate(self.steps):
            enabled = index == 0 or all(
                state.is_completed(previous) for previous in self.steps[:index]
            )
            self.tabs.setTabEnabled(index, enabled)

            title = step.display_name
            if state.is_completed(step):
                title += texts_es.CLEAN_TAB_COMPLETED_SUFFIX
            self.tabs.setTabText(index, title)

        if not self.tabs.isTabEnabled(self.tabs.currentIndex()):
            self._set_current_index(0)

        self._update_progress()
        self._update_navigation()

    def _update_progress(self) -> None:
        """Actualiza el contador de sub-pasos completados."""
        done = sum(1 for step in self.steps if self.controller.state.is_completed(step))
        self.progress_label.setText(
            texts_es.CLEAN_PROGRESS_LABEL.format(done=done, total=len(self.steps))
        )

    def _update_navigation(self) -> None:
        """Ajusta los botones Anterior, Omitir y Siguiente."""
        self.back_button.setEnabled(True)
        if self.tabs.currentIndex() > 0:
            self.back_button.setText(texts_es.BTN_BACK)
        self.skip_button.setEnabled(not self.current_view.is_completed)
        self.next_button.setEnabled(
            all(self.controller.state.is_completed(step) for step in self.steps)
        )

    def _set_current_index(self, index: int) -> None:
        """Cambia de pestaña sin disparar navegación duplicada."""
        self._syncing = True
        try:
            self.tabs.setCurrentIndex(index)
        finally:
            self._syncing = False

    def _restore_current_tab(self) -> None:
        """Sincroniza la pestaña activa con el paso actual del controlador."""
        current = self.controller.state.current
        if current in self.steps:
            self._set_current_index(self.steps.index(current))
        else:
            self._set_current_index(0)
        self._update_navigation()

    # -- Slots -------------------------------------------------------------- #

    def _on_step_done(self) -> None:
        """Señal emitida por una sub-vista al resolver su sub-paso."""
        self._update_tab_states()

    def _on_step_completed(self, _step: Step) -> None:
        """Mantiene sincronizados los indicadores cuando completa cualquier paso."""
        self._update_tab_states()

    def _on_steps_invalidated(self, steps: set[Step]) -> None:
        """Descarta diagnósticos de los sub-pasos que quedaron pendientes."""
        for step in steps:
            if step in self.steps:
                index = self.steps.index(step)
                self.views[index].reset_diagnostics()
        self._update_tab_states()

    def _on_step_changed(self, step: Step) -> None:
        """Sigue la navegación externa (por ejemplo, al entrar al paso 5)."""
        if step not in self.steps:
            return
        index = self.steps.index(step)
        self._set_current_index(index)
        self.views[index].refresh()
        self._update_navigation()

    def _on_state_reset(self) -> None:
        """Reinicia todas las sub-vistas cuando se carga un dataset nuevo."""
        for view in self.views:
            view.reset_diagnostics()
            view.refresh()
        self._set_current_index(0)
        self._update_tab_states()

    def _on_tab_changed(self, index: int) -> None:
        """Navega a la pestaña elegida a través del controlador."""
        if self._syncing or index < 0:
            return

        step = self.steps[index]
        try:
            self.controller.go_to(step)
        except StepLockedError:
            self._restore_current_tab()
            return

        self.views[index].refresh()
        self._update_navigation()

    def _on_back(self) -> None:
        """Retrocede a la pestaña anterior o al paso de tipos de columnas."""
        index = self.tabs.currentIndex()
        if index > 0:
            self._set_current_index(index - 1)
            self._on_tab_changed(index - 1)
            return

        try:
            self.controller.go_to(Step.TYPES)
        except StepLockedError:
            return

    def _on_skip(self) -> None:
        """Omite el sub-paso activo con confirmación."""
        if self.current_view.skip():
            self._update_tab_states()

    def _on_next(self) -> None:
        """Avanza a la exportación cuando E está resuelto."""
        if not self.controller.state.is_completed(Step.CLEAN_E):
            return
        try:
            self.controller.go_to(Step.EXPORT)
        except StepLockedError:
            return
        self.export_requested.emit()
