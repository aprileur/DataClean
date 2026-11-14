# DataClean

Aplicación de escritorio en Python para explorar y limpiar datos tabulares (CSV, Excel, Parquet) paso a paso, sin escribir código.

Proyecto de estudiantes de **Ingeniería en Inteligencia Artificial**, UAEMEX · Materia: **Programación 2**

---

## Integrantes del equipo:
- April Garcia Mastranzo
- Anwar Andrés Sotelo Sahuaya
- Paulina Barrón Careaga
- Fátima Mercado Molina
- Carla Zareth Sanchez Bautista

---

## Características

| Funcionalidad | Estado |
|---|:---:|
| Cargar CSV, Excel (`.xlsx`/`.xls`) y Parquet | ✅ |
| Detección automática de codificación y separador (CSV) | ✅ |
| Selección de hoja en archivos Excel con múltiples hojas | ✅ |
| Arrastrar y soltar archivos (*drag & drop*) y explorador nativo | ✅ |
| Información general del dataset (shape, memoria, conteo de filas/columnas) | ✅ |
| Vista previa interactiva con $N$ registros configurable (`head`) | ✅ |
| Clasificación dinámica de columnas: numéricas, categóricas y fechas | ✅ |
| **Limpieza A** — Datos faltantes (unión de filas, mapa de calor, imputación y eliminación) | ✅ |
| **Limpieza B** — Columnas irrelevantes (constantes, >90% faltantes, IDs/únicos) | ✅ |
| **Limpieza C** — Registros duplicados (subconjunto de columnas, conservar primera/última) | ✅ |
| **Limpieza D** — Outliers (IQR / Z-score, gráficos de boxplot e histograma, eliminación/clipping) | ✅ |
| **Limpieza E** — Errores tipográficos (normalización de texto, similitud difusa con `rapidfuzz`) | ✅ |
| Historial completo de acciones con **Deshacer (Undo)** y **Restaurar original** | ✅ |
| Exportar dataset limpio a CSV (`utf-8-sig`), Excel (`openpyxl`) o Parquet (`pyarrow`) | ✅ |
| Nombres de exportación protegidos (`<nombre>_nuevo.<ext>`), sin sobrescribir el original | ✅ |
| Máquina de estados estricta (`WorkflowController`): navegación guiada sin saltos no permitidos | ✅ |
| Interfaz adaptativa y reescalable (desde 900 × 600 hasta pantalla completa) | ✅ |
| Operaciones asíncronas en segundo plano con indicadores de progreso (`QThread`/`Worker`) | ✅ |
| Manejo robusto de excepciones y sistema de logging rotativo (`data_clean.log`) | ✅ |
| Empaquetado ejecutable autónomo para Windows (`DataClean.exe` con PyInstaller) | ✅ |

---

## Stack técnico

- **Python 3.13**
- **PySide6 (Qt for Python)** — GUI moderna con layouts flexibles y tema visual QSS personalizado.
- **pandas 3** — Manipulación eficiente de DataFrames.
- **pyarrow** — Soporte nativo para lectura y escritura de archivos Parquet.
- **openpyxl / xlrd** — Soporte para hojas de cálculo Excel (`.xlsx` y `.xls`).
- **matplotlib** (backend `QtAgg`) — Renderizado integrado de mapas de calor, boxplots e histogramas.
- **rapidfuzz** — Comparación difusa de cadenas para la detección de errores tipográficos.
- **pytest + pytest-qt** — Suite exhaustiva de **284 pruebas automatizadas** (unitarias e integración).
- **pyinstaller** — Empaquetado en binario ejecutable independiente de Windows.

---

## Estructura del proyecto

