# PLAN.md — Limpiador de CSV (aplicación de escritorio en Python)

> **Fuente de verdad:** `AGENTS.md`. Este plan **no** reemplaza la especificación; la descompone en tareas ejecutables.
> Si hay conflicto entre este archivo y `AGENTS.md`, gana `AGENTS.md`. Si hay ambigüedad, ver §2 (Decisiones fijadas) y §3 (Preguntas abiertas).

**Generado por:** agente Plan (DeepSeek) · **Fecha:** 2026-11-12 · **Actualizado:** 2026-11-12 (decisiones del usuario)
**Estado del repo al planear:** solo existe `AGENTS.md`; sin git, sin código, sin tests.

---

## 0. Cómo debe usar este plan el agente Build

1. Implementa **una tarea por sesión**, en el orden numérico (T01 → T25). No adelantes tareas.
2. Antes de empezar: lee `AGENTS.md` y la última entrada de §11 (Handoff).
3. Al terminar cada tarea:
   - `python -m pytest -q` en verde.
   - `python -m app` abre la ventana sin excepciones.
   - `ruff check app tests` y `black --check app tests` sin errores.
   - Commit pequeño (`feat:`, `fix:`, `test:`, `docs:`).
   - Actualiza `AGENTS.md` §11 (ver §5 de este plan).
4. Si una tarea supera ~200 líneas cambiadas, **pártela** y anótalo en §11 como tarea nueva; no la entregues a medias.
5. Si encuentras una contradicción o un requisito no cubierto: **no improvises**. Anótalo en `PLAN.md` → §3 "Preguntas abiertas" con la decisión provisional que tomaste, y sigue.

### Definición de terminado (aplica a toda tarea)

- [ ] Tests nuevos o actualizados para lo implementado.
- [ ] `python -m pytest -q` pasa completo.
- [ ] `python -m app` abre sin traceback.
- [ ] `app/services/**` no importa Qt (`PySide6`/`PyQt5`/`PyQt6`): verificar con búsqueda en el código.
- [ ] Ningún texto visible al usuario fuera de `app/ui/texts_es.py`.
- [ ] Ningún `setGeometry` ni coordenadas absolutas en `app/`.
- [ ] `original_df` nunca se muta (usar `.copy()`).
- [ ] `AGENTS.md` §11 actualizado al cerrar la sesión.

---

## 1. Contexto verificado del entorno

| Comprobación | Resultado | Implicación |
|---|---|---|
| Python por defecto | **3.14.7** (también hay 3.13) | PySide6/pyarrow pueden no tener wheel para 3.14 → usar venv con **3.13** (decisión D1). |
| pandas instalado | **3.0.6** | pandas 3 usa dtype `str` por defecto (no `object`) y Copy-on-Write. Afecta la clasificación de columnas en T07. |
| matplotlib instalado | 3.11.2 | Backend debe fijarse a `QtAgg` explícitamente. |
| PySide6 / pyarrow / openpyxl / pytest | **no instalados** | `requirements.txt` + venv en T01. |
| Git | 2.55 disponible, repo **no inicializado** | T01 ejecuta `git init` y primer commit. |
| `C:\Users\April\.opencode\plan` | no existía | Creado al escribir este archivo. |

---

## 2. Decisiones fijadas (defaults)

| ID | Tema | Decisión | Motivo |
|---|---|---|---|
| D1 | Versión de Python | **Python 3.13 confirmado** para `.venv` y para el build del `.exe`. `requirements.txt` con versiones mínimas compatibles. | Confirmado por el usuario; PyInstaller también tiene mejor soporte en 3.13. |
| D2 | Git | `git init` en T01; rama `main`; `.gitignore` con `.venv/`, `__pycache__/`, `*.log`, `exports/`, `.pytest_cache/`, `.ruff_cache/`, `build/dataclean/`, `dist/` (el `.spec` **sí** se commitea). | §2 y §7 exigen commits por tarea. |
| D3 | Similitud de cadenas | **`rapidfuzz`** (`fuzz.WRatio` + `process.extractOne`), no `difflib`. | **Aprobado por el usuario.** Mejor calidad en typos cortos. |
| D4 | Clasificación de tipos | Numéricas: `number` (excluye bool). Categóricas: `str`, `object`, `category`, `bool`. Fechas: `datetime64`, `timedelta64`. | pandas 3 devuelve `str` en vez de `object`. |
| D5 | Excel con varias hojas | Diálogo modal de selección **antes** de cargar; si solo hay una, cargar directo. | §5 Paso 1. |
| D6 | Mapa de calor | Filas > 100 → muestreo determinista (`random_state=42`) + texto "Muestra de N filas". Hasta 20 columnas visibles; más → submuestreo de columnas con aviso. | §5A pide ~100 filas. |
| D7 | Historial | Máximo **10 snapshots completos** (`.copy()`). Si el df supera 50 MB, avisar en banner y conservar solo 5. | §6.9. |
| D8 | Exportación | CSV con `utf-8-sig`; Excel con `openpyxl`; Parquet con `pyarrow`. **Siempre nombre nuevo**: `<stem>_nuevo.<ext>` (ej. `ventas_nuevo.csv`). Nunca sobrescribe el original ni pregunta por sobrescribir. | **Confirmado por el usuario.** |
| D9 | Logging | `RotatingFileHandler` a `data_clean.log` (1 MB × 3), nivel INFO; traceback completo solo al log. | §7. |
| D10 | Hilos | `QThread` + objeto worker con señales `finished`/`error`/`progress`; solo para carga de archivos y cálculo de outliers. | §7. |
| D11 | Dataset de ejemplo | Generado por script reproducible y **commiteado** (`tests/data/sample.csv`). | §8 lo exige como archivo. |
| D12 | Omitir sub-paso | Diálogo de confirmación explícito; queda registrado en el historial como "Omitido por el usuario". | §6.4. |
| D13 | Empaquetado | **PyInstaller en alcance**: `.exe` con `--onedir --windowed`, nombre `DataClean`, spec commiteado (`build/dataclean.spec`) y script `scripts/build_exe.ps1`. Se construye solo con Python 3.13. | **Confirmado por el usuario.** |

