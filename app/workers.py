"""Ejecución de operaciones pesadas fuera del hilo de la interfaz (tarea T21).

`Worker` es un `QRunnable` que ejecuta un callable en el `QThreadPool` global y
comunica el resultado mediante señales Qt. **El worker nunca toca widgets**: solo
calcula y emite; los slots conectados corren en el hilo principal y son los
únicos que actualizan la interfaz.

Uso:
    worker = Worker(load_file, path)
    worker.signals.finished.connect(on_result)
    worker.signals.error.connect(on_error)
    QThreadPool.globalInstance().start(worker)

Nota: el `QThreadPool` toma la propiedad del `QRunnable` (`autoDelete=True`). Si
necesitas conservarlo para reconectar señales, guarda una referencia al objeto
Python mientras se ejecuta.
"""

from __future__ import annotations

import inspect
import logging
from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal

from app.ui import texts_es

logger = logging.getLogger(__name__)

#: Nombre del parámetro opcional que permite reportar progreso (0–100).
PROGRESS_PARAM: str = "progress_callback"


class WorkerSignals(QObject):
    """Señales emitidas por un `Worker` (siempre entregadas en el hilo de UI)."""

    finished = Signal(object)  # resultado de la función
    error = Signal(str)  # mensaje de error en español
    progress = Signal(int)  # porcentaje 0–100


class Worker(QRunnable):
    """Ejecuta `fn(*args, **kwargs)` en un hilo del `QThreadPool`.

    Si `fn` acepta un parámetro llamado `progress_callback`, el worker lo
    inyecta para que la función pueda reportar avance (0–100).
    """

    def __init__(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
        super().__init__()
        self._fn = fn
        self._args = args
        self._kwargs = kwargs
        self.signals = WorkerSignals()
        self._inject_progress = _accepts_progress(fn) and PROGRESS_PARAM not in kwargs
        self.setAutoDelete(True)

    def run(self) -> None:  # noqa: D401 - implementación de QRunnable
        """Ejecuta la función y emite `finished` o `error` según el resultado."""
        kwargs = dict(self._kwargs)
        if self._inject_progress:
            kwargs[PROGRESS_PARAM] = self.signals.progress.emit
        try:
            result = self._fn(*self._args, **kwargs)
        except Exception as exc:  # noqa: BLE001 - se traduce a señal de error
            logger.exception("Background worker failed while running %r", self._fn)
            self.signals.error.emit(_user_facing_message(exc))
        else:
            self.signals.finished.emit(result)


def run_in_thread(
    fn: Callable[..., Any],
    *args: Any,
    on_result: Callable[[Any], None] | None = None,
    on_error: Callable[[str], None] | None = None,
    on_progress: Callable[[int], None] | None = None,
    **kwargs: Any,
) -> Worker:
    """Crea y lanza un `Worker` con callbacks opcionales.

    Args:
        fn: Función a ejecutar en segundo plano.
        *args: Argumentos posicionales de `fn`.
        on_result: Slot que recibe el resultado (`finished`).
        on_error: Slot que recibe el mensaje de error en español (`error`).
        on_progress: Slot que recibe el porcentaje de avance (`progress`).
        **kwargs: Argumentos con nombre de `fn`.

    Returns:
        El `Worker` lanzado (útil para guardar una referencia o desconectar).
    """
    worker = Worker(fn, *args, **kwargs)
    if on_result is not None:
        worker.signals.finished.connect(on_result)
    if on_error is not None:
        worker.signals.error.connect(on_error)
    if on_progress is not None:
        worker.signals.progress.connect(on_progress)

    QThreadPool.globalInstance().start(worker)
    return worker


def _accepts_progress(fn: Callable[..., Any]) -> bool:
    """Indica si `fn` puede recibir el callback de progreso inyectado."""
    try:
        parameters = inspect.signature(fn).parameters
    except (TypeError, ValueError):  # pragma: no cover - callables exóticos
        return False
    return PROGRESS_PARAM in parameters


def _user_facing_message(exc: BaseException) -> str:
    """Devuelve un mensaje en español para el diálogo de error.

    Los errores de los servicios propios (`app.services.*`) ya traen un mensaje
    en español pensado para el usuario; cualquier otra excepción se traduce a un
    texto genérico y su detalle queda solo en el log.
    """
    module = type(exc).__module__ or ""
    message = str(exc).strip()
    if message and module.startswith("app."):
        return message
    return texts_es.WORKER_ERROR_GENERIC
