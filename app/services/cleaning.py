"""Limpieza del dataset: servicios puros para los pasos 5A–5E.

Este módulo es lógica pura: **no** importa Qt ni conoce la interfaz gráfica.
Todas las funciones reciben un `pd.DataFrame` y devuelven un DataFrame nuevo
(o una máscara nueva), sin mutar nunca el DataFrame de entrada.

Los errores de cara al usuario se lanzan como `CleaningError` con un mensaje
en español, listo para mostrarse en un diálogo.
"""

from __future__ import annotations

import logging
from typing import Any, Final

import pandas as pd
from rapidfuzz import fuzz

from app.services import profiling
from app.ui import texts_es

logger = logging.getLogger(__name__)

#: Estrategias de imputación aceptadas por `impute_column`.
IMPUTATION_STRATEGIES: Final[tuple[str, ...]] = ("mean", "median", "mode", "constant")

#: Valor usado cuando no se puede calcular una moda ni hay valor constante.
UNKNOWN_VALUE: Final[str] = "Desconocido"

#: Semilla fija para que la muestra del mapa de calor sea reproducible.
HEATMAP_RANDOM_STATE: Final[int] = 42

#: Filas máximas que se dibujan por defecto en el mapa de calor.
HEATMAP_MAX_ROWS: Final[int] = 100


class CleaningError(Exception):
    """Error de limpieza con un mensaje descriptivo listo para el usuario."""


# --------------------------------------------------------------------------- #
# Sub-paso 5A: Datos Faltantes
# --------------------------------------------------------------------------- #


def missing_report(df: pd.DataFrame, only_with_missing: bool = True) -> pd.DataFrame:
    """Resumen de datos faltantes por columna."""
    return profiling.missing_summary(df, only_with_missing=only_with_missing)


def missing_union(df: pd.DataFrame) -> tuple[int, float]:
    """Filas con al menos un valor faltante (unión, no suma por columna)."""
    return profiling.missing_row_union(df)


