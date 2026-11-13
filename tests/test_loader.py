"""Pruebas del servicio de carga de archivos (tarea T05)."""

from __future__ import annotations

import ast
import hashlib
import shutil
from pathlib import Path

import pandas as pd
import pytest

from app.services import loader as loader_module
from app.services.loader import (
    LoaderError,
    LoadResult,
    detect_encoding,
    detect_separator,
    list_sheets,
    load_file,
)

# Contenido que ningún separador candidato puede analizar: comilla sin cerrar.
CORRUPT_CSV_BYTES = b'a,b\n"sin cerrar,1\n2,3\n'
# Cabecera ZIP falsa: openpyxl no puede abrirla.
CORRUPT_XLSX_BYTES = b"PK\x03\x04esto no es un libro de Excel"
# Texto plano renombrado a .parquet: pyarrow no puede abrirlo.
CORRUPT_PARQUET_BYTES = b"esto no es un archivo parquet"


def _write_bytes(path: Path, content: bytes) -> Path:
    """Escribe `content` en `path` y devuelve la ruta."""
    path.write_bytes(content)
    return path


def _write_excel(path: Path, sheets: dict[str, pd.DataFrame]) -> Path:
    """Escribe un libro de Excel con una hoja por cada entrada de `sheets`."""
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        for sheet_name, frame in sheets.items():
            frame.to_excel(writer, sheet_name=sheet_name, index=False)
    return path


@pytest.fixture()
def two_sheet_excel(tmp_path: Path) -> Path:
    """Libro `.xlsx` con dos hojas de contenido distinto."""
    return _write_excel(
        tmp_path / "libro.xlsx",
        {
            "Primera": pd.DataFrame({"id": [1, 2, 3], "nombre": ["Ana", "Luis", "Eva"]}),
            "Segunda": pd.DataFrame({"clave": ["a", "b"], "valor": [10.5, 20.25]}),
        },
    )


# --------------------------------------------------------------------------- #
# CSV
# --------------------------------------------------------------------------- #


def test_load_sample_csv_returns_expected_result(sample_path: Path) -> None:
    """`sample.csv` se carga con su forma, codificación y separador esperados."""
    result = load_file(sample_path)

    assert isinstance(result, LoadResult)
    assert result.df.shape == (1000, 8)
    assert result.encoding == "utf-8"
    assert result.separator == ","
    assert result.sheet is None
    assert result.file_name == "sample.csv"


def test_load_csv_with_semicolon_and_latin1(tmp_path: Path) -> None:
    """Un CSV separado por `;` y codificado en latin-1 se detecta y se carga bien."""
    content = "id;nombre;ciudad\n1;José;México\n2;Ana;Lima\n"
    path = _write_bytes(tmp_path / "latino.csv", content.encode("latin-1"))

    result = load_file(path)

    assert result.encoding == "latin-1"
    assert result.separator == ";"
    assert list(result.df.columns) == ["id", "nombre", "ciudad"]
    assert result.df.loc[0, "nombre"] == "José"
    assert result.df.loc[0, "ciudad"] == "México"
    assert result.df.shape == (2, 3)


def test_load_csv_with_tab_separator(tmp_path: Path) -> None:
    """Un TSV se carga detectando el tabulador como separador."""
    content = "id\tnombre\tmonto\n1\tAna\t10.5\n2\tLuis\t20.25\n"
    path = _write_bytes(tmp_path / "datos.tsv.csv", content.encode("utf-8"))

    result = load_file(path)

    assert result.separator == "\t"
    assert list(result.df.columns) == ["id", "nombre", "monto"]
    assert result.df.shape == (2, 3)


def test_load_csv_with_pipe_separator(tmp_path: Path) -> None:
    """Un CSV separado por `|` también se carga correctamente."""
    content = "id|nombre\n1|Ana\n2|Luis\n3|Eva\n"
    path = _write_bytes(tmp_path / "pipes.csv", content.encode("utf-8"))

    result = load_file(path)

    assert result.separator == "|"
    assert result.df.shape == (3, 2)


