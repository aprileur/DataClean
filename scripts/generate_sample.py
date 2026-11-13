"""Genera el dataset de ejemplo reproducible que usan las pruebas de DataClean.

El archivo resultante (`tests/data/sample.csv`) contiene 1000 filas y 8 columnas
con problemas sembrados a propósito: datos faltantes (algunos solapados),
duplicados exactos, outliers en `ingreso` y errores tipográficos en `ciudad`.

Uso:
    python scripts/generate_sample.py
    python scripts/generate_sample.py --output ruta/alternativa.csv

Con la semilla fija (42) el script es idempotente: dos ejecuciones producen
exactamente el mismo archivo, byte por byte.
"""

from __future__ import annotations

import argparse
import random
from pathlib import Path

import pandas as pd

SEED = 42
TOTAL_ROWS = 1000
DUPLICATE_ROWS = 30
BASE_ROWS = TOTAL_ROWS - DUPLICATE_ROWS  # 970 filas únicas; el resto son copias exactas

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = REPO_ROOT / "tests" / "data" / "sample.csv"

COLUMNS = ("id", "edad", "genero", "ingreso", "gastos", "ciudad", "estado", "tipocliente")

GENDERS = ("F", "M", "Otro")
GENDER_WEIGHTS = (0.47, 0.49, 0.04)

CUSTOMER_TYPES = ("Nuevo", "Frecuente", "Premium")
CUSTOMER_WEIGHTS = (0.50, 0.35, 0.15)

CITIES = ("Toluca", "Metepec", "Lerma", "CDMX", "Guadalajara", "Monterrey", "Puebla", "Querétaro")
CITY_WEIGHTS = (0.22, 0.08, 0.06, 0.20, 0.15, 0.12, 0.09, 0.08)

CITY_TO_STATE = {
    "Toluca": "México",
    "Metepec": "México",
    "Lerma": "México",
    "CDMX": "Ciudad de México",
    "Guadalajara": "Jalisco",
    "Monterrey": "Nuevo León",
    "Puebla": "Puebla",
    "Querétaro": "Querétaro",
}

# Variantes tipográficas sembradas de forma determinista (fila base -> valor).
CITY_TYPO_PLAN = (
    (5, "toluca "),
    (6, "toluca "),
    (7, "Tolucaa"),
    (8, "Tolucaa"),
    (10, "cdmx"),
    (11, "cdmx"),
    (12, "cdmx"),
)
CITY_TYPO_VARIANTS = {
    "Toluca": ("toluca ", "Tolucaa", "TOLUCA"),
    "CDMX": ("cdmx", "Cdmx", "CDMX "),
}
TYPO_PROBABILITY = 0.05

# Outliers de ingreso: siempre por encima de Q3 + 3 * IQR.
OUTLIER_ROW_INDEXES = tuple(range(40, 52))
OUTLIER_VALUES = tuple(round(150_000.0 + 12_500.0 * step, 2) for step in range(12))

# Faltantes: 50 filas (5 %) repartidas para que la unión de filas (50) sea
# estrictamente menor que la suma de faltantes por columna (58).
MISSING_EDAD_ONLY = 18
MISSING_GASTOS_ONLY = 10
MISSING_CIUDAD_ONLY = 8
MISSING_TIPOCLIENTE_ONLY = 6
MISSING_EDAD_AND_GASTOS = 8
MISSING_ROWS = (
    MISSING_EDAD_ONLY
    + MISSING_GASTOS_ONLY
    + MISSING_CIUDAD_ONLY
    + MISSING_TIPOCLIENTE_ONLY
    + MISSING_EDAD_AND_GASTOS
)


