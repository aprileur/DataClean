"""Pruebas del gestor de historial con snapshots (tarea T19)."""

from __future__ import annotations

import ast
from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from app import history
from app.history import History, HistoryItem

# Módulos que la lógica pura no debe importar nunca.
FORBIDDEN_MODULES = ("PySide6", "PySide2", "PyQt5", "PyQt6", "qtpy", "shiboken6")


# ------------------------------------------------------------------ helpers


def _df(value: int, rows: int = 3) -> pd.DataFrame:
    """DataFrame pequeño y distinguible para cada snapshot."""
    return pd.DataFrame(
        {
            "id": list(range(rows)),
            "valor": [value] * rows,
            "ciudad": [f"ciudad-{value}"] * rows,
        }
    )


# ------------------------------------------------------------------ pila básica


def test_new_history_is_empty() -> None:
    hist = History()

    assert len(hist) == 0
    assert hist.size == 0
    assert not hist
    assert hist.current_df is None
    assert hist.current_item is None
    assert hist.descriptions() == []
    assert hist.can_undo is False
    assert hist.undo() is None


def test_push_and_current_df() -> None:
    hist = History()
    original = _df(0)

    hist.push("Carga inicial", original)

    assert len(hist) == 1
    assert hist.can_undo is False
    current = hist.current_df
    assert current is not None
    assert_frame_equal(current, original)


def test_descriptions_in_chronological_order() -> None:
    hist = History()

    hist.push("Carga inicial", _df(0))
    hist.push("Eliminar duplicados", _df(1))
    hist.push("Imputar edad", _df(2))

    assert hist.descriptions() == ["Carga inicial", "Eliminar duplicados", "Imputar edad"]
    assert len(hist) == 3
    assert hist.can_undo is True


def test_history_item_has_timestamp() -> None:
    before = datetime.now()
    item = HistoryItem(description="Acción", df=_df(0))
    after = datetime.now()

    assert item.description == "Acción"
    assert before <= item.timestamp <= after
    assert_frame_equal(item.df, _df(0))


def test_clear_empties_the_stack() -> None:
    hist = History()
    hist.push("Carga inicial", _df(0))
    hist.push("Acción", _df(1))

    hist.clear()

    assert len(hist) == 0
    assert hist.current_df is None
    assert hist.descriptions() == []
    assert hist.can_undo is False


@pytest.mark.parametrize("bad_size", [0, -1, -10])
def test_invalid_max_size_raises(bad_size: int) -> None:
    with pytest.raises(ValueError, match="entero positivo"):
        History(max_size=bad_size)


# ------------------------------------------------------------------ inmutabilidad


def test_push_copies_input_dataframe() -> None:
    hist = History()
    source = _df(1)
    expected = _df(1)

    hist.push("Acción", source)
    source.loc[0, "valor"] = 999
    source["nueva"] = 0

    snapshot = hist.current_df
    assert snapshot is not None
    assert_frame_equal(snapshot, expected)


def test_current_df_returns_a_copy() -> None:
    hist = History()
    hist.push("Acción", _df(1))
    expected = _df(1)

    first = hist.current_df
    assert first is not None
    first.loc[0, "valor"] = 42

    second = hist.current_df
    assert second is not None
    assert_frame_equal(second, expected)


def test_undo_returns_a_copy() -> None:
    hist = History()
    hist.push("Carga inicial", _df(0))
    hist.push("Acción", _df(1))
    expected = _df(0)

    restored = hist.undo()
    assert restored is not None
    restored.loc[0, "valor"] = 123

    assert_frame_equal(hist.current_df, expected)


# ------------------------------------------------------------------ límite de 10


def test_limit_keeps_only_the_ten_most_recent_snapshots() -> None:
    hist = History()

    for index in range(12):
        hist.push(f"Acción {index}", _df(index))

    assert len(hist) == 10
    assert hist.size == 10
    assert len(hist.descriptions()) == 10
    # Los dos más antiguos (Acción 0 y Acción 1) se descartaron.
    assert hist.descriptions()[0] == "Acción 2"
    assert hist.descriptions()[-1] == "Acción 11"
    assert "Acción 0" not in hist.descriptions()
    assert "Acción 1" not in hist.descriptions()
    assert_frame_equal(hist.current_df, _df(11))


