"""Pruebas de la vista del Paso 3 (vista previa con N configurable)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from PySide6.QtCore import Qt
from pytestqt.qtbot import QtBot

from app.state import Step, WorkflowController
from app.ui import texts_es
from app.views.step3_preview import Step3PreviewView


@pytest.fixture()
def preview_controller(sample_df: pd.DataFrame, sample_path: Path) -> WorkflowController:
    """Controlador en el Paso 3 con el dataset de ejemplo y los pasos previos hechos."""
    controller = WorkflowController()
    controller.set_dataset(sample_df, sample_path)
    for step in (Step.LOAD, Step.INFO):
        controller.complete(step)
    controller.go_to(Step.PREVIEW)
    return controller


class TestStep3PreviewView:
    """Pruebas de la vista del Paso 3."""

    def test_default_shows_five_rows(
        self, qtbot: QtBot, preview_controller: WorkflowController
    ) -> None:
        """Al abrir la vista se muestran 5 filas y el total de registros."""
        view = Step3PreviewView(preview_controller)
        qtbot.addWidget(view)
        view.show()

        assert view.spinbox.value() == 5
        assert view.spinbox.maximum() == 1000
        assert view.table.table_model.rowCount() == 5
        assert view.total_label.text() == texts_es.PREVIEW_TOTAL_LABEL.format(total=1000)
        assert view.table.dataframe is not None
        assert list(view.table.dataframe.columns) == list(
            preview_controller.state.working_df.columns
        )

    def test_changing_spinbox_updates_table(
        self, qtbot: QtBot, preview_controller: WorkflowController
    ) -> None:
        """Cambiar N a 10 actualiza la tabla de forma reactiva."""
        view = Step3PreviewView(preview_controller)
        qtbot.addWidget(view)
        view.show()

        view.spinbox.setValue(10)

        assert view.table.table_model.rowCount() == 10
        assert view.table.dataframe is not None
        assert len(view.table.dataframe) == 10

    def test_extreme_values(self, qtbot: QtBot, preview_controller: WorkflowController) -> None:
        """Los valores extremos del spinbox (1 y 1000) muestran la cantidad pedida."""
        view = Step3PreviewView(preview_controller)
        qtbot.addWidget(view)
        view.show()

        view.spinbox.setValue(1)
        assert view.table.table_model.rowCount() == 1

        view.spinbox.setValue(1000)
        assert view.table.table_model.rowCount() == 1000

    def test_refresh_with_smaller_dataset(
        self, qtbot: QtBot, preview_controller: WorkflowController, sample_df: pd.DataFrame
    ) -> None:
        """`refresh()` ajusta máximo, total y tabla cuando el dataset se reduce."""
        view = Step3PreviewView(preview_controller)
        qtbot.addWidget(view)
        view.show()

        reduced = sample_df.head(3)
        preview_controller.set_dataset(reduced, "reducido.csv")
        view.refresh()

        assert view.spinbox.maximum() == 3
        assert view.spinbox.value() == 3
        assert view.table.table_model.rowCount() == 3
        assert view.total_label.text() == texts_es.PREVIEW_TOTAL_LABEL.format(total=3)

    def test_refresh_with_empty_dataset(
        self,
        qtbot: QtBot,
        preview_controller: WorkflowController,
        empty_df: pd.DataFrame,
    ) -> None:
        """Con un dataset vacío la tabla queda sin filas y el spinbox se mantiene válido."""
        view = Step3PreviewView(preview_controller)
        qtbot.addWidget(view)
        view.show()

        preview_controller.set_dataset(empty_df, "vacio.csv")
        view.refresh()

        assert view.spinbox.maximum() == 1
        assert view.spinbox.value() == 1
        assert view.table.table_model.rowCount() == 0
        assert view.total_label.text() == texts_es.PREVIEW_TOTAL_LABEL.format(total=0)

    def test_refresh_after_empty_dataset_restores_default(
        self,
        qtbot: QtBot,
        preview_controller: WorkflowController,
        sample_df: pd.DataFrame,
        empty_df: pd.DataFrame,
    ) -> None:
        """Tras pasar por un dataset vacío, uno nuevo vuelve al valor por defecto."""
        view = Step3PreviewView(preview_controller)
        qtbot.addWidget(view)
        view.show()

        preview_controller.set_dataset(empty_df, "vacio.csv")
        view.refresh()
        preview_controller.set_dataset(sample_df, "sample.csv")
        view.refresh()

        assert view.spinbox.value() == 5
        assert view.table.table_model.rowCount() == 5

    def test_no_dataset_does_not_crash(self, qtbot: QtBot) -> None:
        """Sin dataset la vista se construye sin errores y la tabla queda vacía."""
        controller = WorkflowController()
        view = Step3PreviewView(controller)
        qtbot.addWidget(view)
        view.show()

        assert view.spinbox.value() == 1
        assert view.table.table_model.rowCount() == 0
        assert view.total_label.text() == texts_es.PREVIEW_TOTAL_LABEL.format(total=0)

    def test_understood_completes_and_advances(
        self, qtbot: QtBot, preview_controller: WorkflowController
    ) -> None:
        """«Entendido» completa el Paso 3 y avanza a los tipos de columnas."""
        view = Step3PreviewView(preview_controller)
        qtbot.addWidget(view)
        view.show()

        qtbot.mouseClick(view.understood_button, Qt.MouseButton.LeftButton)

        assert Step.PREVIEW in preview_controller.state.completed
        assert preview_controller.state.current is Step.TYPES

    def test_back_returns_to_info(
        self, qtbot: QtBot, preview_controller: WorkflowController
    ) -> None:
        """«Anterior» regresa al paso de información general (retroceso libre)."""
        view = Step3PreviewView(preview_controller)
        qtbot.addWidget(view)
        view.show()

        qtbot.mouseClick(view.back_button, Qt.MouseButton.LeftButton)

        assert preview_controller.state.current is Step.INFO
