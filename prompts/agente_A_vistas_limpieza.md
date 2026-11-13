# Prompt — Agente A: Vistas del Paso 5 (Limpieza A–E + Contenedor)

## Contexto del proyecto

Eres el **Agente A** del proyecto **DataClean**, una aplicación de escritorio en Python/PySide6 que permite cargar un dataset tabular (CSV, Excel, Parquet) y limpiarlo paso a paso a través de un flujo guiado de 5 pasos. El idioma de la UI es **español**; el código (variables, funciones, clases) va en **inglés**.

El repositorio ya está en GitHub. Tu trabajo se hace en la branch **`feature/vistas-limpieza`** y al terminar envías un Pull Request a `main`.

---

## Repositorio

```
D:\pycharm\Estructura de Datos\Programacion 2\DataClean
```

**URL de GitHub:** `https://github.com/aprileur/DataClean`

---

## Lo que YA existe (no toques esto)

Todos los servicios de datos están implementados y testeados en `app/services/`. **No los modifiques.**

### Servicios disponibles en `app/services/cleaning.py`

**Sub-paso A — Faltantes:**
- `missing_report(df, only_with_missing) -> DataFrame` — columnas: `columna`, `faltantes`, `porcentaje`
- `missing_union(df) -> (n: int, pct: float)` — filas con al menos un faltante (unión, no suma)
- `drop_missing_rows(df) -> DataFrame`
- `impute_column(df, column, strategy, fill_value) -> DataFrame` — estrategias: `"mean"`, `"median"`, `"mode"`, `"constant"`
- `heatmap_sample(df, max_rows=100) -> DataFrame` — máscara booleana de faltantes para el heatmap

**Sub-paso B — Irrelevantes:**
- `suggest_irrelevant(df) -> dict[col, reason]` — razones en español ya listas
- `drop_columns(df, columns) -> DataFrame`

**Sub-paso C — Duplicados:**
- `count_duplicates(df, subset) -> int`
- `get_duplicate_examples(df, subset, max_rows=20) -> DataFrame`
- `drop_duplicates(df, subset, keep) -> DataFrame` — keep: `"first"` o `"last"`
- `duplicate_mask(df, subset, keep) -> Series`

**Sub-paso D — Outliers:**
- `analyze_outliers(df, method, threshold) -> DataFrame` — columnas: `columna`, `outliers`, `porcentaje`, `limite_inferior`, `limite_superior`
- `outlier_mask(series, method, threshold) -> Series`
- `clip_outliers(df, column, method, threshold) -> DataFrame`
- `drop_outliers(df, column, method, threshold) -> DataFrame`
- Métodos: `"iqr"` (default, threshold=1.5) y `"zscore"` (threshold=3.0)

**Sub-paso E — Typos:**
- `suggest_merges(series, cutoff=85.0) -> list[tuple[variant, canonical, count, score]]`
- `apply_merges(df, column, mapping) -> DataFrame`
- `normalize_text(series) -> Series`

### Widgets reutilizables disponibles

- `app/widgets/dataframe_table.py` → `DataFrameTable(QTableView)` + `DataFrameTableModel`
  - Uso: `table = DataFrameTable(parent); table.set_dataframe(df)`
  - Encabezados rosa para numéricas, verde para categóricas; faltantes como "—"; formato de miles
- `app/widgets/heatmap.py` → `MissingDataHeatmap(FigureCanvasQTAgg)`
  - Uso: `heatmap = MissingDataHeatmap(parent); heatmap.set_data(mask_df, is_sample, total_rows)`
  - Redibujar en resizeEvent llamando a `heatmap.set_data(...)` de nuevo
- `app/widgets/banner.py` → `WarningBanner(QWidget)`
- `app/widgets/buttons.py` → `DangerButton(QPushButton)` — rojo con borde
- `app/widgets/cards.py` → `StatCard`, `InfoCard`
- `app/widgets/step_header.py` → `StepHeader` — título con círculo lila numerado

### Estado y controlador

