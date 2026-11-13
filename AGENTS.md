# AGENTS.md — Limpiador de CSV (aplicación de escritorio en Python)

> Este archivo es la fuente de verdad para cualquier agente (Plan o Build) que trabaje en este repositorio.
> Léelo completo antes de actuar. Si algo aquí contradice una suposición tuya, gana este archivo.

---

## 1. Objetivo

Construir un programa en **Python** que corra en una **ventana de escritorio, reescalable**, y permita a un usuario cargar un archivo tabular (CSV, Excel o Parquet), explorarlo y **limpiarlo paso a paso**, siguiendo el flujo del template visual del proyecto (5 pasos, el quinto con 5 sub-pasos).

El idioma de toda la interfaz es **español**. El código (nombres de variables, funciones, clases) va en inglés; los textos visibles al usuario, en español.

---

## 2. Flujo de trabajo con agentes



### Reglas para el agente Build
1. Implementa **solo** lo que está en `PLAN.md`, tarea por tarea, en el orden indicado.
2. Si `PLAN.md` no existe, crealo utilizando lo discutido con el agente build.
3. Después de cada tarea: ejecuta `pytest` y verifica que la app abre (`python -m app`).
4. Haz commits pequeños con mensajes descriptivos (`feat:`, `fix:`, `test:`, `docs:`).
5. No agregues dependencias sin registrarlas en `requirements.txt` y justificarlas en `PLAN.md`.
6. **Al terminar tu sesión, actualiza obligatoriamente la sección 11 (Handoff).** Es la última acción de cada sesión.

---

## 3. Stack técnico

- **Python 3.11+**
- **GUI: PySide6 (Qt)** — elegido por su sistema de layouts, que facilita el reescalado real de la ventana.
- **pandas** para manipulación de datos; **pyarrow** para Parquet; **openpyxl** para Excel.
- **matplotlib** (backend `QtAgg`) para la visualización de datos faltantes y outliers.
- **pytest** + **pytest-qt** para pruebas.
- Sin acceso a internet en tiempo de ejecución. Todo funciona offline.

### Estructura de carpetas esperada

```
proyecto/
├── AGENTS.md
├── PLAN.md                  # lo mantiene el agente Plan
├── requirements.txt
├── app/
│   ├── __main__.py          # punto de entrada: python -m app
│   ├── main_window.py       # ventana principal, sidebar + QStackedWidget
│   ├── state.py             # AppState y WorkflowController (ver sección 6)
│   ├── services/            # lógica pura SIN imports de Qt (testeable)
│   │   ├── loader.py
│   │   ├── profiling.py     # shape, tipos, faltantes
│   │   └── cleaning.py      # A–E
│   ├── views/               # una vista por paso
│   │   ├── step1_load.py
│   │   ├── step2_info.py
│   │   ├── step3_preview.py
│   │   ├── step4_types.py
│   │   └── step5_cleaning/
│   │       ├── missing.py
│   │       ├── irrelevant.py
│   │       ├── duplicates.py
│   │       ├── outliers.py
│   │       └── typos.py
│   └── widgets/             # componentes reutilizables (tarjetas, banners, tablas)
└── tests/
```

**Principio clave:** la lógica de datos vive en `services/` y **no importa Qt**. Las vistas solo llaman a servicios y muestran resultados.

---

## 4. Requisitos de ventana y reescalado

- Ventana principal `QMainWindow` con tamaño inicial ~1920×1080 y **tamaño mínimo 900×600**.
- **Todo** el layout usa `QVBoxLayout`, `QHBoxLayout`, `QGridLayout` y `QSplitter`. **Prohibido** posicionar widgets con coordenadas absolutas o `setGeometry`.
- Sidebar izquierda de ancho fijo razonable (~240 px) que no crece; el área de contenido se expande (`QSizePolicy.Expanding`).
- Las tablas (`QTableView`) se estiran y tienen scroll propio; nunca se desbordan fuera de la ventana.
- Las tarjetas de la fila superior (shape / filas / columnas) se reacomodan con `QGridLayout` y no se cortan al reducir la ventana.
- Los gráficos matplotlib usan `FigureCanvasQTAgg` con `tight_layout()` y se redibujan en `resizeEvent`.
- Soportar maximizar, minimizar y pantallas HiDPI (`QT_ENABLE_HIGHDPI_SCALING`).
- **Criterio de aceptación:** redimensionar de 900×600 a pantalla completa no produce texto cortado, solapamientos ni barras de scroll innecesarias.

