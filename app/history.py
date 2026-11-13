"""Historial de acciones y deshacer para el flujo de limpieza (tarea T19).

Este módulo es lógica pura: **no** importa Qt ni conoce la interfaz gráfica.
Guarda snapshots completos del DataFrame de trabajo (decisión D7: máximo 10)
para permitir deshacer la última acción o restaurar el dataset original.

Nunca se mutan los DataFrames recibidos ni los almacenados: cada `push` y cada
consulta (`current_df`, `undo`) trabaja sobre una copia (`.copy()`).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime

import pandas as pd

logger = logging.getLogger(__name__)

#: Número máximo de snapshots completos conservados en memoria (decisión D7).
DEFAULT_MAX_SIZE: int = 10


@dataclass
class HistoryItem:
    """Snapshot del dataset asociado a la acción que lo produjo."""

    description: str
    df: pd.DataFrame
    timestamp: datetime = field(default_factory=datetime.now)


class History:
    """Pila de snapshots del dataset con límite de tamaño y deshacer.

    El snapshot más antiguo (la base) representa el estado inicial del dataset;
    cada acción de limpieza añade un snapshot nuevo en la cima. `undo` descarta
    la cima y devuelve una copia del snapshot anterior.
    """

    def __init__(self, max_size: int = DEFAULT_MAX_SIZE) -> None:
        """Inicializa una pila vacía con capacidad máxima `max_size`.

        Raises:
            ValueError: si `max_size` no es un entero positivo.
        """
        if not isinstance(max_size, int) or isinstance(max_size, bool) or max_size < 1:
            raise ValueError(
                "El tamaño máximo del historial debe ser un entero positivo "
                f"(recibido: {max_size!r})."
            )
        self.max_size = max_size
        self._items: list[HistoryItem] = []

    # ------------------------------------------------------------------ API

    def push(self, description: str, df: pd.DataFrame) -> None:
        """Añade un snapshot inmutable del dataset a la cima de la pila.

        Args:
            description: Texto en español que describe la acción aplicada.
            df: DataFrame resultante de la acción; se guarda una copia.
        """
        self._items.append(HistoryItem(description=description, df=df.copy()))
        if len(self._items) > self.max_size:
            removed = self._items.pop(0)
            logger.debug(
                "Historial lleno (%s snapshots): se descarta el más antiguo (%r).",
                self.max_size,
                removed.description,
            )

    @property
    def can_undo(self) -> bool:
        """True si existe un estado previo al cual retroceder."""
        return len(self._items) > 1

    def undo(self) -> pd.DataFrame | None:
        """Descarta el estado actual y devuelve una copia del estado anterior.

        Returns:
            Copia del nuevo snapshot en la cima, o `None` si no hay nada que
            deshacer (pila vacía o con un único snapshot base).
        """
        if not self.can_undo:
            return None
        removed = self._items.pop()
        logger.debug("Deshacer acción %r.", removed.description)
        return self._items[-1].df.copy()

    def restore_original(
        self, original_df: pd.DataFrame, description: str = "Restaurar original"
    ) -> pd.DataFrame:
        """Reinicia la pila con una copia del dataset original.

        Descarta todas las acciones posteriores y deja un único snapshot base.

        Returns:
            Copia exacta del DataFrame original recibido.
        """
        self._items.clear()
        self._items.append(HistoryItem(description=description, df=original_df.copy()))
        logger.debug("Historial reiniciado con el dataset original.")
        return original_df.copy()

    @property
    def current_df(self) -> pd.DataFrame | None:
        """Copia del snapshot en la cima, o `None` si la pila está vacía."""
        if not self._items:
            return None
        return self._items[-1].df.copy()

    @property
    def current_item(self) -> HistoryItem | None:
        """Snapshot completo en la cima (sin copia del DataFrame), o `None`."""
        if not self._items:
            return None
        return self._items[-1]

    def clear(self) -> None:
        """Vacía por completo la pila de snapshots."""
        self._items.clear()

    def descriptions(self) -> list[str]:
        """Descripciones de las acciones guardadas, en orden cronológico."""
        return [item.description for item in self._items]

    def __len__(self) -> int:
        """Cantidad de snapshots guardados actualmente."""
        return len(self._items)

    @property
    def size(self) -> int:
        """Alias explícito de `len(history)`."""
        return len(self._items)

    def __bool__(self) -> bool:
        """True si el historial contiene al menos un snapshot."""
        return bool(self._items)
