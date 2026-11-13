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
