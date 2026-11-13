"""Fixtures compartidas por la suite de pruebas de DataClean."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

DATA_DIR = Path(__file__).resolve().parent / "data"
SAMPLE_CSV = DATA_DIR / "sample.csv"

# Orden exacto de las columnas del dataset de ejemplo (ver scripts/generate_sample.py).
EXPECTED_COLUMNS = (
    "id",
    "edad",
    "genero",
    "ingreso",
    "gastos",
    "ciudad",
    "estado",
    "tipocliente",
)


@pytest.fixture()
def sample_path() -> Path:
    """Ruta al dataset de ejemplo commiteado (`tests/data/sample.csv`)."""
    return SAMPLE_CSV


@pytest.fixture()
def sample_df(sample_path: Path) -> pd.DataFrame:
    """DataFrame cargado desde `sample.csv`; cada test recibe una copia nueva."""
    return pd.read_csv(sample_path)


@pytest.fixture()
def empty_df() -> pd.DataFrame:
    """DataFrame sin filas pero con las columnas y tipos esperados del dataset."""
    return pd.DataFrame(
        {
            "id": pd.Series(dtype="int64"),
            "edad": pd.Series(dtype="float64"),
            "genero": pd.Series(dtype="str"),
            "ingreso": pd.Series(dtype="float64"),
            "gastos": pd.Series(dtype="float64"),
            "ciudad": pd.Series(dtype="str"),
            "estado": pd.Series(dtype="str"),
            "tipocliente": pd.Series(dtype="str"),
        }
    )


@pytest.fixture()
def overlap_missing_df() -> pd.DataFrame:
    """DataFrame con faltantes solapados: la unión de filas es menor que la suma por columna.

    Columna `a`: 2 faltantes (filas 1 y 3).
    Columna `b`: 2 faltantes (filas 0 y 1).
    Suma = 4, pero solo 3 filas distintas tienen algún faltante.
    """
    return pd.DataFrame(
        {
            "a": [1.0, None, 3.0, None, 5.0, 6.0],
            "b": [None, None, 3.0, 4.0, 5.0, 6.0],
            "c": ["x", "y", "z", "w", "v", "u"],
        }
    )
