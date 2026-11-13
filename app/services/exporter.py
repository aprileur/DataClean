"""Exportación del dataset limpio a CSV, Excel o Parquet.

Este módulo es lógica pura: **no** importa Qt ni conoce la interfaz gráfica.
Todos los errores de cara al usuario se lanzan como `ExportError` con un
mensaje en español, listo para mostrarse en un diálogo.

Decisión D8 del proyecto:
- CSV se escribe con codificación `utf-8-sig` (BOM, compatible con Excel).
- Excel usa el motor `openpyxl`.
- Parquet usa el motor `pyarrow`.
- Nunca se sobrescribe un archivo existente: el destino siempre es un nombre
  nuevo `<stem>_nuevo.<ext>` y, si ya existe, `<stem>_nuevo_2.<ext>`, etc.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Final

import pandas as pd

logger = logging.getLogger(__name__)

#: Extensiones aceptadas por `export_dataset` (siempre en minúsculas).
SUPPORTED_EXTENSIONS: Final[frozenset[str]] = frozenset({".csv", ".xlsx", ".parquet"})

#: Codificación usada al exportar CSV (decisión D8: utf-8-sig con BOM).
CSV_EXPORT_ENCODING: Final[str] = "utf-8-sig"

#: Motor usado al exportar Excel.
EXCEL_ENGINE: Final[str] = "openpyxl"

#: Motor usado al exportar Parquet.
PARQUET_ENGINE: Final[str] = "pyarrow"

#: Sufijo base para el nombre del archivo exportado.
NEW_SUFFIX: Final[str] = "_nuevo"

#: Formatos de mensaje por extensión no soportada.
_UNSUPPORTED_MSG: Final[str] = (
    "Formato de exportación no soportado: '{ext}'. "
    "Los formatos disponibles son CSV (.csv), Excel (.xlsx) y Parquet (.parquet)."
)

_READ_FAIL_MSG: Final[str] = (
    "No se pudo exportar el dataset a '{path}'. "
    "Verifica que tengas permisos de escritura y que el archivo no esté abierto en otro programa."
)

_BAD_PATH_MSG: Final[str] = (
    "La ruta de exportación '{path}' no es válida. Verifica que la carpeta destino exista."
)


class ExportError(Exception):
    """Error de exportación con un mensaje descriptivo listo para el usuario."""


def _as_path(path: Path | str) -> Path:
    """Convierte `path` a `Path` aceptando `str`."""
    return path if isinstance(path, Path) else Path(path)


def generate_export_path(
    source_path: Path | str,
    target_extension: str,
    output_dir: Path | str | None = None,
) -> Path:
    """Calcula la ruta de destino para la exportación sin colisión de nombres.

    Regla D8: el destino siempre es un archivo nuevo `<stem>_nuevo.<ext>` en el
    directorio de salida. Si ese nombre ya existe, se incrementa el sufijo:
    `<stem>_nuevo_2.<ext>`, `<stem>_nuevo_3.<ext>`, etc. Nunca se sobrescribe
    el archivo original ni ningún archivo existente.

    Args:
        source_path: Ruta del archivo de origen (solo se usan su stem y directorio).
        target_extension: Extensión destino, con o sin punto (ej. `.csv` o `csv`).
        output_dir: Directorio de salida; si es `None` se usa el directorio
            padre de `source_path`.

    Returns:
        Ruta `Path` libre (que aún no existe en disco).

    Raises:
        ExportError: si la extensión no está soportada.
    """
    extension = target_extension.lower()
    if not extension.startswith("."):
        extension = f".{extension}"

    if extension not in SUPPORTED_EXTENSIONS:
        raise ExportError(_UNSUPPORTED_MSG.format(ext=extension))

    source = _as_path(source_path)
    directory = source.parent if output_dir is None else _as_path(output_dir)

    base = directory / f"{source.stem}{NEW_SUFFIX}{extension}"
    candidate = base
    counter = 2
    while candidate.exists():
        candidate = directory / f"{source.stem}{NEW_SUFFIX}_{counter}{extension}"
        counter += 1
    return candidate


def export_dataset(df: pd.DataFrame, target_path: Path | str) -> Path:
    """Exporta el DataFrame al archivo `target_path` según su extensión.

    El formato se detecta por la extensión:
    - `.csv` → escritura con codificación `utf-8-sig`.
    - `.xlsx` → escritura con `openpyxl`.
    - `.parquet` → escritura con `pyarrow`.

    Args:
        df: DataFrame a exportar (no se modifica).
        target_path: Ruta destino. Se recomienda construirlo con
            `generate_export_path` para no sobrescribir archivos existentes.

    Returns:
        `Path` absoluto del archivo creado.

    Raises:
        ExportError: si la extensión no está soportada o el guardado falla.
    """
    file_path = _as_path(target_path)
    extension = file_path.suffix.lower()

    if extension not in SUPPORTED_EXTENSIONS:
        raise ExportError(_UNSUPPORTED_MSG.format(ext=extension or "(sin extensión)"))

    try:
        if extension == ".csv":
            df.to_csv(file_path, index=False, encoding=CSV_EXPORT_ENCODING)
        elif extension == ".xlsx":
            df.to_excel(file_path, index=False, engine=EXCEL_ENGINE)
        else:  # .parquet
            df.to_parquet(file_path, index=False, engine=PARQUET_ENGINE)
    except OSError as exc:
        logger.debug("Fallo de I/O al exportar a %s: %s", file_path, exc)
        raise ExportError(_READ_FAIL_MSG.format(path=file_path)) from exc
    except (ValueError, TypeError) as exc:
        # pandas lanza ValueError/TypeError para datos no serializables
        # (ej. columnas con objetos mixtos en Parquet).
        logger.debug("Fallo al serializar datos para %s: %s", file_path, exc)
        raise ExportError(_READ_FAIL_MSG.format(path=file_path)) from exc

    if not file_path.is_file():  # pragma: no cover - defensa extra
        raise ExportError(_BAD_PATH_MSG.format(path=file_path))

    absolute = file_path.resolve()
    logger.info("Dataset exportado a %s", absolute)
    return absolute
