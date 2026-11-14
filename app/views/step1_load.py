"""Vista del Paso 1 del flujo: selección y carga de un dataset tabular.

La vista se ocupa únicamente de la interacción con el usuario (drag & drop,
diálogo de selección de archivo, elección de hoja de Excel y mensajes de
error). La lectura de archivos vive en `app.services.loader` y la máquina de
estados del flujo, en `app.state`.
"""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDragMoveEvent, QDropEvent
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMessageBox,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.services.loader import (
    EXCEL_EXTENSIONS,
    SUPPORTED_EXTENSIONS,
    LoaderError,
    LoadResult,
    list_sheets,
    load_file,
)
from app.state import Step, WorkflowController
from app.ui import texts_es
from app.widgets import BusyIndicator, PrimaryButton, StepHeader
from app.workers import Worker, run_in_thread

logger = logging.getLogger(__name__)


class _Cancelled:
    """Marcador interno: el usuario canceló una acción (por ejemplo, la hoja)."""


_CANCELLED = _Cancelled()


class DropZone(QFrame):
    """Zona de arrastre que acepta archivos tabulares y notifica al usuario.

    Emite:
        file_dropped: ruta (str) del archivo soltado con extensión soportada.
        invalid_file_dropped: extensión (str) del archivo soltado no soportada.
        clicked: el usuario hizo clic dentro de la zona.
    """

    file_dropped = Signal(str)
    invalid_file_dropped = Signal(str)
    clicked = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("dropZone")
        self.setAcceptDrops(True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumHeight(220)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.title_label = QLabel(texts_es.LOAD_DROP_TITLE, self)
        self.title_label.setObjectName("dropZoneTitle")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.subtitle_label = QLabel(texts_es.LOAD_DROP_SUBTITLE, self)
        self.subtitle_label.setObjectName("dropZoneSubtitle")
        self.subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.subtitle_label.setWordWrap(True)

        self.file_label = QLabel("", self)
        self.file_label.setObjectName("dropZoneFileInfo")
        self.file_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.file_label.setWordWrap(True)
        self.file_label.setVisible(False)

        layout.addWidget(self.title_label)
        layout.addWidget(self.subtitle_label)
        layout.addWidget(self.file_label)

    # -- Arrastrar y soltar ------------------------------------------------ #

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802 (API Qt)
        """Acepta el arrastre solo si contiene un archivo con extensión válida."""
        if self._first_supported_path(event) is not None:
            self._set_drag_active(True)
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:  # noqa: N802 (API Qt)
        """Mantiene la aceptación del arrastre mientras se mueve sobre la zona."""
        if self._first_supported_path(event) is not None:
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802 (API Qt)
        """Emite la ruta del archivo soltado (o avisa si el formato no sirve)."""
        self._set_drag_active(False)
        supported = self._first_supported_path(event)
        if supported is not None:
            self.file_dropped.emit(str(supported))
            event.acceptProposedAction()
            return

        rejected = self._first_path(event)
        suffix = rejected.suffix.lower() if rejected is not None else ""
        self.invalid_file_dropped.emit(suffix)
        event.ignore()

    # -- Interacción ------------------------------------------------------- #

    def mouseReleaseEvent(self, event) -> None:  # noqa: ANN001, N802 (API Qt)
        """Emite `clicked` al hacer clic dentro de la zona de arrastre."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mouseReleaseEvent(event)

    # -- Utilidades internas ----------------------------------------------- #

    @staticmethod
    def _local_paths(event) -> list[Path]:  # noqa: ANN001
        """Extrae las rutas locales contenidas en el MIME del evento."""
        mime_data = event.mimeData()
        if mime_data is None or not mime_data.hasUrls():
            return []
        paths: list[Path] = []
        for url in mime_data.urls():
            if url.isLocalFile():
                paths.append(Path(url.toLocalFile()))
        return paths

    def _first_path(self, event) -> Path | None:  # noqa: ANN001
        """Devuelve la primera ruta local del evento de arrastre."""
        paths = self._local_paths(event)
        return paths[0] if paths else None

    def _first_supported_path(self, event) -> Path | None:  # noqa: ANN001
        """Devuelve la primera ruta local con una extensión soportada."""
        for path in self._local_paths(event):
            if path.suffix.lower() in SUPPORTED_EXTENSIONS:
                return path
        return None

    def _set_drag_active(self, active: bool) -> None:
        """Activa o desactiva el resaltado visual del arrastre."""
        self.setProperty("dragActive", "true" if active else "false")
        style = self.style()
        if style is not None:
            style.unpolish(self)
            style.polish(self)
        self.update()


class Step1LoadView(QWidget):
    """Vista del paso 1: arrastrar, elegir y cargar el archivo de datos."""

    def __init__(self, controller: WorkflowController, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.controller = controller
        self._selected_path: Path | None = None
        #: Referencia al worker en curso. Mantenerla viva evita que se destruya
        #: antes de entregar `finished`/`error` y sirve de guarda anti doble clic.
        self._load_worker: Worker | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        self.header = StepHeader(step_number=1, title=texts_es.STEP_1_NAME, parent=self)

        self.drop_zone = DropZone(self)
        self.drop_zone.file_dropped.connect(self.select_file)
        self.drop_zone.invalid_file_dropped.connect(self._on_invalid_file)
        self.drop_zone.clicked.connect(self.open_file_dialog)

        buttons_row = QHBoxLayout()
        buttons_row.setContentsMargins(0, 0, 0, 0)
        buttons_row.setSpacing(10)

        self.select_button = PrimaryButton(texts_es.LOAD_BTN_SELECT, self)
        self.select_button.clicked.connect(self.open_file_dialog)

        self.load_button = PrimaryButton(texts_es.LOAD_BTN_LOAD, self)
        self.load_button.setEnabled(False)
        self.load_button.setToolTip(texts_es.LOAD_BTN_LOAD_DISABLED_TOOLTIP)
        self.load_button.clicked.connect(self.load_selected_file)

        buttons_row.addWidget(self.select_button)
        buttons_row.addWidget(self.load_button)
        buttons_row.addStretch()

        self.busy_indicator = BusyIndicator(texts_es.LOAD_PROGRESS_LABEL, self)

        layout.addWidget(self.header)
        layout.addWidget(self.drop_zone, 1)
        layout.addLayout(buttons_row)
        layout.addWidget(self.busy_indicator)

    # -- API pública ------------------------------------------------------- #

    @property
    def selected_path(self) -> Path | None:
        """Ruta del archivo seleccionado actualmente (o None)."""
        return self._selected_path

    @property
    def is_loading(self) -> bool:
        """Indica si hay una carga en curso en segundo plano."""
        return self._load_worker is not None

    def select_file(self, path: str | Path) -> bool:
        """Selecciona el archivo a cargar.

        Valida la extensión: si no está soportada muestra un error y deja el
        estado intacto. Devuelve `True` si el archivo fue aceptado.
        """
        file_path = Path(path)
        suffix = file_path.suffix.lower()
        if suffix not in SUPPORTED_EXTENSIONS:
            self._on_invalid_file(suffix)
            return False

        self._selected_path = file_path
        self._update_file_label()
        self.load_button.setEnabled(True)
        self.load_button.setToolTip(texts_es.LOAD_BTN_LOAD_TOOLTIP)
        return True

    def open_file_dialog(self) -> None:
        """Abre el diálogo del sistema para elegir un archivo de datos."""
        path, _selected_filter = QFileDialog.getOpenFileName(
            self, texts_es.LOAD_BTN_SELECT, "", texts_es.LOAD_FILE_FILTER
        )
        if path:
            self.select_file(path)

    def load_selected_file(self) -> None:
        """Carga el archivo seleccionado en segundo plano.

        La lectura corre en el `QThreadPool` mediante `run_in_thread`; el
        resultado se procesa en `_on_load_finished`, ya en el hilo de interfaz.
        Mientras la operación está en curso la vista queda deshabilitada y se
        ignora cualquier intento de arrancar una segunda carga.
        """
        path = self._selected_path
        if path is None or self._load_worker is not None:
            return

        sheet = self._ask_for_sheet(path)
        if isinstance(sheet, _Cancelled):
            return

        self._set_busy(True)
        logger.info("Cargando %s en segundo plano (hoja=%s)", path, sheet)
        self._load_worker = run_in_thread(
            load_file,
            path,
            sheet=sheet,
            on_result=self._on_load_finished,
            on_error=self._on_load_error,
        )

    # -- Resultado de la carga (hilo de interfaz) -------------------------- #

    def _on_load_finished(self, result: LoadResult) -> None:
        """Aplica el `LoadResult` recibido del worker y avanza al paso 2."""
        self._load_worker = None
        self._set_busy(False)

        df = result.df
        file_name = result.file_name
        if self.controller.state.has_data:
            self.controller.reset()

        self.controller.set_dataset(df, file_name)
        self.controller.complete(Step.LOAD)
        self.controller.go_to(Step.INFO)

    def _on_load_error(self, message: str) -> None:
        """Muestra el error en español y deja la vista lista para reintentar."""
        self._load_worker = None
        self._set_busy(False)
        logger.warning("No se pudo cargar el archivo: %s", message)

        # Los `LoaderError` ya traen un mensaje en español; el resto de
        # excepciones llegan como mensaje genérico y se traducen al texto de
        # carga para dar contexto al usuario.
        if message == texts_es.WORKER_ERROR_GENERIC:
            message = texts_es.LOAD_UNEXPECTED_ERROR
        self._show_error(message)

    # -- Utilidades internas ----------------------------------------------- #

    def _set_busy(self, busy: bool) -> None:
        """Deshabilita la vista y muestra la barra indeterminada mientras carga."""
        self.busy_indicator.set_busy(busy)
        self.setEnabled(not busy)

    def _ask_for_sheet(self, path: Path) -> str | None | _Cancelled:
        """Pregunta qué hoja de Excel cargar si el libro tiene más de una."""
        if path.suffix.lower() not in EXCEL_EXTENSIONS:
            return None

        try:
            sheets = list_sheets(path)
        except LoaderError as exc:
            logger.warning("No se pudieron listar las hojas de %s: %s", path, exc)
            self._show_error(str(exc))
            return _CANCELLED

        if len(sheets) <= 1:
            return None

        sheet, accepted = QInputDialog.getItem(
            self,
            texts_es.LOAD_SHEET_DIALOG_TITLE,
            texts_es.LOAD_SHEET_DIALOG_PROMPT,
            sheets,
            0,
            False,
        )
        return sheet if accepted else _CANCELLED

    def _on_invalid_file(self, suffix: str) -> None:
        """Muestra un error amigable cuando el formato no está soportado."""
        shown = suffix or "sin extensión"
        supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        self._show_error(texts_es.LOAD_INVALID_FORMAT.format(ext=shown, supported=supported))

    def _show_error(self, message: str) -> None:
        """Muestra un diálogo de error en español (nunca un traceback)."""
        QMessageBox.critical(self, texts_es.LOAD_ERR_TITLE, message)

    def _update_file_label(self) -> None:
        """Actualiza la etiqueta con el nombre y el tamaño del archivo elegido."""
        path = self._selected_path
        if path is None:
            self.drop_zone.file_label.setText("")
            self.drop_zone.file_label.setVisible(False)
            return

        self.drop_zone.file_label.setText(
            texts_es.LOAD_FILE_INFO.format(name=path.name, size=format_file_size(path))
        )
        self.drop_zone.file_label.setVisible(True)


def format_file_size(path: Path) -> str:
    """Devuelve el tamaño del archivo en un formato legible (B, KB o MB)."""
    try:
        size = path.stat().st_size
    except OSError:
        return "?"

    if size >= 1024 * 1024:
        value = f"{size / (1024 * 1024):.2f}".replace(".", ",")
        return texts_es.LOAD_SIZE_MB.format(size=value)
    if size >= 1024:
        value = f"{size / 1024:.1f}".replace(".", ",")
        return texts_es.LOAD_SIZE_KB.format(size=value)
    return texts_es.LOAD_SIZE_B.format(size=size)
