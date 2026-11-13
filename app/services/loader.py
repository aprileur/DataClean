"""Carga de archivos tabulares (CSV, Excel y Parquet).

Este módulo es lógica pura: **no** importa Qt ni conoce la interfaz gráfica.
Todos los errores de cara al usuario se lanzan como `LoaderError` con un
mensaje en español, listo para mostrarse en un diálogo.
"""

from __future__ import annotations

import codecs
import csv
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import pandas as pd

logger = logging.getLogger(__name__)

#: Extensiones aceptadas por `load_file` (siempre en minúsculas).
SUPPORTED_EXTENSIONS: Final[frozenset[str]] = frozenset({".csv", ".xlsx", ".xls", ".parquet"})

#: Extensiones que se leen como libro de Excel.
EXCEL_EXTENSIONS: Final[frozenset[str]] = frozenset({".xlsx", ".xls"})

#: Codificaciones candidatas, en el orden en que se prueban.
CSV_CANDIDATE_ENCODINGS: Final[tuple[str, ...]] = ("utf-8", "utf-8-sig", "latin-1")

#: Separadores candidatos, en el orden en que se prueban como respaldo.
CSV_CANDIDATE_SEPARATORS: Final[tuple[str, ...]] = (",", ";", "\t", "|")

#: Tamaño máximo de la muestra que se analiza para detectar el separador.
_SAMPLE_CHARS: Final[int] = 64 * 1024

#: Tamaño de bloque usado al validar una codificación.
_CHUNK_BYTES: Final[int] = 64 * 1024


class LoaderError(Exception):
    """Error de carga con un mensaje descriptivo listo para el usuario."""


@dataclass(slots=True)
class LoadResult:
    """Resultado de una carga exitosa.

    Attributes:
        df: DataFrame independiente del archivo en disco (ya es una copia).
        encoding: Codificación usada para leer el archivo (solo CSV).
        separator: Separador de campos detectado (solo CSV).
        sheet: Nombre de la hoja leída (solo Excel).
        file_name: Nombre del archivo de origen, sin la ruta.
    """

    df: pd.DataFrame
    encoding: str | None
    separator: str | None
    sheet: str | None
    file_name: str


def detect_encoding(path: Path | str) -> str:
    """Devuelve la codificación con la que se puede leer `path` completo.

    Se respeta el orden `utf-8`, `utf-8-sig`, `latin-1`. Si el archivo empieza
    con BOM UTF-8 se devuelve `utf-8-sig` para que el BOM no contamine el
    nombre de la primera columna.

    Raises:
        LoaderError: si el archivo no existe, no se puede leer o no se puede
            decodificar con ninguna de las codificaciones candidatas.
    """
    file_path = _as_path(path)
    _ensure_readable(file_path)

    try:
        with file_path.open("rb") as handle:
            head = handle.read(4)
    except OSError as exc:  # pragma: no cover - cubierto por _ensure_readable
        raise LoaderError(_unreadable_message(file_path, exc)) from exc

    if head.startswith(codecs.BOM_UTF8):
        return "utf-8-sig"

    for encoding in CSV_CANDIDATE_ENCODINGS:
        if _can_decode(file_path, encoding):
            logger.debug("Codificación detectada para %s: %s", file_path.name, encoding)
            return encoding

    raise LoaderError(
        f"No se pudo determinar la codificación del archivo «{file_path.name}». "
        "Guárdalo como UTF-8 o Latin-1 y vuelve a intentarlo."
    )


def detect_separator(sample_text: str) -> str:
    """Detecta el separador de un CSV a partir de una muestra de su contenido.

    Usa `csv.Sniffer`; si falla, cuenta los delimitadores candidatos
    (`,`, `;`, tabulador y `|`) en las primeras líneas. Cuando no hay ninguna
    evidencia de separación devuelve `,`.
    """
    if not sample_text.strip():
        return ","

    try:
        dialect = csv.Sniffer().sniff(sample_text, delimiters="".join(CSV_CANDIDATE_SEPARATORS))
    except csv.Error:
        logger.debug("csv.Sniffer no detectó el separador; se usa el conteo de delimitadores.")
    else:
        if dialect.delimiter in CSV_CANDIDATE_SEPARATORS:
            return dialect.delimiter

    return _separator_by_count(sample_text)