### Estilo visual (según template)
- Barra superior lila redondeada con el título `DataClean`
- Sidebar con iconos; el paso activo resaltado en lila; los sub-pasos A–E indentados bajo "5. Limpieza de datos".
- Cada paso muestra un círculo lila numerado junto al título.
- Tarjetas con fondo gris muy claro y bordes redondeados; columnas numéricas con encabezado rosa, categóricas con encabezado verde claro.
- Banner amarillo para advertencias; botón rojo con borde para acciones destructivas.
- Centralizar colores y tipografías en un único archivo de tema (QSS) — no repetir estilos en cada vista.

---

## 5. Especificación por paso

### Paso 1 — Cargar datos
- Zona de arrastre con borde punteado ("Selecciona un archivo — CSV, Excel o Parquet") que acepta **drag & drop** y clic para abrir diálogo.
- Botón **Cargar datos**, deshabilitado hasta que haya un archivo seleccionado y válido.
- CSV: detectar separador y codificación (probar `utf-8`, `utf-8-sig`, `latin-1`). Excel: permitir elegir hoja si hay varias.
- Errores (archivo vacío, corrupto, sin permisos, formato no soportado) se muestran en un diálogo claro en español, nunca con traceback.
- Cargar un archivo nuevo **reinicia todo el flujo** (ver sección 6, regla de invalidación).
- Guardar una copia inmutable del DataFrame original (`original_df`) y trabajar siempre sobre `working_df`.

### Paso 2 — Consultar información general
- Tarjeta "Forma del dataset (shape)" mostrando `(filas, columnas)`.
- Tarjetas "Registros (filas)" y "Columnas" con formato de miles (`1,000`).
- Extras opcionales: uso de memoria, nombre del archivo.

### Paso 3 — Vista previa (head)
- Control numérico "Mostrar [N] registros" (default 5, mínimo 1, máximo = total de filas).
- Tabla de solo lectura con las primeras N filas; se actualiza al cambiar N.

### Paso 4 — Tipos de columnas
- Dos tarjetas: **Columnas numéricas** (verde) y **Columnas categóricas** (morado) con listas dinámicas obtenidas del dataset real.
- Clasificación: `select_dtypes` para numéricas; `object`, `category`, `bool` y strings para categóricas. Las fechas se muestran en una tercera tarjeta "Fecha/otras" solo si existen.
- Si una columna numérica en realidad es un código (ej. `id`), solo informar; **no** reclasificar automáticamente.

### Paso 5 — Limpieza de datos
Pestañas **A–E**. Cada pestaña sigue el patrón: *diagnóstico → previsualización del impacto → acción → confirmación → registro en historial*.

**A. Datos faltantes**
- Tabla: Columna · Registros faltantes · Porcentaje (solo columnas con faltantes primero; opción de ver todas).
- Banner amarillo: "Si se eliminan los registros con datos faltantes, se perderían **N** registros (**X %** del total)". **N se calcula con la unión de filas** (`df.isna().any(axis=1).sum()`), **no sumando** los faltantes por columna, para no contar dos veces filas con varios huecos.
- Visualización: mapa de calor (presente = azul claro, faltante = rosa). Si el dataset es grande, mostrar una muestra de hasta ~100 filas o agrupar filas en bloques; indicar en el gráfico que es una muestra.
- Acciones: **Eliminar registros con datos faltantes** (botón rojo, pide confirmación mostrando el conteo exacto) y, además, una alternativa no destructiva: imputar por columna (media/mediana para numéricas, moda o "Desconocido" para categóricas).

**B. Columnas irrelevantes**
- Lista de columnas con casillas. Sugerencias automáticas (no aplicadas solos): columnas constantes, con >90 % de faltantes, o con un valor único por fila (posibles IDs).
- Acción: eliminar columnas marcadas, con confirmación.

**C. Registros repetidos**
- Contar duplicados exactos y mostrar ejemplos. Permitir elegir subconjunto de columnas y qué copia conservar (primera/última).
- Acción: eliminar duplicados, con confirmación y conteo previo.

**D. Outliers**
- Por columna numérica: método IQR (default) o Z-score, con umbral editable.
- Mostrar boxplot/histograma y conteo de outliers por columna.
- Acciones: eliminar, limitar (clip / winsorizar) o conservar. Ninguna se aplica sin elección explícita.

**E. Errores tipográficos**
- Por columna categórica: normalizar espacios y mayúsculas/minúsculas, y detectar variantes similares (ej. `Toluca` / `toluca ` / `Tolucaa`) con similitud de cadenas (`difflib` o `rapidfuzz` si se aprueba).
- Mostrar propuestas de fusión (variante → valor canónico) que el usuario acepta o rechaza una por una.

**Cierre del flujo:** al completar A–E, habilitar un botón **Exportar dataset limpio** (CSV / Excel / Parquet) y un resumen de todo lo aplicado (historial).

---

## 6. Evitar que el usuario salte pasos (OBLIGATORIO)

