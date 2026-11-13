"""Pruebas de la vista del Paso 1: selección y carga del dataset."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from PySide6.QtCore import QMimeData, QPointF, Qt, QUrl
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import QFileDialog, QInputDialog, QMessageBox
from pytestqt.qtbot import QtBot

from app.state import Step, WorkflowController
from app.ui import texts_es
from app.views.step1_load import Step1LoadView


@pytest.fixture()
def controller() -> WorkflowController:
    """Controlador de flujo limpio para cada prueba."""
    return WorkflowController()


@pytest.fixture()
def view(qtbot: QtBot, controller: WorkflowController) -> Step1LoadView:
    """Vista del paso 1 visible y lista para interactuar."""
    widget = Step1LoadView(controller)
    qtbot.addWidget(widget)
    widget.show()
    return widget


@pytest.fixture()
def captured_errors(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str]]:
    """Captura los mensajes mostrados por `QMessageBox.critical`."""
    messages: list[tuple[str, str]] = []

    def fake_critical(parent, title, text, *args, **kwargs):  # noqa: ANN001, ANN002, ANN003
        messages.append((str(title), str(text)))
        return QMessageBox.StandardButton.Ok

    monkeypatch.setattr(QMessageBox, "critical", fake_critical)
    return messages


def test_load_button_starts_disabled(view: Step1LoadView) -> None:
    """El botón «Cargar datos» nace deshabilitado y con tooltip explicativo."""
    assert view.load_button.isEnabled() is False
    assert view.load_button.toolTip() == texts_es.LOAD_BTN_LOAD_DISABLED_TOOLTIP
    assert view.selected_path is None


def test_select_valid_file_enables_button(view: Step1LoadView, sample_path: Path) -> None:
    """Al elegir un archivo con extensión válida el botón se habilita."""
    assert view.select_file(sample_path) is True
    assert view.load_button.isEnabled() is True
    assert view.load_button.toolTip() == texts_es.LOAD_BTN_LOAD_TOOLTIP
    assert view.selected_path == sample_path
    assert sample_path.name in view.drop_zone.file_label.text()


def test_file_dialog_selection_enables_button(
    view: Step1LoadView, sample_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Elegir el archivo desde el diálogo del sistema también habilita el botón."""
    monkeypatch.setattr(
        QFileDialog, "getOpenFileName", staticmethod(lambda *args, **kwargs: (str(sample_path), ""))
    )

    view.open_file_dialog()

    assert view.load_button.isEnabled() is True
    assert view.selected_path == sample_path