def list_sheets(path: Path | str) -> list[str]:
    """Devuelve los nombres de las hojas de un libro de Excel.

    Raises:
        LoaderError: si el archivo no es Excel, no existe, no se puede leer o
            está corrupto.
    """
    file_path = _as_path(path)
    _ensure_readable(file_path)

    if file_path.suffix.lower() not in EXCEL_EXTENSIONS:
        raise LoaderError(
            f"El archivo «{file_path.name}» no es un libro de Excel. "
            "Solo se admiten archivos .xlsx o .xls para listar hojas."
        )

    engine = _excel_engine(file_path)
    try:
        with pd.ExcelFile(file_path, engine=engine) as excel_file:
            sheets = [str(name) for name in excel_file.sheet_names]
    except ImportError as exc:
        raise LoaderError(
            f"Falta la librería necesaria para leer «{file_path.name}» "
            f"(motor «{engine}»). Revisa la instalación de las dependencias."
        ) from exc
    except Exception as exc:  # noqa: BLE001 - se traduce a un error amigable
        logger.debug("Error al listar hojas de %s: %s", file_path, exc)
        raise LoaderError(
            f"No se pudo abrir «{file_path.name}» como libro de Excel. "
            "El archivo puede estar dañado o no ser realmente un Excel."
        ) from exc

    return sheets


def load_file(path: Path | str, sheet: str | None = None) -> LoadResult:
    """Carga un CSV, Excel o Parquet y devuelve un `LoadResult`.

    Args:
        path: Ruta del archivo a cargar (admite `~`).
        sheet: Hoja a leer en archivos de Excel. Si es `None` se usa la primera.

    Returns:
        `LoadResult` cuyo `df` es una copia independiente del archivo en disco.

    Raises:
        LoaderError: archivo inexistente, sin permisos, vacío, corrupto, de
            formato no soportado o con una hoja inexistente.
    """
    file_path = _as_path(path)
    _ensure_readable(file_path)

    suffix = file_path.suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        shown = suffix or "sin extensión"
        supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise LoaderError(f"Formato no soportado: «{shown}». Se admiten: {supported}.")

    if file_path.stat().st_size == 0:
        raise LoaderError(
            f"El archivo «{file_path.name}» está vacío (0 bytes). "
            "Selecciona un archivo con datos."
        )

    if suffix == ".csv":
        result = _load_csv(file_path)
    elif suffix in EXCEL_EXTENSIONS:
        result = _load_excel(file_path, sheet)
    else:
        result = _load_parquet(file_path)

    logger.info(
        "Archivo cargado: %s (%s filas x %s columnas)",
        result.file_name,
        result.df.shape[0],
        result.df.shape[1],
    )
    return result


# --------------------------------------------------------------------------- #
# Implementación interna
# --------------------------------------------------------------------------- #


def _as_path(path: Path | str) -> Path:
    """Normaliza la entrada a `Path`, expandiendo `~` si hace falta."""
    return path if isinstance(path, Path) else Path(path).expanduser()


def _ensure_readable(path: Path) -> None:
    """Comprueba que la ruta existe, es un archivo y se puede abrir en lectura."""
    if not path.exists():
        raise LoaderError(f"No se encontró el archivo «{path}».")

    if not path.is_file():
        raise LoaderError(f"La ruta «{path}» no corresponde a un archivo.")

    try:
        with path.open("rb") as handle:
            handle.read(1)
    except PermissionError as exc:
        raise LoaderError(
            f"No hay permisos para leer «{path.name}». "
            "Cierra el archivo si está abierto en otro programa o revisa sus permisos."
        ) from exc
    except OSError as exc:
        raise LoaderError(_unreadable_message(path, exc)) from exc


def _unreadable_message(path: Path, exc: OSError) -> str:
    """Traduce un `OSError` de apertura a un mensaje en español."""
    detail = exc.strerror or str(exc)
    return f"No se pudo abrir «{path.name}»: {detail}."


def _can_decode(path: Path, encoding: str) -> bool:
    """Indica si el archivo completo se puede decodificar con `encoding`."""
    decoder = codecs.getincrementaldecoder(encoding)(errors="strict")
    try:
        with path.open("rb") as handle:
            while chunk := handle.read(_CHUNK_BYTES):
                decoder.decode(chunk)
        decoder.decode(b"", final=True)
    except UnicodeDecodeError:
        return False
    except OSError as exc:  # pragma: no cover - cubierto por _ensure_readable
        raise LoaderError(_unreadable_message(path, exc)) from exc
    return True


def _separator_by_count(sample_text: str) -> str:
    """Elige el separador más consistente contando delimitadores por línea."""
    lines = [line for line in sample_text.splitlines() if line.strip()][:20]
    if not lines:
        return ","

    best_separator = ","
    best_score = 0
    for separator in CSV_CANDIDATE_SEPARATORS:
        counts = [line.count(separator) for line in lines]
        # Se premia que el separador aparezca el mismo número de veces en cada
        # línea (estructura tabular) y, como desempate, cuántas veces aparece.
        consistent = min(counts)
        score = consistent * 1000 + sum(counts)
        if consistent > 0 and score > best_score:
            best_separator = separator
            best_score = score
    return best_separator