```python
# En app/state.py
class Step(StrEnum):
    LOAD, INFO, PREVIEW, TYPES, CLEAN_A, CLEAN_B, CLEAN_C, CLEAN_D, CLEAN_E, EXPORT

class WorkflowController(QObject):
    # Señales disponibles:
    step_changed = Signal(object)      # emite Step
    step_completed = Signal(object)    # emite Step
    steps_invalidated = Signal(object) # emite set[Step]
    state_reset = Signal()

    def complete(self, step): ...       # marca paso como completado
    def invalidate_from(self, step, inclusive=False): ...  # cascada
    def go_to(self, step): ...          # navega (lanza StepLockedError si bloqueado)
    def advance(self): ...              # avanza al siguiente paso

class AppState:
    original_df: pd.DataFrame | None
    working_df: pd.DataFrame | None
    file_path: Path | None
    history: History
    completed: set[Step]
    current: Step
```

### Historial

```python
# En app/history.py
class History:
    def push(self, description: str, df: pd.DataFrame): ...  # guarda snapshot
    def undo(self) -> pd.DataFrame | None: ...
    def restore_original(self, original_df, description) -> pd.DataFrame: ...
    can_undo: bool
    def descriptions() -> list[str]: ...
```

### Textos en español (todos centralizados en `app/ui/texts_es.py`)

Claves relevantes para el Paso 5:
```python
STEP_5A_NAME, STEP_5B_NAME, STEP_5C_NAME, STEP_5D_NAME, STEP_5E_NAME
CLEAN_NO_ISSUES_FOUND        # "Sin problemas detectados en este paso."
CLEAN_SKIP_CONFIRM_TITLE     # "¿Omitir este paso?"
CLEAN_SKIP_CONFIRM_MSG
BTN_SKIP_STEP, BTN_NEXT, BTN_BACK, BTN_CONFIRM, BTN_CANCEL, BTN_APPLY

# 5A
MISSING_TABLE_COL, MISSING_TABLE_COUNT, MISSING_TABLE_PCT
MISSING_VIEW_ALL             # "Ver todas las columnas"
MISSING_BANNER_WARNING       # "...se perderían {count} registros ({pct:.1f}% del total)."
MISSING_BTN_DROP, MISSING_BTN_IMPUTE
MISSING_DROP_CONFIRM_TITLE, MISSING_DROP_CONFIRM_MSG  # {count}, {pct}

# 5B
IRRELEVANT_INFO, IRRELEVANT_BTN_DROP
IRRELEVANT_CONFIRM_TITLE, IRRELEVANT_CONFIRM_MSG  # {cols}
IRRELEVANT_SUGGESTION_CONST, IRRELEVANT_SUGGESTION_EMPTY, IRRELEVANT_SUGGESTION_ID

# 5C
DUPLICATES_COUNT_LABEL       # {count}
DUPLICATES_KEEP_LABEL, DUPLICATES_KEEP_FIRST, DUPLICATES_KEEP_LAST
DUPLICATES_BTN_DROP
DUPLICATES_CONFIRM_TITLE, DUPLICATES_CONFIRM_MSG  # {count}

# 5D
OUTLIERS_METHOD_LABEL, OUTLIERS_IQR, OUTLIERS_ZSCORE
OUTLIERS_THRESHOLD_LABEL
OUTLIERS_ACTION_DROP, OUTLIERS_ACTION_CLIP, OUTLIERS_ACTION_KEEP

# 5E
TYPOS_COL_SELECT, TYPOS_SIMILARITY_LABEL
TYPOS_TABLE_VARIANT, TYPOS_TABLE_CANONICAL, TYPOS_TABLE_COUNT
TYPOS_BTN_APPLY
```

Si necesitas añadir textos nuevos, agrégalos al final de `app/ui/texts_es.py`.

---

## Tu tarea

### Paso 0 — Crear la branch

```powershell
cd "D:\pycharm\Estructura de Datos\Programacion 2\DataClean"
git checkout main
git pull origin main
git checkout -b feature/vistas-limpieza
```

