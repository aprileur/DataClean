"""Prueba de humo básica para instanciación de la ventana principal."""

from PySide6.QtWidgets import QSizePolicy
from pytestqt.qtbot import QtBot

from app import __app_name__, __version__
from app.main_window import MainWindow


def test_main_window_smoke(qtbot: QtBot) -> None:
    """Verifica que MainWindow se instancia con las dimensiones y layouts correctos."""
    window = MainWindow()
    qtbot.addWidget(window)

    # Título y versión
    assert window.windowTitle() == f"{__app_name__} {__version__}"
    assert "0.0.1-alpha" in window.windowTitle()

    # Dimensiones mínimas y tamaño inicial
    assert window.minimumWidth() >= 900
    assert window.minimumHeight() >= 600

    # Sidebar fija
    assert window.sidebar is not None
    assert window.sidebar.width() == 240
    assert window.sidebar.sizePolicy().horizontalPolicy() == QSizePolicy.Policy.Fixed

    # Contenedor central expandible
    assert window.content_stack is not None
    assert window.content_stack.sizePolicy().horizontalPolicy() == QSizePolicy.Policy.Expanding
    assert window.content_stack.sizePolicy().verticalPolicy() == QSizePolicy.Policy.Expanding

    # Máquina de estados
    assert window.controller is not None
    assert window.controller.state.current.value == "LOAD"

    window.show()
    assert window.isVisible()