---

## 3. Preguntas abiertas

### 3.1 Resueltas por el usuario (2026-11-12)

| # | Pregunta | Respuesta | Impacto |
|---|---|---|---|
| Q1 | ¿Python 3.13 o 3.14? | **3.13** | D1; venv y build del `.exe` en 3.13. |
| Q2 | ¿Se permite `rapidfuzz`? | **Sí** | D3; T17 usa `rapidfuzz`; se registra en `requirements.txt`. |
| Q3 | ¿Empaquetar como `.exe`? | **Sí, con PyInstaller** | D13; tarea nueva **T24** (empaquetado) antes del cierre. |
| Q4 | ¿Exportar puede sobrescribir el original? | **Nunca** | D8; nombre fijo `<stem>_nuevo.<ext>`. |

### 3.2 Pendientes (default aplicado, no bloquean)

| # | Pregunta | Default aplicado |
|---|---|---|
| Q5 | ¿Idioma de logs y mensajes técnicos? | Logs en inglés, UI en español. |
| Q6 | ¿El historial se exporta junto al dataset? | No: solo resumen en pantalla; el export contiene únicamente los datos. |
| Q7 | ¿Icono y metadatos del `.exe` (nombre de empresa/versión)? | Sin icono propio; nombre `DataClean`, versión **`0.0.1-alpha`**. |
| Q8 | ¿Firma de código / instalador (MSI)? | Fuera de alcance; se entrega carpeta `dist/DataClean/`. |

---

## 4. Tareas

### Resumen

| # | Tarea | Depende de | Archivos principales |
|---|---|---|---|
| T01 | Andamiaje: venv, git, estructura, ventana base | — | `requirements.txt`, `pyproject.toml`, `app/__main__.py`, `app/main_window.py` |
| T02 | Textos ES, tema QSS y widgets base | T01 | `app/ui/texts_es.py`, `app/theme.qss`, `app/widgets/*` |
| T03 | `AppState` + `WorkflowController` + pruebas | T01 | `app/state.py`, `tests/test_workflow.py` |
| T04 | Dataset de ejemplo y fixtures (**movido del final**) | T01 | `scripts/generate_sample.py`, `tests/data/sample.csv`, `tests/conftest.py` |
| T05 | `services/loader.py` + pruebas | T04 | `app/services/loader.py`, `tests/test_loader.py` |
| T06 | Vista Paso 1 (carga) | T02, T03, T05 | `app/views/step1_load.py` |
| T07 | `services/profiling.py` + pruebas | T04 | `app/services/profiling.py` |
| T08 | Widget tabla reutilizable | T02, T07 | `app/widgets/dataframe_table.py` |
| T09 | Vistas Pasos 2 y 4 | T03, T07, T08 | `app/views/step2_info.py`, `step4_types.py` |
| T10 | Vista Paso 3 (vista previa) | T08 | `app/views/step3_preview.py` |
| T11 | Limpieza A: servicio de faltantes | T04, T07 | `app/services/cleaning.py` (sección A) |
| T12 | Vista 5A: diagnóstico + banner + tabla | T11 | `app/views/step5_cleaning/missing.py` (parte 1) |
| T13 | Vista 5A: mapa de calor + acciones | T12 | `missing.py` (parte 2), `app/widgets/heatmap.py` |
| T14 | Limpieza B: columnas irrelevantes | T11 | `cleaning.py` (B), `views/.../irrelevant.py` |
| T15 | Limpieza C: duplicados | T14 | `cleaning.py` (C), `views/.../duplicates.py` |
| T16 | Limpieza D: outliers | T15 | `cleaning.py` (D), `views/.../outliers.py` |
| T17 | Limpieza E: errores tipográficos | T16 | `cleaning.py` (E), `views/.../typos.py` |
| T18 | Contenedor Paso 5: pestañas, omitir, auto-completar | T13, T17 | `views/step5_cleaning/__init__.py` |
| T19 | Historial, deshacer y restaurar original | T03, T18 | `app/history.py`, `tests/test_history.py` |
| T20 | Exportación y resumen final | T19 | `app/services/exporter.py`, `app/views/export.py` |
| T21 | Hilos para operaciones pesadas | T06, T16 | `app/workers.py` |
| T22 | Logging y borde de errores | T01 | `app/logging_config.py`, `app/ui/error_boundary.py` |
| T23 | Pulido QSS y pruebas de reescalado | T18 | `app/theme.qss`, `tests/test_resize.py` |
| T24 | Empaquetado `.exe` con PyInstaller | T23 | `build/dataclean.spec`, `scripts/build_exe.ps1` |
| T25 | Cierre: suite completa y `AGENTS.md` | todas | `AGENTS.md`, `PLAN.md` |

