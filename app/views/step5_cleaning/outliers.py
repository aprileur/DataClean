"""Vista del sub-paso 5D: valores atípicos (outliers).

Diagnostica outliers por columna numérica con el método y umbral elegidos,
los visualiza (diagrama de caja + histograma) y exige una acción explícita
por columna: eliminar, limitar (winsorizar) o conservar.
"""

from __future__ import annotations

import matplotlib
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QSizePolicy,
    QSplitter,
    QWidget,
)

matplotlib.use("QtAgg")

import pandas as pd  # noqa: E402
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402

from app.services.cleaning import (  # noqa: E402
    analyze_outliers,
    clip_outliers,
    drop_outliers,
    outlier_bounds,
    outlier_mask,
)
from app.state import Step, WorkflowController  # noqa: E402
from app.ui import texts_es  # noqa: E402
from app.views.step5_cleaning.base import CleaningStepView  # noqa: E402
from app.widgets import DangerButton, PrimaryButton  # noqa: E402
from app.widgets.dataframe_table import DataFrameTable  # noqa: E402

#: Umbral por defecto del método IQR.
IQR_DEFAULT_THRESHOLD = 1.5

#: Umbral por defecto del método Z-score.
ZSCORE_DEFAULT_THRESHOLD = 3.0

#: Colores del gráfico (coherentes con el tema lila).
BOX_COLOR = "#93C5FD"
HIST_COLOR = "#C4B5FD"
LIMIT_COLOR = "#DC2626"


