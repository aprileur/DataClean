"""Constantes de texto en español para toda la interfaz de usuario de DataClean.

Ningún texto visible al usuario debe estar fuera de este archivo.
"""

# Textos Generales y Aplicación
APP_TITLE = "DataClean"
APP_SUBTITLE = "Limpiador interactivo y asistido de datasets"
SIDEBAR_TITLE = "Pasos del flujo"

# Navegación / Botones comunes
BTN_NEXT = "Siguiente"
BTN_BACK = "Anterior"
BTN_UNDERSTOOD = "Entendido"
BTN_CANCEL = "Cancelar"
BTN_CONFIRM = "Confirmar"
BTN_APPLY = "Aplicar"
BTN_SKIP_STEP = "Omitir este paso"
BTN_UNDO = "Deshacer última acción"
BTN_RESTORE_ORIGINAL = "Restaurar original"

# Tooltips de navegación
TOOLTIP_STEP_LOCKED = "Completa primero: {step_name}"
TOOLTIP_STEP_COMPLETED = "Paso completado: {step_name}"
ERROR_STEP_LOCKED = "El paso '{step_name}' está bloqueado. Completa primero los pasos anteriores."

# Nombres de los pasos del flujo
STEP_1_NAME = "1. Cargar datos"
STEP_2_NAME = "2. Información general"
STEP_3_NAME = "3. Vista previa"
STEP_4_NAME = "4. Tipos de columnas"
STEP_5_NAME = "5. Limpieza de datos"
STEP_5A_NAME = "A. Datos faltantes"
STEP_5B_NAME = "B. Columnas irrelevantes"
STEP_5C_NAME = "C. Registros repetidos"
STEP_5D_NAME = "D. Valores atípicos (outliers)"
STEP_5E_NAME = "E. Errores tipográficos"
STEP_EXPORT_NAME = "Exportar dataset limpio"

# Iconos de la sidebar (clave = valor de Step)
STEP_ICONS = {
    "LOAD": "📁",
    "INFO": "ℹ️",
    "PREVIEW": "👁️",
    "TYPES": "🔢",
    "CLEAN_A": "🧩",
    "CLEAN_B": "🧹",
    "CLEAN_C": "📑",
    "CLEAN_D": "📈",
    "CLEAN_E": "✏️",
    "EXPORT": "💾",
}

# Paso 1: Carga de datos
LOAD_DROP_TITLE = "Selecciona un archivo"
LOAD_DROP_SUBTITLE = (
    "Arrastra y suelta aquí tu archivo CSV, Excel o Parquet, o haz clic para explorar"
)
LOAD_BTN_SELECT = "Elegir archivo..."
LOAD_BTN_LOAD = "Cargar datos"
LOAD_ERR_TITLE = "Error al cargar archivo"
LOAD_SHEET_DIALOG_TITLE = "Seleccionar hoja de Excel"
LOAD_SHEET_DIALOG_PROMPT = "El archivo contiene varias hojas. Selecciona la que deseas cargar:"
LOAD_FILE_FILTER = (
    "Archivos de datos (*.csv *.xlsx *.xls *.parquet);;"
    "CSV (*.csv);;"
    "Excel (*.xlsx *.xls);;"
    "Parquet (*.parquet);;"
    "Todos los archivos (*)"
)
LOAD_FILE_INFO = "{name} ({size})"
LOAD_BTN_LOAD_TOOLTIP = "Cargar el archivo seleccionado y continuar con el flujo."
LOAD_BTN_LOAD_DISABLED_TOOLTIP = (
    "Selecciona un archivo válido (CSV, Excel o Parquet) para poder cargar los datos."
)
LOAD_INVALID_FORMAT = "Formato no soportado: «{ext}». Se admiten: {supported}."
LOAD_UNEXPECTED_ERROR = (
    "Ocurrió un error inesperado al cargar el archivo. "
    "Verifica que el archivo no esté dañado e inténtalo de nuevo."
)
LOAD_SIZE_B = "{size} B"
LOAD_SIZE_KB = "{size} KB"
LOAD_SIZE_MB = "{size} MB"