---

### T01 — Andamiaje del proyecto

**Objetivo:** repo ejecutable y ventana vacía reescalable.

**Entregable**
- `.venv` con Python 3.13 y `requirements.txt` en dos bloques comentados:
  - **runtime:** `PySide6`, `pandas`, `pyarrow`, `openpyxl`, `matplotlib`, `rapidfuzz`.
  - **desarrollo:** `pytest`, `pytest-qt`, `ruff`, `black`, `pyinstaller`.
- `pyproject.toml` (ruff/black línea 100, pytest con `pythonpath = ["."]`).
- `git init`, `.gitignore`, primer commit.
- `app/__init__.py` con `__version__ = "0.0.1-alpha"` (fuente única para el título, el "Acerca de" y los metadatos del `.exe`), `app/__main__.py`, `app/main_window.py` con `QMainWindow`: 1200×800, mínimo 900×600.
- Layout: `QHBoxLayout` → sidebar fija 240 px (`QSizePolicy.Fixed`) + `QStackedWidget` `Expanding` con un placeholder.
- `tests/test_smoke.py` con `pytest-qt` que instancia `MainWindow`.

**Criterio de aceptación**
- [ ] `python -m app` abre la ventana vacía con sidebar.
- [ ] El título de la ventana muestra `DataClean 0.0.1-alpha` (leído desde `app.__version__`).
- [ ] `python -m pytest -q` → 1 test en verde.
- [ ] `git log --oneline` muestra el commit inicial.
- [ ] `Select-String -Path app -Pattern "setGeometry"` no devuelve resultados.

---

### T02 — Textos ES, tema QSS y widgets base

**Objetivo:** centralizar todo el texto visible y el estilo; evitar estilos repetidos.

**Entregable**
- `app/ui/texts_es.py`: constantes agrupadas por paso (títulos, banners, botones, tooltips, mensajes de error).
- `app/theme.qss` + `app/theme.py` (carga el QSS una sola vez al arrancar).
- `app/widgets/cards.py`: `StatCard` y `InfoCard` (fondo claro, borde redondeado).
- `app/widgets/banner.py`: `WarningBanner` (amarillo).
- `app/widgets/step_header.py`: título con círculo azul numerado.
- `app/widgets/buttons.py`: `DangerButton` (rojo con borde).
- Tests de humo: instanciar cada widget.

**Criterio de aceptación**
- [ ] `main_window` aplica `theme.qss`; cambiar un color en un solo archivo lo cambia en toda la app.
- [ ] `Select-String -Path app\views -Pattern "QLabel\("` solo aparece con texto desde `texts_es`.
- [ ] Widgets se adaptan a 900×600 sin recortes.

---

### T03 — `AppState` + `WorkflowController`

**Objetivo:** máquina de estados que impide saltar pasos (capa lógica).

**Entregable**
- `app/state.py`:
  - `class Step(Enum)`: `LOAD, INFO, PREVIEW, TYPES, CLEAN_A, CLEAN_B, CLEAN_C, CLEAN_D, CLEAN_E, EXPORT`.
  - `STEP_ORDER: tuple[Step, ...]`.
  - `class AppState`: `original_df`, `working_df`, `completed: set[Step]`, `current: Step`, `file_path`.
  - `class WorkflowController`: `can_enter(step)`, `go_to(step)` (lanza `StepLockedError`), `complete(step)`, `invalidate_from(step)`, `reset()`, señal Qt opcional `step_changed`.
  - `class StepLockedError(Exception)`.
- `tests/test_workflow.py` con los 4 casos obligatorios de §6.

**Criterio de aceptación**
- [ ] Saltar de `LOAD` a `CLEAN_A` lanza `StepLockedError`.
- [ ] Completar un paso desbloquea **solo** el siguiente.
- [ ] Completar hasta `CLEAN_C` y volver a modificar `CLEAN_A` deja `CLEAN_B..CLEAN_E` en pendiente.
- [ ] `reset()` vuelve a `LOAD` y limpia `completed`.
- [ ] Retroceder a un paso completado está permitido.

---

### T04 — Dataset de ejemplo y fixtures (prioridad alta)

**Objetivo:** datos realistas para probar todo el flujo desde el principio (antes estaba al final).

**Entregable**
- `scripts/generate_sample.py` con semilla fija (`random_state=42`) que produce `tests/data/sample.csv`:
  - 1000 filas; columnas `id, edad, genero, ingreso, gastos, ciudad, estado, tipocliente`.
  - Sembrar: ~5 % de filas con al menos un faltante (incluyendo filas con **dos** faltantes para probar la unión), 30 duplicados exactos, outliers en `ingreso` (valores > Q3 + 3·IQR), typos en `ciudad` (`Toluca`, `toluca `, `Tolucaa`, `CDMX`, `cdmx`), `id` único por fila.
