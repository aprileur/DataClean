# Prompt — Agente B: Infraestructura transversal + integración final

## Contexto del proyecto

Eres el **Agente B** del proyecto **DataClean**, una aplicación de escritorio en Python/PySide6 que permite cargar un dataset tabular (CSV, Excel, Parquet) y limpiarlo paso a paso. El idioma de la UI es **español**; el código (variables, funciones, clases) va en **inglés**.

El repositorio ya está en GitHub. Tu trabajo se hace en la branch **`feature/infraestructura`** y al terminar envías un Pull Request a `main`.

---

## Repositorio

```
D:\pycharm\Estructura de Datos\Programacion 2\DataClean
```

**URL de GitHub:** `https://github.com/aprileur/DataClean`

---

## Lo que YA existe (no toques esto)

### Stack y estructura

- Python 3.13 · PySide6 · pandas 3 · pyarrow · openpyxl · rapidfuzz · matplotlib (backend `QtAgg`)
- Tests con pytest + pytest-qt (219 en verde al inicio de tu sesión)

```
app/
├── __main__.py          # QApplication + HiDPI setup
├── main_window.py       # QMainWindow: top bar lila + sidebar 240px + QStackedWidget
├── state.py             # AppState + WorkflowController + Step(StrEnum) + StepLockedError
├── history.py           # History: push / undo / restore_original (máx. 10 snapshots)
├── theme.py / theme.qss # Estilos centralizados
├── services/
│   ├── loader.py        # load_file, detect_encoding, detect_separator, list_sheets, LoaderError
│   ├── profiling.py     # dataset_shape, classify_columns, missing_summary, missing_row_union
│   ├── cleaning.py      # servicios A–E (todos implementados y testeados)
│   └── exporter.py      # export_dataset, generate_export_path, ExportError
├── views/
│   ├── step1_load.py    # vista de carga (drag & drop)
│   ├── step2_info.py    # información general
│   ├── step3_preview.py # vista previa con spinbox
│   ├── step4_types.py   # clasificación de columnas
│   └── step5_cleaning/  # ← el Agente A trabaja aquí (branch separada)
├── widgets/
│   ├── dataframe_table.py  # DataFrameTable (QTableView reutilizable)
│   ├── heatmap.py          # MissingDataHeatmap (matplotlib)
│   ├── banner.py           # WarningBanner
│   ├── buttons.py          # DangerButton
│   ├── cards.py            # StatCard, InfoCard
│   └── step_header.py      # StepHeader (círculo numerado)
└── ui/
    └── texts_es.py      # TODOS los textos visibles al usuario
```

### Servicio de exportación (ya implementado, solo necesitas la vista)

```python
# app/services/exporter.py
def generate_export_path(source_path, target_extension, output_dir=None) -> Path:
    # Calcula ruta sin colisión: <stem>_nuevo.<ext>, luego <stem>_nuevo_2.<ext>…

def export_dataset(df, target_path) -> Path:
    # Exporta según extensión: .csv (utf-8-sig), .xlsx (openpyxl), .parquet (pyarrow)
    # Lanza ExportError con mensaje en español si falla
```

### WorkflowController (referencia rápida)

```python
class Step(StrEnum):
    LOAD, INFO, PREVIEW, TYPES, CLEAN_A, CLEAN_B, CLEAN_C, CLEAN_D, CLEAN_E, EXPORT

class WorkflowController(QObject):
    step_changed    = Signal(object)   # emite Step
    step_completed  = Signal(object)   # emite Step
    state_reset     = Signal()

    def complete(self, step): ...       # marca paso completado
    def go_to(self, step): ...          # navega (lanza StepLockedError si bloqueado)
    def advance(self): ...
    def can_enter(self, step) -> bool
    state: AppState   # .working_df, .original_df, .file_path, .history, .completed

class AppState:
    working_df: pd.DataFrame | None
    original_df: pd.DataFrame | None
    file_path: Path | None
    history: History
```

### Textos en español relevantes

```python
# app/ui/texts_es.py
EXPORT_TITLE          # "Exportar dataset limpio"
EXPORT_BTN            # "Exportar dataset limpio"
EXPORT_SUMMARY_TITLE  # "Resumen de cambios aplicados:"
EXPORT_SUCCESS_TITLE  # "Exportación exitosa"
EXPORT_SUCCESS_MSG    # "El dataset limpio fue guardado exitosamente en:\n{path}"
BTN_UNDO              # "Deshacer última acción"
BTN_RESTORE_ORIGINAL  # "Restaurar original"
STEP_EXPORT_NAME      # "Exportar dataset limpio"
```

Si necesitas añadir textos nuevos, agrégalos al final de `app/ui/texts_es.py`.