def build_sample_dataframe(seed: int = SEED) -> pd.DataFrame:
    """Construye el DataFrame de ejemplo con todos los problemas sembrados."""
    rng = random.Random(seed)

    records: list[dict[str, object]] = []
    for row_index in range(BASE_ROWS):
        ingreso = round(max(4_500.0, rng.gauss(18_000.0, 5_500.0)), 2)
        gastos = round(ingreso * rng.uniform(0.35, 0.75), 2)
        ciudad = rng.choices(CITIES, weights=CITY_WEIGHTS, k=1)[0]
        records.append(
            {
                "id": row_index + 1,
                "edad": rng.randint(18, 78),
                "genero": rng.choices(GENDERS, weights=GENDER_WEIGHTS, k=1)[0],
                "ingreso": ingreso,
                "gastos": gastos,
                "ciudad": ciudad,
                "estado": CITY_TO_STATE[ciudad],
                "tipocliente": rng.choices(CUSTOMER_TYPES, weights=CUSTOMER_WEIGHTS, k=1)[0],
            }
        )

    # Errores tipográficos garantizados en ciudad (Toluca / CDMX y sus variantes).
    for row_index, typo in CITY_TYPO_PLAN:
        records[row_index]["ciudad"] = typo

    # Ruido tipográfico adicional, reproducible con la misma semilla.
    for row_index in range(BASE_ROWS):
        if rng.random() < TYPO_PROBABILITY:
            variants = CITY_TYPO_VARIANTS.get(str(records[row_index]["ciudad"]))
            if variants:
                records[row_index]["ciudad"] = rng.choice(variants)

    # Outliers de ingreso muy por encima del límite superior de IQR.
    for offset, row_index in enumerate(OUTLIER_ROW_INDEXES):
        records[row_index]["ingreso"] = OUTLIER_VALUES[offset]

    # Datos faltantes: 50 filas, ocho de ellas con dos huecos (edad y gastos).
    missing_indexes = rng.sample(range(BASE_ROWS), MISSING_ROWS)
    cursor = 0
    edad_only = missing_indexes[cursor : cursor + MISSING_EDAD_ONLY]
    cursor += MISSING_EDAD_ONLY
    gastos_only = missing_indexes[cursor : cursor + MISSING_GASTOS_ONLY]
    cursor += MISSING_GASTOS_ONLY
    ciudad_only = missing_indexes[cursor : cursor + MISSING_CIUDAD_ONLY]
    cursor += MISSING_CIUDAD_ONLY
    tipocliente_only = missing_indexes[cursor : cursor + MISSING_TIPOCLIENTE_ONLY]
    cursor += MISSING_TIPOCLIENTE_ONLY
    edad_and_gastos = missing_indexes[cursor : cursor + MISSING_EDAD_AND_GASTOS]

    for row_index in edad_only:
        records[row_index]["edad"] = None
    for row_index in gastos_only:
        records[row_index]["gastos"] = None
    for row_index in ciudad_only:
        records[row_index]["ciudad"] = None
    for row_index in tipocliente_only:
        records[row_index]["tipocliente"] = None
    for row_index in edad_and_gastos:
        records[row_index]["edad"] = None
        records[row_index]["gastos"] = None

    # 30 duplicados exactos: copias de filas completas (mismo id incluido).
    # Se eligen entre filas sin faltantes para que el conteo de nulos no cambie.
    missing_positions = set(missing_indexes)
    eligible_rows = [index for index in range(BASE_ROWS) if index not in missing_positions]
    duplicate_sources = rng.sample(eligible_rows, DUPLICATE_ROWS)
    duplicated_records = [dict(records[index]) for index in duplicate_sources]

    all_records = records + duplicated_records
    order = list(range(len(all_records)))
    rng.shuffle(order)
    shuffled = [all_records[index] for index in order]

    df = pd.DataFrame(shuffled, columns=list(COLUMNS))

    # Tipos estables: enteros anulables para edad, flotantes para montos y texto para el resto.
    df["id"] = df["id"].astype("int64")
    df["edad"] = df["edad"].astype("Int64")
    df["ingreso"] = df["ingreso"].astype("float64")
    df["gastos"] = df["gastos"].astype("float64")
    for column in ("genero", "ciudad", "estado", "tipocliente"):
        df[column] = df[column].astype("str")

    return df


def write_sample_csv(output: Path = DEFAULT_OUTPUT, seed: int = SEED) -> pd.DataFrame:
    """Genera el dataset y lo escribe en `output` (creando el directorio si hace falta)."""
    df = build_sample_dataframe(seed=seed)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    # `lineterminator="\n"` mantiene el archivo idéntico en cualquier sistema operativo.
    df.to_csv(output, index=False, encoding="utf-8", lineterminator="\n")
    return df


def main(argv: list[str] | None = None) -> int:
    """Punto de entrada del script de generación."""
    parser = argparse.ArgumentParser(
        description="Genera el dataset de ejemplo reproducible de DataClean.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Ruta del CSV a generar (por defecto: {DEFAULT_OUTPUT}).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=SEED,
        help=f"Semilla aleatoria (por defecto: {SEED}).",
    )
    args = parser.parse_args(argv)

    df = write_sample_csv(args.output, seed=args.seed)
    print(f"Dataset generado: {args.output} ({len(df)} filas, {df.shape[1]} columnas)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