- `tests/conftest.py`: fixtures `sample_df`, `sample_path`, `empty_df`, `overlap_missing_df` (faltantes solapados en 2 columnas).
- Test que verifica las cantidades sembradas (duplicados, nulos, outliers, variantes).

**Criterio de aceptación**
- [ ] El script es idempotente: dos ejecuciones producen el mismo CSV.
- [ ] `pytest -q tests/test_sample_data.py` valida conteos > 0 de cada problema sembrado.
- [ ] `sample.csv` está commiteado y pesa < 200 KB.

---

### T05 — `services/loader.py`

**Objetivo:** cargar CSV/Excel/Parquet con detección robusta y errores en español.

**Entregable**
- `load_file(path, sheet=None) -> LoadResult` con `df`, `encoding`, `separator`, `sheet`, `file_name`.
- `detect_encoding(path)` probando `utf-8`, `utf-8-sig`, `latin-1`.
- `detect_separator(sample)` con `csv.Sniffer` y fallback a `,` y `;`.
- `list_sheets(path)` para Excel.
- `LoaderError` con mensajes en español (vacío, corrupto, sin permisos, formato no soportado).
- Tests con CSV `;` + latin-1, CSV tabulado, Excel de 2 hojas, Parquet, archivo vacío y corrupto.

**Criterio de aceptación**
- [ ] Los 4 formatos cargan con tipos correctos.
- [ ] Archivo vacío/corrupto lanza `LoaderError`, no `ValueError` crudo.
- [ ] `app/services/` no contiene imports de Qt.
- [ ] El DataFrame cargado es independiente del archivo (modificarlo no toca el disco).

---

### T06 — Vista Paso 1

**Objetivo:** zona de carga con drag & drop, validación y reinicio del flujo.

**Entregable**
- `app/views/step1_load.py`: zona punteada, acepta `.csv/.xlsx/.xls/.parquet`, clic abre diálogo.
- Botón **Cargar datos** deshabilitado hasta archivo válido; tooltip explicativo.
- Selector de hoja modal si hay varias.
- Errores vía `QMessageBox` en español; nunca traceback visible.
- Al cargar: `controller.reset()` si había datos, guarda `original_df` inmutable y `working_df = original_df.copy()`, completa `LOAD`.

**Criterio de aceptación**
- [ ] Arrastrar CSV válido habilita el botón; arrastrar `.txt` lo mantiene deshabilitado.
- [ ] Cargar el ejemplo lleva a `INFO` y `original_df` no se modifica al editar `working_df`.
- [ ] Cargar un segundo archivo limpia historial y pasos completados.
- [ ] Test con monkeypatch de `QMessageBox` verifica el texto en español.

---

### T07 — `services/profiling.py`

**Objetivo:** shape, tipos y resumen de faltantes puros (sin Qt).

**Entregable**
- `dataset_shape(df)`, `memory_usage(df)`, `row_count`, `column_count`.
- `classify_columns(df) -> ColumnTypes(numeric, categorical, datetime, other)` respetando D4.
- `missing_summary(df, only_with_missing=True) -> DataFrame` con columnas `columna`, `faltantes`, `porcentaje`.
- `missing_row_union(df) -> tuple[int, float]` usando `df.isna().any(axis=1)`.
- `looks_like_id(series) -> bool` (heurística: único por fila y > 90 % distintos).
- Tests con `sample_df` y DataFrames sintéticos (incluye dtype `str` de pandas 3 y bool).

**Criterio de aceptación**
- [ ] `missing_row_union` < suma de faltantes por columna en `overlap_missing_df`.
- [ ] Columna `str` y `bool` aparecen en categóricas; `datetime` en su grupo.
- [ ] `looks_like_id` marca `id` pero **no** reclasifica nada.

---

### T08 — Widget tabla reutilizable

**Objetivo:** un solo componente de tabla para pasos 3 y 5.

**Entregable**
- `app/widgets/dataframe_table.py`: `DataFrameTableModel(QAbstractTableModel)` de solo lectura + `DataFrameTable(QTableView)`.
- Encabezados: verde claro para numéricas, morado claro para categóricas (QSS o `headerData`).
- Formato de miles en celdas numéricas; `None`/`NaN` como "—".
- Scroll propio, `QSizePolicy.Expanding`, sin `setGeometry`.

**Criterio de aceptación**
- [ ] `rowCount`/`columnCount` correctos con `sample_df[:20]`.
- [ ] `flags()` no incluye `ItemIsEditable`; `setData` devuelve `False`.
- [ ] 10 000 filas se muestran sin bloqueo perceptible (< 1 s).

---

### T09 — Vistas Pasos 2 y 4

**Objetivo:** información general y clasificación de tipos visibles.

**Entregable**
- `step2_info.py`: tarjetas shape, filas, columnas (formato `1,000`), memoria y nombre de archivo.
- `step4_types.py`: tarjeta verde (numéricas), morada (categóricas) y "Fecha/otras" solo si hay fechas.
- Botón **Entendido** completa el paso y avanza.

**Criterio de aceptación**
- [ ] Las listas reflejan el df real (cargar otro archivo las cambia).
- [ ] Sin columnas de fecha, la tercera tarjeta no existe.
- [ ] "Entendido" desbloquea el siguiente paso solo una vez.

---

### T10 — Vista Paso 3

**Objetivo:** vista previa con N configurable.

