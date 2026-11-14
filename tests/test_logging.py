"""Pruebas del logging con rotación y del borde de errores (T22)."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

import pytest

from app.logging_config import (
    BACKUP_COUNT,
    FILE_HANDLER_NAME,
    MAX_BYTES,
    STREAM_HANDLER_NAME,
    setup_logging,
)
from app.ui import error_boundary, texts_es


@pytest.fixture()
def clean_root_logger():
    """Restaura los handlers y el nivel del logger raíz tras cada prueba."""
    root = logging.getLogger()
    original_handlers = list(root.handlers)
    original_level = root.level
    yield root

    for handler in list(root.handlers):
        if handler not in original_handlers:
            root.removeHandler(handler)
            handler.close()
    root.handlers[:] = original_handlers
    root.setLevel(original_level)


@pytest.fixture()
def shown_dialogs(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Captura los mensajes que el borde de errores mostraría al usuario."""
    messages: list[str] = []

    def fake_dialog(message: str = texts_es.ERROR_UNEXPECTED_MSG) -> None:
        messages.append(message)

    monkeypatch.setattr(error_boundary, "_show_error_dialog", fake_dialog)
    return messages


def test_setup_logging_creates_log_file(tmp_path: Path, clean_root_logger: logging.Logger) -> None:
    """`setup_logging` crea el archivo de log y configura la rotación."""
    log_path = setup_logging(tmp_path / "data_clean.log")

    assert log_path.is_absolute()
    assert log_path.name == "data_clean.log"
    assert log_path.parent.is_dir()

    rotating = [h for h in clean_root_logger.handlers if isinstance(h, RotatingFileHandler)]
    assert len(rotating) == 1
    handler = rotating[0]
    assert handler.maxBytes == MAX_BYTES == 1024 * 1024
    assert handler.backupCount == BACKUP_COUNT == 3
    assert handler.level == logging.INFO
    assert clean_root_logger.level == logging.INFO


def test_setup_logging_writes_formatted_lines(
    tmp_path: Path, clean_root_logger: logging.Logger
) -> None:
    """Los mensajes INFO llegan al archivo con timestamp, nivel y nombre del logger."""
    log_path = setup_logging(tmp_path / "data_clean.log")

    logging.getLogger("app.test").info("mensaje de prueba")
    for handler in clean_root_logger.handlers:
        handler.flush()

    contents = log_path.read_text(encoding="utf-8")
    assert "mensaje de prueba" in contents
    assert "[INFO]" in contents
    assert "app.test" in contents


def test_setup_logging_adds_warning_stream_handler(
    tmp_path: Path, clean_root_logger: logging.Logger
) -> None:
    """stderr solo recibe avisos y errores, no cada mensaje INFO."""
    setup_logging(tmp_path / "data_clean.log")

    stream_handlers = [h for h in clean_root_logger.handlers if h.name == STREAM_HANDLER_NAME]
    assert len(stream_handlers) == 1
    assert all(handler.level == logging.WARNING for handler in stream_handlers)


def test_setup_logging_is_idempotent(tmp_path: Path, clean_root_logger: logging.Logger) -> None:
    """Invocarla dos veces no duplica handlers."""
    setup_logging(tmp_path / "data_clean.log")
    setup_logging(tmp_path / "data_clean.log")

    rotating = [h for h in clean_root_logger.handlers if h.name == FILE_HANDLER_NAME]
    stream = [h for h in clean_root_logger.handlers if h.name == STREAM_HANDLER_NAME]
    assert len(rotating) == 1
    assert len(stream) == 1


def test_error_context_swallows_exception(
    shown_dialogs: list[str], caplog: pytest.LogCaptureFixture
) -> None:
    """`ErrorContext` loguea el traceback, muestra el diálogo y no re-lanza."""
    caplog.set_level(logging.ERROR)

    with error_boundary.ErrorContext():
        raise ValueError("fallo simulado")

    assert shown_dialogs == [texts_es.ERROR_UNEXPECTED_MSG]
    assert "Exception handled by ErrorContext" in caplog.text
    assert "fallo simulado" in caplog.text


def test_error_context_lets_system_exit_through(shown_dialogs: list[str]) -> None:
    """Las salidas del sistema no se silencian."""
    with pytest.raises(SystemExit):
        with error_boundary.ErrorContext():
            raise SystemExit(1)
    assert shown_dialogs == []


def test_qt_slot_error_handler_does_not_propagate(shown_dialogs: list[str]) -> None:
    """El decorador de slots captura la excepción y no la propaga."""

    @error_boundary.qt_slot_error_handler
    def slot() -> None:
        raise RuntimeError("slot roto")

    assert slot() is None
    assert shown_dialogs == [texts_es.ERROR_UNEXPECTED_MSG]


def test_handle_exception_logs_and_shows_dialog(
    shown_dialogs: list[str], caplog: pytest.LogCaptureFixture
) -> None:
    """`sys.excepthook` registra el traceback y muestra el mensaje amigable."""
    caplog.set_level(logging.CRITICAL)
    error = RuntimeError("excepción no controlada")

    error_boundary.handle_exception(type(error), error, error.__traceback__)

    assert shown_dialogs == [texts_es.ERROR_UNEXPECTED_MSG]
    assert "Unhandled exception" in caplog.text
    assert "excepción no controlada" in caplog.text


def test_handle_exception_delegates_keyboard_interrupt(
    shown_dialogs: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ctrl+C se delega al hook original de Python."""
    calls: list[type[BaseException]] = []

    def fake_hook(exc_type, exc_value, exc_tb) -> None:  # noqa: ANN001
        calls.append(exc_type)

    monkeypatch.setattr(error_boundary.sys, "__excepthook__", fake_hook)

    error_boundary.handle_exception(KeyboardInterrupt, KeyboardInterrupt(), None)

    assert calls == [KeyboardInterrupt]
    assert shown_dialogs == []


def test_error_context_does_nothing_without_exception(shown_dialogs: list[str]) -> None:
    """Salir del contexto sin excepción no muestra diálogo."""
    with error_boundary.ErrorContext() as context:
        assert context is not None
    assert shown_dialogs == []
