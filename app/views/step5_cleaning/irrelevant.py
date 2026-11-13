"""Vista del sub-paso 5B: columnas irrelevantes.

Lista todas las columnas con casillas. Las que el servicio considera
candidatas (constantes, casi vacías o posibles identificadores) aparecen
premarcadas y con su motivo, pero nada se elimina sin acción explícita.
"""

from __future__ import annotations

from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.services.cleaning import drop_columns, suggest_irrelevant
from app.state import Step, WorkflowController
from app.ui import texts_es
from app.views.step5_cleaning.base import CleaningStepView
from app.widgets import DangerButton

#: Color gris usado para el motivo de una sugerencia.
SUGGESTION_REASON_COLOR = "#6B7280"


class IrrelevantView(CleaningStepView):
    """Vista del sub-paso B: selección y eliminación de columnas irrelevantes."""

    step = Step.CLEAN_B
    step_letter = "B"
    step_title = texts_es.STEP_5B_NAME

    def __init__(self, controller: WorkflowController, parent: QWidget | None = None) -> None:
        super().__init__(controller, parent)

        self.info_label = QLabel(texts_es.IRRELEVANT_INFO, self)
        self.info_label.setWordWrap(True)

        self.no_issues_label = QLabel(texts_es.CLEAN_NO_ISSUES_FOUND, self)
        self.no_issues_label.setObjectName("cleanNoIssuesLabel")
        self.no_issues_label.setVisible(False)

        self.no_columns_label = QLabel(texts_es.IRRELEVANT_NO_COLUMNS, self)
        self.no_columns_label.setVisible(False)

        self.checkboxes: dict[str, QCheckBox] = {}
        self._checked: dict[str, bool] = {}

        list_container = QWidget(self)
        self.list_layout = QVBoxLayout(list_container)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(6)

        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(list_container)

        self.drop_button = DangerButton(texts_es.IRRELEVANT_BTN_DROP, self)
        self.drop_button.setEnabled(False)
        self.drop_button.clicked.connect(self.drop_selected_columns)

        actions_row = QHBoxLayout()
        actions_row.setContentsMargins(0, 0, 0, 0)
        actions_row.addWidget(self.drop_button)
        actions_row.addStretch()

        self.body_layout.addWidget(self.info_label)
        self.body_layout.addWidget(self.scroll_area, 1)
        self.body_layout.addWidget(self.no_issues_label)
        self.body_layout.addWidget(self.no_columns_label)
        self.body_layout.addLayout(actions_row)

        self.refresh()

    # -- API pública ------------------------------------------------------- #

    def refresh(self) -> None:
        """Reconstruye la lista de columnas y sus sugerencias."""
        df = self.dataframe
        if df is None:
            self._clear_list()
            self.no_issues_label.setVisible(False)
            self.no_columns_label.setVisible(False)
            self.drop_button.setEnabled(False)
            return

        suggestions = suggest_irrelevant(df)
        self._clear_list()

        has_columns = len(df.columns) > 0
        self.no_columns_label.setVisible(not has_columns)

        for column in df.columns:
            name = str(column)
            was_checked = self._checked.get(name, name in suggestions)
            self._add_column_row(name, suggestions.get(name), was_checked)

        self.list_layout.addStretch(1)
        self._update_button()

        has_issues = bool(suggestions)
        self.no_issues_label.setVisible(not has_issues and has_columns)
        self.complete_if_no_issues(has_issues)

    def selected_columns(self) -> list[str]:
        """Nombres de las columnas marcadas actualmente."""
        return [name for name, box in self.checkboxes.items() if box.isChecked()]

    def drop_selected_columns(self) -> None:
        """Elimina las columnas marcadas tras confirmar el impacto exacto."""
        df = self.dataframe
        selected = self.selected_columns()
        if df is None or not selected:
            return

        answer = QMessageBox.question(
            self,
            texts_es.IRRELEVANT_CONFIRM_TITLE,
            texts_es.IRRELEVANT_CONFIRM_MSG.format(cols=", ".join(selected)),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        new_df = drop_columns(df, selected)
        description = texts_es.IRRELEVANT_HISTORY_DROP.format(columns=", ".join(selected))
        for name in selected:
            self._checked.pop(name, None)
        self.apply_result(new_df, description)

    def reset_diagnostics(self) -> None:
        """Olvida las casillas marcadas al reiniciar el flujo."""
        self._checked.clear()
        super().reset_diagnostics()

    # -- Utilidades internas ----------------------------------------------- #

    def _clear_list(self) -> None:
        """Elimina los widgets de la lista actual antes de reconstruirla."""
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self.checkboxes.clear()

    def _add_column_row(self, name: str, reason: str | None, checked: bool) -> None:
        """Añade una fila con la casilla de la columna y, si aplica, su motivo."""
        row = QWidget(self.scroll_area.widget())
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(8)

        checkbox = QCheckBox(name, row)
        checkbox.setChecked(checked)
        checkbox.toggled.connect(lambda value, col=name: self._on_toggled(col, value))
        self.checkboxes[name] = checkbox

        row_layout.addWidget(checkbox)
        if reason:
            reason_label = QLabel(texts_es.IRRELEVANT_SUGGESTION_LABEL.format(reason=reason), row)
            font = QFont(reason_label.font())
            font.setItalic(True)
            reason_label.setFont(font)
            palette = QPalette(reason_label.palette())
            palette.setColor(QPalette.ColorRole.WindowText, QColor(SUGGESTION_REASON_COLOR))
            reason_label.setPalette(palette)
            row_layout.addWidget(reason_label)
        row_layout.addStretch(1)

        self.list_layout.addWidget(row)

    def _on_toggled(self, column: str, checked: bool) -> None:
        """Recuerda el estado de la casilla y actualiza el botón de acción."""
        self._checked[column] = checked
        self._update_button()

    def _update_button(self) -> None:
        """Habilita el botón de eliminación solo si hay columnas marcadas."""
        self.drop_button.setEnabled(bool(self.selected_columns()))