def _read_sample(path: Path, encoding: str) -> str:
    """Lee los primeros caracteres del archivo para analizar su estructura."""
    try:
        with path.open("r", encoding=encoding, errors="strict") as handle:
            return handle.read(_SAMPLE_CHARS)
    except OSError as exc:  # pragma: no cover - cubierto por _ensure_readable
        raise LoaderError(_unreadable_message(path, exc)) from exc


def _load_csv(path: Path) -> LoadResult:
    """Carga un CSV detectando codificación y separador."""
    encoding = detect_encoding(path)
    sample = _read_sample(path, encoding)
    separator = detect_separator(sample)

    df = _read_csv_with_fallback(path, encoding, separator)
    _ensure_not_empty(df, path)

    return LoadResult(
        df=df.copy(),
        encoding=encoding,
        separator=separator,
        sheet=None,
        file_name=path.name,
    )


def _read_csv_with_fallback(path: Path, encoding: str, separator: str) -> pd.DataFrame:
    """Lee el CSV con `separator`; si falla, prueba el resto de candidatos."""
    candidates = [separator] + [
        candidate for candidate in CSV_CANDIDATE_SEPARATORS if candidate != separator
    ]
    last_error: Exception | None = None

    for candidate in candidates:
        try:
            df = pd.read_csv(path, sep=candidate, encoding=encoding, low_memory=False)
        except (pd.errors.ParserError, UnicodeDecodeError, ValueError) as exc:
            last_error = exc
            logger.debug("Fallo al leer %s con separador %r: %s", path.name, candidate, exc)
            continue
        if df.shape[1] > 0:
            if candidate != separator:
                logger.debug("Se usó el separador de respaldo %r para %s", candidate, path.name)
            return df

    detail = f" Detalle: {last_error}" if last_error else ""
    raise LoaderError(
        f"No se pudo leer «{path.name}» como CSV. "
        "El archivo puede estar dañado o no tener una estructura tabular válida." + detail
    )


def _excel_engine(path: Path) -> str:
    """Devuelve el motor de pandas adecuado para la extensión del libro."""
    return "xlrd" if path.suffix.lower() == ".xls" else "openpyxl"


def _load_excel(path: Path, sheet: str | None) -> LoadResult:
    """Carga un libro de Excel; si no se indica hoja, usa la primera."""
    engine = _excel_engine(path)
    sheets = list_sheets(path)

    if not sheets:
        raise LoaderError(f"El libro «{path.name}» no contiene ninguna hoja.")

    target = sheet if sheet is not None else sheets[0]
    if target not in sheets:
        available = ", ".join(sheets)
        raise LoaderError(
            f"La hoja «{target}» no existe en «{path.name}». Hojas disponibles: {available}."
        )

    try:
        df = pd.read_excel(path, sheet_name=target, engine=engine)
    except ImportError as exc:
        raise LoaderError(
            f"Falta la librería necesaria para leer «{path.name}» "
            f"(motor «{engine}»). Revisa la instalación de las dependencias."
        ) from exc
    except Exception as exc:  # noqa: BLE001 - se traduce a un error amigable
        logger.debug("Error al leer la hoja %r de %s: %s", target, path, exc)
        raise LoaderError(
            f"No se pudo leer la hoja «{target}» de «{path.name}». "
            "El archivo puede estar dañado."
        ) from exc

    _ensure_not_empty(df, path)

    return LoadResult(
        df=df.copy(),
        encoding=None,
        separator=None,
        sheet=str(target),
        file_name=path.name,
    )


def _load_parquet(path: Path) -> LoadResult:
    """Carga un archivo Parquet usando pyarrow."""
    try:
        df = pd.read_parquet(path, engine="pyarrow")
    except ImportError as exc:
        raise LoaderError(
            f"Falta la librería necesaria para leer «{path.name}» (motor «pyarrow»). "
            "Revisa la instalación de las dependencias."
        ) from exc
    except Exception as exc:  # noqa: BLE001 - se traduce a un error amigable
        logger.debug("Error al leer Parquet %s: %s", path, exc)
        raise LoaderError(
            f"No se pudo leer «{path.name}» como Parquet. "
            "El archivo puede estar dañado o no ser realmente un Parquet."
        ) from exc

    _ensure_not_empty(df, path)

    return LoadResult(
        df=df.copy(),
        encoding=None,
        separator=None,
        sheet=None,
        file_name=path.name,
    )


def _ensure_not_empty(df: pd.DataFrame, path: Path) -> None:
    """Lanza `LoaderError` si el DataFrame resultante no tiene datos."""
    if df.shape[0] == 0 or df.shape[1] == 0:
        raise LoaderError(
            f"El archivo «{path.name}» no contiene datos legibles "
            "(no se encontraron filas ni columnas)."
        )
