"""Vista del sub-paso 5E: errores tipográficos en columnas categóricas.

Detecta variantes parecidas con `rapidfuzz` (a través del servicio de
limpieza) y propone un valor canónico por variante. El usuario acepta o
rechaza cada propuesta antes de aplicar las fusiones.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
)

from app.services.cleaning import apply_merges, suggest_merges
from app.services.profiling import classify_columns
from app.state import Step, WorkflowController
from app.ui import texts_es
from app.views.step5_cleaning.base import CleaningStepView
from app.widgets import PrimaryButton

#: Similitud mínima por defecto para sugerir fusiones.
DEFAULT_CUTOFF = 85

#: Índices de columna de la tabla de propuestas.
ACCEPT_COL = 0
VARIANT_COL = 1
CANONICAL_COL = 2
COUNT_COL = 3
SCORE_COL = 4


class TyposView(CleaningStepView):
    """Vista del sub-paso E: propuestas de fusión de variantes tipográficas."""

    step = Step.CLEAN_E
    step_letter = "E"
    step_title = texts_es.STEP_5E_NAME

    def __init__(self, controller: WorkflowController, parent: QWidget | None = None) -> None:
        super().__init__(controller, parent)
        self._resolved: set[str] = set()

        self.column_label = QLabel(texts_es.TYPOS_COL_SELECT, self)
        self.column_combo = QComboBox(self)

        self.similarity_label = QLabel(texts_es.TYPOS_SIMILARITY_LABEL, self)
        self.similarity_spin = QSpinBox(self)
        self.similarity_spin.setRange(0, 100)
        self.similarity_spin.setValue(DEFAULT_CUTOFF)
        self.similarity_spin.setSuffix(texts_es.TYPOS_SIMILARITY_SUFFIX)

        controls_row = QHBoxLayout()
        controls_row.setContentsMargins(0, 0, 0, 0)
        controls_row.setSpacing(8)
        controls_row.addWidget(self.column_label)
        controls_row.addWidget(self.column_combo)
        controls_row.addSpacing(16)
        controls_row.addWidget(self.similarity_label)
        controls_row.addWidget(self.similarity_spin)
        controls_row.addStretch()

        self.proposals_title = QLabel(texts_es.TYPOS_PROPOSALS_TITLE, self)

        self.proposals_table = QTableWidget(0, 5, self)
        self.proposals_table.setHorizontalHeaderLabels(
            [
                texts_es.TYPOS_TABLE_ACCEPT,
                texts_es.TYPOS_TABLE_VARIANT,
                texts_es.TYPOS_TABLE_CANONICAL,
                texts_es.TYPOS_TABLE_COUNT,
                texts_es.TYPOS_TABLE_SCORE,
            ]
        )
        self.proposals_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.proposals_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.proposals_table.setAlternatingRowColors(True)
        self.proposals_table.verticalHeader().setVisible(False)

        header = self.proposals_table.horizontalHeader()
        header.setSectionResizeMode(ACCEPT_COL, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(VARIANT_COL, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(CANONICAL_COL, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(COUNT_COL, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(SCORE_COL, QHeaderView.ResizeMode.ResizeToContents)

        self.no_issues_label = QLabel(texts_es.CLEAN_NO_ISSUES_FOUND, self)
        self.no_issues_label.setObjectName("cleanNoIssuesLabel")
        self.no_issues_label.setVisible(False)

        self.no_columns_label = QLabel(texts_es.TYPOS_NO_COLUMNS, self)
        self.no_columns_label.setVisible(False)

        self.apply_button = PrimaryButton(texts_es.TYPOS_BTN_APPLY, self)
        self.apply_button.setEnabled(False)
        self.apply_button.clicked.connect(self.apply_selected_merges)

        self.discard_button = PrimaryButton(texts_es.TYPOS_BTN_DISCARD, self)
        self.discard_button.clicked.connect(self.discard_proposals)

        actions_row = QHBoxLayout()
        actions_row.setContentsMargins(0, 0, 0, 0)
        actions_row.setSpacing(10)
        actions_row.addWidget(self.apply_button)
        actions_row.addWidget(self.discard_button)
        actions_row.addStretch()

        self.body_layout.addLayout(controls_row)
        self.body_layout.addWidget(self.proposals_title)
        self.body_layout.addWidget(self.proposals_table, 1)
        self.body_layout.addWidget(self.no_issues_label)
        self.body_layout.addWidget(self.no_columns_label)
        self.body_layout.addLayout(actions_row)

        self.column_combo.currentIndexChanged.connect(self._on_column_changed)
        self.similarity_spin.valueChanged.connect(self._on_similarity_changed)

        self.refresh()

    # -- API pública ------------------------------------------------------- #

    def refresh(self) -> None:
        """Recalcula las columnas categóricas y las propuestas de la columna activa."""
        df = self.dataframe
        if df is None:
            self.column_combo.blockSignals(True)
            self.column_combo.clear()
            self.column_combo.blockSignals(False)
            self.proposals_table.setRowCount(0)
            self.no_issues_label.setVisible(False)
            self.no_columns_label.setVisible(False)
            self.apply_button.setEnabled(False)
            self.discard_button.setEnabled(False)
            return

        columns = classify_columns(df).categorical
        self.no_columns_label.setVisible(not columns)
        self._rebuild_columns(columns)

        if not columns:
            self.proposals_table.setRowCount(0)
            self.apply_button.setEnabled(False)
            self.discard_button.setEnabled(False)
            self.complete_if_no_issues(has_issues=False)
            return

        self._populate_proposals()

        has_any = any(self._has_suggestions(column) for column in columns)
        self.no_issues_label.setVisible(not has_any)
        self.complete_if_no_issues(has_issues=has_any)
        self._maybe_complete()

    def selected_column(self) -> str:
        """Columna categórica activa (o cadena vacía)."""
        return str(self.column_combo.currentText())

    def selected_mapping(self) -> dict[str, str]:
        """Mapeo `{variante: canónico}` de las filas marcadas en la tabla."""
        mapping: dict[str, str] = {}
        for row in range(self.proposals_table.rowCount()):
            accept = self.proposals_table.item(row, ACCEPT_COL)
            variant = self.proposals_table.item(row, VARIANT_COL)
            canonical = self.proposals_table.item(row, CANONICAL_COL)
            if (
                accept is not None
                and variant is not None
                and canonical is not None
                and accept.checkState() == Qt.CheckState.Checked
            ):
                mapping[variant.text()] = canonical.text()
        return mapping

    def apply_selected_merges(self) -> None:
        """Aplica las fusiones aceptadas y marca la columna como revisada."""
        df = self.dataframe
        column = self.selected_column()
        if df is None or not column:
            return

        mapping = self.selected_mapping()
        if not mapping:
            return

        new_df = apply_merges(df, column, mapping)
        self._resolved.add(column)
        description = texts_es.TYPOS_HISTORY_APPLY.format(column=column, count=len(mapping))
        self.apply_result(new_df, description)

    def discard_proposals(self) -> None:
        """Descarta las propuestas de la columna activa sin modificar los datos."""
        column = self.selected_column()
        if not column:
            return
        self._resolved.add(column)
        self.show_status(texts_es.TYPOS_COLUMN_REVIEWED.format(column=column))
        self._update_apply_button()
        self._maybe_complete()

    def reset_diagnostics(self) -> None:
        """Olvida las columnas revisadas al reiniciar el flujo."""
        self._resolved.clear()
        super().reset_diagnostics()

    # -- Utilidades internas ----------------------------------------------- #

    def _rebuild_columns(self, columns: list[str]) -> None:
        """Reconstruye el combo de columnas categóricas conservando la selección."""
        previous = self.column_combo.currentText()
        self.column_combo.blockSignals(True)
        try:
            self.column_combo.clear()
            self.column_combo.addItems(columns)
            if previous in columns:
                self.column_combo.setCurrentText(previous)
        finally:
            self.column_combo.blockSignals(False)

    def _populate_proposals(self) -> None:
        """Llena la tabla con las propuestas de la columna activa."""
        df = self.dataframe
        column = self.selected_column()
        if df is None or not column or column not in df.columns:
            self.proposals_table.setRowCount(0)
            self._update_apply_button()
            return

        suggestions = suggest_merges(df[column], cutoff=float(self.similarity_spin.value()))
        if not suggestions:
            self._resolved.add(column)
            self.show_status(texts_es.TYPOS_NO_SUGGESTIONS)

        self.proposals_table.setRowCount(len(suggestions))
        for row, (variant, canonical, count, score) in enumerate(suggestions):
            accept_item = QTableWidgetItem("")
            accept_item.setFlags(
                Qt.ItemFlag.ItemIsUserCheckable
                | Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsSelectable
            )
            accept_item.setCheckState(Qt.CheckState.Checked)
            self.proposals_table.setItem(row, ACCEPT_COL, accept_item)

            variant_item = QTableWidgetItem(str(variant))
            variant_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self.proposals_table.setItem(row, VARIANT_COL, variant_item)

            canonical_item = QTableWidgetItem(str(canonical))
            canonical_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self.proposals_table.setItem(row, CANONICAL_COL, canonical_item)

            count_item = QTableWidgetItem(f"{count:,}")
            count_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            count_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.proposals_table.setItem(row, COUNT_COL, count_item)

            score_item = QTableWidgetItem(f"{score:.1f}")
            score_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            score_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.proposals_table.setItem(row, SCORE_COL, score_item)

        self._update_apply_button()

    def _update_apply_button(self) -> None:
        """Habilita el botón de aplicar solo si hay filas para fusionar."""
        self.apply_button.setEnabled(self.proposals_table.rowCount() > 0)
        self.discard_button.setEnabled(self.proposals_table.rowCount() > 0)

    def _on_column_changed(self) -> None:
        """Repuebla las propuestas al cambiar de columna."""
        self.show_status("")
        self._populate_proposals()
        self._maybe_complete()

    def _on_similarity_changed(self, _value: int) -> None:
        """Repuebla las propuestas al cambiar la similitud mínima."""
        self._resolved.clear()
        self._populate_proposals()
        self._maybe_complete()

    def _has_suggestions(self, column: str) -> bool:
        """Indica si una columna tiene propuestas con la similitud actual."""
        df = self.dataframe
        if df is None or column not in df.columns:
            return False
        return bool(suggest_merges(df[column], cutoff=float(self.similarity_spin.value())))

    def _maybe_complete(self) -> None:
        """Completa el sub-paso cuando todas las columnas categóricas están resueltas."""
        df = self.dataframe
        if df is None:
            return

        columns = classify_columns(df).categorical
        if not columns:
            self.complete_if_no_issues(has_issues=False)
            return

        pending = [
            column
            for column in columns
            if column not in self._resolved and self._has_suggestions(column)
        ]
        if not pending and not self.is_completed:
            self.mark_completed()