def test_load_csv_with_utf8_bom_does_not_pollute_first_column(tmp_path: Path) -> None:
    """Un CSV con BOM se lee como `utf-8-sig` y la primera columna queda limpia."""
    content = "id,nombre\n1,José\n"
    path = _write_bytes(tmp_path / "bom.csv", content.encode("utf-8-sig"))

    result = load_file(path)

    assert result.encoding == "utf-8-sig"
    assert list(result.df.columns) == ["id", "nombre"]
    assert result.df.loc[0, "nombre"] == "José"


def test_load_single_column_csv_is_not_considered_empty(tmp_path: Path) -> None:
    """Un CSV de una sola columna es válido (no debe confundirse con vacío)."""
    path = _write_bytes(tmp_path / "una_columna.csv", b"nombre\nAna\nLuis\n")

    result = load_file(path)

    assert result.df.shape == (2, 1)
    assert list(result.df.columns) == ["nombre"]


def test_csv_without_rows_raises_loader_error(tmp_path: Path) -> None:
    """Un CSV solo con cabecera no aporta datos y se rechaza con mensaje claro."""
    path = _write_bytes(tmp_path / "solo_cabecera.csv", b"id,nombre\n")

    with pytest.raises(LoaderError) as excinfo:
        load_file(path)

    assert "no contiene datos" in str(excinfo.value)


def test_load_accepts_uppercase_extension(tmp_path: Path, sample_path: Path) -> None:
    """La extensión se evalúa sin distinguir mayúsculas."""
    target = tmp_path / "MAYUS.CSV"
    shutil.copyfile(sample_path, target)

    result = load_file(target)

    assert result.df.shape == (1000, 8)
    assert result.file_name == "MAYUS.CSV"


# --------------------------------------------------------------------------- #
# Detección de codificación y separador
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("content", "file_encoding", "expected"),
    [
        ("id,nombre\n1,Ana\n", "utf-8", "utf-8"),
        ("id,nombre\n1,José\n", "utf-8", "utf-8"),
        ("id;nombre\n1;José\n", "latin-1", "latin-1"),
        ("id;nombre\n1;México\n", "latin-1", "latin-1"),
    ],
)
def test_detect_encoding(tmp_path: Path, content: str, file_encoding: str, expected: str) -> None:
    """`detect_encoding` distingue UTF-8 de Latin-1 probando en orden."""
    path = _write_bytes(tmp_path / "codificado.csv", content.encode(file_encoding))

    assert detect_encoding(path) == expected


def test_detect_encoding_returns_utf8_sig_for_bom(tmp_path: Path) -> None:
    """Si el archivo empieza con BOM, se informa `utf-8-sig`."""
    path = _write_bytes(tmp_path / "bom.csv", "id,nombre\n".encode("utf-8-sig"))

    assert detect_encoding(path) == "utf-8-sig"


@pytest.mark.parametrize(
    ("sample", "expected"),
    [
        ("id,nombre\n1,Ana\n2,Luis\n", ","),
        ("id;nombre\n1;Ana\n2;Luis\n", ";"),
        ("id\tnombre\n1\tAna\n2\tLuis\n", "\t"),
        ("id|nombre\n1|Ana\n2|Luis\n", "|"),
        ('nombre,descripcion\nAna,"Lima, Peru"\nLuis,"Bogota, Colombia"\n', ","),
        ("nombre\nAna\nLuis\n", ","),
        ("", ","),
        ("   \n\n", ","),
    ],
)
def test_detect_separator(sample: str, expected: str) -> None:
    """`detect_separator` reconoce los delimitadores habituales y tiene respaldo."""
    assert detect_separator(sample) == expected


def test_detect_separator_falls_back_to_counting(tmp_path: Path) -> None:
    """Cuando `csv.Sniffer` falla, el conteo de delimitadores resuelve."""
    # Texto irregular (líneas de distinta longitud) que hace fallar a Sniffer.
    sample = "a;b;c\n1;2\n3;4;5;6\n"
    assert detect_separator(sample) == ";"


