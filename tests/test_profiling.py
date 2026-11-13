"""Pruebas del servicio de perfilado (tarea T07)."""

from __future__ import annotations

import ast
from pathlib import Path

import pandas as pd

from app.services import profiling

# Contenido que no debe aparecer en los imports del servicio.
FORBIDDEN_MODULES = ("PySide6", "PyQt5", "PyQt6", "qtpy")


# ---------------------------------------------------------------- shape/memoria


def test_dataset_shape_with_sample_df(sample_df: pd.DataFrame) -> None:
    assert profiling.dataset_shape(sample_df) == sample_df.shape
    assert profiling.dataset_shape(sample_df)[1] == 8  # 8 columnas del dataset de ejemplo


def test_row_and_column_count(sample_df: pd.DataFrame) -> None:
    assert profiling.row_count(sample_df) == sample_df.shape[0]
    assert profiling.column_count(sample_df) == sample_df.shape[1]
    assert profiling.row_count(sample_df) > 0


def test_memory_usage_formats_by_size() -> None:
    assert profiling._format_bytes(500) == "500 B"
    assert profiling._format_bytes(1024) == "1.0 KB"
    assert profiling._format_bytes(1536) == "1.5 KB"
    assert profiling._format_bytes(1024 * 1024) == "1.0 MB"
    assert profiling._format_bytes(int(1.2 * 1024**2)) == "1.2 MB"
    assert profiling._format_bytes(450 * 1024) == "450.0 KB"
    assert profiling._format_bytes(12.4 * 1024**3) == "12.4 GB"
    assert profiling._format_bytes(1024**4 * 2) == "2.0 TB"


def test_memory_usage_returns_string_for_df(sample_df: pd.DataFrame) -> None:
    text = profiling.memory_usage(sample_df)
    assert isinstance(text, str)
    assert text.endswith(("B", "KB", "MB", "GB", "TB"))


# ---------------------------------------------------------------- clasificación


def test_classify_columns_with_all_dtypes() -> None:
    df = pd.DataFrame(
        {
            "entero": pd.Series([1, 2, 3], dtype="int64"),
            "flotante": pd.Series([1.5, 2.5, 3.5], dtype="float64"),
            "texto_objeto": pd.Series(["a", "b", "c"], dtype=object),
            "texto_str": pd.Series(["a", "b", "c"], dtype="str"),
            "categoria": pd.Series(["x", "y", "x"], dtype="category"),
            "booleano": pd.Series([True, False, True], dtype="bool"),
            "fecha": pd.Series(pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"])),
            "complejo": pd.Series([1 + 1j, 2 + 2j, 3 + 3j]),
            "intervalo": pd.Series(pd.arrays.IntervalArray.from_breaks([0, 1, 2, 3])),
        }
    )
    types = profiling.classify_columns(df)

    assert types.numeric == ["entero", "flotante", "complejo"]
    assert types.categorical == ["texto_objeto", "texto_str", "categoria", "booleano"]
    assert types.datetime == ["fecha"]
    assert types.other == ["intervalo"]


def test_classify_columns_excludes_bool_from_numeric() -> None:
    df = pd.DataFrame({"flag": pd.Series([True, False], dtype="bool")})
    types = profiling.classify_columns(df)
    assert "flag" not in types.numeric
    assert "flag" in types.categorical


def test_classify_columns_datetime_tz_aware() -> None:
    df = pd.DataFrame({"ts": pd.Series(pd.to_datetime(["2024-01-01", "2024-06-01"], utc=True))})
    types = profiling.classify_columns(df)
    assert types.datetime == ["ts"]


def test_classify_columns_empty_df(empty_df: pd.DataFrame) -> None:
    types = profiling.classify_columns(empty_df)
    assert types.numeric == ["id", "edad", "ingreso", "gastos"]
    assert types.categorical == ["genero", "ciudad", "estado", "tipocliente"]
    assert types.datetime == []
    assert types.other == []


# ---------------------------------------------------------------- faltantes


def test_missing_summary_only_with_missing(sample_df: pd.DataFrame) -> None:
    summary = profiling.missing_summary(sample_df)
    assert list(summary.columns) == ["columna", "faltantes", "porcentaje"]
    assert len(summary) > 0
    assert (summary["faltantes"] > 0).all()
    # Ordenado descendente por faltantes.
    assert summary["faltantes"].is_monotonic_decreasing
    assert summary["faltantes"].sum() == int(sample_df.isna().sum().sum())
    # Porcentajes consistentes con el total de filas.
    recalculated = (summary["faltantes"] / len(sample_df) * 100).round(2)
    assert (summary["porcentaje"] == recalculated).all()


def test_missing_summary_all_columns(sample_df: pd.DataFrame) -> None:
    summary = profiling.missing_summary(sample_df, only_with_missing=False)
    assert len(summary) == len(sample_df.columns)
    assert (summary["faltantes"] >= 0).all()
    assert summary["faltantes"].is_monotonic_decreasing


def test_missing_row_union_counts_rows_once(overlap_missing_df: pd.DataFrame) -> None:
    union_rows, percentage = profiling.missing_row_union(overlap_missing_df)

    per_column_sum = int(overlap_missing_df.isna().sum().sum())
    assert union_rows < per_column_sum
    assert union_rows == 3
    assert percentage == round(3 / len(overlap_missing_df) * 100, 2)


def test_missing_row_union_no_missing(sample_df: pd.DataFrame) -> None:
    clean = sample_df.dropna()
    rows, percentage = profiling.missing_row_union(clean)
    assert rows == 0
    assert percentage == 0.0


def test_missing_row_union_empty_df() -> None:
    assert profiling.missing_row_union(pd.DataFrame()) == (0, 0.0)


def test_missing_summary_empty_df() -> None:
    summary = profiling.missing_summary(pd.DataFrame())
    assert len(summary) == 0
    assert list(summary.columns) == ["columna", "faltantes", "porcentaje"]


# ---------------------------------------------------------------- looks_like_id


def test_looks_like_id_with_sequential_id() -> None:
    series = pd.Series(range(1, 101), dtype="int64")
    assert profiling.looks_like_id(series) is True


def test_looks_like_id_with_repeated_ages() -> None:
    ages = pd.Series([25, 30, 35, 40] * 25, dtype="int64")
    assert profiling.looks_like_id(ages) is False


def test_looks_like_id_with_categories() -> None:
    categories = pd.Series(["sur"] * 50 + ["norte"] * 50, dtype="str")
    assert profiling.looks_like_id(categories) is False


def test_looks_like_id_with_unique_strings() -> None:
    values = pd.Series(f"cliente-{i}" for i in range(100))
    assert profiling.looks_like_id(values) is True


def test_looks_like_id_edge_cases() -> None:
    assert profiling.looks_like_id(pd.Series([], dtype="int64")) is False
    # Muchos nulos: no puede ser un ID fiable.
    half_nulls = pd.Series([None] * 50 + list(range(50)), dtype="Int64")
    assert profiling.looks_like_id(half_nulls) is False


def test_sample_id_looks_like_id(sample_df: pd.DataFrame) -> None:
    assert profiling.looks_like_id(sample_df["id"]) is True


# ---------------------------------------------------------------- reglas


def test_profiling_does_not_import_qt() -> None:
    source = Path(profiling.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not any(alias.name.startswith(mod) for mod in FORBIDDEN_MODULES), alias.name
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            assert not any(module.startswith(mod) for mod in FORBIDDEN_MODULES), module