Implementar la protección en **dos capas**: la interfaz y la lógica. Si solo se bloquea la UI, una regresión puede reabrir el hueco.

1. **Máquina de estados central.** `WorkflowController` en `state.py` define el orden: `LOAD → INFO → PREVIEW → TYPES → CLEAN_A → CLEAN_B → CLEAN_C → CLEAN_D → CLEAN_E → EXPORT`. Mantiene el conjunto de pasos completados y expone `can_enter(step)`.
2. **Sidebar bloqueada.** Los elementos de pasos no desbloqueados aparecen deshabilitados (gris, icono de candado, tooltip: "Completa primero: *Paso X*"). Un clic en uno deshabilitado no hace nada.
3. **Guardia en el controlador.** `go_to(step)` rechaza (lanza `StepLockedError`) cualquier salto no permitido, aunque se llame por código o atajo de teclado. Las vistas **no** cambian de página directamente: siempre pasan por el controlador.
4. **Botones "Siguiente" / "Anterior".** Cada vista tiene uno al pie. "Siguiente" se habilita solo cuando el paso cumple su condición de completitud:
   - Paso 1: dataset cargado sin errores.
   - Pasos 2, 3, 4: la vista fue mostrada y el usuario pulsó "Entendido/Siguiente" (consulta informativa).
   - Pasos A–E: el usuario **resolvió** el sub-paso — aplicó una acción **o** eligió explícitamente "Omitir este paso" (con diálogo de confirmación) **o** el diagnóstico no encontró nada que limpiar (se auto-completa con un mensaje "Sin problemas detectados").
5. **Retroceder es libre, avanzar no.** Volver a pasos ya completados está permitido (solo lectura de lo hecho). Pero si el usuario **modifica** datos en un paso anterior, todos los pasos posteriores vuelven a estado "pendiente" y se vuelven a bloquear (invalidación en cascada).
6. **Cargar un archivo nuevo reinicia todo:** estado, historial y pasos completados.
7. **Exportar bloqueado** hasta completar A–E.
8. **Indicador de progreso** visible (barra o marcas ✓ en la sidebar) para que el usuario vea qué falta.
9. **Historial y deshacer.** Cada acción destructiva guarda un snapshot (o diff) del `working_df`. Botón "Deshacer última acción" y "Restaurar original". Limitar memoria: máximo ~10 snapshots o guardar solo diffs en datasets grandes.
10. **Acciones destructivas siempre piden confirmación** con el impacto exacto (filas/columnas afectadas).

**Pruebas obligatorias** (`tests/test_workflow.py`): saltar del paso 1 al 5 falla; completar un paso desbloquea solo el siguiente; modificar el paso A tras completar C re-bloquea B–E; recargar archivo reinicia.

---

## 7. Reglas de código

- Type hints en funciones públicas; docstrings cortos en español o inglés (consistente por archivo).
- Funciones de `services/` son **puras** cuando sea posible: reciben un DataFrame y devuelven un resultado/DataFrame nuevo, sin efectos secundarios.
- Nunca modificar `original_df`. Usar `.copy()` al derivar.
- Operaciones pesadas (cargar archivos grandes, calcular outliers) fuera del hilo de UI (`QThread`/`QRunnable`) con indicador de progreso, para que la ventana no se congele.
- Manejo de errores: capturar excepciones en el borde de la UI y mostrar mensajes amigables; registrar el detalle técnico con `logging` en un archivo.
- Formato: `ruff` + `black` (línea 100). Sin `print` de depuración en commits.
- Cualquier texto de UI en un solo lugar (constantes o archivo de strings) para facilitar correcciones.

## 8. Pruebas

- `services/`: pruebas unitarias con DataFrames pequeños (faltantes, duplicados, outliers, typos, tipos).
- `WorkflowController`: pruebas de la máquina de estados (sección 6).
- Vistas: pruebas de humo con `pytest-qt` (la ventana abre, cada vista se instancia, los botones se habilitan/deshabilitan correctamente).
- Incluir un dataset de ejemplo `tests/data/sample.csv` (~1000 filas, 8 columnas: `id, edad, genero, ingreso, gastos, ciudad, estado, tipocliente`) con faltantes, duplicados, outliers y typos sembrados a propósito.

## 9. Criterios de aceptación globales

- [ ] `python -m app` abre la ventana sin errores.
- [ ] Carga CSV, Excel y Parquet.
- [ ] Ventana reescalable de 900×600 a pantalla completa sin romper el layout.
- [ ] Imposible llegar al paso 5 o exportar sin completar los anteriores (UI **y** controlador).
- [ ] Los cinco sub-pasos A–E funcionan, con confirmación e historial.
- [ ] Deshacer y restaurar original funcionan.
- [ ] Exporta el dataset limpio y el original no se modifica nunca.
- [ ] La suite `pytest` pasa en limpio.