---

## Paso 0 — Crear la branch

```powershell
cd "D:\pycharm\Estructura de Datos\Programacion 2\DataClean"
git checkout main
git pull origin main
git checkout -b feature/infraestructura
```

## Paso 1 — Verificar estado inicial

```powershell
.venv\Scripts\Activate.ps1
python -m pytest -q   # debe pasar en verde (219 tests)
python -m app         # debe abrir la ventana
```

---

## Tareas a implementar (en este orden)

### T22 — Logging y borde de errores

**Archivos:** `app/logging_config.py` y `app/ui/error_boundary.py`

#### `app/logging_config.py`

```python
def setup_logging() -> None:
    """Configura el logger raíz con RotatingFileHandler.

    - Archivo: data_clean.log (en el directorio de trabajo)
    - Rotación: 1 MB × 3 archivos de respaldo
    - Nivel: INFO
    - Formato: "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    - También añade un StreamHandler a stderr con nivel WARNING
      (para que los errores sean visibles en desarrollo sin inundar la consola)
    """
```

Llámalo desde `app/__main__.py` **antes** de crear el `QApplication`.

#### `app/ui/error_boundary.py`

```python
def handle_exception(exc_type, exc_value, exc_tb) -> None:
    """sys.excepthook: loguea el traceback completo y muestra QMessageBox amigable."""

def qt_slot_error_handler(func):
    """Decorador para slots Qt: captura excepciones, loguea y muestra diálogo."""

class ErrorContext:
    """Context manager: captura excepciones, loguea y muestra diálogo."""
    def __enter__(self): ...
    def __exit__(self, exc_type, exc_value, exc_tb) -> bool: ...
```

Reglas:
- El `QMessageBox` muestra un mensaje genérico en español ("Ocurrió un error inesperado. Consulta el archivo `data_clean.log` para más detalles."), **nunca** el traceback.
- El traceback completo va **solo** al log con `logging.exception(...)`.
- Configurar `sys.excepthook = handle_exception` en `app/__main__.py`.
- Los mensajes del log van en inglés (formato técnico); los del diálogo en español.

**Tests:** `tests/test_logging.py`
- Verificar que `setup_logging()` crea el archivo de log y el handler de rotación.
- Verificar que `ErrorContext` captura excepciones y no las re-lanza.
- Verificar que el decorador `qt_slot_error_handler` no propaga la excepción.

---

### T21 — Hilos para operaciones pesadas

**Archivo:** `app/workers.py`

```python
class WorkerSignals(QObject):
    finished = Signal(object)   # emite el resultado de la función
    error    = Signal(str)      # emite mensaje de error en español
    progress = Signal(int)      # emite 0–100

class Worker(QRunnable):
    """Ejecuta una función callable en un hilo de QThreadPool.

    Uso:
        worker = Worker(fn, *args, **kwargs)
        worker.signals.finished.connect(on_result)
        worker.signals.error.connect(on_error)
        QThreadPool.globalInstance().start(worker)
    """

def run_in_thread(fn, *args, on_result=None, on_error=None, **kwargs) -> Worker:
    """Atajo para crear y lanzar un Worker con callbacks opcionales."""
```

Integrar en la vista del Paso 1 (`step1_load.py`) para que la carga de archivos corra en el worker. Mientras carga:
- Deshabilitar el botón "Cargar datos".
- Mostrar una `QProgressBar` indeterminada (`.setRange(0, 0)`).
- Al terminar (señal `finished`): re-habilitar botón, ocultar progress, actualizar estado.
- Al error (señal `error`): re-habilitar botón, ocultar progress, mostrar `QMessageBox` con el mensaje.

**Regla crítica:** el worker **nunca** accede a widgets Qt. Solo computa y emite señales. Los slots que reciben las señales corren en el hilo principal y son los únicos que tocan la UI.

**Tests:** `tests/test_workers.py`
- Verificar que `Worker` emite `finished` con el resultado correcto para una función simple.
- Verificar que emite `error` cuando la función lanza una excepción.
- Usar `QSignalSpy` para esperar las señales.

---

### Vista de exportación (parte UI de T20)

**Archivo:** `app/views/export.py`

Clase `ExportView(QWidget)`:

1. **Encabezado** con `StepHeader` usando el título `EXPORT_TITLE`.

2. **Resumen de historial**: `QListWidget` de solo lectura con las descripciones de las acciones aplicadas (`state.history.descriptions()`). Título `EXPORT_SUMMARY_TITLE`.

3. **Selector de formato**: `QComboBox` con opciones "CSV (.csv)", "Excel (.xlsx)", "Parquet (.parquet)".

