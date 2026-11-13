"""Pruebas del widget reutilizable `DataFrameTable` y su modelo."""

from __future__ import annotations

import time

import numpy as np
import pandas as pd
import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QAbstractItemView, QSizePolicy
from pytestqt.qtbot import QtBot

from app.widgets.dataframe_table import (
    CATEGORICAL_HEADER_COLOR,
    MISSING_TEXT,
    NUMERIC_HEADER_COLOR,
    DataFrameTable,
    DataFrameTableModel,
    format_cell_value,
    is_missing_value,
    is_numeric_column,
)


@pytest.fixture()
def table_df() -> pd.DataFrame:
    """DataFrame mixto: enteros, flotantes, texto, booleanos y faltantes."""
    return pd.DataFrame(
        {
            "id": [1, 2, 3, 4],
            "ingreso": [1000.0, 25400.5, None, 300.0],
            "ciudad": ["Toluca", "toluca ", None, "Metepec"],
            "activo": [True, False, True, False],
        }
    )


@pytest.fixture()
def table(qtbot: QtBot, table_df: pd.DataFrame) -> DataFrameTable:
    widget = DataFrameTable(table_df)
    qtbot.addWidget(widget)
    return widget


# -- Modelo ---------------------------------------------------------------- #


def test_model_dimensions(table: DataFrameTable, table_df: pd.DataFrame) -> None:
    model = table.table_model
    assert model.rowCount() == len(table_df)
    assert model.columnCount() == len(table_df.columns)
    assert table.dataframe is table_df


def test_model_read_only_flags(table: DataFrameTable) -> None:
    model = table.table_model
    flags = model.flags(model.index(0, 0))

    assert flags & Qt.ItemFlag.ItemIsEnabled
    assert flags & Qt.ItemFlag.ItemIsSelectable
    assert not (flags & Qt.ItemFlag.ItemIsEditable)

    assert model.flags(model.index(-1, -1)) == Qt.ItemFlag.NoItemFlags


def test_table_is_read_only(table: DataFrameTable) -> None:
    assert table.editTriggers() == QAbstractItemView.EditTrigger.NoEditTriggers


def test_display_role_formatting(table: DataFrameTable) -> None:
    model = table.table_model
    role = Qt.ItemDataRole.DisplayRole

    assert model.data(model.index(0, 0), role) == "1"
    assert model.data(model.index(0, 1), role) == "1,000.00"
    assert model.data(model.index(1, 1), role) == "25,400.50"
    assert model.data(model.index(2, 1), role) == MISSING_TEXT
    assert model.data(model.index(2, 2), role) == MISSING_TEXT
    assert model.data(model.index(0, 2), role) == "Toluca"
    assert model.data(model.index(1, 2), role) == "toluca "
    assert model.data(model.index(0, 3), role) == "True"
    assert model.data(model.index(1, 3), role) == "False"


def test_text_alignment_role(table: DataFrameTable) -> None:
    model = table.table_model
    role = Qt.ItemDataRole.TextAlignmentRole
    right = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
    left = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter

    assert model.data(model.index(0, 0), role) == right
    assert model.data(model.index(0, 1), role) == right
    assert model.data(model.index(0, 2), role) == left
    assert model.data(model.index(0, 3), role) == left
    assert model.data(model.index(2, 1), role) == Qt.AlignmentFlag.AlignCenter
    assert model.data(model.index(2, 2), role) == Qt.AlignmentFlag.AlignCenter


def test_headers_display_and_colors(table: DataFrameTable, table_df: pd.DataFrame) -> None:
    model = table.table_model
    display = Qt.ItemDataRole.DisplayRole
    background = Qt.ItemDataRole.BackgroundRole
    horizontal = Qt.Orientation.Horizontal
    vertical = Qt.Orientation.Vertical

    assert [
        model.headerData(col, horizontal, display) for col in range(model.columnCount())
    ] == list(table_df.columns)
    assert model.headerData(0, vertical, display) == 1
    assert model.headerData(3, vertical, display) == 4

    def header_color(col: int) -> str:
        brush = model.headerData(col, horizontal, background)
        assert brush is not None
        return brush.color().name().lower()

    assert header_color(0) == NUMERIC_HEADER_COLOR.lower()
    assert header_color(1) == NUMERIC_HEADER_COLOR.lower()
    assert header_color(2) == CATEGORICAL_HEADER_COLOR.lower()
    # `bool` se trata como categórico aunque `is_numeric_dtype` lo acepte.
    assert header_color(3) == CATEGORICAL_HEADER_COLOR.lower()
    assert model.headerData(0, vertical, background) is None


