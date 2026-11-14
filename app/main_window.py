"""Ventana principal de DataClean: barra superior, sidebar y flujo completo."""

from __future__ import annotations

import logging
import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app import __app_name__, __version__
from app.state import STEP_ORDER, Step, StepLockedError, WorkflowController
from app.theme import apply_theme
from app.ui import texts_es
from app.views.export import ExportView
from app.views.step1_load import Step1LoadView
from app.views.step2_info import Step2InfoView
from app.views.step3_preview import Step3PreviewView
from app.views.step4_types import Step4TypesView
from app.views.step5_cleaning import Step5CleaningView
from app.widgets import DangerButton

logger = logging.getLogger(__name__)

#: Sub-pasos del bloque de limpieza (se muestran indentados en la sidebar).
CLEANING_STEPS: tuple[Step, ...] = (
    Step.CLEAN_A,
    Step.CLEAN_B,
    Step.CLEAN_C,
    Step.CLEAN_D,
    Step.CLEAN_E,
)


class MainWindow(QMainWindow):
    """Ventana principal con barra superior, sidebar fija y contenedor central expandible."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"{__app_name__} {__version__}")
        self.setMinimumSize(900, 600)
        self.resize(1920, 1080)

        self.controller = WorkflowController(parent=self)
        self.step_buttons: dict[Step, QPushButton] = {}

        self._setup_ui()
        self._create_views()
        self._connect_signals()
        apply_theme(self)
        self._sync_sidebar()
        self._sync_history_buttons()

    # -- Construcción de la interfaz --------------------------------------- #

    def _setup_ui(self) -> None:
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        # Layout vertical principal: Barra superior lila + Cuerpo (Sidebar + Contenido)
        main_vbox = QVBoxLayout(central_widget)
        main_vbox.setContentsMargins(0, 0, 0, 0)
        main_vbox.setSpacing(0)

        # Barra superior lila redondeada
        self.top_bar = QWidget(central_widget)
        self.top_bar.setObjectName("topBar")
        top_bar_layout = QHBoxLayout(self.top_bar)
        top_bar_layout.setContentsMargins(16, 10, 16, 10)
        top_bar_layout.setSpacing(10)

        self.title_label = QLabel(texts_es.APP_TITLE, self.top_bar)
        self.title_label.setObjectName("topBarTitle")
        self.subtitle_label = QLabel(f"— {texts_es.APP_SUBTITLE}", self.top_bar)
        self.subtitle_label.setObjectName("topBarSubtitle")

        # Botones de historial (T19), disponibles desde cualquier paso.
        self.undo_button = QPushButton(texts_es.BTN_UNDO, self.top_bar)
        self.undo_button.setObjectName("historyButton")
        self.undo_button.clicked.connect(self._on_undo)

        self.restore_button = DangerButton(texts_es.BTN_RESTORE_ORIGINAL, self.top_bar)
        self.restore_button.setProperty("historyAction", "true")
        self.restore_button.clicked.connect(self._on_restore_original)

        top_bar_layout.addWidget(self.title_label)
        top_bar_layout.addWidget(self.subtitle_label)
        top_bar_layout.addStretch()
        top_bar_layout.addWidget(self.undo_button)
        top_bar_layout.addWidget(self.restore_button)

        main_vbox.addWidget(self.top_bar, 0)

        # Cuerpo: Sidebar izquierda + Stack de contenido
        body_container = QWidget(central_widget)
        body_layout = QHBoxLayout(body_container)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        # Sidebar izquierda fija de 240 px
        self.sidebar = QWidget(body_container)
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(240)
        self.sidebar.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)

        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(12, 20, 12, 20)
        sidebar_layout.setSpacing(6)

        self.sidebar_title = QLabel(texts_es.SIDEBAR_TITLE, self.sidebar)
        self.sidebar_title.setObjectName("sidebarTitle")
        self.sidebar_title.setAlignment(Qt.AlignmentFlag.AlignLeft)
        sidebar_layout.addWidget(self.sidebar_title)

        self._create_sidebar_buttons(sidebar_layout)
        sidebar_layout.addStretch(1)

        self.progress_bar = QProgressBar(self.sidebar)
        self.progress_bar.setObjectName("sidebarProgress")
        self.progress_bar.setRange(0, len(STEP_ORDER))
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat(texts_es.SIDEBAR_PROGRESS_FORMAT)
        sidebar_layout.addWidget(self.progress_bar)

        body_layout.addWidget(self.sidebar, 0)

        # Área de contenido central expandible
        self.content_stack = QStackedWidget(body_container)
        self.content_stack.setObjectName("contentStack")
        self.content_stack.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        body_layout.addWidget(self.content_stack, 1)

        main_vbox.addWidget(body_container, 1)

    def _create_sidebar_buttons(self, sidebar_layout: QVBoxLayout) -> None:
        """Crea un botón de navegación por paso, con A–E indentados bajo el paso 5."""
        for step in STEP_ORDER:
            if step is Step.CLEAN_A:
                section = QLabel(texts_es.STEP_5_NAME, self.sidebar)
                section.setObjectName("sidebarSection")
                section.setContentsMargins(8, 10, 0, 2)
                sidebar_layout.addWidget(section)

            icon = texts_es.STEP_ICONS.get(step.value, "")
            button = QPushButton(f"{icon} {step.display_name}", self.sidebar)
            button.setObjectName("stepButton")
            button.setProperty("step", step.value)
            button.setProperty("subStep", "true" if step in CLEANING_STEPS else "false")
            button.setProperty("active", "false")
            button.setProperty("locked", "false")
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(
                lambda _checked=False, target=step: self._navigate(target)  # noqa: B023
            )
            self.step_buttons[step] = button
            sidebar_layout.addWidget(button)

    def _create_views(self) -> None:
        """Instancia las vistas de cada paso y las monta en el `QStackedWidget`."""
        self.load_view = Step1LoadView(self.controller, self.content_stack)
        self.info_view = Step2InfoView(self.controller, self.content_stack)
        self.preview_view = Step3PreviewView(self.controller, self.content_stack)
        self.types_view = Step4TypesView(self.controller, self.content_stack)
        self.cleaning_view = Step5CleaningView(self.controller, self.content_stack)
        self.export_view = ExportView(self.controller, self.content_stack)

        for widget in (
            self.load_view,
            self.info_view,
            self.preview_view,
            self.types_view,
            self.cleaning_view,
            self.export_view,
        ):
            self.content_stack.addWidget(widget)

        self.content_stack.setCurrentWidget(self.load_view)

    def _connect_signals(self) -> None:
        """Conecta la máquina de estados con la navegación y la sidebar."""
        self.controller.step_changed.connect(self._on_step_changed)
        self.controller.step_completed.connect(self._on_flow_changed)
        self.controller.steps_invalidated.connect(self._on_flow_changed)
        self.controller.state_reset.connect(self._on_state_reset)

    # -- Navegación -------------------------------------------------------- #

    def _wrapper_for(self, step: Step) -> QWidget:
        """Devuelve la página del `QStackedWidget` que muestra un paso dado."""
        if step in CLEANING_STEPS:
            return self.cleaning_view
        mapping = {
            Step.LOAD: self.load_view,
            Step.INFO: self.info_view,
            Step.PREVIEW: self.preview_view,
            Step.TYPES: self.types_view,
            Step.EXPORT: self.export_view,
        }
        return mapping[step]

    def _navigate(self, step: Step) -> None:
        """Navega al paso elegido en la sidebar si está desbloqueado."""
        try:
            self.controller.go_to(step)
        except StepLockedError:
            logger.debug("Navegación bloqueada hacia %s", step)
            return

    def _on_step_changed(self, step: Step) -> None:
        """Muestra la vista correspondiente y refresca su contenido."""
        self.content_stack.setCurrentWidget(self._wrapper_for(step))
        self._refresh_view(step)
        self._sync_sidebar()
        self._sync_history_buttons()

    def _on_flow_changed(self, _payload: object) -> None:
        """Reacciona a pasos completados o invalidados (sidebar, progreso e historial)."""
        self._sync_sidebar()
        self._sync_history_buttons()

    def _on_state_reset(self) -> None:
        """Vuelve al inicio cuando se carga un dataset nuevo."""
        self.content_stack.setCurrentWidget(self.load_view)
        self.export_view.refresh()
        self._refresh_all()
        self._sync_sidebar()
        self._sync_history_buttons()

    def _refresh_view(self, step: Step) -> None:
        """Refresca la vista del paso indicado (los datos pueden haber cambiado)."""
        if step in CLEANING_STEPS:
            # El contenedor del paso 5 ya reacciona por su cuenta a `step_changed`.
            self.cleaning_view.refresh()
            return

        view = self._wrapper_for(step)
        refresh = getattr(view, "refresh", None)
        if callable(refresh):
            refresh()

    def _refresh_all(self) -> None:
        """Refresca todas las vistas que muestran datos del dataset de trabajo."""
        for view in (self.info_view, self.preview_view, self.types_view):
            view.refresh()
        self.cleaning_view.refresh()
        self.export_view.refresh()

    # -- Historial --------------------------------------------------------- #

    def _sync_history_buttons(self) -> None:
        """Habilita deshacer/restaurar según el estado del historial y los datos."""
        state = self.controller.state
        can_undo = state.history.can_undo
        self.undo_button.setEnabled(can_undo)
        self.undo_button.setToolTip(
            texts_es.TOOLTIP_UNDO if can_undo else texts_es.TOOLTIP_UNDO_DISABLED
        )

        can_restore = state.original_df is not None
        self.restore_button.setEnabled(can_restore)
        self.restore_button.setToolTip(
            texts_es.TOOLTIP_RESTORE_ORIGINAL
            if can_restore
            else texts_es.TOOLTIP_RESTORE_DISABLED
        )

    def _on_undo(self) -> None:
        """Deshace la última acción y vuelve a bloquear los sub-pasos A–E."""
        state = self.controller.state
        df = state.history.undo()
        if df is None:
            QMessageBox.information(self, texts_es.UNDO_NOTHING_TITLE, texts_es.UNDO_NOTHING_MSG)
            return

        state.working_df = df
        self._rewind_cleaning()
        self._refresh_all()
        self._sync_sidebar()
        self._sync_history_buttons()

    def _on_restore_original(self) -> None:
        """Descarta los cambios aplicados y restaura una copia del dataset original."""
        state = self.controller.state
        if state.original_df is None:
            return

        answer = QMessageBox.question(
            self,
            texts_es.RESTORE_CONFIRM_TITLE,
            texts_es.RESTORE_CONFIRM_MSG,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        state.working_df = state.history.restore_original(state.original_df)
        self._rewind_cleaning()
        self._refresh_all()
        self._sync_sidebar()
        self._sync_history_buttons()

    def _rewind_cleaning(self) -> None:
        """Invalida A–E y regresa al inicio de la limpieza si ya se había pasado de ahí."""
        self.controller.invalidate_from(Step.CLEAN_A, inclusive=True)
        current_index = STEP_ORDER.index(self.controller.state.current)
        if current_index >= STEP_ORDER.index(Step.CLEAN_A):
            try:
                self.controller.go_to(Step.CLEAN_A)
            except StepLockedError:  # pragma: no cover - los pasos previos siguen completos
                logger.debug("No se pudo regresar a CLEAN_A tras deshacer.")

    # -- Sidebar ----------------------------------------------------------- #

    def _sync_sidebar(self) -> None:
        """Actualiza botones (activo/bloqueado/completado) y la barra de progreso."""
        state = self.controller.state

        for step, button in self.step_buttons.items():
            enabled = self.controller.can_enter(step)
            active = step == state.current
            completed = state.is_completed(step)

            text = f"{texts_es.STEP_ICONS.get(step.value, '')} {step.display_name}"
            if completed:
                text += texts_es.CLEAN_TAB_COMPLETED_SUFFIX

            button.setText(text)
            button.setEnabled(enabled)
            button.setProperty("active", "true" if active else "false")
            button.setProperty("locked", "false" if enabled else "true")
            button.setToolTip(self._step_tooltip(step, enabled, completed))
            _repolish(button)

        self.progress_bar.setValue(len(state.completed))

    def _step_tooltip(self, step: Step, enabled: bool, completed: bool) -> str:
        """Tooltip explicativo: completado, disponible o bloqueado con el paso pendiente."""
        if not enabled:
            pending = self._first_pending_step(step)
            name = pending.display_name if pending is not None else step.display_name
            return texts_es.TOOLTIP_STEP_LOCKED.format(step_name=name)
        if completed:
            return texts_es.TOOLTIP_STEP_COMPLETED.format(step_name=step.display_name)
        return step.display_name

    def _first_pending_step(self, step: Step) -> Step | None:
        """Primer paso previo sin completar (motivo del bloqueo)."""
        index = STEP_ORDER.index(step)
        for previous in STEP_ORDER[:index]:
            if not self.controller.state.is_completed(previous):
                return previous
        return None


def _repolish(widget: QWidget) -> None:
    """Reaplica el QSS tras cambiar propiedades dinámicas (active/locked)."""
    style = widget.style()
    if style is not None:
        style.unpolish(widget)
        style.polish(widget)
    widget.update()


def main() -> int:
    """Punto de entrada de la interfaz gráfica."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
