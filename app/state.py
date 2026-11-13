"""Gestión central del estado de la aplicación y máquina de estados del flujo de trabajo."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

import pandas as pd
from PySide6.QtCore import QObject, Signal

from app.ui import texts_es


class Step(StrEnum):
    """Pasos ordenados del flujo de trabajo de DataClean."""

    LOAD = "LOAD"
    INFO = "INFO"
    PREVIEW = "PREVIEW"
    TYPES = "TYPES"
    CLEAN_A = "CLEAN_A"
    CLEAN_B = "CLEAN_B"
    CLEAN_C = "CLEAN_C"
    CLEAN_D = "CLEAN_D"
    CLEAN_E = "CLEAN_E"
    EXPORT = "EXPORT"

    @property
    def display_name(self) -> str:
        """Nombre amigable en español para mostrar en la interfaz."""
        names = {
            Step.LOAD: texts_es.STEP_1_NAME,
            Step.INFO: texts_es.STEP_2_NAME,
            Step.PREVIEW: texts_es.STEP_3_NAME,
            Step.TYPES: texts_es.STEP_4_NAME,
            Step.CLEAN_A: texts_es.STEP_5A_NAME,
            Step.CLEAN_B: texts_es.STEP_5B_NAME,
            Step.CLEAN_C: texts_es.STEP_5C_NAME,
            Step.CLEAN_D: texts_es.STEP_5D_NAME,
            Step.CLEAN_E: texts_es.STEP_5E_NAME,
            Step.EXPORT: texts_es.STEP_EXPORT_NAME,
        }
        return names.get(self, self.value)


STEP_ORDER: tuple[Step, ...] = (
    Step.LOAD,
    Step.INFO,
    Step.PREVIEW,
    Step.TYPES,
    Step.CLEAN_A,
    Step.CLEAN_B,
    Step.CLEAN_C,
    Step.CLEAN_D,
    Step.CLEAN_E,
    Step.EXPORT,
)


class StepLockedError(Exception):
    """Excepción lanzada cuando se intenta acceder a un paso no desbloqueado."""

    def __init__(self, step: Step, reason: str = "") -> None:
        self.step = step
        self.reason = reason
        step_name = step.display_name if isinstance(step, Step) else str(step)
        message = texts_es.ERROR_STEP_LOCKED.format(step_name=step_name)
        if reason:
            message += f" ({reason})"
        super().__init__(message)


@dataclass
class AppState:
    """Estado global de datos y progreso de la aplicación."""

    original_df: pd.DataFrame | None = None
    working_df: pd.DataFrame | None = None
    completed: set[Step] = field(default_factory=set)
    current: Step = Step.LOAD
    file_path: Path | None = None

    @property
    def has_data(self) -> bool:
        """Indica si hay un dataset cargado en la aplicación."""
        return self.working_df is not None

    def is_completed(self, step: Step) -> bool:
        """Verifica si un paso específico ya fue completado."""
        return step in self.completed

    def reset(self) -> None:
        """Reinicia el estado al punto inicial sin datos cargados."""
        self.original_df = None
        self.working_df = None
        self.completed.clear()
        self.current = Step.LOAD
        self.file_path = None


class WorkflowController(QObject):
    """Controlador central de navegación y máquina de estados del flujo de limpieza."""

    step_changed = Signal(object)  # Emite el nuevo Step actual
    step_completed = Signal(object)  # Emite el Step completado
    steps_invalidated = Signal(object)  # Emite el conjunto set[Step] invalidado
    state_reset = Signal()  # Emite cuando el flujo se reinicia por completo

    def __init__(self, state: AppState | None = None, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.state = state if state is not None else AppState()

    def can_enter(self, step: Step) -> bool:
        """Determina si es válido ingresar al paso indicado.

        Reglas:
        - El paso actual siempre es accesible.
        - El paso inicial (LOAD) siempre es accesible.
        - Para cualquier otro paso, todos los pasos precedentes deben estar completados.
        """
        if step == self.state.current:
            return True
        idx = STEP_ORDER.index(step)
        if idx == 0:
            return True
        return all(prev in self.state.completed for prev in STEP_ORDER[:idx])

    def go_to(self, step: Step) -> None:
        """Navega al paso indicado si está desbloqueado; de lo contrario lanza StepLockedError."""
        if not self.can_enter(step):
            raise StepLockedError(step)
        if self.state.current != step:
            self.state.current = step
            self.step_changed.emit(step)

    def complete(self, step: Step | None = None) -> None:
        """Marca un paso como completado y emite la señal correspondiente."""
        target = step if step is not None else self.state.current
        if target not in self.state.completed:
            self.state.completed.add(target)
            self.step_completed.emit(target)

    def invalidate_from(self, step: Step, inclusive: bool = False) -> set[Step]:
        """Invalida (remueve de completed) los pasos posteriores a `step`.

        Si `inclusive` es True, también invalida `step`.
        Por defecto (`inclusive=False`), preserva `step` y deja en pendiente
        únicamente los pasos subsecuentes (invalidación en cascada).
        Devuelve el conjunto de pasos que fueron removidos.
        """
        idx = STEP_ORDER.index(step)
        start_idx = idx if inclusive else idx + 1
        invalidated: set[Step] = set()
        for s in STEP_ORDER[start_idx:]:
            if s in self.state.completed:
                self.state.completed.remove(s)
                invalidated.add(s)

        if invalidated:
            self.steps_invalidated.emit(invalidated)
        return invalidated

    def invalidate_after(self, step: Step) -> set[Step]:
        """Invalida estrictamente los pasos posteriores a `step`."""
        return self.invalidate_from(step, inclusive=False)

    def reset(self) -> None:
        """Reinicia el flujo completo: borra datos, pasos completados y regresa a LOAD."""
        previous_step = self.state.current
        self.state.reset()
        self.state_reset.emit()
        if previous_step != Step.LOAD:
            self.step_changed.emit(Step.LOAD)

    def next_step(self) -> Step | None:
        """Obtiene el siguiente paso en la secuencia, o None si está al final."""
        idx = STEP_ORDER.index(self.state.current)
        if idx + 1 < len(STEP_ORDER):
            return STEP_ORDER[idx + 1]
        return None

    def previous_step(self) -> Step | None:
        """Obtiene el paso anterior en la secuencia, o None si está al inicio."""
        idx = STEP_ORDER.index(self.state.current)
        if idx > 0:
            return STEP_ORDER[idx - 1]
        return None

    def can_advance(self) -> bool:
        """Determina si es posible avanzar al siguiente paso."""
        nxt = self.next_step()
        if nxt is None:
            return False
        return self.can_enter(nxt)

    def advance(self) -> None:
        """Avanza al siguiente paso en la secuencia si está permitido."""
        nxt = self.next_step()
        if nxt is not None:
            self.go_to(nxt)

    def retreat(self) -> None:
        """Retrocede al paso anterior en la secuencia si existe."""
        prev = self.previous_step()
        if prev is not None:
            self.go_to(prev)

    def set_dataset(self, df: pd.DataFrame, file_path: Path | str | None = None) -> None:
        """Establece el dataset original inmutable y su copia de trabajo."""
        self.state.original_df = df.copy()
        self.state.working_df = df.copy()
        self.state.file_path = Path(file_path) if file_path else None