def test_set_dataframe_updates_model(qtbot: QtBot, table: DataFrameTable) -> None:
    new_df = pd.DataFrame({"a": [10, 20], "b": ["x", "y"], "c": [1.5, 2.5]})

    with qtbot.waitSignal(table.table_model.modelReset, timeout=1000):
        table.set_dataframe(new_df)

    model = table.table_model
    assert table.dataframe is new_df
    assert model.rowCount() == 2
    assert model.columnCount() == 3
    assert model.headerData(0, Qt.Orientation.Horizontal, Qt.ItemDataRole.DisplayRole) == "a"
    assert model.data(model.index(1, 0), Qt.ItemDataRole.DisplayRole) == "20"


def test_none_and_empty_dataframes(qtbot: QtBot, empty_df: pd.DataFrame) -> None:
    empty_table = DataFrameTable()
    qtbot.addWidget(empty_table)
    assert empty_table.dataframe is None
    assert empty_table.table_model.rowCount() == 0
    assert empty_table.table_model.columnCount() == 0
    assert empty_table.table_model.headerData(0, Qt.Orientation.Horizontal) is None

    empty_table.set_dataframe(empty_df)
    assert empty_table.dataframe is empty_df
    assert empty_table.table_model.rowCount() == 0
    assert empty_table.table_model.columnCount() == len(empty_df.columns)


def test_table_expands_and_scrolls(table: DataFrameTable) -> None:
    policy = table.sizePolicy()
    assert policy.horizontalPolicy() == QSizePolicy.Policy.Expanding
    assert policy.verticalPolicy() == QSizePolicy.Policy.Expanding
    assert table.alternatingRowColors() is True
    assert table.verticalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAsNeeded
    assert table.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAsNeeded


def test_formatting_helpers() -> None:
    assert format_cell_value(1000) == "1,000"
    assert format_cell_value(-1234567) == "-1,234,567"
    assert format_cell_value(25400.5) == "25,400.50"
    assert format_cell_value(True) == "True"
    assert format_cell_value("texto") == "texto"
    for missing in (None, float("nan"), pd.NA, pd.NaT):
        assert format_cell_value(missing) == MISSING_TEXT
        assert is_missing_value(missing) is True
    assert is_missing_value([1, 2]) is False
    assert is_numeric_column(np.dtype("int64")) is True
    assert is_numeric_column(np.dtype("float64")) is True
    assert is_numeric_column(np.dtype("bool")) is False
    assert is_numeric_column(pd.StringDtype()) is False


# -- Rendimiento ----------------------------------------------------------- #


def test_loads_ten_thousand_rows_quickly(qtbot: QtBot) -> None:
    rows = 10_000
    big_df = pd.DataFrame(
        {
            "id": np.arange(rows),
            "valor": np.linspace(0.0, 25_400.5, rows),
            "categoria": pd.Series(["grupo"] * rows, dtype="str"),
        }
    )
    table = DataFrameTable()
    qtbot.addWidget(table)

    started = time.perf_counter()
    table.set_dataframe(big_df)
    load_seconds = time.perf_counter() - started

    model = table.table_model
    assert model.rowCount() == rows
    assert model.columnCount() == 3
    assert load_seconds < 1.0

    # Recorrer todas las celdas (lo que hace la vista al hacer scroll) debe
    # seguir siendo rápido: el formateo es perezoso, por celda.
    started = time.perf_counter()
    for row in range(model.rowCount()):
        for col in range(model.columnCount()):
            model.data(model.index(row, col), Qt.ItemDataRole.DisplayRole)
    render_seconds = time.perf_counter() - started

    assert render_seconds < 2.0


def test_model_is_standalone(qtbot: QtBot) -> None:
    """El modelo puede usarse sin la tabla (útil para pruebas y reutilización)."""
    df = pd.DataFrame({"x": [1, None]})
    model = DataFrameTableModel(df)
    assert model.rowCount() == 2
    assert model.data(model.index(1, 0), Qt.ItemDataRole.DisplayRole) == MISSING_TEXT
    model.set_dataframe(None)
    assert model.rowCount() == 0
