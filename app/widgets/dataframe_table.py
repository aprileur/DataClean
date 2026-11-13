"""Tabla reutilizable de solo lectura para mostrar un `pd.DataFrame`.

El modelo formatea las celdas (miles para números, "—" para faltantes),
alinea el contenido según su tipo y colorea el encabezado según la columna
sea numérica (rosa) o categórica (verde). La tabla usa layouts de Qt, tiene
scroll propio y se expande con la ventana.
"""

from __future__ import annotations

import numbers
from typing import Any

import pandas as pd
from PySide6.QtCore import QAbstractTableModel, QModelIndex, QObject, Qt
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QSizePolicy,
    QTableView,
    QWidget,
)

#: Texto mostrado en celdas con valores faltantes.
MISSING_TEXT = "—"

#: Fondo de encabezado para columnas numéricas (rosa suave).
NUMERIC_HEADER_COLOR = "#FCE7F3"

#: Fondo de encabezado para columnas categóricas, de texto u otras (verde claro).
CATEGORICAL_HEADER_COLOR = "#DCFCE7"


def is_missing_value(value: Any) -> bool:
    """Indica si un valor escalar debe mostrarse como faltante.

    Cubre `None`, `pd.NA`, `pd.NaT`, `NaN` y variantes de NumPy. Para valores
    no escalares (listas, arrays) retorna `False` en lugar de fallar.
    """
    if value is None or value is pd.NA or value is pd.NaT:
        return True
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def format_cell_value(value: Any) -> str:
    """Devuelve el texto a mostrar en una celda de la tabla.

    - Faltantes (`NaN`, `None`, `pd.NA`, ...) -> "—".
    - Enteros -> separador de miles (ej. `1,000`).
    - Flotantes -> separador de miles y 2 decimales (ej. `25,400.50`).
    - Booleanos y texto -> representación textual habitual.
    """
    if is_missing_value(value):
        return MISSING_TEXT
    if isinstance(value, bool):
        return "True" if value else "False"
    if isinstance(value, numbers.Integral):
        return f"{int(value):,}"
    if isinstance(value, numbers.Real):
        return f"{float(value):,.2f}"
    return str(value)


def is_numeric_column(dtype: object) -> bool:
    """Indica si un dtype corresponde a una columna numérica.

    `bool` se considera categórico (coherente con `services.profiling`),
    aunque `pandas.api.types.is_numeric_dtype` lo marque como numérico.
    """
    if pd.api.types.is_bool_dtype(dtype):
        return False
    return bool(pd.api.types.is_numeric_dtype(dtype))


def text_alignment(value: Any) -> Qt.AlignmentFlag:
    """Alineación de una celda: derecha para números, izquierda para texto."""
    if is_missing_value(value):
        return Qt.AlignmentFlag.AlignCenter
    if isinstance(value, bool):
        return Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
    if isinstance(value, numbers.Real):
        return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
    return Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter


class DataFrameTableModel(QAbstractTableModel):
    """Modelo Qt de solo lectura que expone un `pd.DataFrame`."""

    def __init__(self, df: pd.DataFrame | None = None, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._df: pd.DataFrame | None = None
        self._numeric_columns: list[bool] = []
        if df is not None:
            self.set_dataframe(df)

    # -- API pública ------------------------------------------------------- #

    @property
    def dataframe(self) -> pd.DataFrame | None:
        """DataFrame actualmente mostrado (o `None` si no hay datos)."""
        return self._df

    def set_dataframe(self, df: pd.DataFrame | None) -> None:
        """Reemplaza el DataFrame mostrado y notifica a las vistas."""
        self.beginResetModel()
        self._df = df
        self._numeric_columns = [] if df is None else [is_numeric_column(d) for d in df.dtypes]
        self.endResetModel()

    # -- QAbstractTableModel ----------------------------------------------- #

    def rowCount(self, parent: QModelIndex | None = None) -> int:  # noqa: N802 (API Qt)
        if self._df is None or (parent is not None and parent.isValid()):
            return 0
        return int(len(self._df))

    def columnCount(self, parent: QModelIndex | None = None) -> int:  # noqa: N802 (API Qt)
        if self._df is None or (parent is not None and parent.isValid()):
            return 0
        return int(self._df.shape[1])

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid() or self._df is None:
            return None

        row, col = index.row(), index.column()
        value = self._df.iat[row, col]

        if role == Qt.ItemDataRole.DisplayRole:
            return format_cell_value(value)
        if role == Qt.ItemDataRole.TextAlignmentRole:
            return text_alignment(value)
        return None

    def headerData(  # noqa: N802 (API Qt)
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        if self._df is None:
            return None

        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                if 0 <= section < len(self._df.columns):
                    return str(self._df.columns[section])
                return None
            return section + 1

        if role == Qt.ItemDataRole.BackgroundRole:
            if orientation == Qt.Orientation.Horizontal and 0 <= section < len(
                self._numeric_columns
            ):
                color = (
                    NUMERIC_HEADER_COLOR
                    if self._numeric_columns[section]
                    else CATEGORICAL_HEADER_COLOR
                )
                return QBrush(QColor(color))
            return None

        if role == Qt.ItemDataRole.TextAlignmentRole and orientation == Qt.Orientation.Vertical:
            return Qt.AlignmentFlag.AlignCenter

        return None

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable


class DataFrameTable(QTableView):
    """Vista de tabla de solo lectura para un `pd.DataFrame`.

    Se expande con la ventana (`QSizePolicy.Expanding`) y gestiona su propio
    scroll; no permite editar celdas.
    """

    def __init__(self, df: pd.DataFrame | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("dataFrameTable")

        self._table_model = DataFrameTableModel(df, self)
        self.setModel(self._table_model)

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setAlternatingRowColors(True)
        self.setWordWrap(False)
        self.setSortingEnabled(False)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)

        horizontal = self.horizontalHeader()
        horizontal.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        horizontal.setDefaultSectionSize(140)
        horizontal.setStretchLastSection(True)
        horizontal.setHighlightSections(False)

        vertical = self.verticalHeader()
        vertical.setDefaultSectionSize(26)
        vertical.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        vertical.setHighlightSections(False)

    # -- API pública ------------------------------------------------------- #

    @property
    def dataframe(self) -> pd.DataFrame | None:
        """DataFrame actualmente mostrado (o `None` si no hay datos)."""
        return self._table_model.dataframe

    @property
    def table_model(self) -> DataFrameTableModel:
        """Modelo tipado de la tabla (evita casts al usar `model()`)."""
        return self._table_model

    def set_dataframe(self, df: pd.DataFrame | None) -> None:
        """Reemplaza el DataFrame mostrado y ajusta la vista."""
        self._table_model.set_dataframe(df)
        # Ajuste automático solo en datasets pequeños: recorrer 10k filas para
        # calcular anchos bloquearía la interfaz sin aportar valor.
        if df is not None and len(df) <= 200:
            self.resizeColumnsToContents()
        self.scrollToTop()
