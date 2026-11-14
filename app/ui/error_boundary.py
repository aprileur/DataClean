"""Borde de errores de la interfaz (tarea T22).

Cualquier excepción no controlada se registra con su traceback en el log y se
presenta al usuario como un diálogo amigable en español. Nunca se muestra un
traceback en pantalla.
"""

from __future__ import annotations

import functools
import logging
import sys
from collections.abc import Callable
from types import TracebackType
from typing import Any, TypeVar

from PySide6.QtWidgets import QApplication, QMessageBox

from app.ui import texts_es

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


def _show_error_dialog(message: str = texts_es.ERROR_UNEXPECTED_MSG) -> None:
    """Muestra un `QMessageBox` genérico si hay una `QApplication` activa."""
    if QApplication.instance() is None:
        logger.warning("No QApplication available to show the error dialog: %s", message)
        return
    QMessageBox.critical(None, texts_es.ERROR_UNEXPECTED_TITLE, message)


def handle_exception(
    exc_type: type[BaseException],
    exc_value: BaseException,
    exc_tb: TracebackType | None,
) -> None:
    """`sys.excepthook`: registra el traceback y muestra un diálogo amigable.

    Las interrupciones de teclado se delegan al hook original para no romper el
    comportamiento estándar de la consola.
    """
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_tb)
        return

    logger.critical("Unhandled exception", exc_info=(exc_type, exc_value, exc_tb))
    _show_error_dialog()


class ErrorContext:
    """Context manager que captura excepciones, las loguea y muestra un diálogo.

    La excepción **no** se propaga: `__exit__` devuelve `True` tras informar al
    usuario. `KeyboardInterrupt` y `SystemExit` se dejan pasar.
    """

    def __enter__(self) -> ErrorContext:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool:
        if exc_type is None:
            return False
        if issubclass(exc_type, (KeyboardInterrupt, SystemExit)):
            return False

        logger.exception("Exception handled by ErrorContext", exc_info=(exc_type, exc_value, exc_tb))
        _show_error_dialog()
        return True


def qt_slot_error_handler(func: F) -> F:
    """Decorador para slots Qt: captura, loguea y muestra un diálogo.

    Uso:
        @qt_slot_error_handler
        def _on_button_clicked(self) -> None:
            ...
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        with ErrorContext():
            return func(*args, **kwargs)

    return wrapper  # type: ignore[return-value]
