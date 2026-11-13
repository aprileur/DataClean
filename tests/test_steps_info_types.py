"""Pruebas de las vistas del Paso 2 (información) y Paso 4 (tipos de columnas)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from PySide6.QtCore import Qt
from pytestqt.qtbot import QtBot

from app.state import Step, WorkflowController
from app.ui import texts_es
from app.views.step2_info import Step2InfoView
from app.views.step4_types import Step4TypesView


@pytest.fixture()
def info_controller(sample_df: pd.DataFrame, sample_path: Path) -> WorkflowController:
    """Controlador con el dataset de ejemplo cargado y el Paso 1 completado."""
    controller = WorkflowController()
    controller.set_dataset(sample_df, sample_path)
    controller.complete(Step.LOAD)
    controller.go_to(Step.INFO)
    return controller


@pytest.fixture()
def types_controller(sample_df: pd.DataFrame, sample_path: Path) -> WorkflowController:
    """Controlador posicionado en el Paso 4 con los pasos previos completados."""
    controller = WorkflowController()
    controller.set_dataset(sample_df, sample_path)
    for step in (Step.LOAD, Step.INFO, Step.PREVIEW):
        controller.complete(step)
    controller.go_to(Step.TYPES)
    return controller


# --------------------------------------------------------------------------- #
# Paso 2: Información general
# --------------------------------------------------------------------------- #


class TestStep2InfoView:
    """Pruebas de la vista del Paso 2."""

    def test_cards_show_correct_data(
        self, qtbot: QtBot, info_controller: WorkflowController
    ) -> None:
        """Las tarjetas muestran la forma, conteos y archivo del dataset."""
        view = Step2InfoView(info_controller)
        qtbot.addWidget(view)
        view.show()

        assert view.shape_card.value_label.text() == "(1000, 8)"
        assert view.rows_card.value_label.text() == "1,000"
        assert view.cols_card.value_label.text() == "8"
        assert view.file_card.value_label.text() == "sample.csv"
        assert view.memory_card.value_label.text() != ""

    def test_cards_empty_without_dataset(self, qtbot: QtBot) -> None:
        """Sin dataset cargado las tarjetas quedan vacías sin lanzar errores."""
        controller = WorkflowController()
        view = Step2InfoView(controller)
        qtbot.addWidget(view)
        view.show()

        assert view.rows_card.value_label.text() == ""
        assert view.cols_card.value_label.text() == ""
        assert view.shape_card.value_label.text() == ""

    def test_refresh_updates_cards(
        self, qtbot: QtBot, info_controller: WorkflowController, sample_df: pd.DataFrame
    ) -> None:
        """`refresh()` recalcula las tarjetas tras cambiar el dataset."""
        view = Step2InfoView(info_controller)
        qtbot.addWidget(view)
        view.show()

        reduced = sample_df.head(120)
        info_controller.set_dataset(reduced, "otro.csv")
        view.refresh()

        assert view.rows_card.value_label.text() == "120"
        assert view.file_card.value_label.text() == "otro.csv"

    def test_understood_completes_and_advances(
        self, qtbot: QtBot, info_controller: WorkflowController
    ) -> None:
        """«Entendido» completa el Paso 2 y avanza a la vista previa."""
        view = Step2InfoView(info_controller)
        qtbot.addWidget(view)
        view.show()

        qtbot.mouseClick(view.understood_button, Qt.MouseButton.LeftButton)

        assert Step.INFO in info_controller.state.completed
        assert info_controller.state.current is Step.PREVIEW

    def test_back_returns_to_load(self, qtbot: QtBot, info_controller: WorkflowController) -> None:
        """«Anterior» regresa al paso de carga (retroceso libre)."""
        view = Step2InfoView(info_controller)
        qtbot.addWidget(view)
        view.show()

        qtbot.mouseClick(view.back_button, Qt.MouseButton.LeftButton)

        assert info_controller.state.current is Step.LOAD


# --------------------------------------------------------------------------- #
# Paso 4: Tipos de columnas
# --------------------------------------------------------------------------- #


class TestStep4TypesView:
    """Pruebas de la vista del Paso 4."""

    def test_classification_cards(self, qtbot: QtBot, types_controller: WorkflowController) -> None:
        """Las columnas de `sample_df` se clasifican en numéricas y categóricas."""
        view = Step4TypesView(types_controller)
        qtbot.addWidget(view)
        view.show()

        numeric_content = view.numeric_card.content_label.text()
        categorical_content = view.categorical_card.content_label.text()

        for col in ("id", "edad", "ingreso", "gastos"):
            assert col in numeric_content
        for col in ("genero", "ciudad", "estado", "tipocliente"):
            assert col in categorical_content

    def test_id_warning_is_shown(self, qtbot: QtBot, types_controller: WorkflowController) -> None:
        """La heurística detecta `id` como posible identificador y avisa."""
        view = Step4TypesView(types_controller)
        qtbot.addWidget(view)
        view.show()

        assert view.id_banner.isVisible()
        assert texts_es.TYPES_ID_WARNING.format(col="id") in view.id_banner.message_label.text()

    def test_other_card_hidden_without_dates(
        self, qtbot: QtBot, types_controller: WorkflowController
    ) -> None:
        """Sin columnas de fecha u `other`, la tarjeta «Fecha / Otras» no aparece."""
        view = Step4TypesView(types_controller)
        qtbot.addWidget(view)
        view.show()

        assert not view.other_card.isVisible()

    def test_other_card_shown_with_datetime(
        self, qtbot: QtBot, sample_df: pd.DataFrame, sample_path: Path
    ) -> None:
        """Al añadir una columna de fecha sintética, la tarjeta «Fecha / Otras» aparece."""
        controller = WorkflowController()
        df = sample_df.copy()
        df["fecha_registro"] = pd.date_range("2024-01-01", periods=len(df), freq="D")
        controller.set_dataset(df, sample_path)
        for step in (Step.LOAD, Step.INFO, Step.PREVIEW):
            controller.complete(step)
        controller.go_to(Step.TYPES)

        view = Step4TypesView(controller)
        qtbot.addWidget(view)
        view.show()

        assert view.other_card.isVisible()
        assert "fecha_registro" in view.other_card.content_label.text()

    def test_refresh_updates_cards(
        self, qtbot: QtBot, sample_df: pd.DataFrame, sample_path: Path
    ) -> None:
        """`refresh()` recalcula la clasificación tras cambiar el dataset."""
        controller = WorkflowController()
        controller.set_dataset(sample_df, sample_path)
        for step in (Step.LOAD, Step.INFO, Step.PREVIEW):
            controller.complete(step)
        controller.go_to(Step.TYPES)

        view = Step4TypesView(controller)
        qtbot.addWidget(view)
        view.show()

        controller.set_dataset(sample_df[["edad", "genero"]], sample_path)
        view.refresh()

        assert view.numeric_card.content_label.text() == "edad"
        assert view.categorical_card.content_label.text() == "genero"
        assert not view.id_banner.isVisible()

    def test_understood_completes_and_advances(
        self, qtbot: QtBot, types_controller: WorkflowController
    ) -> None:
        """«Entendido» completa el Paso 4 y avanza a la limpieza (5A)."""
        view = Step4TypesView(types_controller)
        qtbot.addWidget(view)
        view.show()

        qtbot.mouseClick(view.understood_button, Qt.MouseButton.LeftButton)

        assert Step.TYPES in types_controller.state.completed
        assert types_controller.state.current is Step.CLEAN_A

    def test_back_returns_to_preview(
        self, qtbot: QtBot, types_controller: WorkflowController
    ) -> None:
        """«Anterior» regresa al paso de vista previa (retroceso libre)."""
        view = Step4TypesView(types_controller)
        qtbot.addWidget(view)
        view.show()

        qtbot.mouseClick(view.back_button, Qt.MouseButton.LeftButton)

        assert types_controller.state.current is Step.PREVIEW