# --------------------------------------------------------------------------- #
# Excel
# --------------------------------------------------------------------------- #


def test_list_sheets_returns_workbook_sheets(two_sheet_excel: Path) -> None:
    """`list_sheets` devuelve los nombres de las hojas en orden."""
    assert list_sheets(two_sheet_excel) == ["Primera", "Segunda"]


def test_load_excel_defaults_to_first_sheet(two_sheet_excel: Path) -> None:
    """Sin `sheet`, se carga la primera hoja y se registra en el resultado."""
    result = load_file(two_sheet_excel)

    assert result.sheet == "Primera"
    assert result.encoding is None
    assert result.separator is None
    assert result.file_name == "libro.xlsx"
    assert list(result.df.columns) == ["id", "nombre"]
    assert result.df.shape == (3, 2)


def test_load_excel_specific_sheet(two_sheet_excel: Path) -> None:
    """Se puede pedir una hoja concreta por nombre."""
    result = load_file(two_sheet_excel, sheet="Segunda")

    assert result.sheet == "Segunda"
    assert list(result.df.columns) == ["clave", "valor"]
    assert result.df.shape == (2, 2)


def test_load_excel_missing_sheet_raises(two_sheet_excel: Path) -> None:
    """Pedir una hoja inexistente lanza `LoaderError` mencionando las disponibles."""
    with pytest.raises(LoaderError) as excinfo:
        load_file(two_sheet_excel, sheet="NoExiste")

    message = str(excinfo.value)
    assert "NoExiste" in message
    assert "Primera" in message
    assert "Segunda" in message


def test_list_sheets_rejects_non_excel_file(sample_path: Path) -> None:
    """`list_sheets` solo acepta libros de Excel."""
    with pytest.raises(LoaderError) as excinfo:
        list_sheets(sample_path)

    assert "Excel" in str(excinfo.value)


def test_list_sheets_missing_file_raises(tmp_path: Path) -> None:
    """`list_sheets` valida la existencia del archivo."""
    with pytest.raises(LoaderError) as excinfo:
        list_sheets(tmp_path / "no_existe.xlsx")

    assert "No se encontró" in str(excinfo.value)


def test_corrupt_excel_raises_loader_error(tmp_path: Path) -> None:
    """Un binario corrupto con extensión `.xlsx` lanza `LoaderError`, no `BadZipFile`."""
    path = _write_bytes(tmp_path / "corrupto.xlsx", CORRUPT_XLSX_BYTES)

    with pytest.raises(LoaderError) as excinfo:
        load_file(path)

    assert "Excel" in str(excinfo.value)


# --------------------------------------------------------------------------- #
# Parquet
# --------------------------------------------------------------------------- #


def test_load_parquet(tmp_path: Path) -> None:
    """Un Parquet se carga con pyarrow conservando tipos y datos."""
    frame = pd.DataFrame(
        {
            "id": [1, 2, 3],
            "monto": [10.5, 20.25, 30.125],
            "activo": [True, False, True],
        }
    )
    path = tmp_path / "datos.parquet"
    frame.to_parquet(path, engine="pyarrow")

    result = load_file(path)

    assert result.encoding is None
    assert result.separator is None
    assert result.sheet is None
    assert result.file_name == "datos.parquet"
    pd.testing.assert_frame_equal(result.df, frame)


def test_corrupt_parquet_raises_loader_error(tmp_path: Path) -> None:
    """Un archivo que no es Parquet lanza `LoaderError` con mensaje en español."""
    path = _write_bytes(tmp_path / "corrupto.parquet", CORRUPT_PARQUET_BYTES)

    with pytest.raises(LoaderError) as excinfo:
        load_file(path)

    assert "Parquet" in str(excinfo.value)


# --------------------------------------------------------------------------- #
# Errores
# --------------------------------------------------------------------------- #