### Paso 1 — Verificar estado inicial

```powershell
.venv\Scripts\Activate.ps1
python -m pytest -q   # debe pasar en verde (219 tests)
python -m app         # debe abrir la ventana
```

---

### Tareas a implementar (en este orden)

#### T12 + T13 — Vista 5A: Datos faltantes

**Archivo:** `app/views/step5_cleaning/missing.py`

Implementa la clase `MissingView(QWidget)` con:

1. **Tabla de diagnóstico** usando `DataFrameTable` con las columnas `Columna / Registros faltantes / Porcentaje`.
   - Checkbox "Ver todas las columnas" que alterna entre `only_with_missing=True/False`.
   - Si no hay faltantes → muestra `CLEAN_NO_ISSUES_FOUND` y auto-completa el sub-paso.

2. **Banner amarillo** (`WarningBanner`) con el texto `MISSING_BANNER_WARNING` usando `missing_union()` (nunca la suma por columna).

3. **Mapa de calor** usando `MissingDataHeatmap`. Si hay más de 100 filas, llamar a `heatmap_sample()` para obtener la máscara y pasar `is_sample=True, total_rows=len(df)`.

4. **Botón `DangerButton`** "Eliminar registros con datos faltantes":
   - `QMessageBox` de confirmación con el conteo exacto (`MISSING_DROP_CONFIRM_MSG`).
   - Al confirmar: `new_df = drop_missing_rows(df)` → `history.push(desc, new_df)` → actualizar `state.working_df` → `controller.invalidate_from(Step.CLEAN_A, inclusive=False)` → refrescar la vista.

5. **Botón** "Imputar datos faltantes..." → abre un `QDialog` simple con:
   - `QComboBox` selector de columna (solo columnas con faltantes).
   - `QComboBox` estrategia: media / mediana / moda / constante (mostrar solo las válidas según el tipo de columna: media y mediana solo para numéricas).
   - Campo de texto para el valor constante (visible solo si estrategia = constante).
   - Botón Aplicar → `impute_column(...)` → push historial → actualizar working_df → refrescar.

6. **Botón "Omitir"** con `QMessageBox` de confirmación (`CLEAN_SKIP_CONFIRM_MSG`). Al confirmar, registra `history.push("Omitido: Datos faltantes", working_df)` y llama a `controller.complete(Step.CLEAN_A)`.

7. **Botón "Siguiente"** habilitado solo cuando el paso está completado.

**Señal pública:** `step_done = Signal()` que el contenedor usará para habilitar la siguiente pestaña.

---

#### T14 — Vista 5B: Columnas irrelevantes

**Archivo:** `app/views/step5_cleaning/irrelevant.py`

Clase `IrrelevantView(QWidget)`:

1. Lista de todas las columnas con `QCheckBox` por cada una.
2. Las sugeridas por `suggest_irrelevant(df)` aparecen **pre-marcadas** y con el motivo entre paréntesis (en gris itálico). Las demás sin marcar.
3. Si no hay sugerencias y todas están sin marcar → opción de igual modo permitir marcar manualmente.
4. **Botón `DangerButton`** "Eliminar columnas seleccionadas":
   - Deshabilitado si ninguna está marcada.
   - `QMessageBox` confirmación listando los nombres y el conteo (`IRRELEVANT_CONFIRM_MSG`).
   - Al confirmar: `drop_columns(df, selected)` → push historial → actualizar working_df → `controller.invalidate_from(Step.CLEAN_B, inclusive=False)` → refrescar.
5. Auto-completar si no hay sugerencias y el usuario no marca nada → mostrar `CLEAN_NO_ISSUES_FOUND` y completar.
6. **Omitir** y **Siguiente** iguales que 5A.

---

#### T15 — Vista 5C: Registros duplicados

**Archivo:** `app/views/step5_cleaning/duplicates.py`

Clase `DuplicatesView(QWidget)`:

1. Etiqueta `DUPLICATES_COUNT_LABEL.format(count=N)` con el conteo inicial.
2. **Selector múltiple de columnas** (`QListWidget` con `QAbstractItemView.MultiSelection` o checkboxes): por defecto todas seleccionadas.
3. **Radio buttons** "Primera ocurrencia" / "Última ocurrencia" (`keep`).
4. Tabla de ejemplos (máximo 20 filas) usando `DataFrameTable` con `get_duplicate_examples(df, subset)`.
5. Si `count_duplicates == 0` → `CLEAN_NO_ISSUES_FOUND` + auto-completar.
6. **Botón `DangerButton`** "Eliminar duplicados":
   - `QMessageBox` confirmación con conteo exacto actualizado según columnas elegidas.
   - Al confirmar: `drop_duplicates(df, subset, keep)` → push historial → actualizar → invalidar → refrescar.
7. **Omitir** y **Siguiente**.

---

#### T16 — Vista 5D: Outliers

**Archivo:** `app/views/step5_cleaning/outliers.py`

Clase `OutliersView(QWidget)`:

1. **Selector de método** (`QComboBox`): IQR / Z-Score.
2. **Umbral editable** (`QDoubleSpinBox`): default 1.5 para IQR, 3.0 para Z-Score. Cambiar método actualiza el default.
3. **Tabla de resumen** con `DataFrameTable` mostrando el resultado de `analyze_outliers(df, method, threshold)`.
4. **Selector de columna** (`QComboBox`) con las columnas numéricas. Al cambiar columna, redibuja el gráfico.
5. **Gráfico matplotlib** (boxplot + histograma side-by-side) para la columna seleccionada. Usar `FigureCanvasQTAgg` directamente (no el widget de heatmap). Redibujar al cambiar de columna y en `resizeEvent`.
6. Si no hay outliers en ninguna columna → `CLEAN_NO_ISSUES_FOUND` + auto-completar.
7. **Tres botones de acción** (por columna activa):
   - "Eliminar outliers" (`DangerButton`) → `drop_outliers(df, col, method, threshold)` → push → invalidar → refrescar.
   - "Limitar (Winsorizar)" → `clip_outliers(df, col, method, threshold)` → push → invalidar → refrescar.
   - "Conservar valores" → no modifica nada pero marca la columna como resuelta.
   - Ninguna acción se aplica automáticamente. El usuario elige explícitamente.
8. El sub-paso se completa cuando todas las columnas numéricas tienen una acción elegida (o no hay outliers).
9. **Omitir** y **Siguiente**.

---

#### T17 — Vista 5E: Errores tipográficos

**Archivo:** `app/views/step5_cleaning/typos.py`

Clase `TyposView(QWidget)`:

1. **Selector de columna categórica** (`QComboBox`) — nunca muestra columnas numéricas.
2. **Slider/spinbox "Similitud mínima"** (0–100, default 85).
3. Al cambiar columna o similitud: ejecutar `suggest_merges(series, cutoff)` y poblar la tabla.
4. **Tabla de propuestas** con `QTableWidget` (no `DataFrameTable`): columnas Variante detectada / Valor canónico / Ocurrencias / Similitud. Cada fila tiene un `QCheckBox` en la primera columna para aceptar/rechazar.
5. Si no hay propuestas → `CLEAN_NO_ISSUES_FOUND` + auto-completar para esa columna.
6. **Botón "Aplicar fusiones seleccionadas"**:
   - Construye `mapping = {variante: canonico}` solo de las filas con checkbox marcado.
   - `apply_merges(df, column, mapping)` → push historial → actualizar → invalidar desde CLEAN_E → refrescar.
7. El sub-paso completa cuando el usuario aplicó o descartó propuestas en todas las columnas categóricas.
8. **Omitir** y **Siguiente**.

---

#### T18 — Contenedor del Paso 5

**Archivo:** `app/views/step5_cleaning/__init__.py`

Clase `Step5CleaningView(QWidget)`:

