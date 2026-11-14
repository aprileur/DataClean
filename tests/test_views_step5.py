"""Pruebas de humo e integración de las vistas del Paso 5 (limpieza A–E)."""

from __future__ import annotations

import pandas as pd
import pytest
from PySide6.QtWidgets import QMessageBox

from app.services.cleaning import CleaningError, missing_union
from app.state import Step, WorkflowController
from app.ui import texts_es
from app.views.step5_cleaning import Step5CleaningView
from app.views.step5_cleaning.duplicates import DuplicatesView
from app.views.step5_cleaning.irrelevant import IrrelevantView
from app.views.step5_cleaning.missing import MissingView
from app.views.step5_cleaning.outliers import OutliersView
from app.views.step5_cleaning.typos import TyposView


def _controller(df: pd.DataFrame) -> WorkflowController:
    controller = WorkflowController()
    controller.set_dataset(df)
    return controller


def _confirm_yes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *args, **kwargs: QMessageBox.StandardButton.Yes,
    )


def test_missing_view_smoke(qtbot, sample_df):
    controller = _controller(sample_df)
    view = MissingView(controller)
    qtbot.addWidget(view)
    view.show()

    assert view.table.dataframe is not None
    assert view.banner.isVisible()
    assert view.drop_button.isEnabled()
    assert Step.CLEAN_A not in controller.state.completed


def test_irrelevant_view_smoke(qtbot, sample_df):
    controller = _controller(sample_df)
    view = IrrelevantView(controller)
    qtbot.addWidget(view)
    view.show()

    assert set(view.checkboxes) == set(sample_df.columns)


def test_duplicates_view_smoke(qtbot, sample_df):
    controller = _controller(sample_df)
    view = DuplicatesView(controller)
    qtbot.addWidget(view)
    view.show()

    assert view.columns_list.count() == len(sample_df.columns)
    assert view.drop_button.isEnabled()


def test_outliers_view_smoke(qtbot, sample_df):
    controller = _controller(sample_df)
    view = OutliersView(controller)
    qtbot.addWidget(view)
    view.show()

    qtbot.waitUntil(lambda: not view.is_busy, timeout=10000)

    assert view.column_combo.count() > 0
    assert view.table.dataframe is not None


def test_typos_view_smoke(qtbot, sample_df):
    controller = _controller(sample_df)
    view = TyposView(controller)
    qtbot.addWidget(view)
    view.show()

    assert view.column_combo.count() > 0


def test_step5_container_smoke(qtbot, sample_df):
    controller = _controller(sample_df)
    container = Step5CleaningView(controller)
    qtbot.addWidget(container)
    container.show()

    assert container.tabs.count() == 5
    assert container.tabs.isTabEnabled(0)
    assert not container.tabs.isTabEnabled(1)
    assert not container.next_button.isEnabled()


def test_missing_no_missing_autocompletes(qtbot):
    df = pd.DataFrame({"a": [1, 1, 2], "b": ["x", "x", "y"]})
    controller = _controller(df)
    view = MissingView(controller)
    qtbot.addWidget(view)

    assert Step.CLEAN_A in controller.state.completed
    assert not view.drop_button.isEnabled()


def test_duplicates_no_dups_autocompletes(qtbot):
    df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
    controller = _controller(df)
    view = DuplicatesView(controller)
    qtbot.addWidget(view)

    assert Step.CLEAN_C in controller.state.completed
    assert not view.drop_button.isEnabled()


def test_missing_drop_rows_updates_working_df(qtbot, sample_df, monkeypatch):
    controller = _controller(sample_df)
    view = MissingView(controller)
    qtbot.addWidget(view)

    expected_rows, _pct = missing_union(sample_df)
    _confirm_yes(monkeypatch)
    view.drop_button.click()

    assert len(controller.state.working_df) == len(sample_df) - expected_rows
    assert len(controller.state.original_df) == len(sample_df)
    assert Step.CLEAN_A in controller.state.completed
    assert controller.state.working_df is not controller.state.original_df


def test_irrelevant_drop_columns_updates_working_df(qtbot, sample_df, monkeypatch):
    controller = _controller(sample_df)
    view = IrrelevantView(controller)
    qtbot.addWidget(view)

    _confirm_yes(monkeypatch)
    view.checkboxes["estado"].setChecked(True)
    view.drop_button.click()

    assert "estado" not in controller.state.working_df.columns
    assert "estado" in controller.state.original_df.columns


