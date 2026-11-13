"""Pruebas unitarias para AppState y WorkflowController (máquina de estados)."""

import pandas as pd
import pytest

from app.state import STEP_ORDER, Step, StepLockedError, WorkflowController


def test_initial_state_can_only_enter_load():
    """Al inicio, el único paso accesible es LOAD; intentar saltar lanza StepLockedError."""
    controller = WorkflowController()
    assert controller.state.current == Step.LOAD
    assert controller.state.completed == set()
    assert controller.can_enter(Step.LOAD) is True

    # Los demás pasos deben estar bloqueados
    for step in STEP_ORDER[1:]:
        assert controller.can_enter(step) is False
        with pytest.raises(StepLockedError):
            controller.go_to(step)


def test_jump_from_load_to_clean_a_raises_step_locked_error():
    """Saltar directamente de LOAD a CLEAN_A lanza StepLockedError (caso obligatorio §6)."""
    controller = WorkflowController()
    assert controller.can_enter(Step.CLEAN_A) is False

    with pytest.raises(StepLockedError) as exc_info:
        controller.go_to(Step.CLEAN_A)

    assert exc_info.value.step == Step.CLEAN_A
    assert Step.CLEAN_A.value in str(exc_info.value) or Step.CLEAN_A.display_name in str(
        exc_info.value
    )


def test_complete_step_unlocks_only_immediate_next():
    """Completar un paso desbloquea SOLO el siguiente paso en la secuencia (caso §6)."""
    controller = WorkflowController()

    # Completar LOAD
    controller.complete(Step.LOAD)
    assert Step.LOAD in controller.state.completed

    # Ahora INFO debe ser accesible, pero PREVIEW y posteriores no
    assert controller.can_enter(Step.INFO) is True
    assert controller.can_enter(Step.PREVIEW) is False
    assert controller.can_enter(Step.TYPES) is False
    assert controller.can_enter(Step.CLEAN_A) is False

    # Avanzar a INFO y completarlo
    controller.go_to(Step.INFO)
    assert controller.state.current == Step.INFO
    controller.complete(Step.INFO)

    # Ahora PREVIEW se desbloquea, pero TYPES sigue bloqueado
    assert controller.can_enter(Step.PREVIEW) is True
    assert controller.can_enter(Step.TYPES) is False


def test_can_freely_retreat_to_completed_steps():
    """Retroceder a pasos ya completados está permitido y no altera lo completado (caso §6)."""
    controller = WorkflowController()

    # Avanzar hasta TYPES
    for step in [Step.LOAD, Step.INFO, Step.PREVIEW]:
        controller.complete(step)
        nxt = controller.next_step()
        assert nxt is not None
        controller.go_to(nxt)

    assert controller.state.current == Step.TYPES

    # Retroceder libremente a pasos anteriores
    assert controller.can_enter(Step.PREVIEW) is True
    controller.go_to(Step.PREVIEW)
    assert controller.state.current == Step.PREVIEW

    assert controller.can_enter(Step.INFO) is True
    controller.go_to(Step.INFO)
    assert controller.state.current == Step.INFO

    assert controller.can_enter(Step.LOAD) is True
    controller.go_to(Step.LOAD)
    assert controller.state.current == Step.LOAD

    # El conjunto de completados no se alteró al solo retroceder
    assert {Step.LOAD, Step.INFO, Step.PREVIEW}.issubset(controller.state.completed)