1. `QTabWidget` con pestañas A, B, C, D, E (en ese orden).
2. Las pestañas B–E están **deshabilitadas** al inicio; cada una se habilita cuando la anterior emite `step_done`.
3. Botones **Anterior** (siempre habilitado) y **Siguiente** (habilitado solo cuando E está completo).
4. Botón **"Omitir este paso"** global (omite la pestaña activa con confirmación).
5. **Indicador de progreso**: marcas ✓ en las pestañas completadas.
6. Al completar E: llamar a `controller.complete(Step.CLEAN_E)` y emitir señal para que `MainWindow` avance al Paso Export.

---

### Reglas obligatorias

1. **Nunca modifiques `original_df`**. Siempre trabaja sobre `state.working_df`.
2. **Sin imports de Qt en `app/services/`**. Las vistas llaman a los servicios, nunca al revés.
3. **Sin texto visible hardcodeado**. Todo texto va en `app/ui/texts_es.py`.
4. **Sin `setGeometry` ni coordenadas absolutas**.
5. **Cada acción destructiva** pide confirmación con el impacto exacto.
6. **Invalidación en cascada**: después de cualquier acción en el sub-paso X, llamar a `controller.invalidate_from(Step.CLEAN_X, inclusive=False)`.
7. **Resizeability**: los gráficos matplotlib deben redibujar en `resizeEvent`.

---

### Tests requeridos

Crea `tests/test_views_step5.py` con pruebas de humo (`pytest-qt`):

```python
def test_missing_view_smoke(qtbot, sample_df): ...      # instancia sin crash
def test_irrelevant_view_smoke(qtbot, sample_df): ...
def test_duplicates_view_smoke(qtbot, sample_df): ...
def test_outliers_view_smoke(qtbot, sample_df): ...
def test_typos_view_smoke(qtbot, sample_df): ...
def test_step5_container_smoke(qtbot, sample_df): ...   # QTabWidget instancia
def test_missing_no_missing_autocompletes(qtbot): ...   # df sin nulos → auto-completa
def test_duplicates_no_dups_autocompletes(qtbot): ...
```

Usa el fixture `sample_df` de `tests/conftest.py`.

---

### Flujo de commits esperado

```
feat(T12-T13): vista 5A datos faltantes (diagnóstico, banner, heatmap, acciones)
feat(T14): vista 5B columnas irrelevantes
feat(T15): vista 5C registros duplicados
feat(T16): vista 5D outliers (gráfico + acciones por columna)
feat(T17): vista 5E errores tipográficos con rapidfuzz
feat(T18): contenedor paso 5 con QTabWidget, progreso y navegación
test: pruebas de humo para vistas del paso 5
```

---

### Verificación antes del Pull Request

```powershell
# Desde el venv activado:
python -m pytest -q                        # todos en verde
python -m ruff check app tests             # sin errores
python -m black --check app tests          # sin errores de formato
python -m app                              # abre la ventana sin traceback

# Verificar arquitectura:
Select-String -Path app\services\*.py -Pattern "PySide6|PyQt"  # sin resultados
Select-String -Path app -Pattern "setGeometry"                  # sin resultados
```

---

### Pull Request

Una vez que todos los tests pasen y la app abra:

```powershell
git push origin feature/vistas-limpieza
```

Luego en GitHub (`https://github.com/aprileur/DataClean`), abre un Pull Request:
- **Base:** `main`
- **Compare:** `feature/vistas-limpieza`
- **Título:** `feat: vistas del Paso 5 — limpieza A–E y contenedor`
- **Descripción:** lista los archivos creados, el conteo de tests nuevos y confirma que `pytest -q` pasa en verde.

---

### Punto de sincronización con el Agente B

El Agente B hace T22 (logging), T21 (hilos), y la vista de exportación en paralelo. **No interfieren** con tus archivos. Solo cuando tu PR esté mergeado podrá el Agente B hacer T23 (pulido visual) y T24 (empaquetado), que requieren la app completa.