def test_drag_and_drop_enables_button(view: Step1LoadView, sample_path: Path) -> None:
    """Soltar un archivo válido sobre la zona de arrastre lo selecciona."""
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(sample_path))])

    enter_event = QDragEnterEvent(
        QPointF(10.0, 10.0),
        Qt.DropAction.CopyAction,
        mime,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    view.drop_zone.dragEnterEvent(enter_event)
    assert enter_event.isAccepted() is True

    drop_event = QDropEvent(
        QPointF(10.0, 10.0),
        Qt.DropAction.CopyAction,
        mime,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    view.drop_zone.dropEvent(drop_event)

    assert view.load_button.isEnabled() is True
    assert view.selected_path == sample_path


def test_invalid_extension_is_rejected(
    view: Step1LoadView, tmp_path: Path, captured_errors: list[tuple[str, str]]
) -> None:
    """Un archivo con extensión no soportada se rechaza con un mensaje friendly."""
    invalid = tmp_path / "datos.txt"
    invalid.write_text("no soy una tabla", encoding="utf-8")

    assert view.select_file(invalid) is False
    assert view.load_button.isEnabled() is False
    assert view.selected_path is None
    assert captured_errors, "Debe mostrarse un error al usuario"
    title, message = captured_errors[0]
    assert title == texts_es.LOAD_ERR_TITLE
    assert ".txt" in message


def test_load_button_click_loads_dataset(view: Step1LoadView, sample_path: Path) -> None:
    """Clic en «Cargar datos» deja el dataset cargado y avanza al paso 2."""
    view.select_file(sample_path)

    view.load_button.click()

    assert view.controller.state.has_data is True
    assert Step.LOAD in view.controller.state.completed
    assert view.controller.state.current == Step.INFO
    assert view.controller.state.working_df is not None
    assert not view.controller.state.working_df.empty
    assert view.controller.state.original_df is not None


def test_load_uses_controller_signal_flow(view: Step1LoadView, sample_path: Path) -> None:
    """El controlador recibe el dataset y emite los eventos del flujo."""
    seen: list[str] = []
    view.controller.step_changed.connect(lambda step: seen.append(f"changed:{step}"))
    view.controller.step_completed.connect(lambda step: seen.append(f"completed:{step}"))

    view.select_file(sample_path)
    view.load_selected_file()

    assert "completed:LOAD" in seen
    assert "changed:INFO" in seen


def test_load_error_is_handled_without_traceback(
    view: Step1LoadView, tmp_path: Path, captured_errors: list[tuple[str, str]]
) -> None:
    """Un archivo corrupto muestra un error en español y no rompe la vista."""
    broken = tmp_path / "corrupto.csv"
    broken.write_text("", encoding="utf-8")  # 0 bytes: el loader lo rechaza

    view.select_file(broken)
    view.load_selected_file()

    assert captured_errors, "Debe mostrarse un error al usuario"
    title, message = captured_errors[0]
    assert title == texts_es.LOAD_ERR_TITLE
    assert message
    assert "Traceback" not in message
    assert view.controller.state.has_data is False
    assert Step.LOAD not in view.controller.state.completed
    assert view.controller.state.current == Step.LOAD


def test_unexpected_error_is_handled(
    view: Step1LoadView, sample_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Una excepción inesperada se traduce a un mensaje amigable."""

    def boom(path, sheet=None):  # noqa: ANN001, ANN202
        raise RuntimeError("fallo interno con traceback simulado")

    monkeypatch.setattr("app.views.step1_load.load_file", boom)
    messages: list[tuple[str, str]] = []

    def fake_critical(parent, title, text, *args, **kwargs):  # noqa: ANN001, ANN002, ANN003
        messages.append((str(title), str(text)))
        return QMessageBox.StandardButton.Ok

    monkeypatch.setattr(QMessageBox, "critical", fake_critical)

    view.select_file(sample_path)
    view.load_selected_file()

    assert messages
    assert messages[0][1] == texts_es.LOAD_UNEXPECTED_ERROR
    assert view.controller.state.has_data is False


def test_excel_with_multiple_sheets_asks_for_sheet(
    view: Step1LoadView, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Con varias hojas se pregunta cuál cargar y se usa la elegida."""
    excel_path = tmp_path / "libro.xlsx"
    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        pd.DataFrame({"a": [1, 2], "b": ["x", "y"]}).to_excel(
            writer, sheet_name="Primera", index=False
        )
        pd.DataFrame({"a": [3, 4], "b": ["z", "w"]}).to_excel(
            writer, sheet_name="Segunda", index=False
        )

    monkeypatch.setattr(
        QInputDialog, "getItem", staticmethod(lambda *args, **kwargs: ("Segunda", True))
    )

    view.select_file(excel_path)
    view.load_selected_file()

    assert view.controller.state.has_data is True
    working = view.controller.state.working_df
    assert working is not None
    assert list(working["b"]) == ["z", "w"]


def test_excel_sheet_dialog_can_be_cancelled(
    view: Step1LoadView, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Si el usuario cancela la elección de hoja, no se carga nada."""
    excel_path = tmp_path / "libro.xlsx"
    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        pd.DataFrame({"a": [1]}).to_excel(writer, sheet_name="Primera", index=False)
        pd.DataFrame({"a": [2]}).to_excel(writer, sheet_name="Segunda", index=False)

    monkeypatch.setattr(QInputDialog, "getItem", staticmethod(lambda *args, **kwargs: ("", False)))

    view.select_file(excel_path)
    view.load_selected_file()

    assert view.controller.state.has_data is False
    assert Step.LOAD not in view.controller.state.completed


def test_loading_a_new_file_resets_the_flow(
    view: Step1LoadView, sample_path: Path, tmp_path: Path
) -> None:
    """Cargar un segundo archivo reinicia el flujo y reemplaza los datos."""
    view.select_file(sample_path)
    view.load_selected_file()
    assert view.controller.state.current == Step.INFO

    other = tmp_path / "otro.csv"
    other.write_text("a,b\n1,2\n", encoding="utf-8")

    view.select_file(other)
    view.load_selected_file()

    assert view.controller.state.completed == {Step.LOAD}
    assert view.controller.state.current == Step.INFO
    assert view.controller.state.working_df is not None
    assert list(view.controller.state.working_df.columns) == ["a", "b"]
