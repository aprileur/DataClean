# DataClean

Aplicación de escritorio en Python para explorar y limpiar datos tabulares (CSV, Excel, Parquet) paso a paso, sin escribir código.

Proyecto de estudiantes de **Ingeniería en Inteligencia Artificial**, UAEMEX · Materia: **Programación 2**

---

## Capturas de pantalla

> *(se agregarán al completar el pulido visual — T23)*

---

## Características

| Funcionalidad | Estado |
|---|---|
| Cargar CSV, Excel (`.xlsx`/`.xls`) y Parquet | ✅ |
| Detección automática de codificación y separador (CSV) | ✅ |
| Selección de hoja en archivos Excel de varias hojas | ✅ |
| Arrastrar y soltar archivos (*drag & drop*) | ✅ |
| Información general del dataset (shape, memoria, tipos) | ✅ |
| Vista previa con N configurable | ✅ |
| Clasificación de columnas: numéricas, categóricas, fechas | ✅ |
| Limpieza A — Datos faltantes (diagnóstico, imputación, eliminación) | 🔧 Servicio listo · Vista pendiente |
| Limpieza B — Columnas irrelevantes | 🔧 Servicio listo · Vista pendiente |
| Limpieza C — Registros duplicados | 🔧 Servicio listo · Vista pendiente |
| Limpieza D — Outliers (IQR / Z-score, boxplot) | 🔧 Servicio listo · Vista pendiente |
| Limpieza E — Errores tipográficos (`rapidfuzz`) | 🔧 Servicio listo · Vista pendiente |
| Historial de acciones (deshacer, restaurar original) | ✅ |
| Exportar dataset limpio (CSV / Excel / Parquet) | 🔧 Servicio listo · Vista pendiente |
| Protección de flujo: imposible saltarse pasos | ✅ |
| Ventana reescalable (900 × 600 → pantalla completa) | ✅ |
| Empaquetado como `.exe` (PyInstaller) | ⏳ Pendiente |

---

## Stack técnico

- **Python 3.13** (requerido; PyInstaller no soporta 3.14 aún)
- **PySide6** — GUI con layouts adaptables, sin coordenadas absolutas
- **pandas 3** — manipulación de datos (dtype `str` por defecto)
- **pyarrow** — soporte Parquet
- **openpyxl / xlrd** — Excel `.xlsx` y `.xls`
- **matplotlib** (backend `QtAgg`) — mapa de calor y gráficos de outliers
- **rapidfuzz** — detección de errores tipográficos por similitud de cadenas
- **pytest + pytest-qt** — 219 tests en suite

---

## Estructura del proyecto

```
DataClean/
├── app/
│   ├── __main__.py          # Punto de entrada: python -m app
│   ├── main_window.py       # QMainWindow: sidebar + QStackedWidget
│   ├── state.py             # AppState + WorkflowController (máquina de estados)
│   ├── history.py           # Historial de snapshots (deshacer / restaurar)
│   ├── theme.py / theme.qss # Estilos centralizados (colores, tipografía)
│   ├── services/            # Lógica pura SIN imports de Qt (100 % testeable)
│   │   ├── loader.py        # Carga CSV/Excel/Parquet con detección robusta
│   │   ├── profiling.py     # Shape, tipos, faltantes, heurística de IDs
│   │   ├── cleaning.py      # Operaciones A–E (faltantes, irrelevantes, dups, outliers, typos)
│   │   └── exporter.py      # Exportación CSV/Excel/Parquet sin colisión de nombres
│   ├── views/               # Una vista por paso del flujo
│   │   ├── step1_load.py    # Carga con drag & drop
│   │   ├── step2_info.py    # Información general
│   │   ├── step3_preview.py # Vista previa (head N)
│   │   ├── step4_types.py   # Tipos de columnas
│   │   └── step5_cleaning/  # Sub-vistas A–E (en construcción)
│   ├── widgets/             # Componentes reutilizables
│   │   ├── dataframe_table.py  # Tabla de solo lectura con colores por tipo
│   │   ├── heatmap.py          # Mapa de calor de faltantes (matplotlib)
│   │   ├── cards.py            # StatCard / InfoCard
│   │   ├── banner.py           # WarningBanner (amarillo)
│   │   ├── buttons.py          # DangerButton (rojo)
│   │   └── step_header.py      # Título con círculo numerado
│   └── ui/
│       └── texts_es.py      # Todos los textos visibles al usuario en español
├── tests/
│   ├── data/sample.csv      # Dataset de ejemplo (1 000 filas, problemas sembrados)
│   └── conftest.py          # Fixtures: sample_df, empty_df, overlap_missing_df
├── scripts/
│   ├── generate_sample.py   # Genera tests/data/sample.csv (semilla fija = 42)
│   └── build_exe.ps1        # Empaqueta la app con PyInstaller (Python 3.13)
├── AGENTS.md                # Especificación completa del proyecto
├── PLAN.md                  # Plan de tareas para agentes de IA
├── requirements.txt
└── pyproject.toml
```