def test_limit_respects_custom_max_size() -> None:
    hist = History(max_size=3)

    for index in range(5):
        hist.push(f"Acción {index}", _df(index))

    assert len(hist) == 3
    assert hist.descriptions() == ["Acción 2", "Acción 3", "Acción 4"]


def test_max_size_one_disables_undo() -> None:
    hist = History(max_size=1)

    hist.push("Carga inicial", _df(0))
    hist.push("Acción", _df(1))

    assert len(hist) == 1
    assert hist.can_undo is False
    assert hist.undo() is None


# ------------------------------------------------------------------ undo


def test_undo_step_by_step_returns_exact_previous_state() -> None:
    hist = History()
    states = [_df(index) for index in range(3)]
    for index, state in enumerate(states):
        hist.push(f"Acción {index}", state)

    first_undo = hist.undo()
    assert first_undo is not None
    assert_frame_equal(first_undo, states[1])
    assert len(hist) == 2

    second_undo = hist.undo()
    assert second_undo is not None
    assert_frame_equal(second_undo, states[0])
    assert len(hist) == 1


def test_undo_preserves_index_and_dtypes() -> None:
    hist = History()
    original = pd.DataFrame({"id": [10, 11, 12], "nombre": ["Ana", "Luis", "Eva"]})
    modified = original.drop(index=1).reset_index(drop=True)

    hist.push("Carga inicial", original)
    hist.push("Eliminar fila", modified)
    restored = hist.undo()

    assert restored is not None
    assert_frame_equal(restored, original)
    assert list(restored.index) == [0, 1, 2]


def test_can_undo_becomes_false_at_base_state() -> None:
    hist = History()
    hist.push("Carga inicial", _df(0))
    hist.push("Acción", _df(1))
    assert hist.can_undo is True

    hist.undo()

    assert hist.can_undo is False
    assert hist.undo() is None
    assert len(hist) == 1


def test_can_undo_false_on_empty_history() -> None:
    hist = History()

    assert hist.can_undo is False
    assert hist.undo() is None


# ------------------------------------------------------------------ restore original


def test_restore_original_clears_later_actions() -> None:
    original = _df(0)
    hist = History()
    hist.push("Carga inicial", original)
    hist.push("Eliminar duplicados", _df(1))
    hist.push("Imputar edad", _df(2))

    restored = hist.restore_original(original)

    assert len(hist) == 1
    assert hist.can_undo is False
    assert hist.descriptions() == ["Restaurar original"]
    assert_frame_equal(restored, original)
    assert_frame_equal(hist.current_df, original)


def test_restore_original_uses_custom_description() -> None:
    hist = History()
    hist.push("Acción", _df(1))

    hist.restore_original(_df(0), description="Volver al dataset cargado")

    assert hist.descriptions() == ["Volver al dataset cargado"]


def test_restore_original_copies_both_ways() -> None:
    original = _df(0)
    expected = _df(0)
    hist = History()

    returned = hist.restore_original(original)
    original.loc[0, "valor"] = 777
    returned.loc[1, "valor"] = 888

    snapshot = hist.current_df
    assert snapshot is not None
    assert_frame_equal(snapshot, expected)


def test_restore_original_works_on_empty_history() -> None:
    hist = History()

    returned = hist.restore_original(_df(5))

    assert len(hist) == 1
    assert_frame_equal(returned, _df(5))


# ------------------------------------------------------------------ reglas


def test_history_does_not_import_qt() -> None:
    source = Path(history.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not any(alias.name.startswith(mod) for mod in FORBIDDEN_MODULES), alias.name
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            assert not any(module.startswith(mod) for mod in FORBIDDEN_MODULES), module
