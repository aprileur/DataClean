"""Vista final del flujo: exportación del dataset limpio y resumen del historial."""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.services.exporter import ExportError, export_dataset, generate_export_path
from app.state import Step, StepLockedError, WorkflowController
from app.ui import texts_es
from app.widgets import PrimaryButton, StepHeader

logger = logging.getLogger(__name__)

#: Formatos disponibles: (texto visible, extensión).
EXPORT_FORMATS: tuple[tuple[str, str], ...] = (
    (texts_es.EXPORT_FORMAT_CSV, ".csv"),
    (texts_es.EXPORT_FORMAT_EXCEL, ".xlsx"),
    (texts_es.EXPORT_FORMAT_PARQUET, ".parquet"),
)

#: Filtro del diálogo de guardado por extensión.
EXPORT_FILTERS: dict[str, str] = {
    ".csv": texts_es.EXPORT_FILE_FILTER_CSV,
    ".xlsx": texts_es.EXPORT_FILE_FILTER_EXCEL,
    ".parquet": texts_es.EXPORT_FILE_FILTER_PARQUET,
}


class ExportView(QWidget):
    """Paso final: resumen de acciones y exportación en CSV, Excel o Parquet."""

    def __init__(self, controller: WorkflowController, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.controller = controller

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        self.header = StepHeader(texts_es.EXPORT_BADGE, texts_es.EXPORT_TITLE, parent=self)

        self.summary_title = QLabel(texts_es.EXPORT_SUMMARY_TITLE, self)
        self.summary_title.setObjectName("summaryTitle")

        self.summary_list = QListWidget(self)
        self.summary_list.setObjectName("exportSummary")
        self.summary_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self.summary_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        format_row = QHBoxLayout()
        format_row.setContentsMargins(0, 0, 0, 0)
        format_row.setSpacing(10)

        self.format_label = QLabel(texts_es.EXPORT_FORMAT_LABEL, self)
        self.format_combo = QComboBox(self)
        self.format_combo.setObjectName("exportFormatCombo")
        for label, extension in EXPORT_FORMATS:
            self.format_combo.addItem(label, extension)

        format_row.addWidget(self.format_label)
        format_row.addWidget(self.format_combo)
        format_row.addStretch()

        nav_row = QHBoxLayout()
        nav_row.setContentsMargins(0, 0, 0, 0)
        nav_row.setSpacing(10)

        self.back_button = QPushButton(texts_es.BTN_BACK, self)
        self.back_button.clicked.connect(self._on_back)

        self.export_button = PrimaryButton(texts_es.EXPORT_BTN, self)
        self.export_button.clicked.connect(self._on_export)

        nav_row.addWidget(self.back_button)
        nav_row.addStretch()
        nav_row.addWidget(self.export_button)

        layout.addWidget(self.header)
        layout.addWidget(self.summary_title)
        layout.addWidget(self.summary_list, 1)
        layout.addLayout(format_row)
        layout.addLayout(nav_row)

        self.controller.step_completed.connect(self._on_step_state_changed)
        self.controller.steps_invalidated.connect(self._on_step_state_changed)
        self.controller.state_reset.connect(self.refresh)

        self.refresh()

    # -- API pública ------------------------------------------------------- #

    @property
    def can_export(self) -> bool:
        """True si el flujo permite entrar al paso de exportación."""
        return self.controller.can_enter(Step.EXPORT)

    @property
    def selected_extension(self) -> str:
        """Extensión del formato elegido (con punto, en minúsculas)."""
        data = self.format_combo.currentData()
        return str(data) if data else ".csv"

    def refresh(self) -> None:
        """Actualiza el resumen del historial y el estado del botón de exportación."""
        self._refresh_summary()

        enabled = self.can_export and self.controller.state.working_df is not None
        self.export_button.setEnabled(enabled)
        self.export_button.setToolTip(
            texts_es.EXPORT_READY_TOOLTIP if enabled else texts_es.EXPORT_LOCKED_TOOLTIP
        )

    # -- Exportación ------------------------------------------------------- #

    def suggested_path(self) -> Path:
        """Ruta de destino sugerida `<stem>_nuevo.<ext>` para el formato actual."""
        state = self.controller.state
        extension = self.selected_extension
        if state.file_path is not None:
            return generate_export_path(state.file_path, extension)
        return Path.cwd() / f"{texts_es.EXPORT_DEFAULT_STEM}_nuevo{extension}"

    def _on_export(self) -> None:
        """Pide la ruta destino y exporta el dataset de trabajo (nunca lo modifica)."""
        state = self.controller.state
        df = state.working_df
        if df is None or not self.can_export:
            return

        extension = self.selected_extension
        target, _selected_filter = QFileDialog.getSaveFileName(
            self,
            texts_es.EXPORT_DIALOG_TITLE,
            str(self.suggested_path()),
            EXPORT_FILTERS.get(extension, texts_es.EXPORT_FILE_FILTER_CSV),
        )
        if not target:
            return

        try:
            exported = export_dataset(df, Path(target))
        except ExportError as exc:
            logger.warning("No se pudo exportar el dataset: %s", exc)
            QMessageBox.warning(self, texts_es.EXPORT_ERR_TITLE, str(exc))
            return
        except Exception:  # noqa: BLE001 - se traduce a un mensaje amigable
            logger.exception("Error inesperado al exportar el dataset")
            QMessageBox.critical(self, texts_es.EXPORT_ERR_TITLE, texts_es.ERROR_UNEXPECTED_MSG)
            return

        QMessageBox.information(
            self,
            texts_es.EXPORT_SUCCESS_TITLE,
            texts_es.EXPORT_SUCCESS_MSG.format(path=exported),
        )

    # -- Navegación -------------------------------------------------------- #

    def _on_back(self) -> None:
        """Regresa al último sub-paso de limpieza (retroceder siempre es libre)."""
        try:
            self.controller.go_to(Step.CLEAN_E)
        except StepLockedError:
            return

    # -- Utilidades internas ----------------------------------------------- #

    def _refresh_summary(self) -> None:
        """Lista las acciones aplicadas, en orden, omitiendo el snapshot base."""
        self.summary_list.clear()
        descriptions = self.controller.state.history.descriptions()
        actions = descriptions[1:] if descriptions else []
        if not actions:
            self.summary_list.addItem(texts_es.EXPORT_NO_ACTIONS)
            return
        self.summary_list.addItems(actions)

    def _on_step_state_changed(self, _payload: object) -> None:
        """Mantiene el botón sincronizado con el estado del flujo."""
        self.refresh()