---

## 10. HANDOFF — Instrucciones para el siguiente agente

> **Esta sección debe actualizarla el agente que termine una sesión, como última acción.**
> Reglas de uso:
> 1. Lista las tareas pendientes **en orden de importancia** (la 1 es la más urgente).
> 2. Estados permitidos: `PENDIENTE`, `EN PROGRESO`, `COMPLETADA`, `BLOQUEADA`.
> 3. Si una tarea **no pudo terminarse**, escribe la **razón concreta** (error, dependencia faltante, ambigüedad, límite de tiempo/contexto) y márcala como **⚠️ PRIORITARIA**. Las prioritarias se atienden **antes** que cualquier tarea nueva, sin importar su posición previa.
> 4. No borres tareas completadas: déjalas al final con fecha y commit.
> 5. Indica siempre el estado de las pruebas (`pytest`) y si la app abre.

**Última actualización:** 2026-11-12 / Antigravity Plus / Build
**Estado de pruebas:** pasan (1)
**¿La app abre?:** sí (DataClean 0.0.1-alpha)

### Tareas en orden de importancia

| # | Tarea | Estado | Prioridad | Razón si no se terminó |
|---|-------|--------|-----------|------------------------|
| T02 | Textos ES, tema QSS y widgets base | PENDIENTE | Normal | — |
| T03 | AppState + WorkflowController + pruebas | PENDIENTE | Normal | — |
| T04 | Dataset de ejemplo y fixtures (`tests/data/sample.csv`) | PENDIENTE | Normal | — |
| T05 | `services/loader.py` + pruebas | PENDIENTE | Normal | — |
| T06 | Vista Paso 1 (carga) | PENDIENTE | Normal | — |
| T07 | `services/profiling.py` + pruebas | PENDIENTE | Normal | — |
| T08 | Widget tabla reutilizable (`DataFrameTable`) | PENDIENTE | Normal | — |
| T09 | Vistas Pasos 2 y 4 | PENDIENTE | Normal | — |
| T10 | Vista Paso 3 (vista previa) | PENDIENTE | Normal | — |
| T11 | Limpieza A: servicio de faltantes | PENDIENTE | Normal | — |
| T12 | Vista 5A: diagnóstico + banner + tabla | PENDIENTE | Normal | — |
| T13 | Vista 5A: mapa de calor + acciones | PENDIENTE | Normal | — |
| T14 | Limpieza B: columnas irrelevantes | PENDIENTE | Normal | — |
| T15 | Limpieza C: duplicados | PENDIENTE | Normal | — |
| T16 | Limpieza D: outliers | PENDIENTE | Normal | — |
| T17 | Limpieza E: errores tipográficos (`rapidfuzz`) | PENDIENTE | Normal | — |
| T18 | Contenedor Paso 5: pestañas, omitir, auto-completar | PENDIENTE | Normal | — |
| T19 | Historial, deshacer y restaurar original | PENDIENTE | Normal | — |
| T20 | Exportación y resumen final (`<stem>_nuevo.<ext>`) | PENDIENTE | Normal | — |
| T21 | Hilos para operaciones pesadas (`QThread` worker) | PENDIENTE | Normal | — |
| T22 | Logging y borde de errores | PENDIENTE | Normal | — |
| T23 | Pulido visual y pruebas de reescalado | PENDIENTE | Normal | — |
| T24 | Empaquetado `.exe` con PyInstaller (`0.0.1-alpha`) | PENDIENTE | Normal | — |
| T25 | Cierre: suite completa y verificación de criterios | PENDIENTE | Normal | — |
| T01 | Andamiaje: venv, git, estructura, ventana base | COMPLETADA | Normal | 2026-11-12 (commit b2532a3) |

### Plantilla para marcar una tarea no terminada

```
| N | <nombre de la tarea> | BLOQUEADA | ⚠️ PRIORITARIA | <razón concreta: qué falló, en qué archivo/línea, qué se intentó, qué se necesita para continuar> |
```

### Notas para el siguiente agente
- Entorno configurado en `.venv` con Python 3.13.15 y dependencias completas (PySide6, pandas, matplotlib, rapidfuzz, pytest, etc.).
- La ventana principal inicia en 1920x1080 (mínimo 900x600) con sidebar fija de 240px y QStackedWidget expandible.
- El título de la app se obtiene de `app.__version__` (`DataClean 0.0.1-alpha`).
- La siguiente tarea en orden es **T02: Textos ES, tema QSS y widgets base**.
- Comandos útiles: `.\.venv\Scripts\Activate.ps1`, `python -m pytest -q`, `python -m app`.