def test_cascade_invalidation_after_modifying_previous_step():
    """Completar hasta CLEAN_C y modificar CLEAN_A deja CLEAN_B..CLEAN_E en pendiente (caso §6)."""
    controller = WorkflowController()

    # Completar en orden lineal hasta CLEAN_C
    steps_to_complete = [
        Step.LOAD,
        Step.INFO,
        Step.PREVIEW,
        Step.TYPES,
        Step.CLEAN_A,
        Step.CLEAN_B,
        Step.CLEAN_C,
    ]
    for step in steps_to_complete:
        controller.complete(step)
        nxt = controller.next_step()
        if nxt and nxt in steps_to_complete:
            controller.go_to(nxt)

    assert controller.state.current == Step.CLEAN_C
    assert set(steps_to_complete).issubset(controller.state.completed)

    # El usuario retrocede a CLEAN_A
    controller.go_to(Step.CLEAN_A)
    assert controller.state.current == Step.CLEAN_A

    # El usuario modifica datos en CLEAN_A -> invalidación en cascada de pasos posteriores
    invalidated = controller.invalidate_from(Step.CLEAN_A)

    # CLEAN_A permanece completado; CLEAN_B y CLEAN_C fueron invalidados
    assert Step.CLEAN_A in controller.state.completed
    assert Step.CLEAN_B not in controller.state.completed
    assert Step.CLEAN_C not in controller.state.completed
    assert invalidated == {Step.CLEAN_B, Step.CLEAN_C}

    # CLEAN_B puede ser ingresado porque su prerrequisito (CLEAN_A) está completo
    assert controller.can_enter(Step.CLEAN_B) is True

    # Pero CLEAN_C..EXPORT están completamente bloqueados
    assert controller.can_enter(Step.CLEAN_C) is False
    assert controller.can_enter(Step.CLEAN_D) is False
    assert controller.can_enter(Step.CLEAN_E) is False
    assert controller.can_enter(Step.EXPORT) is False

    with pytest.raises(StepLockedError):
        controller.go_to(Step.CLEAN_C)


def test_reset_restores_load_and_clears_all():
    """reset() vuelve a LOAD, limpia completados, dataset y metadatos (caso obligatorio §6)."""
    controller = WorkflowController()
    sample_df = pd.DataFrame({"col": [1, 2, 3]})
    controller.set_dataset(sample_df, "test.csv")

    controller.complete(Step.LOAD)
    controller.go_to(Step.INFO)
    controller.complete(Step.INFO)

    assert controller.state.current == Step.INFO
    assert len(controller.state.completed) == 2
    assert controller.state.has_data is True

    # Ejecutar reset
    controller.reset()

    assert controller.state.current == Step.LOAD
    assert controller.state.completed == set()
    assert controller.state.original_df is None
    assert controller.state.working_df is None
    assert controller.state.file_path is None
    assert controller.state.has_data is False
    assert controller.can_enter(Step.INFO) is False


def test_dataset_immutability_on_controller():
    """Modificar working_df no muta original_df (aislamiento por .copy())."""
    controller = WorkflowController()
    df = pd.DataFrame({"a": [10, 20], "b": ["x", "y"]})
    controller.set_dataset(df, "data.csv")

    # Modificar working_df
    assert controller.state.working_df is not None
    assert controller.state.original_df is not None

    controller.state.working_df["c"] = [99, 100]
    controller.state.working_df.loc[0, "a"] = 999

    # original_df debe permanecer intacto
    assert "c" not in controller.state.original_df.columns
    assert controller.state.original_df.loc[0, "a"] == 10


def test_controller_signals_emitted():
    """Verifica la emisión de señales Qt durante transiciones y cambios de estado."""
    controller = WorkflowController()

    changed_steps = []
    completed_steps = []
    invalidated_payloads = []
    reset_called = []

    controller.step_changed.connect(changed_steps.append)
    controller.step_completed.connect(completed_steps.append)
    controller.steps_invalidated.connect(invalidated_payloads.append)
    controller.state_reset.connect(lambda: reset_called.append(True))

    controller.complete(Step.LOAD)
    assert completed_steps == [Step.LOAD]

    controller.go_to(Step.INFO)
    assert changed_steps == [Step.INFO]

    controller.complete(Step.INFO)
    assert completed_steps == [Step.LOAD, Step.INFO]

    controller.invalidate_from(Step.LOAD)
    assert len(invalidated_payloads) == 1
    assert Step.INFO in invalidated_payloads[0]

    controller.reset()
    assert len(reset_called) == 1
    assert changed_steps[-1] == Step.LOAD


def test_navigation_helpers():
    """Prueba advance(), retreat(), next_step(), previous_step() y can_advance()."""
    controller = WorkflowController()
    assert controller.previous_step() is None
    assert controller.next_step() == Step.INFO
    assert controller.can_advance() is False

    controller.complete(Step.LOAD)
    assert controller.can_advance() is True

    controller.advance()
    assert controller.state.current == Step.INFO
    assert controller.previous_step() == Step.LOAD

    controller.retreat()
    assert controller.state.current == Step.LOAD
