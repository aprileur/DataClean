"""Limpieza del dataset: datos faltantes (sub-paso 5A).

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

from app.services import profiling

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


def missing_report(df: pd.DataFrame, only_with_missing: bool = True) -> pd.DataFrame:
    """Resumen de datos faltantes por columna.

    Args:
        df: DataFrame a analizar (no se modifica).
        only_with_missing: Si es True, solo incluye columnas con al menos un
            faltante; si es False, incluye todas las columnas.

    Returns:
        DataFrame con columnas `columna`, `faltantes` y `porcentaje`, ordenado
        por cantidad de faltantes de forma descendente.
    """
    return profiling.missing_summary(df, only_with_missing=only_with_missing)


def missing_union(df: pd.DataFrame) -> tuple[int, float]:
    """Filas con al menos un valor faltante (unión, no suma por columna).

    Cuenta cada fila una sola vez aunque tenga varios huecos, para no
    inflar el impacto real de eliminar registros incompletos.

    Returns:
        `(filas_afectadas, porcentaje_del_total)` con el porcentaje redondeado
        a 2 decimales.
    """
    return profiling.missing_row_union(df)


def drop_missing_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Devuelve una copia del dataset sin las filas que tengan algún faltante.

    El DataFrame de entrada no se modifica.
    """
    return df.dropna().copy()


def impute_column(
    df: pd.DataFrame,
    column: str,
    strategy: str,
    fill_value: Any = None,
) -> pd.DataFrame:
    """Imputa los valores faltantes de `column` y devuelve una copia del dataset.

    Args:
        df: DataFrame de origen (no se modifica).
        column: Nombre de la columna a imputar.
        strategy: Una de `mean`, `median`, `mode` o `constant`.
        fill_value: Valor de respaldo para `constant` y para columnas sin moda
            calculable. Si es `None` se usa "Desconocido" en columnas
            categóricas y `0` en numéricas.

    Returns:
        Copia del DataFrame con los faltantes de `column` reemplazados.

    Raises:
        CleaningError: si la estrategia no es válida, la columna no existe o
            se pide media/mediana en una columna no numérica.
    """
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
    """Máscara booleana de faltantes lista para dibujar el mapa de calor.

    Args:
        df: DataFrame a representar (no se modifica).
        max_rows: Número máximo de filas a devolver. Si el dataset es mayor,
            se toma una muestra determinista para no saturar el gráfico.

    Returns:
        DataFrame booleano con la misma forma que la muestra (`True` = faltante),
        con el índice original de las filas conservadas.

    Raises:
        CleaningError: si `max_rows` no es un entero positivo.
    """
    if max_rows < 1:
        raise CleaningError(
            f"El número máximo de filas del mapa de calor debe ser positivo (recibido: {max_rows})."
        )

    if len(df) <= max_rows:
        return df.isna().copy()

    sample = df.sample(n=max_rows, random_state=HEATMAP_RANDOM_STATE)
    return sample.sort_index().isna()


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
    """Rellena una serie conservando el dtype cuando el valor es compatible.

    Si el dtype no admite el valor (por ejemplo, una media decimal en una
    columna entera nullable) se convierte la columna a `float64`.
    """
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
    except (TypeError, ValueError):  # pragma: no cover - valores no escalares
        return True