class OutlierChartCanvas(FigureCanvasQTAgg):
    """Canvas con diagrama de caja e histograma de la columna seleccionada."""

    def __init__(self, parent: QWidget | None = None, width: float = 7.0, height: float = 3.0):
        self.fig = Figure(figsize=(width, height), dpi=100)
        self.axes_box = self.fig.add_subplot(1, 2, 1)
        self.axes_hist = self.fig.add_subplot(1, 2, 2)
        super().__init__(self.fig)
        self.setParent(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._series: pd.Series | None = None
        self._bounds: tuple[float, float] | None = None
        self._column = ""

    def set_data(
        self, series: pd.Series | None, bounds: tuple[float, float] | None, column: str
    ) -> None:
        """Guarda los datos y redibuja el gráfico."""
        self._series = series
        self._bounds = bounds
        self._column = column
        self._draw()

    def clear(self) -> None:
        """Limpia el gráfico y muestra un aviso."""
        self._series = None
        self._bounds = None
        self._column = ""
        self._draw()

    def resizeEvent(self, event) -> None:  # noqa: N802 (API Qt)
        """Reajusta el layout y redibuja al redimensionar."""
        super().resizeEvent(event)
        try:
            self.fig.tight_layout()
            self.draw_idle()
        except Exception:  # noqa: BLE001 - el redibujo nunca debe romper la UI
            pass

    def _draw(self) -> None:
        """Dibuja el diagrama de caja y el histograma de la serie actual."""
        self.axes_box.clear()
        self.axes_hist.clear()

        series = self._series
        clean = None if series is None else series.dropna()
        if clean is None or clean.empty:
            for axes in (self.axes_box, self.axes_hist):
                axes.text(
                    0.5,
                    0.5,
                    texts_es.OUTLIERS_CHART_EMPTY,
                    ha="center",
                    va="center",
                    fontsize=10,
                    color="#6B7280",
                    transform=axes.transAxes,
                )
                axes.axis("off")
            self.fig.suptitle("")
            self.fig.tight_layout()
            self.draw()
            return

        data = clean.to_numpy()

        self.axes_box.boxplot(
            data,
            orientation="vertical",
            patch_artist=True,
            boxprops={"facecolor": BOX_COLOR, "edgecolor": "#60A5FA"},
            medianprops={"color": "#7C3AED"},
        )
        self.axes_box.set_title(texts_es.OUTLIERS_CHART_BOX, fontsize=10, fontweight="bold")
        self.axes_box.set_ylabel(texts_es.OUTLIERS_CHART_VALUE, fontsize=9)
        self.axes_box.grid(axis="y", alpha=0.25)

        bins = max(5, min(20, int(len(data) ** 0.5)))
        self.axes_hist.hist(data, bins=bins, color=HIST_COLOR, edgecolor="#8B5CF6")
        self.axes_hist.set_title(texts_es.OUTLIERS_CHART_HIST, fontsize=10, fontweight="bold")
        self.axes_hist.set_xlabel(texts_es.OUTLIERS_CHART_VALUE, fontsize=9)
        self.axes_hist.set_ylabel(texts_es.OUTLIERS_CHART_FREQUENCY, fontsize=9)
        self.axes_hist.grid(axis="y", alpha=0.25)

        if self._bounds is not None:
            lower, upper = self._bounds
            for axes in (self.axes_box, self.axes_hist):
                axes.axvline(upper, color=LIMIT_COLOR, linestyle="--", linewidth=1)
                if axes is self.axes_hist:
                    axes.axvline(lower, color=LIMIT_COLOR, linestyle="--", linewidth=1)

        self.fig.suptitle(texts_es.OUTLIERS_CHART_TITLE.format(column=self._column), fontsize=11)
        self.fig.tight_layout()
        self.draw()


class OutliersView(CleaningStepView):
    """Vista del sub-paso D: detección y tratamiento explícito de outliers."""

    step = Step.CLEAN_D
    step_letter = "D"
    step_title = texts_es.STEP_5D_NAME

    def __init__(self, controller: WorkflowController, parent: QWidget | None = None) -> None:
        super().__init__(controller, parent)
        self._resolved: set[str] = set()

        self.method_label = QLabel(texts_es.OUTLIERS_METHOD_LABEL, self)
        self.method_combo = QComboBox(self)
        self.method_combo.addItem(texts_es.OUTLIERS_IQR, "iqr")
        self.method_combo.addItem(texts_es.OUTLIERS_ZSCORE, "zscore")

        self.threshold_label = QLabel(texts_es.OUTLIERS_THRESHOLD_LABEL, self)
        self.threshold_spin = QDoubleSpinBox(self)
        self.threshold_spin.setDecimals(2)
        self.threshold_spin.setMinimum(0.1)
        self.threshold_spin.setMaximum(10.0)
        self.threshold_spin.setSingleStep(0.1)
        self.threshold_spin.setValue(IQR_DEFAULT_THRESHOLD)

        controls_row = QHBoxLayout()
        controls_row.setContentsMargins(0, 0, 0, 0)
        controls_row.setSpacing(8)
        controls_row.addWidget(self.method_label)
        controls_row.addWidget(self.method_combo)
        controls_row.addSpacing(16)
        controls_row.addWidget(self.threshold_label)
        controls_row.addWidget(self.threshold_spin)
        controls_row.addStretch()

        self.table_title = QLabel(texts_es.OUTLIERS_TABLE_TITLE, self)
        self.table = DataFrameTable(parent=self)

        self.column_label = QLabel(texts_es.OUTLIERS_COLUMN_LABEL, self)
        self.column_combo = QComboBox(self)

        column_row = QHBoxLayout()
        column_row.setContentsMargins(0, 0, 0, 0)
        column_row.setSpacing(8)
        column_row.addWidget(self.column_label)
        column_row.addWidget(self.column_combo)
        column_row.addStretch()

        self.chart = OutlierChartCanvas(parent=self)
        self.chart.setMinimumHeight(220)

        self.splitter = QSplitter(Qt.Orientation.Vertical, self)
        self.splitter.addWidget(self.table)
        self.splitter.addWidget(self.chart)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 1)

        self.count_label = QLabel("", self)
        self.count_label.setObjectName("outliersCountLabel")

        self.no_issues_label = QLabel(texts_es.CLEAN_NO_ISSUES_FOUND, self)
        self.no_issues_label.setObjectName("cleanNoIssuesLabel")
        self.no_issues_label.setVisible(False)

        self.no_numeric_label = QLabel(texts_es.OUTLIERS_NO_NUMERIC, self)
        self.no_numeric_label.setVisible(False)

        self.drop_button = DangerButton(texts_es.OUTLIERS_ACTION_DROP, self)
        self.drop_button.clicked.connect(self.drop_selected_outliers)

        self.clip_button = PrimaryButton(texts_es.OUTLIERS_ACTION_CLIP, self)
        self.clip_button.clicked.connect(self.clip_selected_outliers)

        self.keep_button = PrimaryButton(texts_es.OUTLIERS_ACTION_KEEP, self)
        self.keep_button.clicked.connect(self.keep_selected_values)

        actions_row = QHBoxLayout()
        actions_row.setContentsMargins(0, 0, 0, 0)
        actions_row.setSpacing(10)
        actions_row.addWidget(self.drop_button)
        actions_row.addWidget(self.clip_button)
        actions_row.addWidget(self.keep_button)
        actions_row.addStretch()

        self.body_layout.addLayout(controls_row)
        self.body_layout.addWidget(self.table_title)
        self.body_layout.addWidget(self.splitter, 1)
        self.body_layout.addLayout(column_row)
        self.body_layout.addWidget(self.count_label)
        self.body_layout.addWidget(self.no_issues_label)
        self.body_layout.addWidget(self.no_numeric_label)
        self.body_layout.addLayout(actions_row)

        self.method_combo.currentIndexChanged.connect(self._on_method_changed)
        self.threshold_spin.valueChanged.connect(self._on_threshold_changed)
        self.column_combo.currentIndexChanged.connect(self._on_column_changed)

        self.refresh()

    # -- API pública ------------------------------------------------------- #

    def refresh(self) -> None:
        """Recalcula el reporte de outliers y actualiza la tabla y el gráfico."""
        df = self.dataframe
        method, threshold = self._method_and_threshold()

        if df is None:
            self.table.set_dataframe(None)
            self.no_issues_label.setVisible(False)
            self.no_numeric_label.setVisible(False)
            self.count_label.setText("")
            self._rebuild_columns([])
            self.chart.clear()
            self._set_action_enabled(False)
            return

        report = analyze_outliers(df, method=method, threshold=threshold)
        display = report.rename(
            columns={
                "columna": texts_es.OUTLIERS_TABLE_COL,
                "outliers": texts_es.OUTLIERS_TABLE_COUNT,
                "porcentaje": texts_es.OUTLIERS_TABLE_PCT,
                "limite_inferior": texts_es.OUTLIERS_TABLE_LOWER,
                "limite_superior": texts_es.OUTLIERS_TABLE_UPPER,
            }
        )
        self.table.set_dataframe(display)

        numeric_columns = [str(col) for col in report["columna"]]
        self.no_numeric_label.setVisible(not numeric_columns)
        self._rebuild_columns(numeric_columns)

        total_outliers = int(report["outliers"].sum()) if not report.empty else 0
        self.no_issues_label.setVisible(bool(numeric_columns) and total_outliers == 0)

        for column in numeric_columns:
            count = self._count_for(report, column)
            if count == 0:
                self._resolved.add(column)

        self._update_selected_column()

        self.complete_if_no_issues(has_issues=bool(numeric_columns) and total_outliers > 0)
        self._maybe_complete(report)

    def drop_selected_outliers(self) -> None:
        """Elimina las filas con outliers en la columna activa, con confirmación."""
        df = self.dataframe
        column = self.selected_column()
        if df is None or not column:
            return

        method, threshold = self._method_and_threshold()
        count = self._column_outlier_count(df, column, method, threshold)
        if count == 0:
            return

        answer = QMessageBox.question(
            self,
            texts_es.OUTLIERS_DROP_CONFIRM_TITLE,
            texts_es.OUTLIERS_DROP_CONFIRM_MSG.format(count=count, column=column),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        new_df = drop_outliers(df, column, method=method, threshold=threshold)
        self.apply_result(new_df, texts_es.OUTLIERS_HISTORY_DROP.format(column=column))

    def clip_selected_outliers(self) -> None:
        """Limita los outliers de la columna activa a los bordes calculados."""
        df = self.dataframe
        column = self.selected_column()
        if df is None or not column:
            return

        method, threshold = self._method_and_threshold()
        count = self._column_outlier_count(df, column, method, threshold)
        if count == 0:
            return

        answer = QMessageBox.question(
            self,
            texts_es.OUTLIERS_CLIP_CONFIRM_TITLE,
            texts_es.OUTLIERS_CLIP_CONFIRM_MSG.format(count=count, column=column),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        new_df = clip_outliers(df, column, method=method, threshold=threshold)
        self.apply_result(new_df, texts_es.OUTLIERS_HISTORY_CLIP.format(column=column))

    def keep_selected_values(self) -> None:
        """Marca la columna activa como resuelta sin tocar el dataset."""
        column = self.selected_column()
        if not column:
            return
        self._resolved.add(column)
        self.show_status(texts_es.OUTLIERS_KEEP_NOTE.format(column=column))
        report = self._current_report()
        self._update_selected_column()
        self._maybe_complete(report)

    def reset_diagnostics(self) -> None:
        """Olvida las columnas conservadas al reiniciar el flujo."""
        self._resolved.clear()
        super().reset_diagnostics()

    # -- Utilidades internas ----------------------------------------------- #

    def selected_column(self) -> str:
        """Columna numérica seleccionada en el combo (o cadena vacía)."""
        return str(self.column_combo.currentText())

    def _method_and_threshold(self) -> tuple[str, float]:
        """Método y umbral actuales del formulario."""
        method = str(self.method_combo.currentData() or "iqr")
        return method, float(self.threshold_spin.value())

    def _rebuild_columns(self, columns: list[str]) -> None:
        """Reconstruye el combo de columnas conservando la selección previa."""
        previous = self.column_combo.currentText()
        self.column_combo.blockSignals(True)
        try:
            self.column_combo.clear()
            self.column_combo.addItems(columns)
            if previous in columns:
                self.column_combo.setCurrentText(previous)
        finally:
            self.column_combo.blockSignals(False)

    def _on_method_changed(self) -> None:
        """Ajusta el umbral por defecto al cambiar de método."""
        self._resolved.clear()
        default = (
            ZSCORE_DEFAULT_THRESHOLD
            if self.method_combo.currentData() == "zscore"
            else IQR_DEFAULT_THRESHOLD
        )
        self.threshold_spin.blockSignals(True)
        try:
            self.threshold_spin.setValue(default)
        finally:
            self.threshold_spin.blockSignals(False)
        self.refresh()

    def _on_threshold_changed(self, _value: float) -> None:
        """Recalcula el diagnóstico cuando cambia el umbral."""
        self._resolved.clear()
        self.refresh()

    def _on_column_changed(self) -> None:
        """Actualiza el gráfico y las acciones al cambiar de columna."""
        self._update_selected_column()

    def _update_selected_column(self) -> None:
        """Redibuja el gráfico y el conteo de la columna seleccionada."""
        df = self.dataframe
        column = self.selected_column()
        if df is None or not column or column not in df.columns:
            self.count_label.setText("")
            self.chart.clear()
            self._set_action_enabled(False)
            return

        method, threshold = self._method_and_threshold()
        series = df[column]
        bounds = outlier_bounds(series, method=method, threshold=threshold)
        count = int(outlier_mask(series, method=method, threshold=threshold).sum())

        self.count_label.setText(texts_es.OUTLIERS_COLUMN_COUNT.format(column=column, count=count))
        self.chart.set_data(series, bounds, column)
        self._set_action_enabled(count > 0 and column not in self._resolved)

    def _set_action_enabled(self, enabled: bool) -> None:
        """Habilita o deshabilita los tres botones de acción."""
        self.drop_button.setEnabled(enabled)
        self.clip_button.setEnabled(enabled)
        self.keep_button.setEnabled(enabled)

    def _current_report(self) -> pd.DataFrame:
        """Reporte de outliers con el método y umbral actuales."""
        df = self.dataframe
        if df is None:
            return pd.DataFrame()
        method, threshold = self._method_and_threshold()
        return analyze_outliers(df, method=method, threshold=threshold)

    def _maybe_complete(self, report: pd.DataFrame) -> None:
        """Completa el sub-paso cuando todas las columnas numéricas están resueltas."""
        if self.dataframe is None:
            return

        numeric_columns = [str(col) for col in report["columna"]] if not report.empty else []
        if not numeric_columns:
            self.complete_if_no_issues(has_issues=False)
            return

        unresolved = [
            column
            for column in numeric_columns
            if self._count_for(report, column) > 0 and column not in self._resolved
        ]
        if not unresolved and not self.is_completed:
            self.mark_completed()

    @staticmethod
    def _count_for(report: pd.DataFrame, column: str) -> int:
        """Cantidad de outliers de una columna según el reporte."""
        if report.empty:
            return 0
        match = report.loc[report["columna"].astype(str) == column, "outliers"]
        return int(match.iloc[0]) if not match.empty else 0

    @staticmethod
    def _column_outlier_count(df: pd.DataFrame, column: str, method: str, threshold: float) -> int:
        """Cuenta los outliers de una columna con el método y umbral dados."""
        return int(outlier_mask(df[column], method=method, threshold=threshold).sum())