**Entregable**
- `step3_preview.py`: `QSpinBox` "Mostrar [N] registros" (mín. 1, máx. `len(df)`, default 5) + `DataFrameTable`.
- Actualización reactiva al cambiar N; solo lectura.

**Criterio de aceptación**
- [ ] Cambiar N actualiza filas visibles sin recargar el archivo.
- [ ] El máximo del spinbox cambia si se recarga el dataset.
- [ ] N=1 y N=total funcionan sin errores.

---

### T11 — Limpieza A: servicio de faltantes

**Objetivo:** diagnóstico y operaciones de faltantes, puras.

**Entregable** en `app/services/cleaning.py` (sección A):
- `missing_report(df, only_with_missing) -> DataFrame`.
- `missing_union(df) -> (n, pct)`.
- `drop_missing_rows(df) -> DataFrame`.
- `impute_column(df, column, strategy)`: `mean`, `median`, `mode`, `constant("Desconocido")`; error claro si la estrategia no aplica al tipo.
- `heatmap_sample(df, max_rows=100) -> DataFrame` (muestra determinista).

**Criterio de aceptación**
- [ ] `overlap_missing_df`: unión estricta < suma por columna.
- [ ] Imputar media/mediana no toca columnas categóricas.
- [ ] `drop_missing_rows` devuelve copia; el df de entrada no cambia (`assert_frame_equal`).

---

### T12 — Vista 5A: diagnóstico, banner y tabla

**Objetivo:** mostrar el reporte y la advertencia correcta.

**Entregable**
- `app/views/step5_cleaning/missing.py` (parte 1): tabla Columna · Faltantes · %, casilla "Ver todas".
- Banner amarillo con N y X % usando `missing_union` (nunca la suma).
- Estado "Sin problemas detectados" si no hay faltantes (auto-completa el sub-paso).

**Criterio de aceptación**
- [ ] Los números del banner coinciden con el servicio para `sample_df`.
- [ ] Con `overlap_missing_df` el banner muestra la unión, no la suma.
- [ ] Dataset sin nulos → mensaje de sin problemas y paso completado automáticamente.

---

### T13 — Vista 5A: mapa de calor y acciones

**Objetivo:** visualización y acciones destructivas/no destructivas.

**Entregable**
- `app/widgets/heatmap.py`: `FigureCanvasQTAgg` con `tight_layout()`, redibujo en `resizeEvent`, colores azul claro/rosa, leyenda y aviso de muestreo (D6).
- Botón **Eliminar registros con datos faltantes** (`DangerButton`) con `QMessageBox` de confirmación mostrando el conteo exacto.
- Diálogo de imputación por columna (estrategia + valor).
- Cada acción guarda snapshot y completa el sub-paso.

**Criterio de aceptación**
- [ ] Redimensionar la ventana redibuja el gráfico sin deformarse.
- [ ] Cancelar la confirmación no modifica `working_df`.
- [ ] Confirmar elimina exactamente N filas y registra 1 snapshot.
- [ ] Imputar actualiza la tabla de faltantes a cero en esa columna.

---

### T14 — Limpieza B: columnas irrelevantes

**Entregable** (`cleaning.py` + `views/step5_cleaning/irrelevant.py`):
- `suggest_irrelevant(df) -> dict[col, reason]` para constantes, > 90 % faltantes y únicos por fila (IDs). Solo sugiere.
- Lista con casillas; sugeridas premarcadas pero **no aplicadas**.
- Eliminar columnas con confirmación que liste nombres y conteo.

**Criterio de aceptación**
- [ ] Las sugerencias aparecen con su razón y requieren acción del usuario.
- [ ] Eliminar 2 columnas reduce `shape[1]` en 2 y registra snapshot.
- [ ] Modificar B invalida C–E (prueba de cascada).

---

### T15 — Limpieza C: duplicados

**Entregable** (`cleaning.py` + `views/.../duplicates.py`):
- `duplicate_mask(df, subset=None) -> Series[bool]`, `count_duplicates`, `drop_duplicates(df, subset, keep)`.
- Selector múltiple de columnas (default: todas) y radio primera/última.
- Tabla con ejemplos (máx. 20) y conteo previo.
- Confirmación con número exacto de filas a eliminar.

**Criterio de aceptación**
- [ ] `sample_df` reporta exactamente los 30 duplicados sembrados.
- [ ] Cambiar `keep` cambia la fila conservada.
- [ ] Subconjunto vacío equivale a todas las columnas y no rompe.

---

### T16 — Limpieza D: outliers

**Entregable** (`cleaning.py` + `views/.../outliers.py`):
- `outlier_mask_iqr(series, k=1.5)`, `outlier_mask_zscore(series, threshold=3.0)`.
- `clip_outliers(df, column, method, k)` (winsorización a los límites).
- `analyze_outliers(df, method, k) -> DataFrame` con conteo por columna numérica.
- Vista: selector método/umbral, tabla de conteos, boxplot + histograma de la columna seleccionada.
- Acciones explícitas: eliminar / limitar / conservar (por columna). Nada automático.

**Criterio de aceptación**
- [ ] Conteos IQR coinciden con cálculo manual en un df sintético.
- [ ] `clip` no cambia `shape` ni la media más allá de los límites.
- [ ] Si el usuario no elige acción, `working_df` no cambia.
- [ ] Gráfico se redibuja al cambiar de columna y al redimensionar.