```
DataClean/
├── app/
│   ├── __main__.py          # Punto de entrada de la aplicación: python -m app
│   ├── main_window.py       # QMainWindow: barra superior, sidebar y navegación central
│   ├── state.py             # AppState y WorkflowController (máquina de estados del flujo)
│   ├── history.py           # Historial de snapshots (Undo y Restaurar original)
│   ├── logging_config.py    # Configuración de logs con rotación (data_clean.log)
│   ├── workers.py           # Ejecutor en segundo plano (QThreadPool / QRunnable)
│   ├── theme.py / theme.qss # Estilos visuales centralizados (paleta lila, tarjetas, estados)
│   ├── services/            # Lógica pura de datos SIN dependencias de Qt (100% testeable)
│   │   ├── loader.py        # Carga multiformato con detección robusta de encoding y separador
│   │   ├── profiling.py     # Shape, memoria, tipos de datos y heurística de IDs
│   │   ├── cleaning.py      # Operaciones de limpieza A–E (faltantes, irrelevantes, dups, outliers, typos)
│   │   └── exporter.py      # Exportación a CSV, Excel y Parquet con nombres no colisionantes
│   ├── views/               # Vistas desacopladas para cada paso del flujo
│   │   ├── step1_load.py    # Paso 1: Carga de archivo con zona de drag & drop
│   │   ├── step2_info.py    # Paso 2: Información general y shape
│   │   ├── step3_preview.py # Paso 3: Vista previa con N configurable
│   │   ├── step4_types.py   # Paso 4: Clasificación de columnas
│   │   ├── export.py        # Paso final: Resumen del historial y exportación
│   │   └── step5_cleaning/  # Paso 5: Contenedor con pestañas A–E
│   │       ├── __init__.py  # Contenedor de pestañas y control de progreso
│   │       ├── base.py      # Clase base para sub-vistas de limpieza
│   │       ├── missing.py   # 5A: Datos faltantes (tabla, banner de unión, heatmap, imputación/baja)
│   │       ├── irrelevant.py# 5B: Columnas irrelevantes (constantes, nulos extremos, IDs)
│   │       ├── duplicates.py# 5C: Registros repetidos (subconjuntos, keep first/last)
│   │       ├── outliers.py  # 5D: Outliers (IQR / Z-score con boxplot e histograma)
│   │       └── typos.py     # 5E: Errores tipográficos (agrupación y fusión interactiva)
│   ├── widgets/             # Componentes de UI reutilizables
│   │   ├── dataframe_table.py  # QTableView con QAbstractTableModel de solo lectura
│   │   ├── heatmap.py          # Lienzo FigureCanvasQTAgg para mapa de calor
│   │   ├── busy_indicator.py   # Barra indeterminada y etiqueta de operaciones en segundo plano
│   │   ├── cards.py            # StatCard / InfoCard con estilos redondeados
│   │   ├── banner.py           # WarningBanner amarillo
│   │   ├── buttons.py          # Botones con estilos semánticos (DangerButton, PrimaryButton)
│   │   └── step_header.py      # Encabezado de paso con círculo numerado
│   └── ui/
│       ├── texts_es.py      # Fuente única de textos visibles en español
│       └── error_boundary.py# Captura global de excepciones y alertas amigables
├── build/
│   ├── dataclean.spec       # Especificación de PyInstaller
│   └── version_info.txt     # Metadatos del ejecutable (0.0.1-alpha)
├── dist/
│   └── DataClean/           # Directorio con el ejecutable generado (DataClean.exe)
├── tests/
│   ├── data/sample.csv      # Dataset de prueba con 1 000 filas y problemas sembrados
│   ├── conftest.py          # Fixtures y configuraciones de prueba
│   └── test_*.py            # 284 pruebas unitarias, de integración y de UI
├── scripts/
│   ├── generate_sample.py   # Generador determinista del dataset de prueba (semilla 42)
│   ├── launcher.py          # Entrypoint limpio para PyInstaller
│   └── build_exe.ps1        # Script PowerShell para compilar el ejecutable
├── AGENTS.md                # Especificación del proyecto y registro de tareas (Handoff)
├── PLAN.md                  # Plan de ejecución detallado (25 tareas completadas)
├── requirements.txt         # Dependencias de producción y desarrollo
└── pyproject.toml           # Configuración de pytest, ruff y black
```

---

## Instalación y ejecución desde código fuente

### Requisitos previos
- **Python 3.13** instalado en el sistema.

### Pasos
```powershell
# 1. Clonar el repositorio
git clone https://github.com/aprileur/DataClean.git
cd DataClean

# 2. Crear y activar el entorno virtual
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Instalar las dependencias
pip install -r requirements.txt

# 4. Ejecutar la aplicación
python -m app
```

