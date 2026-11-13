"""Perfilado del dataset: forma, memoria, tipos de columnas y datos faltantes.

Este módulo es lógica pura: **no** importa Qt ni conoce la interfaz gráfica.
Todas las funciones reciben un `pd.DataFrame` y devuelven resultados nuevos,
sin efectos secundarios sobre el DataFrame de entrada.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

#: Umbral de proporción de valores únicos para considerar una columna como ID.
_ID_UNIQUE_RATIO: float = 0.90

#: Máximo porcentaje de nulos tolerado en una columna candidata a ID.
_ID_MAX_NULL_PCT: float = 1.0


@dataclass(slots=True)
class ColumnTypes:
    """Clasificación de las columnas del dataset según la decisión D4.

    Attributes:
        numeric: Columnas numéricas (enteros y flotantes, sin `bool`).
        categorical: Columnas categóricas (`str`, `object`, `category`, `bool`).
        datetime: Columnas de fecha (`datetime64`) o duración (`timedelta64`).
        other: Columnas que no encajan en ninguna categoría anterior.
    """

    numeric: list[str] = field(default_factory=list)
    categorical: list[str] = field(default_factory=list)
    datetime: list[str] = field(default_factory=list)
    other: list[str] = field(default_factory=list)


def dataset_shape(df: pd.DataFrame) -> tuple[int, int]:
    """Devuelve la forma del dataset como `(filas, columnas)`."""
    return df.shape


def row_count(df: pd.DataFrame) -> int:
    """Devuelve la cantidad de registros (filas) del dataset."""
    return int(len(df))


def column_count(df: pd.DataFrame) -> int:
    """Devuelve la cantidad de columnas del dataset."""
    return int(df.shape[1])


def memory_usage(df: pd.DataFrame) -> str:
    """Devuelve el uso de memoria del dataset formateado de forma legible.

    Usa `memory_usage(deep=True)` para incluir el costo real de los strings.
    """
    total_bytes = int(df.memory_usage(deep=True).sum())
    return _format_bytes(total_bytes)


def classify_columns(df: pd.DataFrame) -> ColumnTypes:
    """Clasifica cada columna del dataset según la decisión D4.

    - Numéricas: dtypes de entero o flotante (`number`, excluye `bool`).
    - Categóricas: `str`/`StringDtype` (pandas 3), `object`, `category`, `bool`.
    - Fechas: `datetime64` y `timedelta64` (incluye tz-aware).
    - Other: todo lo demás.
    """
    types = ColumnTypes()
    for name in df.columns:
        kind = _column_kind(df[name].dtype)
        getattr(types, kind).append(str(name))
    return types


def missing_summary(df: pd.DataFrame, only_with_missing: bool = True) -> pd.DataFrame:
    """Resumen de datos faltantes por columna.

    Args:
        df: DataFrame a analizar.
        only_with_missing: Si es True, solo incluye columnas con al menos
            un faltante; si es False, incluye todas.

    Returns:
        DataFrame con columnas `columna` (str), `faltantes` (int) y
        `porcentaje` (float, 2 decimales), ordenado por faltantes descendente.
    """
    if df.empty:
        return pd.DataFrame(
            {
                "columna": pd.Series(dtype="str"),
                "faltantes": pd.Series(dtype="int64"),
                "porcentaje": pd.Series(dtype="float64"),
            }
        )

    total_rows = len(df)
    counts = df.isna().sum()
    result = pd.DataFrame(
        {
            "columna": counts.index.astype(str),
            "faltantes": counts.to_numpy(dtype="int64"),
        }
    )
    result["porcentaje"] = (result["faltantes"] / total_rows * 100).round(2)

    if only_with_missing:
        result = result[result["faltantes"] > 0]

    return result.sort_values("faltantes", ascending=False).reset_index(drop=True)


def missing_row_union(df: pd.DataFrame) -> tuple[int, float]:
    """Union de filas con al menos un dato faltante.

    Cuenta cada fila una sola vez aunque tenga varios huecos (a diferencia
    de la suma de faltantes por columna, que puede contar filas repetidas).

    Returns:
        `(filas_afectadas, porcentaje_del_total)` con el porcentaje redondeado
        a 2 decimales. Para un DataFrame vacío retorna `(0, 0.0)`.
    """
    total_rows = len(df)
    if total_rows == 0:
        return 0, 0.0

    affected_rows = int(df.isna().any(axis=1).sum())
    percentage = round(affected_rows / total_rows * 100, 2)
    return affected_rows, percentage


def looks_like_id(series: pd.Series) -> bool:
    """Heurística: True si la serie parece un identificador.

    Criterios (solo informativos, no reclasifica automáticamente):
    - La serie no es vacía.
    - Tiene pocos o ningún nulo (<1 % del total).
    - La proporción de valores únicos sobre el total supera 0.90.
    """
    length = len(series)
    if length == 0:
        return False

    null_ratio = float(series.isna().sum()) / length
    if null_ratio >= _ID_MAX_NULL_PCT / 100:
        return False

    unique_ratio = float(series.nunique()) / length
    return unique_ratio > _ID_UNIQUE_RATIO


def _format_bytes(num_bytes: int) -> str:
    """Formatea una cantidad de bytes en B, KB, MB, GB o TB con 1 decimal."""
    if num_bytes < 1024:
        return f"{num_bytes} B"
    size = float(num_bytes)
    for unit in ("KB", "MB", "GB", "TB"):
        size /= 1024
        if size < 1024:
            return f"{size:.1f} {unit}"
    return f"{size:.1f} PB"


def _column_kind(dtype: object) -> str:
    """Mapea un dtype al nombre de atributo de `ColumnTypes` correspondiente."""
    # pandas 3 usa `str`/StringDtype como dtype por defecto para texto.
    if isinstance(dtype, pd.StringDtype):
        return "categorical"
    if pd.api.types.is_bool_dtype(dtype):
        return "categorical"
    if isinstance(dtype, pd.CategoricalDtype):
        return "categorical"
    if pd.api.types.is_datetime64_any_dtype(dtype) or pd.api.types.is_timedelta64_dtype(dtype):
        return "datetime"
    if pd.api.types.is_object_dtype(dtype) or pd.api.types.is_string_dtype(dtype):
        return "categorical"
    if pd.api.types.is_numeric_dtype(dtype):
        return "numeric"
    return "other"