---

### T17 — Limpieza E: errores tipográficos

**Entregable** (`cleaning.py` + `views/.../typos.py`):
- `normalize_text(series)` (strip, colapsar espacios, `casefold` para comparar).
- `suggest_merges(series, cutoff=85) -> list[tuple[variant, canonical]]` usando `rapidfuzz.fuzz.WRatio` + `rapidfuzz.process.extractOne` (`score_cutoff=cutoff`).
- Agrupar por forma normalizada y elegir canónico por frecuencia (empate → el primero alfabético).
- Vista: por columna categórica, tabla de propuestas con checkbox individual; botón **Aplicar seleccionadas**.
- Al aplicar, guarda snapshot y completa el sub-paso.

**Criterio de aceptación**
- [ ] `Toluca` / `toluca ` / `Tolucaa` genera propuestas hacia un canónico.
- [ ] La detección usa `rapidfuzz` (sin `difflib`) y el umbral es configurable.
- [ ] Rechazar una propuesta no modifica esos valores.
- [ ] Aplicar solo las aceptadas deja el resto intacto.
- [ ] Columnas numéricas nunca aparecen en el selector.

---

### T18 — Contenedor Paso 5 y reglas de avance

**Entregable**
- `views/step5_cleaning/__init__.py`: `QTabWidget` A–E, botones Anterior/Siguiente.
- "Siguiente" habilitado solo si el sub-paso está resuelto (acción, omitido o sin problemas).
- "Omitir este paso" con confirmación; registra "Omitido por el usuario" en historial.
- Indicador de progreso (barra o ✓ en sidebar).

**Criterio de aceptación**
- [ ] No se puede pasar de A a B sin resolver A.
- [ ] Omitir A con confirmación desbloquea B; cancelar no.
- [ ] El progreso refleja 5/5 al completar E.
- [ ] Sidebar muestra candado y tooltip "Completa primero: Paso X".

---

### T19 — Historial, deshacer y restaurar original

**Entregable**
- `app/history.py`: `History` con pila de snapshots (máx. 10 según D7), descripción y timestamp.
- `undo()` devuelve el snapshot anterior; `restore_original()` recarga `original_df.copy()`.
- Botones en la barra superior: **Deshacer última acción** / **Restaurar original** (este último con confirmación).
- Cada acción de limpieza llama a `history.push(desc, df)`.

**Criterio de aceptación**
- [ ] 11 acciones → solo 10 snapshots retenidos.
- [ ] `undo` restaura exactamente el estado previo (`assert_frame_equal`).
- [ ] `original_df` conserva su contenido e identidad tras todas las operaciones.
- [ ] Restaurar original limpia el historial de acciones posteriores.

---

### T20 — Exportación y resumen final

**Entregable**
- `app/services/exporter.py`: `export_csv`, `export_excel`, `export_parquet` con `ExportError` en español.
- `app/views/export.py`: botón **Exportar dataset limpio** habilitado solo tras A–E, `QFileDialog`, selector de formato, resumen del historial.
- Sugerencia de nombre **`<stem>_nuevo.<ext>`** (ej. `ventas_nuevo.csv`); si el archivo existe, añadir sufijo `_2`, `_3`… **sin preguntar**; nunca se sobrescribe el original.

**Criterio de aceptación**
- [ ] Exportar a los 3 formatos produce archivos releíbles con el mismo shape.
- [ ] El nombre por defecto es `<stem>_nuevo.<ext>` y se actualiza al cambiar de formato.
- [ ] Exportar dos veces al mismo destino no sobrescribe: genera `_nuevo_2`.
- [ ] Antes de completar A–E el botón está deshabilitado (UI y controlador).
- [ ] El resumen lista todas las acciones en orden.
- [ ] Exportar no modifica `working_df` ni `original_df`.

---

### T21 — Hilos para operaciones pesadas

**Entregable**
- `app/workers.py`: `Worker(QObject)` + `run_in_thread(fn, *args)` con señales `finished`, `error`, `progress`.
- Carga de archivos y cálculo de outliers fuera del hilo UI.
- `QProgressBar` indeterminada durante la operación; UI deshabilitada mientras corre.

**Criterio de aceptación**
- [ ] Cargar un CSV grande (100k filas) no congela la ventana.
- [ ] Errores del worker llegan a la UI como diálogo en español.
- [ ] Test con `QSignalSpy` verifica `finished`/`error`.
- [ ] No hay accesos a widgets desde el hilo worker.

---

### T22 — Logging y borde de errores

**Entregable**
- `app/logging_config.py`: logger raíz a `data_clean.log` con rotación (D9); formato con timestamp y nivel.
- `app/ui/error_boundary.py`: decorador/contexto que captura excepciones en slots, loguea traceback y muestra `QMessageBox` genérico en español.
- `sys.excepthook` configurado.

**Criterio de aceptación**
- [ ] Provocar un error en un slot genera entrada de log con traceback y diálogo amable.
- [ ] El archivo de log rota al superar 1 MB.
- [ ] Ningún `print` en `app/`.

---

### T23 — Pulido visual y pruebas de reescalado