def drop_missing_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Devuelve una copia del dataset sin las filas que tengan algún faltante."""
    return df.dropna().copy()


def impute_column(
    df: pd.DataFrame,
    column: str,
    strategy: str,
    fill_value: Any = None,
) -> pd.DataFrame:
    """Imputa los valores faltantes de `column` y devuelve una copia del dataset."""
    normalized = strategy.strip().lower() if isinstance(strategy, str) else ""
    if normalized not in IMPUTATION_STRATEGIES:
        allowed = ", ".join(IMPUTATION_STRATEGIES)
        raise CleaningError(
            f"Estrategia de imputación no válida: «{strategy}». Usa una de: {allowed}."
        )

    if column not in df.columns:
        raise CleaningError(
            f"La columna «{column}» no existe en el dataset. "
            "Revisa el nombre o actualiza la lista de columnas."
        )

    result = df.copy()
    series = result[column]
    is_numeric = pd.api.types.is_numeric_dtype(series.dtype)

    if normalized in ("mean", "median") and not is_numeric:
        raise CleaningError(
            f"No se puede calcular la {'media' if normalized == 'mean' else 'mediana'} "
            f"de la columna «{column}» porque no es numérica. "
            "Usa la estrategia «moda» o «constante» para columnas categóricas."
        )

    value = _imputation_value(series, normalized, fill_value, is_numeric)
    result[column] = _fill_series(series, value)

    logger.debug(
        "Columna %r imputada con estrategia %r (valor=%r, faltantes=%s)",
        column,
        normalized,
        value,
        int(series.isna().sum()),
    )
    return result


def heatmap_sample(df: pd.DataFrame, max_rows: int = HEATMAP_MAX_ROWS) -> pd.DataFrame:
    """Máscara booleana de faltantes lista para dibujar el mapa de calor."""
    if max_rows < 1:
        raise CleaningError(
            f"El número máximo de filas del mapa de calor debe ser positivo (recibido: {max_rows})."
        )

    if len(df) <= max_rows:
        return df.isna().copy()

    sample = df.sample(n=max_rows, random_state=HEATMAP_RANDOM_STATE)
    return sample.sort_index().isna()


# --------------------------------------------------------------------------- #
# Sub-paso 5B: Columnas Irrelevantes
# --------------------------------------------------------------------------- #


def suggest_irrelevant(df: pd.DataFrame) -> dict[str, str]:
    """Sugiere columnas candidatas a ser eliminadas por irrelevancia.

    Criterios automáticos de sugerencia:
    - Columna constante (un solo valor único, incluyendo nulos).
    - Columna con más del 90% de valores faltantes.
    - Columna con un valor único por fila (posibles identificadores / IDs).

    Returns:
        Diccionario {nombre_columna: razon_en_espanol}.
    """
    suggestions: dict[str, str] = {}
    total_rows = len(df)
    if total_rows == 0:
        return suggestions

    for col in df.columns:
        series = df[col]
        # 1. Columna con > 90% de valores faltantes
        missing_pct = series.isna().mean()
        if missing_pct > 0.90:
            suggestions[col] = texts_es.IRRELEVANT_SUGGESTION_EMPTY
            continue

        # 2. Columna constante (1 solo valor único)
        unique_count_with_na = series.nunique(dropna=False)
        if unique_count_with_na <= 1:
            suggestions[col] = texts_es.IRRELEVANT_SUGGESTION_CONST
            continue

        # 3. Posible ID único por fila (todos valores únicos y sin nulos)
        if total_rows > 1 and series.nunique(dropna=True) == total_rows:
            suggestions[col] = texts_es.IRRELEVANT_SUGGESTION_ID

    return suggestions


def drop_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Elimina las columnas especificadas y devuelve una copia del DataFrame."""
    if not columns:
        return df.copy()

    missing = [c for c in columns if c not in df.columns]
    if missing:
        raise CleaningError(
            f"Las siguientes columnas no existen en el dataset: {', '.join(missing)}."
        )

    return df.drop(columns=columns).copy()


# --------------------------------------------------------------------------- #
# Sub-paso 5C: Registros Repetidos
# --------------------------------------------------------------------------- #


def duplicate_mask(
    df: pd.DataFrame, subset: list[str] | None = None, keep: str = "first"
) -> pd.Series:
    """Devuelve máscara booleana (`True` = registro duplicado a descartar)."""
    valid_keep = keep if keep in ("first", "last", False) else "first"
    cols = subset if (subset and len(subset) > 0) else None
    return df.duplicated(subset=cols, keep=valid_keep)


def count_duplicates(df: pd.DataFrame, subset: list[str] | None = None) -> int:
    """Devuelve la cantidad de filas duplicadas exactas o por subconjunto."""
    return int(duplicate_mask(df, subset=subset, keep="first").sum())


def get_duplicate_examples(
    df: pd.DataFrame, subset: list[str] | None = None, max_rows: int = 20
) -> pd.DataFrame:
    """Devuelve una muestra de ejemplos de registros duplicados para previsualizar."""
    mask = df.duplicated(subset=subset, keep=False)
    duplicates = df[mask]
    if len(duplicates) > max_rows:
        return duplicates.head(max_rows).copy()
    return duplicates.copy()


def drop_duplicates(
    df: pd.DataFrame, subset: list[str] | None = None, keep: str = "first"
) -> pd.DataFrame:
    """Elimina los registros duplicados y devuelve una copia del DataFrame."""
    valid_keep = keep if keep in ("first", "last") else "first"
    cols = subset if (subset and len(subset) > 0) else None
    return df.drop_duplicates(subset=cols, keep=valid_keep).copy()


# --------------------------------------------------------------------------- #
# Sub-paso 5D: Valores Atípicos (Outliers)
# --------------------------------------------------------------------------- #