---

## Ejecución del binario (.exe en Windows)

La aplicación ya se encuentra compilada como ejecutable portable para Windows de 64 bits en la carpeta `dist/DataClean/`:

```powershell
.\dist\DataClean\DataClean.exe
```

* No requiere tener instalado Python ni activar ningún entorno virtual.
* Puede ejecutarse directamente haciendo doble clic sobre `DataClean.exe` en el Explorador de archivos.

Para reconstruir el ejecutable:
```powershell
.\scripts\build_exe.ps1
```

---

## Pruebas automatizadas y calidad

El proyecto cuenta con una cobertura completa de pruebas automatizadas:

```powershell
# Ejecutar la suite completa (284 pruebas)
python -m pytest -q

# Ejecutar únicamente pruebas de lógica pura (servicios)
python -m pytest tests/ -k "not smoke and not resize"

# Verificar formato y linting
python -m ruff check app tests scripts
python -m black --check app tests scripts
```

---

## Flujo de trabajo de la aplicación

La aplicación implementa una máquina de estados bidireccional protegida:

```
[ Paso 1: Cargar datos ]
         │ (Carga exitosa de CSV / Excel / Parquet)
         ▼
[ Paso 2: Información general ] ────► Shape (filas, columnas), memoria y archivo
         │ (Entendido)
         ▼
[ Paso 3: Vista previa (Head) ] ────► Muestra primeras N filas (interactivo)
         │ (Entendido)
         ▼
[ Paso 4: Tipos de columnas ]   ────► Numéricas / Categóricas / Fechas
         │ (Entendido)
         ▼
[ Paso 5: Limpieza de datos ]
         ├── 5A. Datos faltantes    ──► Detección de unión, mapa de calor, imputación / eliminación
         ├── 5B. Col. irrelevantes  ──► Constantes, >90% nulos, identificadores / claves
         ├── 5C. Duplicados         ──► Conteo exacto, ejemplos, subconjuntos y keep first/last
         ├── 5D. Outliers           ──► Métodos IQR / Z-Score, boxplot, histograma y winsorización/baja
         └── 5E. Errores tipográficos─► Similitud fonética y de caracteres con rapidfuzz
         │ (Todos los sub-pasos resueltos u omitidos)
         ▼
[ Exportar dataset limpio ]     ────► Guardar en CSV / Excel / Parquet con sufijo "_nuevo"
```

### Reglas de integridad
1. **Protección contra saltos:** No es posible acceder a pasos posteriores sin haber completado los anteriores (la barra lateral muestra candados explicativos).
2. **Retroceso libre e invalidación en cascada:** El usuario puede volver a consultar cualquier paso anterior. Si modifica los datos en un paso previo, los pasos posteriores se invalidan y vuelven a bloquearse para garantizar la coherencia.
3. **Historial y Deshacer:** Toda acción destructiva guarda una copia snapshot; los botones **Deshacer última acción** y **Restaurar original** en la barra superior permiten volver atrás en cualquier instante.
4. **Archivo original intacto:** El archivo original nunca se sobrescribe. Al exportar, la aplicación genera un archivo nuevo con el sufijo `_nuevo` (ej. `ventas_nuevo.csv`).

---

## Dataset de prueba

Para experimentar con todas las funciones de limpieza, se incluye el dataset sintético [tests/data/sample.csv](file:///tests/data/sample.csv) con 1 000 filas y 8 columnas (`id`, `edad`, `genero`, `ingreso`, `gastos`, `ciudad`, `estado`, `tipocliente`), el cual incorpora a propósito:
- ~5% de filas con datos faltantes (con filas que contienen múltiples nulos para verificar la unión lógica).
- 30 registros exactamente duplicados.
- Outliers en la columna de ingresos numéricos ($> Q_3 + 3 \times \text{IQR}$).
- Errores tipográficos deliberados en nombres de ciudades (`Toluca`, `toluca `, `Tolucaa`, `CDMX`, `cdmx`).

Para regenerar el dataset de forma determinista:
```powershell
python scripts/generate_sample.py
```