# Paso 2: Información general
INFO_SHAPE_TITLE = "Forma del dataset (shape)"
INFO_ROWS_TITLE = "Registros (filas)"
INFO_COLS_TITLE = "Columnas"
INFO_MEMORY_TITLE = "Uso de memoria aproximado"
INFO_FILENAME_TITLE = "Archivo origen"

# Paso 3: Vista previa
PREVIEW_CONTROL_LABEL = "Mostrar registros:"
PREVIEW_TOTAL_LABEL = "de {total} registros"

# Paso 4: Tipos de columnas
TYPES_NUMERIC_TITLE = "Columnas numéricas"
TYPES_CATEGORICAL_TITLE = "Columnas categóricas"
TYPES_OTHER_TITLE = "Fecha / Otras"
TYPES_ID_WARNING = "Nota: '{col}' parece ser un identificador (valores únicos por fila)."

# Paso 5: Limpieza común
CLEAN_NO_ISSUES_FOUND = "Sin problemas detectados en este paso."
CLEAN_SKIP_CONFIRM_TITLE = "¿Omitir este paso?"
CLEAN_SKIP_CONFIRM_MSG = (
    "¿Estás seguro de que deseas omitir este sub-paso de limpieza sin realizar ninguna acción?"
)

# Paso 5A: Faltantes
MISSING_TABLE_COL = "Columna"
MISSING_TABLE_COUNT = "Registros faltantes"
MISSING_TABLE_PCT = "Porcentaje"
MISSING_VIEW_ALL = "Ver todas las columnas"
MISSING_BANNER_WARNING = (
    "Si se eliminan los registros con datos faltantes, se perderían {count} registros "
    "({pct:.1f}% del total)."
)
MISSING_BTN_DROP = "Eliminar registros con datos faltantes"
MISSING_BTN_IMPUTE = "Imputar datos faltantes..."
MISSING_DROP_CONFIRM_TITLE = "Confirmar eliminación de registros"
MISSING_DROP_CONFIRM_MSG = (
    "Esta acción eliminará {count} filas ({pct:.1f}% del dataset) que contienen "
    "al menos un dato faltante. ¿Deseas continuar?"
)

# Paso 5B: Columnas irrelevantes
IRRELEVANT_INFO = "Selecciona las columnas que deseas remover del dataset:"
IRRELEVANT_SUGGESTION_CONST = "Columna constante (un solo valor)"
IRRELEVANT_SUGGESTION_EMPTY = "Más del 90% de valores faltantes"
IRRELEVANT_SUGGESTION_ID = "Posible identificador único"
IRRELEVANT_BTN_DROP = "Eliminar columnas seleccionadas"
IRRELEVANT_CONFIRM_TITLE = "Confirmar eliminación de columnas"
IRRELEVANT_CONFIRM_MSG = "Se eliminarán las siguientes columnas: {cols}. ¿Deseas continuar?"

# Paso 5C: Duplicados
DUPLICATES_COUNT_LABEL = "Registros duplicados exactos detectados: {count}"
DUPLICATES_KEEP_LABEL = "Copia a conservar:"
DUPLICATES_KEEP_FIRST = "Primera ocurrencia"
DUPLICATES_KEEP_LAST = "Última ocurrencia"
DUPLICATES_BTN_DROP = "Eliminar duplicados"
DUPLICATES_CONFIRM_TITLE = "Confirmar eliminación de duplicados"
DUPLICATES_CONFIRM_MSG = "Se eliminarán {count} filas duplicadas. ¿Deseas continuar?"

# Paso 5D: Outliers
OUTLIERS_METHOD_LABEL = "Método de detección:"
OUTLIERS_IQR = "Rango Intercuartílico (IQR)"
OUTLIERS_ZSCORE = "Z-Score"
OUTLIERS_THRESHOLD_LABEL = "Umbral:"
OUTLIERS_ACTION_DROP = "Eliminar outliers"
OUTLIERS_ACTION_CLIP = "Limitar (Winsorizar)"
OUTLIERS_ACTION_KEEP = "Conservar valores"

