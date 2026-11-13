"""Vista del sub-paso 5C: registros duplicados.

Permite elegir el subconjunto de columnas que define un duplicado y cuál de
las copias conservar. El conteo y la eliminación los calcula
`app.services.cleaning`; la vista solo confirma el impacto exacto.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMessageBox,
    QRadioButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from app.services.cleaning import (
    count_duplicates,
    get_duplicate_examples,
)
from app.services.cleaning import (
    drop_duplicates as drop_duplicate_rows,
)
from app.state import Step, WorkflowController
from app.ui import texts_es
from app.views.step5_cleaning.base import CleaningStepView
from app.widgets import DangerButton
from app.widgets.dataframe_table import DataFrameTable

#: Máximo de filas mostradas como ejemplo de duplicados.
MAX_EXAMPLE_ROWS = 20


class DuplicatesView(CleaningStepView):
    """Vista del sub-paso C: diagnóstico y eliminación de duplicados."""

    step = Step.CLEAN_C
    step_letter = "C"
    step_title = texts_es.STEP_5C_NAME

    def __init__(self, controller: WorkflowController, parent: QWidget | None = None) -> None:
        super().__init__(controller, parent)

        self.count_label = QLabel("", self)
        self.count_label.setObjectName("duplicatesCountLabel")

        self.columns_label = QLabel(texts_es.DUPLICATES_COLUMNS_LABEL, self)

        self.columns_list = QListWidget(self)
        self.columns_list.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self.columns_list.itemSelectionChanged.connect(self._update_diagnosis)

        self.keep_label = QLabel(texts_es.DUPLICATES_KEEP_LABEL, self)
        self.keep_first = QRadioButton(texts_es.DUPLICATES_KEEP_FIRST, self)
        self.keep_last = QRadioButton(texts_es.DUPLICATES_KEEP_LAST, self)
        self.keep_first.setChecked(True)

        keep_row = QHBoxLayout()
        keep_row.setContentsMargins(0, 0, 0, 0)
        keep_row.setSpacing(10)
        keep_row.addWidget(self.keep_label)
        keep_row.addWidget(self.keep_first)
        keep_row.addWidget(self.keep_last)
        keep_row.addStretch()

        self.examples_label = QLabel(texts_es.DUPLICATES_EXAMPLES_TITLE, self)
        self.examples_table = DataFrameTable(parent=self)

        self.no_issues_label = QLabel(texts_es.CLEAN_NO_ISSUES_FOUND, self)
        self.no_issues_label.setObjectName("cleanNoIssuesLabel")
        self.no_issues_label.setVisible(False)

        self.drop_button = DangerButton(texts_es.DUPLICATES_BTN_DROP, self)
        self.drop_button.setEnabled(False)
        self.drop_button.clicked.connect(self.drop_duplicates)

        actions_row = QHBoxLayout()
        actions_row.setContentsMargins(0, 0, 0, 0)
        actions_row.addWidget(self.drop_button)
        actions_row.addStretch()

        columns_panel = QWidget(self)
        columns_layout = QVBoxLayout(columns_panel)
        columns_layout.setContentsMargins(0, 0, 0, 0)
        columns_layout.setSpacing(6)
        columns_layout.addWidget(self.columns_label)
        columns_layout.addWidget(self.columns_list, 1)

        examples_panel = QWidget(self)
        examples_layout = QVBoxLayout(examples_panel)
        examples_layout.setContentsMargins(0, 0, 0, 0)
        examples_layout.setSpacing(6)
        examples_layout.addWidget(self.examples_label)
        examples_layout.addWidget(self.examples_table, 1)

        self.splitter = QSplitter(Qt.Orientation.Horizontal, self)
        self.splitter.addWidget(columns_panel)
        self.splitter.addWidget(examples_panel)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 2)

        self.body_layout.addWidget(self.count_label)
        self.body_layout.addWidget(self.splitter, 1)
        self.body_layout.addLayout(keep_row)
        self.body_layout.addWidget(self.no_issues_label)
        self.body_layout.addLayout(actions_row)

        self.keep_first.toggled.connect(self._update_diagnosis)
        self.keep_last.toggled.connect(self._update_diagnosis)

        self.refresh()

    # -- API pública ------------------------------------------------------- #

    def refresh(self) -> None:
        """Reconstruye la lista de columnas y actualiza el diagnóstico."""
        df = self.dataframe
        if df is None:
            self.count_label.setText(texts_es.DUPLICATES_COUNT_LABEL.format(count=0))
            self.no_issues_label.setVisible(False)
            self.examples_table.set_dataframe(None)
            self.drop_button.setEnabled(False)
            self._rebuild_columns(None)
            return

        self._rebuild_columns(df)
        self._update_diagnosis()

        total = count_duplicates(df)
        self.complete_if_no_issues(total > 0)
        self.no_issues_label.setVisible(total == 0)

    def selected_columns(self) -> list[str]:
        """Columnas seleccionadas para comparar (o lista vacía si no hay ninguna)."""
        return [item.text() for item in self.columns_list.selectedItems()]

    def drop_duplicates(self) -> None:
        """Elimina los duplicados del subconjunto actual tras confirmar el conteo."""
        df = self.dataframe
        if df is None:
            return

        subset = self.selected_columns()
        if not subset:
            return

        count = count_duplicates(df, subset=subset)
        if count == 0:
            return

        answer = QMessageBox.question(
            self,
            texts_es.DUPLICATES_CONFIRM_TITLE,
            texts_es.DUPLICATES_CONFIRM_MSG.format(count=count),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        keep = "last" if self.keep_last.isChecked() else "first"
        new_df = drop_duplicate_rows(df, subset=subset, keep=keep)
        description = texts_es.DUPLICATES_HISTORY_DROP.format(count=count)
        self.apply_result(new_df, description)

    # -- Utilidades internas ----------------------------------------------- #

    def _rebuild_columns(self, df) -> None:  # noqa: ANN001
        """Rehace la lista de columnas conservando la selección previa."""
        previous = {item.text() for item in self.columns_list.selectedItems()}
        had_items = self.columns_list.count() > 0

        self.columns_list.blockSignals(True)
        try:
            self.columns_list.clear()
            if df is not None:
                for column in df.columns:
                    self.columns_list.addItem(str(column))
                for index in range(self.columns_list.count()):
                    item = self.columns_list.item(index)
                    item.setSelected(not had_items or item.text() in previous)
        finally:
            self.columns_list.blockSignals(False)

    def _update_diagnosis(self) -> None:
        """Recalcula el conteo y los ejemplos según la selección actual."""
        df = self.dataframe
        if df is None:
            return

        subset = self.selected_columns()
        if not subset:
            self.count_label.setText(texts_es.DUPLICATES_NO_COLUMNS)
            self.examples_table.set_dataframe(None)
            self.drop_button.setEnabled(False)
            return

        count = count_duplicates(df, subset=subset)
        self.count_label.setText(texts_es.DUPLICATES_COUNT_LABEL.format(count=count))
        self.examples_table.set_dataframe(
            get_duplicate_examples(df, subset=subset, max_rows=MAX_EXAMPLE_ROWS)
        )
        self.drop_button.setEnabled(count > 0)