def outlier_bounds_iqr(series: pd.Series, k: float = 1.5) -> tuple[float, float]:
    """Calcula los límites inferior y superior por el método IQR."""
    clean = series.dropna()
    if clean.empty:
        return (0.0, 0.0)
    q1 = float(clean.quantile(0.25))
    q3 = float(clean.quantile(0.75))
    iqr = q3 - q1
    return (q1 - k * iqr, q3 + k * iqr)


def outlier_bounds_zscore(series: pd.Series, threshold: float = 3.0) -> tuple[float, float]:
    """Calcula los límites inferior y superior por el método Z-score."""
    clean = series.dropna()
    if clean.empty or len(clean) < 2:
        return (0.0, 0.0)
    mean = float(clean.mean())
    std = float(clean.std())
    if std == 0.0:
        return (mean, mean)
    return (mean - threshold * std, mean + threshold * std)


def outlier_bounds(
    series: pd.Series, method: str = "iqr", threshold: float = 1.5
) -> tuple[float, float]:
    """Obtiene los límites de outliers según el método ('iqr' o 'zscore')."""
    m = method.strip().lower()
    if m == "zscore":
        return outlier_bounds_zscore(series, threshold=threshold)
    return outlier_bounds_iqr(series, k=threshold)


def outlier_mask(series: pd.Series, method: str = "iqr", threshold: float = 1.5) -> pd.Series:
    """Devuelve máscara booleana con `True` donde el valor es un outlier."""
    if not pd.api.types.is_numeric_dtype(series.dtype):
        return pd.Series(False, index=series.index)
    clean = series.dropna()
    if clean.empty:
        return pd.Series(False, index=series.index)
    lower, upper = outlier_bounds(series, method=method, threshold=threshold)
    return (series < lower) | (series > upper)


def analyze_outliers(df: pd.DataFrame, method: str = "iqr", threshold: float = 1.5) -> pd.DataFrame:
    """Genera un reporte de outliers para todas las columnas numéricas."""
    numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c].dtype)]
    records = []
    total_rows = len(df)

    for col in numeric_cols:
        series = df[col]
        lower, upper = outlier_bounds(series, method=method, threshold=threshold)
        mask = (series < lower) | (series > upper)
        count = int(mask.sum())
        pct = round((count / total_rows * 100), 2) if total_rows > 0 else 0.0
        records.append(
            {
                "columna": col,
                "outliers": count,
                "porcentaje": pct,
                "limite_inferior": round(lower, 2),
                "limite_superior": round(upper, 2),
            }
        )

    if not records:
        return pd.DataFrame(
            columns=["columna", "outliers", "porcentaje", "limite_inferior", "limite_superior"]
        )
    return pd.DataFrame(records).sort_values(by="outliers", ascending=False).reset_index(drop=True)


def clip_outliers(
    df: pd.DataFrame, column: str, method: str = "iqr", threshold: float = 1.5
) -> pd.DataFrame:
    """Winsoriza (recorta a los límites) los outliers de la columna."""
    if column not in df.columns:
        raise CleaningError(f"La columna «{column}» no existe en el dataset.")
    if not pd.api.types.is_numeric_dtype(df[column].dtype):
        raise CleaningError(f"La columna «{column}» no es numérica.")

    result = df.copy()
    lower, upper = outlier_bounds(result[column], method=method, threshold=threshold)
    result[column] = result[column].clip(lower=lower, upper=upper)
    return result


def drop_outliers(
    df: pd.DataFrame, column: str, method: str = "iqr", threshold: float = 1.5
) -> pd.DataFrame:
    """Elimina las filas que contienen outliers en la columna indicada."""
    if column not in df.columns:
        raise CleaningError(f"La columna «{column}» no existe en el dataset.")
    if not pd.api.types.is_numeric_dtype(df[column].dtype):
        raise CleaningError(f"La columna «{column}» no es numérica.")

    mask = outlier_mask(df[column], method=method, threshold=threshold)
    return df[~mask].copy()


