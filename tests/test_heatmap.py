"""Pruebas unitarias para el widget de mapa de calor MissingDataHeatmap."""

import pandas as pd
from pytestqt.qtbot import QtBot

from app.widgets.heatmap import MissingDataHeatmap


def test_heatmap_instantiation_and_render(qtbot: QtBot):
    """Instancia el heatmap y dibuja una máscara con datos."""
    widget = MissingDataHeatmap()
    qtbot.addWidget(widget)

    mask = pd.DataFrame(
        {
            "col1": [False, True, False, False],
            "col2": [False, False, True, False],
            "col3": [False, False, False, False],
        }
    )

    widget.set_data(mask, is_sample=False)
    assert widget.has_data is True

    # Verificar que el canvas es visible
    widget.show()
    assert widget.isVisible()


def test_heatmap_with_sample_and_clear(qtbot: QtBot):
    """Prueba aviso de muestra representativa y método clear()."""
    widget = MissingDataHeatmap()
    qtbot.addWidget(widget)

    mask = pd.DataFrame({"a": [True, False], "b": [False, True]})
    widget.set_data(mask, is_sample=True, total_rows=1000)
    assert widget.has_data is True
    assert "Muestra" in widget.axes.get_title()

    widget.clear()
    assert widget.has_data is False


def test_heatmap_empty_data(qtbot: QtBot):
    """Prueba con máscara vacía sin errores."""
    widget = MissingDataHeatmap()
    qtbot.addWidget(widget)

    widget.set_data(pd.DataFrame())
    assert widget.has_data is False