**Entregable**
- QSS completo: barra superior azul redondeada con título y nombres del equipo, sidebar con paso activo resaltado y sub-pasos A–E indentados, tarjetas, banner amarillo, botón rojo.
- `tests/test_resize.py`: con `pytest-qt`, redimensionar a 900×600 y 1600×1000 y verificar `minimumSizeHint` respetado y que ningún widget hijo exceda el rectángulo del padre.
- HiDPI: `QT_ENABLE_HIGHDPI_SCALING` documentado en `__main__.py`.

**Criterio de aceptación**
- [ ] De 900×600 a pantalla completa no hay texto cortado ni solapamientos (revisión visual + test).
- [ ] Tablas y gráficos mantienen scroll interno.
- [ ] Un solo archivo de tema controla todos los colores.
- [ ] Checklist de §10 de `AGENTS.md` verificado (etiqueta "Columnas irrelevantes", mapa con todas las columnas, unión de filas, sin datos hardcodeados, círculo "5").

---

### T24 — Empaquetado `.exe` con PyInstaller

**Objetivo:** entregar la app como ejecutable de Windows sin requerir Python instalado.

**Entregable**
- `scripts/launcher.py` (o `run.py` en la raíz): `from app.main_window import main` + `main()`, para que PyInstaller tenga un entrypoint limpio (no usar `__main__.py` como script directo).
- `build/dataclean.spec` commiteado:
  - `Analysis(['scripts/launcher.py'], pathex=['.'])`.
  - `datas=[('app/theme.qss', 'app')]` y cualquier recurso de `app/ui/`.
  - `hiddenimports` necesarios para Qt (`PySide6.QtSvg`, `PySide6.QtPrintSupport` si se usan) y `matplotlib` (`collect_data_files('matplotlib')`).
  - `EXE(..., name='DataClean', console=False, version='build/version_info.txt')` + `COLLECT` → `--onedir`.
- `build/version_info.txt` generado a partir de `app.__version__`: `0.0.1-alpha` → `filevers=(0, 0, 1, 0)` y `FileVersion`/`ProductVersion` = `0.0.1-alpha`.
- `scripts/build_exe.ps1`: activa `.venv` (3.13), verifica `python --version`, ejecuta `pyinstaller build/dataclean.spec --clean --noconfirm` y falla con mensaje claro si algo falta.
- `.gitignore`: ignora `build/dataclean/` y `dist/`, pero **no** el `.spec`.

**Criterio de aceptación**
- [ ] `dist/DataClean/DataClean.exe` abre la ventana completa (sidebar, QSS aplicado).
- [ ] La barra superior de la app y las propiedades del `.exe` muestran **`0.0.1-alpha`**.
- [ ] Desde el `.exe`: carga CSV, Excel y Parquet; completa A–E; exporta `<stem>_nuevo.csv`.
- [ ] El `.exe` corre en una sesión sin `.venv` activo y sin `python` en PATH.
- [ ] El build se reproduce con `.\scripts\build_exe.ps1` sin pasos manuales.
- [ ] `pytest -q` sigue en verde tras el empaquetado.

**Notas**
- Construir **solo** con Python 3.13 (PyInstaller puede no soportar 3.14 al día de hoy).
- Preferir `--onedir` sobre `--onefile`: arranca más rápido y facilita depurar recursos faltantes.
- Si falta un recurso (QSS, iconos), el síntoma típico es app "sin estilos": verificar `datas` en el `.spec` antes de culpar al código.

---

### T25 — Cierre y actualización de `AGENTS.md`

**Entregable**
- `pytest -q` completo en verde; `ruff` y `black --check` limpios.
- Verificación manual de los 8 criterios de §9 de `AGENTS.md`.
- Build final del `.exe` desde el código definitivo y prueba con `tests/data/sample.csv`.
- `AGENTS.md`: marcar §9, reescribir §11 con el estado real y las notas para el siguiente agente.
- `PLAN.md`: marcar tareas completadas y mover pendientes a §3 si aplica.

**Criterio de aceptación**
- [ ] Todos los checks de §9 marcados **solo** si fueron verificados.
- [ ] §11 incluye fecha, estado de pruebas, si la app abre y commits por tarea.
- [ ] El `.exe` final carga CSV/Excel/Parquet y exporta `<stem>_nuevo.csv`.
- [ ] No quedan tareas `⚠️ PRIORITARIA` sin resolver o justificadas.

---

## 5. Instrucciones para Build sobre `AGENTS.md`

> Esto responde a dos problemas detectados al revisar `AGENTS.md`. Build debe resolverlos **en el archivo `AGENTS.md`**, sin tocar la especificación (§1–§10).

### 5.1 Reestructurar §11 en la primera sesión (T01)

La tabla actual de §11 tiene 9 tareas; la #9 mezcla hilos + QSS + pruebas + dataset y el dataset de ejemplo está al final aunque se necesita desde T05. Al cerrar T01, Build debe:

1. **Partir la tarea 9** en tres filas nuevas:
   - "Hilos para operaciones pesadas" → T21
   - "Logging y borde de errores" → T22
   - "Pulido QSS y pruebas de reescalado" → T23