def test_duplicates_drop_updates_working_df(qtbot, sample_df, monkeypatch):
    controller = _controller(sample_df)
    view = DuplicatesView(controller)
    qtbot.addWidget(view)

    _confirm_yes(monkeypatch)
    view.drop_button.click()

    assert len(controller.state.working_df) < len(sample_df)
    assert len(controller.state.original_df) == len(sample_df)


def test_typos_column_selector_excludes_numeric(qtbot, sample_df):
    controller = _controller(sample_df)
    view = TyposView(controller)
    qtbot.addWidget(view)

    columns = [view.column_combo.itemText(i) for i in range(view.column_combo.count())]
    assert "ciudad" in columns
    assert "edad" not in columns
    assert "ingreso" not in columns


def test_container_enables_next_tab_after_skip(qtbot, sample_df, monkeypatch):
    controller = _controller(sample_df)
    container = Step5CleaningView(controller)
    qtbot.addWidget(container)

    assert not container.tabs.isTabEnabled(1)
    _confirm_yes(monkeypatch)
    container.views[0].skip()

    assert Step.CLEAN_A in controller.state.completed
    assert container.tabs.isTabEnabled(1)
    assert "✓" in container.tabs.tabText(0)


def test_action_invalidates_later_steps(qtbot, sample_df, monkeypatch):
    controller = _controller(sample_df)
    for step in (Step.CLEAN_A, Step.CLEAN_B, Step.CLEAN_C, Step.CLEAN_D, Step.CLEAN_E):
        controller.complete(step)

    view = MissingView(controller)
    qtbot.addWidget(view)
    _confirm_yes(monkeypatch)
    view.drop_button.click()

    for step in (Step.CLEAN_B, Step.CLEAN_C, Step.CLEAN_D, Step.CLEAN_E):
        assert step not in controller.state.completed
    assert Step.CLEAN_A in controller.state.completed


def test_outliers_keep_action_completes_step(qtbot, sample_df):
    controller = _controller(sample_df)
    view = OutliersView(controller)
    qtbot.addWidget(view)
    qtbot.waitUntil(lambda: not view.is_busy, timeout=10000)

    assert Step.CLEAN_D not in controller.state.completed

    for index in range(view.column_combo.count()):
        view.column_combo.setCurrentIndex(index)
        if view.keep_button.isEnabled():
            view.keep_button.click()

    qtbot.waitUntil(lambda: Step.CLEAN_D in controller.state.completed, timeout=10000)
    assert Step.CLEAN_D in controller.state.completed


def test_outliers_analysis_is_async_and_disables_controls(qtbot, sample_df):
    """El análisis arranca en segundo plano y bloquea los controles mientras corre."""
    controller = _controller(sample_df)
    view = OutliersView(controller)
    qtbot.addWidget(view)

    assert view.is_busy is True
    assert view.busy_indicator.is_busy is True
    assert view.busy_indicator.label.text() == texts_es.OUTLIERS_PROGRESS_LABEL
    assert view.method_combo.isEnabled() is False
    assert view.threshold_spin.isEnabled() is False
    assert view.drop_button.isEnabled() is False

    qtbot.waitUntil(lambda: not view.is_busy, timeout=10000)

    assert view.busy_indicator.is_busy is False
    assert view.method_combo.isEnabled() is True
    assert view.threshold_spin.isEnabled() is True


def test_outliers_error_is_reported_in_spanish(qtbot, sample_df, monkeypatch):
    """Un fallo del análisis se muestra como diálogo en español."""
    messages: list[tuple[str, str]] = []

    def fake_critical(parent, title, text, *args, **kwargs):  # noqa: ANN001, ANN002, ANN003
        messages.append((str(title), str(text)))
        return QMessageBox.StandardButton.Ok

    def boom(df, method="iqr", threshold=1.5):  # noqa: ANN001, ANN202
        raise CleaningError("No se pudo analizar el dataset.")

    monkeypatch.setattr(QMessageBox, "critical", fake_critical)
    monkeypatch.setattr("app.views.step5_cleaning.outliers.analyze_outliers", boom)

    controller = _controller(sample_df)
    view = OutliersView(controller)
    qtbot.addWidget(view)

    qtbot.waitUntil(lambda: bool(messages), timeout=10000)

    assert messages[0][0] == texts_es.OUTLIERS_ERR_TITLE
    assert messages[0][1] == "No se pudo analizar el dataset."
    assert "Traceback" not in messages[0][1]
    assert view.is_busy is False


def test_history_records_actions(qtbot, sample_df, monkeypatch):
    controller = _controller(sample_df)
    view = MissingView(controller)
    qtbot.addWidget(view)

    base_history = len(controller.state.history)
    _confirm_yes(monkeypatch)
    view.drop_button.click()

    assert len(controller.state.history) == base_history + 1