---

## Instalación y ejecución

**Requisito:** Python 3.13 (se recomienda crear el entorno virtual con esta versión exacta)

```powershell
# 1. Crear y activar el entorno virtual
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Ejecutar la aplicación
python -m app
```

---

## Pruebas

```powershell
# Correr la suite completa
python -m pytest -q

# Solo servicios (sin Qt)
python -m pytest tests/ -k "not smoke and not resize"

# Verificar calidad de código
python -m ruff check app tests
python -m black --check app tests
```

La suite cuenta actualmente con **219 tests** (unitarios de servicios + pruebas de humo Qt).

---

## Flujo de la aplicación

La app obliga al usuario a completar los pasos en orden. No es posible saltarse pasos ni exportar sin terminar la limpieza.

```
Paso 1 — Cargar datos
   │  (archivo válido cargado)
   ▼
Paso 2 — Información general  →  shape, filas, columnas, memoria
   │  (Entendido)
   ▼
Paso 3 — Vista previa         →  head(N), solo lectura
   │  (Entendido)
   ▼
Paso 4 — Tipos de columnas    →  numéricas / categóricas / fechas
   │  (Entendido)
   ▼
Paso 5 — Limpieza de datos
   ├── A. Datos faltantes
   ├── B. Columnas irrelevantes
   ├── C. Registros duplicados
   ├── D. Outliers
   └── E. Errores tipográficos
         │  (todos resueltos u omitidos)
         ▼
      Exportar dataset limpio
```

Cargar un archivo nuevo **reinicia todo el flujo** y limpia el historial.  
Volver a un paso anterior está permitido; modificar datos en un paso intermedio **re-bloquea** todos los pasos posteriores.

---

## Dataset de ejemplo

`tests/data/sample.csv` — 1 000 filas, 8 columnas (`id`, `edad`, `genero`, `ingreso`, `gastos`, `ciudad`, `estado`, `tipocliente`).

Contiene a propósito:
- ~5 % de filas con al menos un valor faltante (incluyendo filas con dos huecos para probar la unión)
- 30 duplicados exactos
- Outliers en `ingreso` (> Q3 + 3·IQR)
- Typos en `ciudad` (`Toluca` / `toluca ` / `Tolucaa` / `CDMX` / `cdmx`)

Regenerar con semilla fija:
```powershell
python scripts/generate_sample.py
```

---

## Empaquetado como `.exe`

> Requiere Python 3.13 activo en el entorno virtual.

```powershell
.\scripts\build_exe.ps1
# Resultado: dist\DataClean\DataClean.exe
```

El ejecutable no requiere Python instalado en el equipo destino.  
*(Tarea T24 — pendiente de completar)*

---

## Convenciones del código

- **Código** (variables, funciones, clases) en **inglés**; **textos de UI** en **español** (centralizados en `app/ui/texts_es.py`).
- `app/services/` no importa Qt: lógica pura, 100 % testeable sin pantalla.
- `original_df` **nunca se muta**; todas las operaciones trabajan sobre `working_df`.
- Sin coordenadas absolutas ni `setGeometry` en ningún widget.
- Formato: `ruff` + `black` (línea 100).

---

## Contribuir

Este es un proyecto académico. Para proponer cambios, consulta `AGENTS.md` (especificación) y `PLAN.md` (tareas pendientes) antes de abrir un PR.
