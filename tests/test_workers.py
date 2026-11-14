"""Pruebas del ejecutor de tareas en segundo plano (tarea T21).

`Worker` corre un callable en el `QThreadPool` y comunica el resultado con
señales Qt. Las slots conectadas a un objeto `QObject` se ejecutan en el hilo
de interfaz, nunca en el hilo del worker.

Nota de entorno: `QSignalSpy.wait()` no entrega señales definidas en Python
(`Signal(...)` de una clase Python) cuando se emiten desde otro hilo en la
versión de PySide6 instalada; por eso se usa `QSignalSpy` para inspeccionar los
valores y `qtbot.waitUntil` para esperar la entrega asíncrona.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, QThread, QThreadPool
from PySide6.QtTest import QSignalSpy
from pytestqt.qtbot import QtBot

from app.services.loader import LoaderError
from app.ui import texts_es
from app.workers import Worker, run_in_thread

#: Tiempo máximo de espera de las señales asíncronas en milisegundos.
SIGNAL_TIMEOUT_MS = 5000


class _Receiver(QObject):
    """Receptor de señales que registra el hilo en el que se ejecuta cada slot."""

    def __init__(self) -> None:
        super().__init__()
        self.results: list[object] = []
        self.threads: list[QThread] = []

    def on_result(self, value: object) -> None:
        """Guarda el resultado y el hilo actual (debe ser el hilo de interfaz)."""
        self.results.append(value)
        self.threads.append(QThread.currentThread())

    def on_error(self, message: str) -> None:
        """Guarda el mensaje de error recibido."""
        self.results.append(message)
        self.threads.append(QThread.currentThread())


def _start(worker: Worker) -> None:
    """Lanza el worker en el pool global, igual que `run_in_thread`."""
    QThreadPool.globalInstance().start(worker)


def _wait_for(spy: QSignalSpy, qtbot: QtBot, count: int = 1) -> None:
    """Espera a que el espía reciba `count` emisiones."""
    qtbot.waitUntil(lambda: spy.count() >= count, timeout=SIGNAL_TIMEOUT_MS)


def test_worker_emits_finished_with_result(qtbot: QtBot) -> None:
    """La señal `finished` entrega el valor devuelto por la función."""
    worker = Worker(lambda: 6 * 7)
    finished = QSignalSpy(worker.signals.finished)

    _start(worker)
    _wait_for(finished, qtbot)

    assert finished.count() == 1
    assert finished.at(0)[0] == 42


def test_worker_propagates_spanish_service_message(qtbot: QtBot) -> None:
    """Un error de `app.services` conserva su mensaje en español."""
    message = "El archivo está vacío."

    def boom() -> None:
        raise LoaderError(message)

    worker = Worker(boom)
    errors = QSignalSpy(worker.signals.error)

    _start(worker)
    _wait_for(errors, qtbot)

    assert errors.count() == 1
    assert errors.at(0)[0] == message


def test_worker_hides_unexpected_exception_details(qtbot: QtBot) -> None:
    """Una excepción inesperada se traduce a un mensaje genérico en español."""
    worker = Worker(lambda: 1 / 0)
    errors = QSignalSpy(worker.signals.error)

    _start(worker)
    _wait_for(errors, qtbot)

    assert errors.count() == 1
    received = errors.at(0)[0]
    assert received == texts_es.WORKER_ERROR_GENERIC
    assert "ZeroDivisionError" not in received


def test_worker_emits_progress_when_function_accepts_callback(qtbot: QtBot) -> None:
    """El worker inyecta `progress_callback` y reemite el avance (0–100)."""

    def job(progress_callback) -> str:  # noqa: ANN001 - parámetro inyectado
        progress_callback(10)
        progress_callback(55)
        progress_callback(100)
        return "listo"

    worker = Worker(job)
    progress = QSignalSpy(worker.signals.progress)
    finished = QSignalSpy(worker.signals.finished)

    _start(worker)
    _wait_for(finished, qtbot)
    _wait_for(progress, qtbot, count=3)

    assert finished.at(0)[0] == "listo"
    assert progress.count() == 3
    assert [progress.at(index)[0] for index in range(progress.count())] == [10, 55, 100]


def test_worker_does_not_inject_progress_without_parameter(qtbot: QtBot) -> None:
    """Si la función no declara `progress_callback`, no se le pasa nada."""
    calls: list[tuple[object, ...]] = []

    def job(*args: object) -> str:
        calls.append(args)
        return "ok"

    worker = Worker(job)
    finished = QSignalSpy(worker.signals.finished)

    _start(worker)
    _wait_for(finished, qtbot)

    assert calls == [()]
    assert finished.at(0)[0] == "ok"


def test_run_in_thread_delivers_result_in_ui_thread(qtbot: QtBot) -> None:
    """`run_in_thread` conecta los callbacks y el slot corre en el hilo de UI."""
    main_thread = QThread.currentThread()
    receiver = _Receiver()

    run_in_thread(lambda: "hecho", on_result=receiver.on_result)

    qtbot.waitUntil(lambda: receiver.results == ["hecho"], timeout=SIGNAL_TIMEOUT_MS)
    assert receiver.threads == [main_thread]


def test_run_in_thread_delivers_error_in_ui_thread(qtbot: QtBot) -> None:
    """Los errores también llegan al slot del hilo de interfaz."""
    main_thread = QThread.currentThread()
    receiver = _Receiver()

    run_in_thread(lambda: 1 / 0, on_error=receiver.on_error)

    qtbot.waitUntil(lambda: len(receiver.results) == 1, timeout=SIGNAL_TIMEOUT_MS)
    assert receiver.results == [texts_es.WORKER_ERROR_GENERIC]
    assert receiver.threads == [main_thread]
