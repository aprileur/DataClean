"""Pruebas del dataset de ejemplo y de las fixtures compartidas (tarea T04)."""

from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

import pandas as pd

from tests.conftest import EXPECTED_COLUMNS

MAX_SIZE_BYTES = 200 * 1024
SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "generate_sample.py"


def _run_generator(output: Path) -> None:
    """Ejecuta el script generador en un subproceso escribiendo en `output`."""
    subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--output", str(output)],
        check=True,
        capture_output=True,
        text=True,
    )


def _sha256(path: Path) -> str:
    """Hash SHA-256 del archivo, para comparar contenidos byte por byte."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_sample_file_exists_and_is_small(sample_path: Path) -> None:
    """El CSV existe, no está vacío y pesa menos de 200 KB."""
    assert sample_path.is_file()
    size = sample_path.stat().st_size
    assert size > 0
    assert size < MAX_SIZE_BYTES


def test_sample_has_expected_shape_and_columns(sample_df: pd.DataFrame) -> None:
    """El dataset tiene exactamente 1000 filas y las 8 columnas esperadas, en orden."""
    assert sample_df.shape == (1000, 8)
    assert list(sample_df.columns) == list(EXPECTED_COLUMNS)


def test_sample_has_thirty_exact_duplicates(sample_df: pd.DataFrame) -> None:
    """Hay 30 duplicados exactos sembrados a propósito."""
    assert int(sample_df.duplicated().sum()) == 30


def test_sample_ids_are_sequential_and_repeated_for_duplicates(sample_df: pd.DataFrame) -> None:
    """Los ids van de 1 a 970 y las 30 filas duplicadas repiten el id de su original."""
    assert sorted(sample_df["id"].unique()) == list(range(1, 971))
    assert int((sample_df["id"].value_counts() > 1).sum()) == 30


def test_sample_has_missing_values_in_several_columns(sample_df: pd.DataFrame) -> None:
    """Hay faltantes en más de una columna y la unión de filas es menor que la suma."""
    missing_per_column = sample_df.isna().sum()
    columns_with_missing = missing_per_column[missing_per_column > 0]

    assert len(columns_with_missing) >= 2

    missing_sum = int(columns_with_missing.sum())
    missing_union = int(sample_df.isna().any(axis=1).sum())

    assert missing_union == 50
    assert missing_union < missing_sum
    assert 0.04 <= missing_union / len(sample_df) <= 0.06


def test_sample_has_rows_with_overlapping_missing_values(sample_df: pd.DataFrame) -> None:
    """Existen filas con dos faltantes (edad y gastos) para probar la unión vs la suma."""
    missing_per_row = sample_df.isna().sum(axis=1)
    rows_with_two = sample_df[missing_per_row >= 2]

    assert len(rows_with_two) >= 1
    for _, row in rows_with_two.iterrows():
        assert pd.isna(row["edad"])
        assert pd.isna(row["gastos"])


def test_sample_has_ingreso_outliers(sample_df: pd.DataFrame) -> None:
    """Hay outliers en `ingreso` por encima del límite Q3 + 3 * IQR."""
    ingreso = sample_df["ingreso"].dropna()
    q1, q3 = ingreso.quantile([0.25, 0.75])
    iqr = q3 - q1

    outliers = ingreso[ingreso > q3 + 3 * iqr]

    assert len(outliers) >= 10
    assert outliers.max() > 100_000


def test_sample_has_ciudad_typo_variants(sample_df: pd.DataFrame) -> None:
    """`ciudad` contiene variantes tipográficas de Toluca y CDMX que colapsan al normalizar."""
    ciudades = sample_df["ciudad"].dropna()
    values = set(ciudades.unique())

    assert {"Toluca", "toluca ", "Tolucaa", "CDMX", "cdmx"}.issubset(values)

    normalized = ciudades.str.strip().str.casefold()
    assert normalized.nunique() < ciudades.nunique()


def test_generator_is_idempotent(tmp_path: Path, sample_path: Path) -> None:
    """Dos ejecuciones del script producen el mismo archivo y coinciden con el commiteado."""
    first = tmp_path / "run1.csv"
    second = tmp_path / "run2.csv"

    _run_generator(first)
    _run_generator(second)

    # Idempotencia estricta: mismo contenido byte por byte entre ejecuciones.
    assert _sha256(first) == _sha256(second)

    # El CSV commiteado debe ser el que produce el script (se compara el contenido,
    # no los bytes, porque git puede convertir los finales de línea al hacer checkout).
    pd.testing.assert_frame_equal(pd.read_csv(first), pd.read_csv(sample_path))


def test_fixtures_are_consistent(
    sample_path: Path,
    sample_df: pd.DataFrame,
    empty_df: pd.DataFrame,
    overlap_missing_df: pd.DataFrame,
) -> None:
    """Las fixtures compartidas tienen la forma y las propiedades que esperan los tests."""
    assert sample_path.name == "sample.csv"
    assert not sample_df.empty

    assert empty_df.empty
    assert empty_df.shape == (0, len(EXPECTED_COLUMNS))
    assert list(empty_df.columns) == list(EXPECTED_COLUMNS)

    missing_sum = int(overlap_missing_df.isna().sum().sum())
    missing_union = int(overlap_missing_df.isna().any(axis=1).sum())
    assert missing_sum == 4
    assert missing_union == 3
    assert missing_union < missing_sum
