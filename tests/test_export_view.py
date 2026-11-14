"""Pruebas de la vista de exportación y del resumen final (T20)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from PySide6.QtWidgets import QFileDialog, QMessageBox
from pytestqt.qtbot import QtBot

from app.services.exporter import ExportError
from app.state import STEP_ORDER, Step, WorkflowController
from app.ui import texts_es
from app.views.export import ExportView


@pytest.fixture()
def controller(sample_df: pd.DataFrame, tmp_path: Path) -> WorkflowController:
    """Controlador con dataset cargado y los sub-pasos A–E completados."""
    ctrl = WorkflowController()
    ctrl.set_dataset(sample_df, tmp_path / "ventas.csv")
    ctrl.state.history.push("Eliminar duplicados (3 filas)", sample_df)
    for step in STEP_ORDER[: STEP_ORDER.index(Step.CLEAN_E) + 1]:
        ctrl.complete(step)
    return ctrl


@pytest.fixture()
def view(qtbot: QtBot, controller: WorkflowController) -> ExportView:
    """Vista de exportación visible lista para interactuar."""
    widget = ExportView(controller)
    qtbot.addWidget(widget)
    widget.show()
    return widget


@pytest.fixture()
def captured_messages(monkeypatch: pytest.MonkeyPatch) -> dict[str, list[tuple[str, str]]]:
    """Captura los diálogos de información y advertencia de la vista."""
    captured: dict[str, list[tuple[str, str]]] = {"info": [], "warning": []}

    def fake_information(parent, title, text, *args, **kwargs):  # noqa: ANN001, ANN002, ANN003
        captured["info"].append((str(title), str(text)))
        return QMessageBox.StandardButton.Ok

    def fake_warning(parent, title, text, *args, **kwargs):  # noqa: ANN001, ANN002, ANN003
        captured["warning"].append((str(title), str(text)))
        return QMessageBox.StandardButton.Ok

    monkeypatch.setattr(QMessageBox, "information", fake_information)
    monkeypatch.setattr(QMessageBox, "warning", fake_warning)
    return captured


def test_export_view_smoke(view: ExportView) -> None:
    """La vista se instancia y muestra el título correcto."""
    assert view.header.title_label.text() == texts_es.EXPORT_TITLE
    assert view.summary_title.text() == texts_es.EXPORT_SUMMARY_TITLE


def test_export_button_disabled_before_cleaning_finishes(qtbot: QtBot) -> None:
    """Sin completar A–E el botón está deshabilitado y explica por qué."""
    ctrl = WorkflowController()
    ctrl.set_dataset(pd.DataFrame({"a": [1, 2]}), Path("datos.csv"))
    widget = ExportView(ctrl)
    qtbot.addWidget(widget)

    assert widget.export_button.isEnabled() is False
    assert widget.export_button.toolTip() == texts_es.EXPORT_LOCKED_TOOLTIP


def test_export_button_enabled_after_cleaning(view: ExportView) -> None:
    """Con A–E completos el botón de exportar se habilita."""
    assert view.export_button.isEnabled() is True
    assert view.export_button.toolTip() == texts_es.EXPORT_READY_TOOLTIP


def test_summary_lists_applied_actions(view: ExportView) -> None:
    """El resumen muestra las acciones del historial en orden, sin el snapshot base."""
    items = [view.summary_list.item(i).text() for i in range(view.summary_list.count())]
    assert items == ["Eliminar duplicados (3 filas)"]


def test_summary_placeholder_without_actions(qtbot: QtBot, sample_df: pd.DataFrame) -> None:
    """Sin acciones de limpieza el resumen muestra un texto informativo."""
    ctrl = WorkflowController()
    ctrl.set_dataset(sample_df, Path("datos.csv"))
    widget = ExportView(ctrl)
    qtbot.addWidget(widget)

    items = [widget.summary_list.item(i).text() for i in range(widget.summary_list.count())]
    assert items == [texts_es.EXPORT_NO_ACTIONS]


def test_suggested_path_uses_new_suffix(view: ExportView) -> None:
    """El nombre sugerido es `<stem>_nuevo.<ext>` y cambia con el formato."""
    assert view.suggested_path().name == "ventas_nuevo.csv"

    view.format_combo.setCurrentIndex(1)  # Excel
    assert view.suggested_path().name == "ventas_nuevo.xlsx"

    view.format_combo.setCurrentIndex(2)  # Parquet
    assert view.suggested_path().name == "ventas_nuevo.parquet"


def test_suggested_path_avoids_collisions(view: ExportView, tmp_path: Path) -> None:
    """Si el nombre sugerido ya existe se propone `_nuevo_2`."""
    (tmp_path / "ventas_nuevo.csv").write_text("existente", encoding="utf-8")

    assert view.suggested_path().name == "ventas_nuevo_2.csv"


def test_export_calls_service_with_working_df(
    view: ExportView,
    controller: WorkflowController,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    captured_messages: dict[str, list[tuple[str, str]]],
) -> None:
    """Al exportar se llama a `export_dataset` con el dataset de trabajo."""
    target = tmp_path / "salida.csv"
    calls: list[tuple[pd.DataFrame, Path]] = []

    monkeypatch.setattr(
        QFileDialog, "getSaveFileName", staticmethod(lambda *args, **kwargs: (str(target), ""))
    )

    def fake_export(df: pd.DataFrame, path: Path) -> Path:
        calls.append((df, Path(path)))
        return Path(path)

    monkeypatch.setattr("app.views.export.export_dataset", fake_export)

    view.export_button.click()

    assert len(calls) == 1
    exported_df, exported_path = calls[0]
    assert exported_df is controller.state.working_df
    assert exported_path == target
    assert captured_messages["info"]
    assert texts_es.EXPORT_SUCCESS_TITLE == captured_messages["info"][0][0]
    assert str(target) in captured_messages["info"][0][1]


def test_export_reports_export_error(
    view: ExportView,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    captured_messages: dict[str, list[tuple[str, str]]],
) -> None:
    """Un `ExportError` se muestra como advertencia con su mensaje en español."""
    target = tmp_path / "salida.csv"

    monkeypatch.setattr(
        QFileDialog, "getSaveFileName", staticmethod(lambda *args, **kwargs: (str(target), ""))
    )

    def failing_export(df: pd.DataFrame, path: Path) -> Path:
        raise ExportError("No se pudo escribir el archivo.")

    monkeypatch.setattr("app.views.export.export_dataset", failing_export)

    view.export_button.click()

    assert captured_messages["warning"] == [
        (texts_es.EXPORT_ERR_TITLE, "No se pudo escribir el archivo.")
    ]


def test_export_cancelled_does_nothing(view: ExportView, monkeypatch: pytest.MonkeyPatch) -> None:
    """Si el usuario cancela el diálogo no se exporta ni se muestra mensaje."""
    called: list[Path] = []

    monkeypatch.setattr(
        QFileDialog, "getSaveFileName", staticmethod(lambda *args, **kwargs: ("", ""))
    )

    def fake_export(df: pd.DataFrame, path: Path) -> Path:
        called.append(Path(path))
        return Path(path)

    monkeypatch.setattr("app.views.export.export_dataset", fake_export)

    view.export_button.click()

    assert called == []


def test_export_does_not_mutate_dataframes(
    view: ExportView,
    controller: WorkflowController,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    captured_messages: dict[str, list[tuple[str, str]]],
) -> None:
    """Exportar no modifica ni el dataset de trabajo ni el original."""
    working_before = controller.state.working_df.copy()
    original_before = controller.state.original_df.copy()
    target = tmp_path / "salida.csv"

    monkeypatch.setattr(
        QFileDialog, "getSaveFileName", staticmethod(lambda *args, **kwargs: (str(target), ""))
    )
    monkeypatch.setattr("app.views.export.export_dataset", lambda df, path: Path(path))

    view.export_button.click()

    pd.testing.assert_frame_equal(controller.state.working_df, working_before)
    pd.testing.assert_frame_equal(controller.state.original_df, original_before)


def test_back_button_returns_to_last_cleaning_step(
    view: ExportView, controller: WorkflowController
) -> None:
    """«Anterior» regresa al sub-paso E de la limpieza."""
    view.back_button.click()

    assert controller.state.current == Step.CLEAN_E