2. **Mover el dataset de ejemplo** de la tarea 9 a su propia fila prioritaria (posición 4), porque todos los servicios lo usan como fixture → T04.
3. **Añadir dos filas nuevas** que no existían en §11: empaquetado `.exe` con PyInstaller (T24) y cierre/verificación final (T25).
4. Mantener la numeración de §11 alineada con este plan. Mapa de equivalencia:

| Tarea antigua (§11) | Tareas nuevas del plan |
|---|---|
| 1. Estructura + ventana | T01, T02 |
| 2. `WorkflowController` + `AppState` | T03 |
| 3. `loader.py` + Paso 1 | T05, T06 |
| 4. `profiling.py` + Pasos 2/3/4 | T07, T08, T09, T10 |
| 5. Paso 5A | T11, T12, T13 |
| 6. Pasos 5B y 5C | T14, T15 |
| 7. Pasos 5D y 5E | T16, T17 |
| 8. Historial + exportación | T18, T19, T20 |
| 9. Hilos + QSS + pruebas + dataset | T04 (dataset), T21, T22, T23 |
| — (nueva, requisito confirmado) | T24 empaquetado `.exe` |
| — (nueva) | T25 cierre |

5. No borrar filas completadas: agregar fecha y commit (`COMPLETADA | 2026-11-12 | abc1234`).
6. Las tareas que fallen o queden a medias se marcan `BLOQUEADA` + `⚠️ PRIORITARIA` con razón concreta y van al principio de la tabla.

### 5.2 Reglas de edición de `AGENTS.md`

- **Prohibido** reescribir §1–§10 para "adaptarlas" al código. Si algo no se puede cumplir, se anota en `PLAN.md` §3 y se escala al usuario.
- Actualizar **siempre** las tres líneas de cabecera de §11:
  - `Última actualización:` fecha / agente / modo.
  - `Estado de pruebas:` `pasan (N)` o `fallan: <test>`.
  - `¿La app abre?:` sí/no + error.
- §11 "Notas para el siguiente agente": máximo 15 líneas, con decisiones, trampas y comandos útiles. No pegar logs.
- Marcar §9 (criterios globales) **solo** con evidencia: test que lo cubre o verificación manual escrita.

### 5.3 Cosas de §10 que Build debe comprobar, no asumir

Al cerrar T23/T25, verificar explícitamente:
- [ ] La pestaña B dice "Columnas irrelevantes" (no "Columnsir irrelevantes").
- [ ] El mapa de calor grafica **todas** las columnas reales.
- [ ] El banner usa la unión de filas, no la suma.
- [ ] No hay ciudades/valores del mockup hardcodeados (`Select-String -Path app -Pattern "Toluca|Metepec|Lerma"` vacío).
- [ ] El círculo del paso 5 muestra "5".

### 5.4 Si este plan y `AGENTS.md` se contradicen

Gana `AGENTS.md`. Build debe registrar el conflicto en `PLAN.md` §3 con la pregunta y el default aplicado, y continuar (no bloquear la sesión por una ambigüedad menor). Si el conflicto es de alcance mayor (nuevo requisito, cambio de stack), detenerse y preguntar al usuario.

---

## 6. Trampas conocidas (para no repetirlas)

| Trampa | Prevención |
|---|---|
| pandas 3 devuelve dtype `str` en vez de `object` | Tests de `profiling` deben cubrir `str` explícitamente (T07). |
| `matplotlib` sin backend Qt | Fijar `matplotlib.use("QtAgg")` antes de crear figuras. |
| `tight_layout()` con `constrained_layout` | Elegir uno; el doc pide `tight_layout()`. |
| Filtrar en la UI en vez de en el servicio | Toda operación de datos va en `services/`; la vista solo muestra. |
| `QMessageBox` bloquea tests | Monkeypatch en `pytest-qt`. |
| Mutar `original_df` por referencia | `.copy()` en cada derivación; test de identidad en T19. |
| QSS no aplicado a widgets hijos | Aplicar en `QApplication` o en `MainWindow` con `setStyleSheet`. |
| `QThread` destruido antes de terminar | Guardar referencia al worker/hilo en la vista. |
| Scroll horizontal innecesario | `QHeaderView.ResizeMode.Stretch` o `ResizeToContents` según columna. |
| Dataset de ejemplo demasiado grande en git | 1000 filas, < 200 KB en T04. |
| Build del `.exe` con Python 3.14 | Construir siempre dentro del venv **3.13** (D1/D13). |
| `.exe` sin estilos o sin gráficos | Declarar `app/theme.qss` y datos de matplotlib en `datas`/`collect_data_files` del `.spec`. |
| `--onefile` lento y difícil de depurar | Usar `--onedir` (D13). |
| `rapidfuzz` sin wheel para la versión elegida | Fijar versión en `requirements.txt`; si falla, registrarlo en §3 y evaluar `difflib` como plan B. |

---

## 7. Comandos útiles

```powershell
# entorno
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt

# calidad
python -m pytest -q
python -m ruff check app tests
python -m black --check app tests
python -m app

# verificación de arquitectura
Select-String -Path app\services\*.py -Pattern "PySide6|PyQt"
Select-String -Path app -Pattern "setGeometry"
Select-String -Path app -Pattern "Toluca|Metepec|Lerma"

# empaquetado
.\scripts\build_exe.ps1
.\dist\DataClean\DataClean.exe
```
