"""Pruebas del servicio de limpieza: datos faltantes (tarea T11)."""

from __future__ import annotations

import ast
from pathlib import Path

import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from app.services import cleaning
from app.services.cleaning import CleaningError

# Módulos que el servicio (lógica pura) no debe importar nunca.
FORBIDDEN_MODULES = ("PySide6", "PyQt5", "PyQt6", "qtpy")


# ------------------------------------------------------------------ reporte


def test_missing_report_only_with_missing(sample_df: pd.DataFrame) -> None:
    report = cleaning.missing_report(sample_df)

    assert list(report.columns) == ["columna", "faltantes", "porcentaje"]
    assert len(report) > 0
    assert (report["faltantes"] > 0).all()
    assert report["faltantes"].is_monotonic_decreasing
    assert report["faltantes"].sum() == int(sample_df.isna().sum().sum())

    recalculated = (report["faltantes"] / len(sample_df) * 100).round(2)
    assert (report["porcentaje"] == recalculated).all()


def test_missing_report_all_columns(sample_df: pd.DataFrame) -> None:
    report = cleaning.missing_report(sample_df, only_with_missing=False)

    assert len(report) == len(sample_df.columns)
    assert set(report["columna"]) == {str(name) for name in sample_df.columns}
    assert (report["faltantes"] >= 0).all()


def test_missing_report_empty_df() -> None:
    report = cleaning.missing_report(pd.DataFrame())

    assert report.empty
    assert list(report.columns) == ["columna", "faltantes", "porcentaje"]


def test_missing_union_counts_rows_once(overlap_missing_df: pd.DataFrame) -> None:
    rows, percentage = cleaning.missing_union(overlap_missing_df)

    per_column_sum = int(overlap_missing_df.isna().sum().sum())
    assert rows == 3
    assert rows < per_column_sum  # la unión no suma filas repetidas
    assert percentage == round(3 / len(overlap_missing_df) * 100, 2)


def test_missing_union_with_sample_df(sample_df: pd.DataFrame) -> None:
    rows, percentage = cleaning.missing_union(sample_df)

    expected_rows = int(sample_df.isna().any(axis=1).sum())
    assert rows == expected_rows
    assert percentage == round(expected_rows / len(sample_df) * 100, 2)
    # Hay filas con más de un hueco: la unión es menor que la suma por columna.
    assert rows < int(sample_df.isna().sum().sum())


def test_missing_union_no_missing_and_empty(sample_df: pd.DataFrame) -> None:
    assert cleaning.missing_union(sample_df.dropna()) == (0, 0.0)
    assert cleaning.missing_union(pd.DataFrame()) == (0, 0.0)


# ------------------------------------------------------------------ drop


def test_drop_missing_rows_removes_only_incomplete_rows(
    overlap_missing_df: pd.DataFrame,
) -> None:
    original = overlap_missing_df.copy(deep=True)

    result = cleaning.drop_missing_rows(overlap_missing_df)

    assert len(result) == 3
    assert not result.isna().any().any()
    assert_frame_equal(result, original.dropna())
    # El DataFrame de entrada no se muta y el resultado es una copia nueva.
    assert_frame_equal(overlap_missing_df, original)
    assert result is not overlap_missing_df


def test_drop_missing_rows_with_sample_df(sample_df: pd.DataFrame) -> None:
    original = sample_df.copy(deep=True)
    expected_rows = len(sample_df) - cleaning.missing_union(sample_df)[0]

    result = cleaning.drop_missing_rows(sample_df)

    assert len(result) == expected_rows
    assert not result.isna().any().any()
    assert_frame_equal(sample_df, original)


def test_drop_missing_rows_empty_df(empty_df: pd.DataFrame) -> None:
    result = cleaning.drop_missing_rows(empty_df)

    assert result.empty
    assert list(result.columns) == list(empty_df.columns)


# ------------------------------------------------------------------ imputación


def test_impute_mean_on_numeric_column(sample_df: pd.DataFrame) -> None:
    original = sample_df.copy(deep=True)
    expected = sample_df["edad"].mean()

    result = cleaning.impute_column(sample_df, "edad", "mean")

    assert result["edad"].isna().sum() == 0
    assert (result["edad"] == expected).sum() == int(original["edad"].isna().sum())
    # Las demás columnas quedan intactas y el original no se muta.
    assert_frame_equal(result.drop(columns="edad"), original.drop(columns="edad"))
    assert_frame_equal(sample_df, original)
    assert result is not sample_df


def test_impute_median_on_numeric_column(sample_df: pd.DataFrame) -> None:
    expected = sample_df["gastos"].median()

    result = cleaning.impute_column(sample_df, "gastos", "median")

    assert result["gastos"].isna().sum() == 0
    assert (result["gastos"] == expected).sum() == int(sample_df["gastos"].isna().sum())