# Paso 5E: Typos
TYPOS_COL_SELECT = "Seleccionar columna categórica:"
TYPOS_SIMILARITY_LABEL = "Similitud mínima:"
TYPOS_SIMILARITY_SUFFIX = " %"
TYPOS_TABLE_VARIANT = "Variante detectada"
TYPOS_TABLE_CANONICAL = "Valor canónico propuesto"
TYPOS_TABLE_COUNT = "Ocurrencias"
TYPOS_BTN_APPLY = "Aplicar fusiones seleccionadas"

# Exportar
EXPORT_TITLE = "Exportar dataset limpio"
EXPORT_BTN = "Exportar dataset limpio"
EXPORT_SUMMARY_TITLE = "Resumen de cambios aplicados:"
EXPORT_SUCCESS_TITLE = "Exportación exitosa"
EXPORT_SUCCESS_MSG = "El dataset limpio fue guardado exitosamente en:\n{path}"
EXPORT_BADGE = "6"
EXPORT_FORMAT_LABEL = "Formato de exportación:"
EXPORT_FORMAT_CSV = "CSV (.csv)"
EXPORT_FORMAT_EXCEL = "Excel (.xlsx)"
EXPORT_FORMAT_PARQUET = "Parquet (.parquet)"
EXPORT_DIALOG_TITLE = "Guardar dataset limpio"
EXPORT_DEFAULT_STEM = "datos"
EXPORT_FILE_FILTER_CSV = "CSV (*.csv)"
EXPORT_FILE_FILTER_EXCEL = "Excel (*.xlsx)"
EXPORT_FILE_FILTER_PARQUET = "Parquet (*.parquet)"
EXPORT_LOCKED_TOOLTIP = (
    "Completa los cinco sub-pasos de limpieza (A–E) para habilitar la exportación."
)
EXPORT_READY_TOOLTIP = "Guardar el dataset limpio en un archivo nuevo."
EXPORT_ERR_TITLE = "Error de exportación"
EXPORT_NO_ACTIONS = "Todavía no se registraron acciones de limpieza."
EXPORT_DATASET_EMPTY = "No hay un dataset cargado para exportar."
EXPORT_HISTORY_PLACEHOLDER = "(Dataset original, sin acciones de limpieza)"

# Paso 5: limpieza (textos compartidos por las sub-vistas A–E)
CLEAN_NO_DATA = "No hay datos cargados."
CLEAN_HISTORY_SKIP = "Omitido: {step_name}"
CLEAN_STEP_SKIPPED = "Sub-paso omitido por el usuario."
CLEAN_PROGRESS_LABEL = "Sub-pasos completados: {done} de {total}"
CLEAN_TAB_COMPLETED_SUFFIX = "  ✓"
CLEAN_DIAGNOSIS_TITLE = "Diagnóstico"

# Errores inesperados, logging y operaciones en segundo plano
ERROR_UNEXPECTED_TITLE = "Error inesperado"
ERROR_UNEXPECTED_MSG = (
    "Ocurrió un error inesperado. Consulta el archivo `data_clean.log` para más detalles."
)
WORKER_ERROR_GENERIC = "Ocurrió un error inesperado al procesar la operación."
LOAD_PROGRESS_LABEL = "Cargando datos, por favor espera..."
OUTLIERS_PROGRESS_LABEL = "Analizando valores atípicos, por favor espera..."
OUTLIERS_ERR_TITLE = "Error al analizar valores atípicos"


# Paso 5A: imputación
MISSING_IMPUTE_DIALOG_TITLE = "Imputar datos faltantes"
MISSING_IMPUTE_COLUMN_LABEL = "Columna:"
MISSING_IMPUTE_STRATEGY_LABEL = "Estrategia:"
MISSING_IMPUTE_VALUE_LABEL = "Valor constante:"
MISSING_STRATEGY_MEAN = "Media"
MISSING_STRATEGY_MEDIAN = "Mediana"
MISSING_STRATEGY_MODE = "Moda"
MISSING_STRATEGY_CONSTANT = "Constante (Desconocido si se deja vacío)"
MISSING_HISTORY_DROP = "Eliminar registros con datos faltantes"
MISSING_HISTORY_IMPUTE = "Imputar columna «{column}» con {strategy}"

# Paso 5B: columnas irrelevantes
IRRELEVANT_SUGGESTION_LABEL = "Sugerencia: {reason}"
IRRELEVANT_HISTORY_DROP = "Eliminar columnas: {columns}"
IRRELEVANT_NO_COLUMNS = "El dataset no tiene columnas para evaluar."

