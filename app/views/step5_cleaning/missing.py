"""Vista del sub-paso 5A: datos faltantes.

Muestra el diagnóstico por columna, el impacto real de eliminar registros
(unión de filas, no suma de faltantes) y un mapa de calor de la máscara de
nulos. Las acciones destructivas piden confirmación y toda la lógica de datos
vive en `app.services.cleaning`.
"""

from __future__ import annotations

import logging

import pandas as pd
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from app.services.cleaning import (
    HEATMAP_MAX_ROWS,
    UNKNOWN_VALUE,
    CleaningError,
    drop_missing_rows,
    heatmap_sample,
    impute_column,
    missing_report,
    missing_union,
)
from app.state import Step, WorkflowController
from app.ui import texts_es
from app.views.step5_cleaning.base import CleaningStepView
from app.widgets import DangerButton, PrimaryButton, WarningBanner
from app.widgets.dataframe_table import DataFrameTable
from app.widgets.heatmap import MissingDataHeatmap

logger = logging.getLogger(__name__)


class ImputationDialog(QDialog):
    """Diálogo que pide la columna, la estrategia y el valor de imputación."""

    def __init__(self, df: pd.DataFrame, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(texts_es.MISSING_IMPUTE_DIALOG_TITLE)
        self._df = df

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.column_combo = QComboBox(self)
        columns = [str(col) for col in df.columns if bool(df[col].isna().any())]
        self.column_combo.addItems(columns)

        self.strategy_combo = QComboBox(self)
        self.value_edit = QLineEdit(self)
        self.value_edit.setPlaceholderText(UNKNOWN_VALUE)

        self.column_label = QLabel(texts_es.MISSING_IMPUTE_COLUMN_LABEL, self)
        self.strategy_label = QLabel(texts_es.MISSING_IMPUTE_STRATEGY_LABEL, self)
        self.value_label = QLabel(texts_es.MISSING_IMPUTE_VALUE_LABEL, self)

        form.addRow(self.column_label, self.column_combo)
        form.addRow(self.strategy_label, self.strategy_combo)
        form.addRow(self.value_label, self.value_edit)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        ok_button = self.buttons.button(QDialogButtonBox.StandardButton.Ok)
        cancel_button = self.buttons.button(QDialogButtonBox.StandardButton.Cancel)
        if ok_button is not None:
            ok_button.setText(texts_es.BTN_APPLY)
        if cancel_button is not None:
            cancel_button.setText(texts_es.BTN_CANCEL)

        layout.addLayout(form)
        layout.addWidget(self.buttons)

        self.column_combo.currentIndexChanged.connect(self._rebuild_strategies)
        self.strategy_combo.currentIndexChanged.connect(self._update_value_visibility)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        self._rebuild_strategies()
        self._update_value_visibility()

    # -- API pública ------------------------------------------------------- #

    def result_values(self) -> tuple[str, str, str | None]:
        """Devuelve `(columna, estrategia, valor_constante)` elegidos por el usuario."""
        strategy = str(self.strategy_combo.currentData())
        value = self.value_edit.text().strip() or None
        return str(self.column_combo.currentText()), strategy, value

    # -- Utilidades internas ----------------------------------------------- #

    def _rebuild_strategies(self) -> None:
        """Muestra solo las estrategias válidas para el tipo de la columna."""
        column = self.column_combo.currentText()
        numeric = column in self._df.columns and pd.api.types.is_numeric_dtype(
            self._df[column].dtype
        )

        current = self.strategy_combo.currentData()
        self.strategy_combo.blockSignals(True)
        try:
            self.strategy_combo.clear()
            if numeric:
                self.strategy_combo.addItem(texts_es.MISSING_STRATEGY_MEAN, "mean")
                self.strategy_combo.addItem(texts_es.MISSING_STRATEGY_MEDIAN, "median")
            self.strategy_combo.addItem(texts_es.MISSING_STRATEGY_MODE, "mode")
            self.strategy_combo.addItem(texts_es.MISSING_STRATEGY_CONSTANT, "constant")

            if current is not None:
                index = self.strategy_combo.findData(current)
                if index >= 0:
                    self.strategy_combo.setCurrentIndex(index)
        finally:
            self.strategy_combo.blockSignals(False)

        self._update_value_visibility()

    def _update_value_visibility(self) -> None:
        """Muestra el campo de valor solo cuando la estrategia es constante."""
        is_constant = self.strategy_combo.currentData() == "constant"
        self.value_label.setVisible(is_constant)
        self.value_edit.setVisible(is_constant)

    def selected_strategy_text(self) -> str:
        """Texto visible de la estrategia seleccionada (para el historial)."""
        return str(self.strategy_combo.currentText())


class MissingView(CleaningStepView):
    """Vista del sub-paso A: diagnóstico, mapa de calor y acciones de faltantes."""

    step = Step.CLEAN_A
    step_letter = "A"
    step_title = texts_es.STEP_5A_NAME

    def __init__(self, controller: WorkflowController, parent: QWidget | None = None) -> None:
        super().__init__(controller, parent)

        self.view_all_checkbox = QCheckBox(texts_es.MISSING_VIEW_ALL, self)
        self.view_all_checkbox.toggled.connect(self.refresh)

        self.table = DataFrameTable(parent=self)

        self.heatmap = MissingDataHeatmap(parent=self)
        self.heatmap.setMinimumHeight(180)

        self.splitter = QSplitter(Qt.Orientation.Vertical, self)
        self.splitter.addWidget(self.table)
        self.splitter.addWidget(self.heatmap)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 1)

        self.banner = WarningBanner(parent=self)
        self.banner.setVisible(False)

        self.no_issues_label = QLabel(texts_es.CLEAN_NO_ISSUES_FOUND, self)
        self.no_issues_label.setObjectName("cleanNoIssuesLabel")
        self.no_issues_label.setVisible(False)

        actions_row = QHBoxLayout()
        actions_row.setContentsMargins(0, 0, 0, 0)
        actions_row.setSpacing(10)

        self.drop_button = DangerButton(texts_es.MISSING_BTN_DROP, self)
        self.drop_button.clicked.connect(self.drop_rows)

        self.impute_button = PrimaryButton(texts_es.MISSING_BTN_IMPUTE, self)
        self.impute_button.clicked.connect(self.open_imputation_dialog)

        actions_row.addWidget(self.drop_button)
        actions_row.addWidget(self.impute_button)
        actions_row.addStretch()

        self.body_layout.addWidget(self.view_all_checkbox)
        self.body_layout.addWidget(self.splitter, 1)
        self.body_layout.addWidget(self.banner)
        self.body_layout.addWidget(self.no_issues_label)
        self.body_layout.addLayout(actions_row)

        self.refresh()

    # -- API pública ------------------------------------------------------- #

    def refresh(self) -> None:
        """Recalcula el reporte, el banner y el mapa de calor."""
        df = self.dataframe
        if df is None:
            self.table.set_dataframe(None)
            self.banner.setVisible(False)
            self.no_issues_label.setVisible(False)
            self.drop_button.setEnabled(False)
            self.impute_button.setEnabled(False)
            self.heatmap.clear()
            return

        report = missing_report(df, only_with_missing=not self.view_all_checkbox.isChecked())
        display = report.rename(
            columns={
                "columna": texts_es.MISSING_TABLE_COL,
                "faltantes": texts_es.MISSING_TABLE_COUNT,
                "porcentaje": texts_es.MISSING_TABLE_PCT,
            }
        )
        self.table.set_dataframe(display)

        count, pct = missing_union(df)
        has_missing = count > 0
        self.banner.setVisible(has_missing)
        if has_missing:
            self.banner.set_message(texts_es.MISSING_BANNER_WARNING.format(count=count, pct=pct))

        self.drop_button.setEnabled(has_missing)
        self.impute_button.setEnabled(has_missing)
        self.no_issues_label.setVisible(not has_missing)

        mask = heatmap_sample(df, max_rows=HEATMAP_MAX_ROWS)
        self.heatmap.set_data(mask, is_sample=len(df) > HEATMAP_MAX_ROWS, total_rows=len(df))

        self.complete_if_no_issues(has_missing)

    def drop_rows(self) -> None:
        """Elimina las filas con algún faltante, previa confirmación con el conteo exacto."""
        df = self.dataframe
        if df is None:
            return
        count, pct = missing_union(df)
        if count == 0:
            return

        answer = QMessageBox.question(
            self,
            texts_es.MISSING_DROP_CONFIRM_TITLE,
            texts_es.MISSING_DROP_CONFIRM_MSG.format(count=count, pct=pct),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        self.apply_result(drop_missing_rows(df), texts_es.MISSING_HISTORY_DROP)

    def open_imputation_dialog(self) -> None:
        """Abre el diálogo de imputación y aplica la estrategia elegida."""
        df = self.dataframe
        if df is None:
            return

        dialog = ImputationDialog(df, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        column, strategy, value = dialog.result_values()
        try:
            new_df = impute_column(df, column, strategy, value)
        except CleaningError as exc:
            logger.warning("No se pudo imputar la columna %r: %s", column, exc)
            QMessageBox.warning(self, texts_es.MISSING_IMPUTE_DIALOG_TITLE, str(exc))
            return

        description = texts_es.MISSING_HISTORY_IMPUTE.format(
            column=column, strategy=dialog.selected_strategy_text()
        )
        self.apply_result(new_df, description)