# --------------------------------------------------------------------------- #
# Sub-paso 5E: Errores Tipográficos (Typos)
# --------------------------------------------------------------------------- #


def normalize_text(series: pd.Series) -> pd.Series:
    """Normaliza texto eliminando espacios sobrantes en extremos e interiores."""
    return series.astype(str).str.strip().str.replace(r"\s+", " ", regex=True)


def suggest_merges(series: pd.Series, cutoff: float = 85.0) -> list[tuple[str, str, int, float]]:
    """Detecta variantes similares que podrían fusionarse a un valor canónico.

    Usa `rapidfuzz` para calcular similitud fonética/textual entre valores únicos.
    El valor canónico se selecciona por mayor frecuencia en el dataset (o alfabético en empate).

    Returns:
        Lista de tuplas: (variante, valor_canonico, conteo_de_variante, puntaje_similitud).
    """
    clean_series = series.dropna()
    if clean_series.empty:
        return []

    # Conteo de frecuencias por valor exacto (como string)
    value_counts = clean_series.astype(str).value_counts().to_dict()
    unique_values = list(value_counts.keys())
    if len(unique_values) < 2:
        return []

    # Ordenar por frecuencia descendente y luego alfabético
    sorted_unique = sorted(unique_values, key=lambda v: (-value_counts[v], v))
    processed: set[str] = set()
    suggestions: list[tuple[str, str, int, float]] = []

    for i, canonical in enumerate(sorted_unique):
        if canonical in processed:
            continue
        canonical_norm = canonical.strip().lower()

        for j in range(i + 1, len(sorted_unique)):
            candidate = sorted_unique[j]
            if candidate in processed:
                continue

            candidate_norm = candidate.strip().lower()

            # Comparar similitud con WRatio
            score = fuzz.WRatio(canonical_norm, candidate_norm)
            if score >= cutoff:
                processed.add(candidate)
                suggestions.append((candidate, canonical, value_counts[candidate], float(score)))

    return sorted(suggestions, key=lambda x: -x[2])


def apply_merges(df: pd.DataFrame, column: str, mapping: dict[str, str]) -> pd.DataFrame:
    """Aplica las fusiones de variantes tipográficas a la columna indicada."""
    if column not in df.columns:
        raise CleaningError(f"La columna «{column}» no existe en el dataset.")
    if not mapping:
        return df.copy()

    result = df.copy()
    result[column] = result[column].astype(str).replace(mapping)
    return result


# --------------------------------------------------------------------------- #
# Implementación interna
# --------------------------------------------------------------------------- #


def _imputation_value(
    series: pd.Series,
    strategy: str,
    fill_value: Any,
    is_numeric: bool,
) -> Any:
    """Calcula el valor con el que se rellenarán los faltantes de `series`."""
    if strategy == "mean":
        value = series.mean()
    elif strategy == "median":
        value = series.median()
    elif strategy == "mode":
        mode = series.mode(dropna=True)
        value = mode.iloc[0] if not mode.empty else fill_value
    else:  # strategy == "constant"
        value = fill_value

    if _is_missing(value):
        return 0 if is_numeric else UNKNOWN_VALUE
    return value


def _fill_series(series: pd.Series, value: Any) -> pd.Series:
    """Rellena una serie conservando el dtype cuando el valor es compatible."""
    try:
        return series.fillna(value)
    except (TypeError, ValueError):
        target = "float64" if pd.api.types.is_numeric_dtype(series.dtype) else "str"
        logger.debug("El dtype %r no admite %r; se convierte a %s.", series.dtype, value, target)
        return series.astype(target).fillna(value)


def _is_missing(value: Any) -> bool:
    """True si el valor calculado es nulo o no es un escalar utilizable."""
    if value is None:
        return True
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return True
