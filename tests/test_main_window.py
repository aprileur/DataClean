"""Pruebas de integración de la ventana principal (navegación, sidebar, historial)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from PySide6.QtWidgets import QMessageBox
from pytestqt.qtbot import QtBot

from app.main_window import MainWindow
from app.state import STEP_ORDER, Step
from app.ui import texts_es


@pytest.fixture()
def window(qtbot: QtBot) -> MainWindow:
    """Ventana principal visible y con el flujo recién iniciado."""
    widget = MainWindow()
    qtbot.addWidget(widget)
    widget.show()
    qtbot.wait(10)
    return widget


def load_dataset(window: MainWindow, df: pd.DataFrame, path: Path) -> None:
    """Simula una carga exitosa y deja el flujo en el paso 2."""
    controller = window.controller
    controller.set_dataset(df, path)
    controller.complete(Step.LOAD)
    controller.go_to(Step.INFO)


def complete_through_cleaning(window: MainWindow) -> None:
    """Marca como completados todos los pasos previos a la exportación."""
    controller = window.controller
    for step in STEP_ORDER[: STEP_ORDER.index(Step.CLEAN_E) + 1]:
        controller.complete(step)


def test_sidebar_starts_locked(window: MainWindow) -> None:
    """Solo el paso 1 está disponible al iniciar; el resto muestra candado."""
    assert window.step_buttons[Step.LOAD].isEnabled() is True
    for step in STEP_ORDER[1:]:
        button = window.step_buttons[step]
        assert button.isEnabled() is False
        assert button.property("locked") == "true"
        assert texts_es.TOOLTIP_STEP_LOCKED.format(step_name=texts_es.STEP_1_NAME) == (
            button.toolTip()
        )


def test_locked_navigation_is_rejected(window: MainWindow) -> None:
    """Navegar por código a un paso bloqueado no cambia la vista."""
    window._navigate(Step.CLEAN_A)

    assert window.controller.state.current == Step.LOAD
    assert window.content_stack.currentWidget() is window.load_view


def test_loading_switches_to_info_view(
    window: MainWindow, sample_df: pd.DataFrame, tmp_path: Path
) -> None:
    """Cargar datos muestra la vista de información y desbloquea el paso 2."""
    load_dataset(window, sample_df, tmp_path / "datos.csv")

    assert window.content_stack.currentWidget() is window.info_view
    assert window.step_buttons[Step.INFO].property("active") == "true"
    # El paso 3 sigue bloqueado hasta confirmar el paso 2 con "Entendido".
    assert window.step_buttons[Step.PREVIEW].isEnabled() is False
    assert window.progress_bar.value() == 1

    window.controller.complete(Step.INFO)

    assert window.step_buttons[Step.PREVIEW].isEnabled() is True
    assert window.progress_bar.value() == 2


def test_sidebar_click_navigates_to_completed_step(
    window: MainWindow, sample_df: pd.DataFrame, tmp_path: Path
) -> None:
    """Al completar el paso 2, el botón del paso 3 navega a la vista previa."""
    load_dataset(window, sample_df, tmp_path / "datos.csv")
    window.controller.complete(Step.INFO)

    window.step_buttons[Step.PREVIEW].click()

    assert window.controller.state.current == Step.PREVIEW
    assert window.content_stack.currentWidget() is window.preview_view


def test_export_view_reachable_after_all_cleaning(
    window: MainWindow, sample_df: pd.DataFrame, tmp_path: Path
) -> None:
    """Con A–E completos se puede entrar a la exportación desde la sidebar."""
    load_dataset(window, sample_df, tmp_path / "datos.csv")
    complete_through_cleaning(window)

    window._navigate(Step.EXPORT)

    assert window.controller.state.current == Step.EXPORT
    assert window.content_stack.currentWidget() is window.export_view
    assert window.export_view.export_button.isEnabled() is True
    assert window.progress_bar.value() == 9  # LOAD, INFO, PREVIEW, TYPES y A–E


def test_history_buttons_disabled_without_actions(window: MainWindow) -> None:
    """Sin dataset no hay nada que deshacer ni restaurar."""
    assert window.undo_button.isEnabled() is False
    assert window.restore_button.isEnabled() is False


def test_undo_restores_previous_snapshot(
    window: MainWindow, sample_df: pd.DataFrame, tmp_path: Path
) -> None:
    """Deshacer devuelve el dataset previo y re-bloquea los sub-pasos A–E."""
    controller = window.controller
    load_dataset(window, sample_df, tmp_path / "datos.csv")
    for step in (Step.INFO, Step.PREVIEW, Step.TYPES):
        controller.complete(step)
    controller.go_to(Step.CLEAN_A)
    controller.complete(Step.CLEAN_A)

    cleaned = sample_df.dropna().copy()
    controller.state.history.push("Eliminar registros con datos faltantes", cleaned)
    controller.state.working_df = cleaned
    window._sync_history_buttons()

    assert window.undo_button.isEnabled() is True
    window.undo_button.click()

    pd.testing.assert_frame_equal(controller.state.working_df, sample_df)
    assert controller.state.is_completed(Step.CLEAN_A) is False
    assert controller.state.current == Step.CLEAN_A
    assert window.undo_button.isEnabled() is False


def test_restore_original_can_be_cancelled(
    window: MainWindow,
    sample_df: pd.DataFrame,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cancelar la confirmación conserva los datos de trabajo actuales."""
    controller = window.controller
    load_dataset(window, sample_df, tmp_path / "datos.csv")
    cleaned = sample_df.dropna().copy()
    controller.state.working_df = cleaned

    monkeypatch.setattr(
        QMessageBox,
        "question",
        staticmethod(lambda *args, **kwargs: QMessageBox.StandardButton.No),
    )

    window.restore_button.click()

    pd.testing.assert_frame_equal(controller.state.working_df, cleaned)


def test_restore_original_resets_working_dataframe(
    window: MainWindow,
    sample_df: pd.DataFrame,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Confirmar la restauración devuelve el dataset original intacto."""
    controller = window.controller
    load_dataset(window, sample_df, tmp_path / "datos.csv")
    for step in (Step.INFO, Step.PREVIEW, Step.TYPES, Step.CLEAN_A):
        controller.complete(step)
    controller.state.working_df = sample_df.head(5).copy()

    monkeypatch.setattr(
        QMessageBox,
        "question",
        staticmethod(lambda *args, **kwargs: QMessageBox.StandardButton.Yes),
    )

    window.restore_button.click()

    pd.testing.assert_frame_equal(controller.state.working_df, sample_df)
    pd.testing.assert_frame_equal(controller.state.original_df, sample_df)
    assert controller.state.is_completed(Step.CLEAN_A) is False