4. **Botón "Exportar dataset limpio"**: habilitado solo si `Step.CLEAN_E in state.completed` (es decir, el controlador permite entrar a `EXPORT`). Si no está completo, mostrar tooltip explicativo.

5. Al pulsar exportar:
   - Abrir `QFileDialog.getSaveFileName(...)` con el nombre sugerido `<stem>_nuevo.<ext>` usando `generate_export_path(state.file_path, extension)`.
   - Llamar a `export_dataset(state.working_df, target_path)`.
   - Éxito: `QMessageBox` con `EXPORT_SUCCESS_MSG.format(path=...)`.
   - Error (`ExportError`): `QMessageBox.warning(...)` con el mensaje de la excepción.
   - **Nunca modifica** `working_df` ni `original_df`.

6. **Botones de historial** en la barra superior (o en esta vista):
   - "Deshacer última acción": `state.history.undo()` → si devuelve df, `state.working_df = df` → `controller.invalidate_from(step_actual, inclusive=True)` → actualizar vista. Deshabilitado si `not history.can_undo`.
   - "Restaurar original": `QMessageBox` de confirmación → `state.working_df = state.history.restore_original(state.original_df)` → `controller.invalidate_from(Step.CLEAN_A, inclusive=True)` → volver a la vista del Paso 1 o CLEAN_A.

**Tests:** `tests/test_export_view.py`
- Smoke test: instancia sin crash.
- Verificar que el botón exportar está deshabilitado cuando CLEAN_E no está completo.
- Verificar que `export_dataset` se llama con `working_df` (monkeypatch de `QFileDialog`).

---

### T23 — Pulido QSS y pruebas de reescalado

**Archivos:** `app/theme.qss` y `tests/test_resize.py`

#### Pulido del tema QSS

Revisa el `app/theme.qss` existente y complétalo con todos los selectores necesarios para que el template visual esté 100% aplicado:

```
Elementos obligatorios en el QSS:
- #topBar                → fondo lila (#7C3AED), color texto blanco, border-radius en la parte inferior
- #topBarTitle           → font-size grande, font-weight bold, color blanco
- #topBarSubtitle        → font-size normal, color #DDD6FE (lila claro)
- #sidebar               → fondo #F5F3FF (lila muy claro), borde derecho 1px #E5E7EB
- #sidebarTitle          → font-weight bold, color #374151
- QPushButton[step]      → estilo de elemento de sidebar (fondo transparente, texto izquierda)
- QPushButton[step][active="true"] → fondo #EDE9FE, color #7C3AED, font-weight bold
- QPushButton[step][locked="true"] → color #9CA3AF (gris), cursor no-change
- StatCard               → background #F9FAFB, border 1px #E5E7EB, border-radius 8px
- WarningBanner          → background #FEF9C3, border 1px #FDE047, border-radius 6px
- DangerButton           → background white, color #DC2626, border 2px #DC2626, border-radius 6px
                           hover: background #FEF2F2
- #contentStack          → background white
- QTableView             → gridline-color #E5E7EB, alternate-background-color #F9FAFB
- QHeaderView::section[numeric="true"]     → background #FCE7F3 (rosa)
- QHeaderView::section[categorical="true"] → background #DCFCE7 (verde claro)
```

Checklist visual a verificar (añadir como comentarios en el QSS):
- [ ] Barra superior lila con `DataClean` en blanco
- [ ] Sidebar con paso activo resaltado en lila
- [ ] Sub-pasos A–E indentados bajo "5. Limpieza de datos"
- [ ] Tarjetas con fondo gris muy claro y bordes redondeados
- [ ] Encabezados tabla: rosa para numéricas, verde para categóricas
- [ ] Banner amarillo visible
- [ ] Botón rojo con borde para acciones destructivas

#### `tests/test_resize.py`

```python
def test_minimum_size_respected(qtbot):
    """La ventana no puede reducirse por debajo de 900x600."""

def test_no_child_overflow_at_minimum(qtbot):
    """Ningún widget hijo excede el rectángulo del padre a 900x600."""

def test_no_child_overflow_at_fullscreen(qtbot):
    """Ningún widget hijo excede el rectángulo del padre a 1920x1080."""

def test_sidebar_fixed_width(qtbot):
    """La sidebar mantiene 240px en cualquier tamaño de ventana."""
```

---

### T24 — Empaquetado `.exe` con PyInstaller

**Archivos:** `build/dataclean.spec` y `scripts/build_exe.ps1`

> **IMPORTANTE:** Esta tarea solo se ejecuta después de que el PR del Agente A esté mergeado en `main` y hayas hecho `git pull origin main` para tener las vistas del Paso 5. Sin ellas, el `.exe` estará incompleto.