# Paso 5C: duplicados
DUPLICATES_COLUMNS_LABEL = "Columnas para comparar:"
DUPLICATES_EXAMPLES_TITLE = "Ejemplos de registros duplicados:"
DUPLICATES_HISTORY_DROP = "Eliminar duplicados ({count} filas)"
DUPLICATES_NO_COLUMNS = "Selecciona al menos una columna para comparar."

# Paso 5D: outliers
OUTLIERS_TABLE_TITLE = "Resumen de valores atípicos por columna:"
OUTLIERS_TABLE_COL = "Columna"
OUTLIERS_TABLE_COUNT = "Outliers"
OUTLIERS_TABLE_PCT = "Porcentaje"
OUTLIERS_TABLE_LOWER = "Límite inferior"
OUTLIERS_TABLE_UPPER = "Límite superior"
OUTLIERS_COLUMN_LABEL = "Columna a visualizar:"
OUTLIERS_CHART_EMPTY = "Sin datos para graficar"
OUTLIERS_CHART_BOX = "Diagrama de caja"
OUTLIERS_CHART_HIST = "Histograma"
OUTLIERS_CHART_VALUE = "Valor"
OUTLIERS_CHART_FREQUENCY = "Frecuencia"
OUTLIERS_CHART_TITLE = "Distribución de «{column}»"
OUTLIERS_HISTORY_DROP = "Eliminar outliers de «{column}»"
OUTLIERS_HISTORY_CLIP = "Limitar outliers de «{column}»"
OUTLIERS_KEEP_NOTE = "Se conservan los valores de «{column}»."
OUTLIERS_NO_NUMERIC = "No hay columnas numéricas en el dataset."
OUTLIERS_COLUMN_COUNT = "Outliers detectados en «{column}»: {count}"
OUTLIERS_DROP_CONFIRM_TITLE = "Confirmar eliminación de outliers"
OUTLIERS_DROP_CONFIRM_MSG = (
    "Se eliminarán {count} filas con valores atípicos en la columna «{column}». "
    "¿Deseas continuar?"
)
OUTLIERS_CLIP_CONFIRM_TITLE = "Confirmar limitación de outliers"
OUTLIERS_CLIP_CONFIRM_MSG = (
    "Se limitarán {count} valores atípicos de la columna «{column}» a los bordes "
    "calculados. ¿Deseas continuar?"
)

# Barra superior: historial y progreso
TOOLTIP_UNDO = "Deshace la última acción registrada en el historial."
TOOLTIP_UNDO_DISABLED = "No hay acciones anteriores que se puedan deshacer."
TOOLTIP_RESTORE_ORIGINAL = "Descarta todos los cambios y vuelve al dataset original."
TOOLTIP_RESTORE_DISABLED = "Carga un dataset para poder restaurar el original."
UNDO_NOTHING_TITLE = "Nada que deshacer"
UNDO_NOTHING_MSG = "No hay acciones anteriores que se puedan deshacer."
RESTORE_CONFIRM_TITLE = "¿Restaurar el dataset original?"
RESTORE_CONFIRM_MSG = (
    "Se descartarán todos los cambios aplicados y se volverá al dataset original. "
    "Los sub-pasos de limpieza A–E deberán resolverse de nuevo. ¿Deseas continuar?"
)
SIDEBAR_PROGRESS_FORMAT = "Progreso: %v de %m pasos"

# Paso 5E: errores tipográficos
TYPOS_PROPOSALS_TITLE = "Propuestas de fusión:"
TYPOS_TABLE_ACCEPT = "Aplicar"
TYPOS_TABLE_SCORE = "Similitud"
TYPOS_BTN_DISCARD = "Descartar propuestas de esta columna"
TYPOS_NO_COLUMNS = "No hay columnas categóricas en el dataset."
TYPOS_NO_SUGGESTIONS = "No se encontraron variantes similares en esta columna."
TYPOS_COLUMN_REVIEWED = "Columna «{column}» revisada."
TYPOS_HISTORY_APPLY = "Fusionar variantes de «{column}» ({count} propuestas)"
