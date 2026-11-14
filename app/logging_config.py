"""Configuración centralizada de logging para DataClean (tarea T22).

El detalle técnico se escribe en un archivo rotativo (`data_clean.log`) y solo
los avisos y errores se reflejan además en stderr. Los mensajes del log van en
inglés (formato técnico); los textos visibles al usuario viven en
`app.ui.texts_es`.
"""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Final

#: Nombre del archivo de log creado en el directorio de trabajo.
LOG_FILENAME: Final[str] = "data_clean.log"

#: Formato de cada línea del log.
LOG_FORMAT: Final[str] = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

#: Tamaño máximo de cada archivo antes de rotar (1 MB).
MAX_BYTES: Final[int] = 1024 * 1024

#: Cantidad de archivos de respaldo conservados durante la rotación.
BACKUP_COUNT: Final[int] = 3

#: Nivel del logger raíz y del archivo de log.
FILE_LEVEL: Final[int] = logging.INFO

#: Nivel del handler de stderr (solo avisos y errores).
STREAM_LEVEL: Final[int] = logging.WARNING

#: Atributo que marca los handlers propios para poder reinstalar sin duplicar.
_HANDLER_MARKER: Final[str] = "_dataclean_handler"

#: Nombres de los handlers instalados (facilitan pruebas y diagnóstico).
FILE_HANDLER_NAME: Final[str] = "dataclean-file"
STREAM_HANDLER_NAME: Final[str] = "dataclean-stderr"


def setup_logging(log_path: Path | str | None = None) -> Path:
    """Configura el logger raíz con rotación de archivo y un handler de stderr.

    La función es idempotente: al invocarla de nuevo retira los handlers que
    instaló una llamada anterior antes de añadir los nuevos, de modo que sea
    seguro usarla en pruebas o al reabrir la aplicación.

    Args:
        log_path: Ruta del archivo de log. Si se omite, se usa
            `data_clean.log` en el directorio de trabajo.

    Returns:
        Ruta absoluta del archivo de log configurado.
    """
    path = Path(log_path) if log_path is not None else Path(LOG_FILENAME)
    path = path.expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    path.parent.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    _remove_managed_handlers(root)

    formatter = logging.Formatter(LOG_FORMAT)

    file_handler = RotatingFileHandler(
        path,
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setLevel(FILE_LEVEL)
    file_handler.setFormatter(formatter)
    file_handler.name = FILE_HANDLER_NAME
    setattr(file_handler, _HANDLER_MARKER, True)

    stream_handler = logging.StreamHandler(stream=sys.stderr)
    stream_handler.setLevel(STREAM_LEVEL)
    stream_handler.setFormatter(formatter)
    stream_handler.name = STREAM_HANDLER_NAME
    setattr(stream_handler, _HANDLER_MARKER, True)

    root.setLevel(FILE_LEVEL)
    root.addHandler(file_handler)
    root.addHandler(stream_handler)

    logging.getLogger(__name__).debug("Logging configured at %s", path)
    return path


def _remove_managed_handlers(logger: logging.Logger) -> None:
    """Retira y cierra los handlers instalados por llamadas anteriores."""
    for handler in list(logger.handlers):
        if getattr(handler, _HANDLER_MARKER, False):
            logger.removeHandler(handler)
            handler.close()