#### `build/dataclean.spec`

```python
# -*- mode: python ; coding: utf-8 -*-
block_cipher = None

a = Analysis(
    ['scripts/launcher.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('app/theme.qss', 'app'),
        ('app/ui', 'app/ui'),
    ],
    hiddenimports=[
        'PySide6.QtSvg',
        'PySide6.QtPrintSupport',
    ],
    hookspath=[],
    hooksconfig={},
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
# + collect_data_files('matplotlib') en datas

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name='DataClean',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # windowed
    version='build/version_info.txt',
)

coll = COLLECT(exe, a.binaries, a.zipfiles, a.datas, strip=False, upx=True, name='DataClean')
```

Crear `scripts/launcher.py`:
```python
"""Entrypoint para PyInstaller."""
from app.main_window import main
import sys

if __name__ == "__main__":
    sys.exit(main())
```

Crear `build/version_info.txt` con la versión `0.0.1-alpha` → `filevers=(0, 0, 1, 0)`.

#### `scripts/build_exe.ps1`

```powershell
# Activa el venv, verifica python 3.13, ejecuta pyinstaller
# Falla con mensaje claro si algo falta
```

**Criterios de aceptación T24:**
- `dist\DataClean\DataClean.exe` abre la ventana con sidebar y QSS aplicado.
- La barra superior y las propiedades del `.exe` muestran `0.0.1-alpha`.
- El `.exe` corre sin `.venv` activo y sin `python` en PATH.
- `pytest -q` sigue en verde tras el empaquetado.

---

### T25 — Cierre y actualización de AGENTS.md

Solo después de que **ambos PRs** estén mergeados en `main` y hayas hecho pull:

1. Ejecutar `python -m pytest -q` → debe estar en verde completo.
2. Ejecutar `python -m ruff check app tests` y `python -m black --check app tests` → sin errores.
3. Verificar manualmente los 8 criterios de §9 de `AGENTS.md` y marcar los que pasen.
4. Actualizar `AGENTS.md §10 (Handoff)` con el estado final.
5. Commit: `docs(T25): cierre del proyecto — suite completa y criterios verificados`.

---

## Reglas obligatorias

1. **Sin texto visible hardcodeado**. Todo texto va en `app/ui/texts_es.py`.
2. **Sin `setGeometry` ni coordenadas absolutas**.
3. **El worker nunca toca widgets**. Solo computa y emite señales.
4. **Sin `print` de depuración** en commits.
5. **`app/services/`** no importa Qt (verificar con `Select-String`).
6. **`original_df` nunca se muta**.

---

## Flujo de commits esperado

```
feat(T22): logging con rotación y borde de errores en slots Qt
feat(T21): worker QRunnable para operaciones pesadas (carga de archivos)
feat(T21): integración del worker en la vista de carga (Paso 1)
feat(export-view): vista de exportación con resumen de historial
feat(T23): QSS completo y pruebas de reescalado
feat(T24): spec de PyInstaller y script de build para Windows
docs(T25): cierre del proyecto — suite completa y criterios verificados
```

---

## Verificación antes del Pull Request

```powershell
# Desde el venv activado:
python -m pytest -q                        # todos en verde
python -m ruff check app tests             # sin errores
python -m black --check app tests          # sin errores de formato
python -m app                              # abre la ventana sin traceback

# Verificar arquitectura:
Select-String -Path app\services\*.py -Pattern "PySide6|PyQt"  # sin resultados
Select-String -Path app -Pattern "setGeometry"                  # sin resultados
Select-String -Path app -Pattern "print\("                      # sin resultados
```

---

## Pull Request

Una vez que todos los tests pasen:

```powershell
git push origin feature/infraestructura
```

En GitHub (`https://github.com/aprileur/DataClean`), abre un Pull Request:
- **Base:** `main`
- **Compare:** `feature/infraestructura`
- **Título:** `feat: infraestructura transversal — logging, hilos, exportación, QSS y empaquetado`
- **Descripción:** lista los archivos creados/modificados, el conteo de tests nuevos y confirma que `pytest -q` pasa en verde.

---

## Punto de sincronización con el Agente A

El Agente A implementa las vistas del Paso 5 en la branch `feature/vistas-limpieza`. Tus archivos **no se solapan** con los suyos: no toques `app/views/step5_cleaning/`. Puedes trabajar en paralelo en T22, T21 y la vista de exportación. Solo T23, T24 y T25 deben esperar a que el PR del Agente A esté mergeado (la app debe estar completa para el pulido visual y el empaquetado).

Cuando necesites sincronizarte:
```powershell
git fetch origin
git merge origin/main  # o rebase, según el estilo del equipo
```