def test_empty_file_raises_loader_error(tmp_path: Path) -> None:
    """Un archivo de 0 bytes lanza `LoaderError` con mensaje en español."""
    path = _write_bytes(tmp_path / "vacio.csv", b"")

    with pytest.raises(LoaderError) as excinfo:
        load_file(path)

    message = str(excinfo.value)
    assert "vacío" in message
    assert "0 bytes" in message


@pytest.mark.parametrize("file_name", ["notas.txt", "documento.pdf", "datos.json", "sin_extension"])
def test_unsupported_extension_raises_loader_error(tmp_path: Path, file_name: str) -> None:
    """Las extensiones no soportadas se rechazan antes de intentar leer."""
    path = _write_bytes(tmp_path / file_name, b"contenido cualquiera")

    with pytest.raises(LoaderError) as excinfo:
        load_file(path)

    assert "Formato no soportado" in str(excinfo.value)


def test_missing_file_raises_loader_error(tmp_path: Path) -> None:
    """Un archivo inexistente lanza `LoaderError` en español."""
    with pytest.raises(LoaderError) as excinfo:
        load_file(tmp_path / "fantasma.csv")

    assert "No se encontró" in str(excinfo.value)


def test_directory_path_raises_loader_error(tmp_path: Path) -> None:
    """Una ruta que es carpeta (no archivo) se rechaza con claridad."""
    folder = tmp_path / "carpeta.csv"
    folder.mkdir()

    with pytest.raises(LoaderError) as excinfo:
        load_file(folder)

    assert "no corresponde a un archivo" in str(excinfo.value)


def test_corrupt_csv_raises_loader_error(tmp_path: Path) -> None:
    """Un CSV con comillas sin cerrar no se puede analizar y lanza `LoaderError`."""
    path = _write_bytes(tmp_path / "corrupto.csv", CORRUPT_CSV_BYTES)

    with pytest.raises(LoaderError) as excinfo:
        load_file(path)

    assert "CSV" in str(excinfo.value)


def test_loader_error_is_an_exception_with_spanish_message(tmp_path: Path) -> None:
    """`LoaderError` es una excepción normal y su mensaje está en español."""
    assert issubclass(LoaderError, Exception)

    with pytest.raises(LoaderError) as excinfo:
        load_file(tmp_path / "inexistente.parquet")

    assert isinstance(excinfo.value, Exception)
    assert "No se encontró" in str(excinfo.value)


# --------------------------------------------------------------------------- #
# Independencia de los datos y ausencia de Qt
# --------------------------------------------------------------------------- #


def test_loaded_dataframe_is_independent_from_disk(sample_path: Path) -> None:
    """Modificar el DataFrame cargado no altera el archivo ni las cargas futuras."""
    before = hashlib.sha256(sample_path.read_bytes()).hexdigest()

    first = load_file(sample_path)
    first.df.loc[0, "edad"] = -999
    first.df = first.df.drop(columns=["id"])

    after = hashlib.sha256(sample_path.read_bytes()).hexdigest()
    assert after == before

    second = load_file(sample_path)
    pd.testing.assert_frame_equal(second.df, pd.read_csv(sample_path))
    assert "id" in second.df.columns
    assert second.df.loc[0, "edad"] == pd.read_csv(sample_path).loc[0, "edad"]


def test_load_result_dataframes_are_separate_objects(sample_path: Path) -> None:
    """Dos cargas devuelven DataFrames distintos en memoria."""
    first = load_file(sample_path)
    second = load_file(sample_path)

    assert first.df is not second.df
    pd.testing.assert_frame_equal(first.df, second.df)


def test_loader_module_does_not_import_qt() -> None:
    """`app/services/loader.py` no debe depender de Qt (lógica pura)."""
    source_path = Path(loader_module.__file__)
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source)

    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)

    forbidden_roots = {"PySide6", "PySide2", "PyQt5", "PyQt6", "shiboken6"}
    offenders = [name for name in imported if name.split(".")[0] in forbidden_roots]

    assert offenders == []
    assert "PySide6" not in source
    assert "PyQt" not in source