def test_impute_mode_on_categorical_column(sample_df: pd.DataFrame) -> None:
    expected = sample_df["ciudad"].mode().iloc[0]

    result = cleaning.impute_column(sample_df, "ciudad", "mode")

    assert result["ciudad"].isna().sum() == 0
    assert (result["ciudad"] == expected).sum() >= int(sample_df["ciudad"].isna().sum())


def test_impute_constant_on_categorical_column(sample_df: pd.DataFrame) -> None:
    result = cleaning.impute_column(sample_df, "ciudad", "constant", fill_value="Desconocido")

    assert result["ciudad"].isna().sum() == 0
    assert (result["ciudad"] == "Desconocido").sum() == int(sample_df["ciudad"].isna().sum())


def test_impute_constant_defaults_by_dtype(sample_df: pd.DataFrame) -> None:
    categorical = cleaning.impute_column(sample_df, "tipocliente", "constant")
    numeric = cleaning.impute_column(sample_df, "edad", "constant")

    assert (categorical["tipocliente"] == cleaning.UNKNOWN_VALUE).sum() == int(
        sample_df["tipocliente"].isna().sum()
    )
    assert (numeric["edad"] == 0).sum() >= int(sample_df["edad"].isna().sum())


def test_impute_mode_on_fully_empty_column_uses_unknown() -> None:
    df = pd.DataFrame({"vacia": pd.Series([None, None, None], dtype="str")})

    result = cleaning.impute_column(df, "vacia", "mode")

    assert result["vacia"].isna().sum() == 0
    assert set(result["vacia"]) == {cleaning.UNKNOWN_VALUE}


def test_impute_mean_on_fully_empty_numeric_column_uses_zero() -> None:
    df = pd.DataFrame({"vacia": pd.Series([None, None], dtype="float64")})

    result = cleaning.impute_column(df, "vacia", "mean")

    assert result["vacia"].isna().sum() == 0
    assert (result["vacia"] == 0).all()


def test_impute_mean_on_non_numeric_column_raises(sample_df: pd.DataFrame) -> None:
    with pytest.raises(CleaningError, match="no es numérica"):
        cleaning.impute_column(sample_df, "ciudad", "mean")

    with pytest.raises(CleaningError, match="mediana"):
        cleaning.impute_column(sample_df, "genero", "median")


def test_impute_unknown_column_raises(sample_df: pd.DataFrame) -> None:
    with pytest.raises(CleaningError, match="no existe"):
        cleaning.impute_column(sample_df, "columna_fantasma", "mode")


def test_impute_invalid_strategy_raises(sample_df: pd.DataFrame) -> None:
    with pytest.raises(CleaningError, match="no válida"):
        cleaning.impute_column(sample_df, "edad", "promedio")

    with pytest.raises(CleaningError, match="no válida"):
        cleaning.impute_column(sample_df, "edad", "")


def test_impute_without_missing_values_is_a_noop(sample_df: pd.DataFrame) -> None:
    result = cleaning.impute_column(sample_df, "genero", "mode")

    assert_frame_equal(result, sample_df)


# ------------------------------------------------------------------ heatmap


def test_heatmap_sample_limits_rows_and_returns_booleans(sample_df: pd.DataFrame) -> None:
    mask = cleaning.heatmap_sample(sample_df, max_rows=100)

    assert isinstance(mask, pd.DataFrame)
    assert len(mask) <= 100
    assert list(mask.columns) == list(sample_df.columns)
    assert all(pd.api.types.is_bool_dtype(dtype) for dtype in mask.dtypes)
    # Las filas conservan el índice original del dataset.
    assert mask.index.isin(sample_df.index).all()
    # El número de faltantes es coherente con las filas muestreadas.
    assert int(mask.to_numpy().sum()) == int(sample_df.loc[mask.index].isna().to_numpy().sum())


def test_heatmap_sample_is_deterministic(sample_df: pd.DataFrame) -> None:
    first = cleaning.heatmap_sample(sample_df, max_rows=50)
    second = cleaning.heatmap_sample(sample_df, max_rows=50)

    assert_frame_equal(first, second)
    assert list(first.index) == sorted(first.index)


def test_heatmap_sample_small_df_returns_full_mask(overlap_missing_df: pd.DataFrame) -> None:
    mask = cleaning.heatmap_sample(overlap_missing_df)

    assert_frame_equal(mask, overlap_missing_df.isna())
    assert len(mask) == len(overlap_missing_df)


def test_heatmap_sample_invalid_max_rows_raises(overlap_missing_df: pd.DataFrame) -> None:
    with pytest.raises(CleaningError, match="positivo"):
        cleaning.heatmap_sample(overlap_missing_df, max_rows=0)


# ------------------------------------------------------------------ reglas


def test_cleaning_does_not_import_qt() -> None:
    source = Path(cleaning.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not any(alias.name.startswith(mod) for mod in FORBIDDEN_MODULES), alias.name
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            assert not any(module.startswith(mod) for mod in FORBIDDEN_MODULES), module
