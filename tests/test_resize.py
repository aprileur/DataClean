"""Pruebas de reescalado de la ventana principal (T23)."""

from __future__ import annotations

from collections.abc import Iterator

from PySide6.QtWidgets import QWidget
from pytestqt.qtbot import QtBot

from app.main_window import MainWindow

#: Tamaño mínimo exigido por la especificación.
MIN_SIZE = (900, 600)

#: Tamaño de pantalla completa usado en las pruebas.
FULL_HD = (1920, 1080)


def visible_descendants(widget: QWidget) -> Iterator[QWidget]:
    """Recorre los widgets hijos visibles (excluye ventanas independientes)."""
    for child in widget.findChildren(QWidget):
        if child.isWindow() or not child.isVisible():
            continue
        yield child
        yield from visible_descendants(child)


def assert_no_overflow(window: MainWindow) -> None:
    """Comprueba que ningún widget visible excede el rectángulo de su padre."""
    for child in visible_descendants(window):
        parent = child.parentWidget()
        if parent is None or not parent.isVisible():
            continue
        assert parent.rect().adjusted(-1, -1, 1, 1).contains(child.geometry()), (
            f"{child.objectName() or type(child).__name__} excede a "
            f"{parent.objectName() or type(parent).__name__}"
        )


def test_minimum_size_respected(qtbot: QtBot) -> None:
    """La ventana no puede reducirse por debajo de 900×600."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()

    window.resize(200, 200)
    qtbot.wait(20)

    assert window.minimumWidth() >= MIN_SIZE[0]
    assert window.minimumHeight() >= MIN_SIZE[1]
    assert window.width() >= MIN_SIZE[0]
    assert window.height() >= MIN_SIZE[1]


def test_no_child_overflow_at_minimum(qtbot: QtBot) -> None:
    """Ningún widget visible excede el rectángulo de su padre a 900×600."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    window.resize(*MIN_SIZE)
    qtbot.wait(30)

    assert (window.width(), window.height()) == MIN_SIZE
    assert_no_overflow(window)


def test_no_child_overflow_at_fullscreen(qtbot: QtBot) -> None:
    """Ningún widget visible excede el rectángulo de su padre a 1920×1080."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    window.resize(*FULL_HD)
    qtbot.wait(30)

    assert (window.width(), window.height()) == FULL_HD
    assert_no_overflow(window)


def test_sidebar_fixed_width(qtbot: QtBot) -> None:
    """La sidebar mantiene 240 px en cualquier tamaño de ventana."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()

    for width, height in (MIN_SIZE, FULL_HD):
        window.resize(width, height)
        qtbot.wait(20)
        assert window.sidebar.width() == 240


def test_content_stack_expands_with_window(qtbot: QtBot) -> None:
    """El área de contenido crece con la ventana y la sidebar no."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()

    window.resize(*MIN_SIZE)
    qtbot.wait(20)
    small = window.content_stack.width()

    window.resize(*FULL_HD)
    qtbot.wait(20)
    large = window.content_stack.width()

    assert large > small
    assert window.sidebar.width() == 240
