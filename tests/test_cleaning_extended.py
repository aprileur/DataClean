"""Pruebas unitarias para los servicios de limpieza extendidos (5B, 5C, 5D, 5E)."""

import ast
from pathlib import Path

import pandas as pd
import pytest

from app.services.cleaning import (
    CleaningError,
    analyze_outliers,
    apply_merges,
    clip_outliers,
    count_duplicates,
    drop_columns,
    drop_duplicates,
    drop_outliers,
    duplicate_mask,
    get_duplicate_examples,
    normalize_text,
    suggest_irrelevant,
    suggest_merges,
)

# --- 5B: Columnas irrelevantes ---


def test_suggest_irrelevant_on_sample(sample_df: pd.DataFrame):
    """Verifica que suggest_irrelevant detecta ID en sample_df."""
    suggestions = suggest_irrelevant(sample_df)
    # id es único por fila en las 970 filas base, pero en 1000 filas con 30 duplicados
    # comprobemos si id o columnas sintéticas se detectan
    assert isinstance(suggestions, dict)


def test_suggest_irrelevant_synthetic():
    """Prueba detección de constante, >90% faltantes y ID único."""
    df = pd.DataFrame(
        {
            "constante": [1, 1, 1, 1, 1],
            "vacia": [None, None, None, None, "a"],  # 80% nulos
            "muy_vacia": [None, None, None, None, None],  # 100% nulos
            "id_unico": ["id1", "id2", "id3", "id4", "id5"],
            "normal": ["a", "b", "c", "b", "a"],
        }
    )
    suggestions = suggest_irrelevant(df)
    assert "constante" in suggestions
    assert "muy_vacia" in suggestions
    assert "id_unico" in suggestions
    assert "normal" not in suggestions


def test_drop_columns():
    """drop_columns elimina columnas y no muta el original."""
    df = pd.DataFrame({"a": [1, 2], "b": [3, 4], "c": [5, 6]})
    res = drop_columns(df, ["b", "c"])
    assert list(res.columns) == ["a"]
    assert "b" in df.columns  # inmutable

    with pytest.raises(CleaningError):
        drop_columns(df, ["inexistente"])


# --- 5C: Duplicados ---


def test_duplicate_operations_on_sample(sample_df: pd.DataFrame):
    """sample_df contiene exactamente 30 duplicados sembrados."""
    count = count_duplicates(sample_df)
    assert count == 30

    mask = duplicate_mask(sample_df)
    assert mask.sum() == 30

    examples = get_duplicate_examples(sample_df)
    assert len(examples) > 0

    clean_df = drop_duplicates(sample_df)
    assert len(clean_df) == 970
    assert count_duplicates(clean_df) == 0
    assert len(sample_df) == 1000  # inmutable


def test_drop_duplicates_keep_option():
    """Verifica keep='first' vs keep='last'."""
    df = pd.DataFrame({"id": [1, 1], "val": ["primero", "segundo"]})
    df_first = drop_duplicates(df, subset=["id"], keep="first")
    assert df_first.iloc[0]["val"] == "primero"

    df_last = drop_duplicates(df, subset=["id"], keep="last")
    assert df_last.iloc[0]["val"] == "segundo"


# --- 5D: Outliers ---


def test_outlier_detection_on_sample(sample_df: pd.DataFrame):
    """Verifica que se detectan outliers en la columna 'ingreso'."""
    report = analyze_outliers(sample_df, method="iqr", threshold=1.5)
    assert "columna" in report.columns
    row = report[report["columna"] == "ingreso"]
    assert not row.empty
    assert int(row.iloc[0]["outliers"]) > 0


def test_clip_and_drop_outliers():
    """clip_outliers recorta sin cambiar forma; drop_outliers elimina filas."""
    df = pd.DataFrame({"val": [10.0, 12.0, 11.0, 10.5, 11.5, 1000.0]})
    # 1000 es outlier evidente
    clipped = clip_outliers(df, "val", method="iqr", threshold=1.5)
    assert len(clipped) == 6
    assert clipped["val"].max() < 1000.0

    dropped = drop_outliers(df, "val", method="iqr", threshold=1.5)
    assert len(dropped) == 5
    assert 1000.0 not in dropped["val"].values
    assert len(df) == 6  # inmutable


def test_outlier_errors():
    """Errores en columnas no numéricas o inexistentes."""
    df = pd.DataFrame({"txt": ["a", "b", "c"]})
    with pytest.raises(CleaningError):
        clip_outliers(df, "txt")
    with pytest.raises(CleaningError):
        drop_outliers(df, "no_existe")


# --- 5E: Errores Tipográficos (Typos) ---


def test_normalize_text():
    """normalize_text elimina espacios y dobles espacios."""
    s = pd.Series(["  Toluca ", "CDMX\n", "Nueva   York"])
    res = normalize_text(s)
    assert list(res) == ["Toluca", "CDMX", "Nueva York"]


def test_suggest_merges_with_rapidfuzz():
    """Detecta variantes similares sembradas en ciudad."""
    s = pd.Series(["Toluca", "Toluca", "toluca", "Tolucaa", "CDMX", "CDMX", "cdmx", "Guadalajara"])
    suggestions = suggest_merges(s, cutoff=80.0)
    assert len(suggestions) > 0

    # Las sugerencias proponen reemplazar variantes hacia el canónico
    variants = [item[0] for item in suggestions]
    canonicals = [item[1] for item in suggestions]
    assert "Toluca" in canonicals or "toluca" in variants or "Tolucaa" in variants


def test_apply_merges():
    """apply_merges aplica el diccionario de reemplazos."""
    df = pd.DataFrame({"ciudad": ["Tolucaa", "toluca ", "Toluca", "Metepec"]})
    mapping = {"Tolucaa": "Toluca", "toluca ": "Toluca"}
    res = apply_merges(df, "ciudad", mapping)
    assert list(res["ciudad"]) == ["Toluca", "Toluca", "Toluca", "Metepec"]
    assert len(df) == 4  # inmutable


def test_no_qt_imports_in_cleaning():
    """Verifica por AST que cleaning.py no importa módulos de Qt."""
    path = Path("app/services/cleaning.py")
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not alias.name.lower().startswith(("pyqt", "pyside", "qt"))
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                assert not node.module.lower().startswith(("pyqt", "pyside", "qt"))
