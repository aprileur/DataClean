"""Pruebas del servicio de exportación (`app/services/exporter.py`).

Cubre: generación de rutas sin colisión (regla D8), exportación a CSV
(utf-8-sig), Excel y Parquet con relectura, errores de extensión no soportada
y la comprobación AST de que el módulo no importa Qt.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pandas as pd
import pytest

from app.services.exporter import (
    CSV_EXPORT_ENCODING,
    ExportError,
    export_dataset,
    generate_export_path,
)

SAMPLE_DF = pd.DataFrame(
    {
        "id": [1, 2, 3],
        "nombre": ["Ana", "Luis", "María"],
        "valor": [10.5, 20.0, 30.25],
    }
)


# ---------------------------------------------------------------------------
# generate_export_path
# ---------------------------------------------------------------------------


class TestGenerateExportPath:
    def test_sufijo_nuevo_basico(self, tmp_path: Path) -> None:
        """`datos.csv` con destino .csv sugiere `datos_nuevo.csv`."""
        source = tmp_path / "datos.csv"
        source.write_text("a\n1\n", encoding="utf-8")

        result = generate_export_path(source, ".csv")

        assert result == tmp_path / "datos_nuevo.csv"
        assert not result.exists()

    def test_extension_con_y_sin_punto(self, tmp_path: Path) -> None:
        source = tmp_path / "datos.csv"
        source.write_text("a\n1\n", encoding="utf-8")

        assert generate_export_path(source, "csv") == tmp_path / "datos_nuevo.csv"
        assert generate_export_path(source, ".CSV") == tmp_path / "datos_nuevo.csv"

    def test_cambio_de_formato(self, tmp_path: Path) -> None:
        """El origen puede ser .csv y el destino .xlsx."""
        source = tmp_path / "datos.csv"
        source.write_text("a\n1\n", encoding="utf-8")

        result = generate_export_path(source, ".xlsx")

        assert result == tmp_path / "datos_nuevo.xlsx"

    def test_colision_incrementa_sufijo(self, tmp_path: Path) -> None:
        """`_nuevo` ocupado → `_nuevo_2`; `_nuevo_2` ocupado → `_nuevo_3`."""
        source = tmp_path / "datos.csv"
        source.write_text("a\n1\n", encoding="utf-8")
        (tmp_path / "datos_nuevo.csv").write_text("x", encoding="utf-8")

        assert generate_export_path(source, ".csv") == tmp_path / "datos_nuevo_2.csv"

        (tmp_path / "datos_nuevo_2.csv").write_text("x", encoding="utf-8")
        assert generate_export_path(source, ".csv") == tmp_path / "datos_nuevo_3.csv"

    def test_nunca_sobrescribe_el_original(self, tmp_path: Path) -> None:
        """El resultado nunca coincide con el archivo de origen."""
        source = tmp_path / "datos.csv"
        source.write_text("a\n1\n", encoding="utf-8")

        result = generate_export_path(source, ".csv")

        assert result != source
        # El original no se tocó.
        assert source.read_text(encoding="utf-8") == "a\n1\n"

    def test_output_dir_distinto_del_origen(self, tmp_path: Path) -> None:
        source = tmp_path / "datos.csv"
        source.write_text("a\n1\n", encoding="utf-8")
        salida = tmp_path / "salida"
        salida.mkdir()

        result = generate_export_path(source, ".csv", output_dir=salida)

        assert result == salida / "datos_nuevo.csv"

    def test_output_dir_colisiona_dentro_de_su_carpeta(self, tmp_path: Path) -> None:
        source = tmp_path / "datos.csv"
        source.write_text("a\n1\n", encoding="utf-8")
        salida = tmp_path / "salida"
        salida.mkdir()
        (salida / "datos_nuevo.csv").write_text("x", encoding="utf-8")

        result = generate_export_path(source, ".csv", output_dir=salida)

        assert result == salida / "datos_nuevo_2.csv"

    def test_extension_no_soportada(self, tmp_path: Path) -> None:
        source = tmp_path / "datos.csv"
        source.write_text("a\n1\n", encoding="utf-8")

        for ext in (".txt", "json", ".docx"):
            with pytest.raises(ExportError, match="no soportado"):
                generate_export_path(source, ext)


# ---------------------------------------------------------------------------
# export_dataset
# ---------------------------------------------------------------------------


class TestExportCsv:
    def test_exporta_y_relee_mismos_datos(self, tmp_path: Path) -> None:
        target = tmp_path / "salida.csv"

        result = export_dataset(SAMPLE_DF, target)

        assert result == target.resolve()
        assert result.is_file()
        releido = pd.read_csv(result)
        pd.testing.assert_frame_equal(releido, SAMPLE_DF)

    def test_codificacion_utf8_sig_bom(self, tmp_path: Path) -> None:
        """El CSV exportado empieza con el BOM de utf-8-sig y acentos íntegros."""
        df = pd.DataFrame({"ciudad": ["Toluca", "México"]})
        target = tmp_path / "bom.csv"

        export_dataset(df, target)

        raw = target.read_bytes()
        assert raw.startswith(b"\xef\xbb\xbf")
        releido = pd.read_csv(target, encoding=CSV_EXPORT_ENCODING)
        assert list(releido["ciudad"]) == ["Toluca", "México"]

    def test_sin_indice_extra(self, tmp_path: Path) -> None:
        target = tmp_path / "idx.csv"
        export_dataset(SAMPLE_DF, target)
        assert list(pd.read_csv(target).columns) == list(SAMPLE_DF.columns)


class TestExportExcel:
    def test_exporta_y_relee_shape_y_datos(self, tmp_path: Path) -> None:
        target = tmp_path / "salida.xlsx"

        result = export_dataset(SAMPLE_DF, target)

        assert result == target.resolve()
        assert result.is_file()
        releido = pd.read_excel(result, engine="openpyxl")
        assert releido.shape == SAMPLE_DF.shape
        assert list(releido.columns) == list(SAMPLE_DF.columns)
        pd.testing.assert_frame_equal(releido, SAMPLE_DF)

    def test_dataframe_vacio_columnas(self, tmp_path: Path) -> None:
        df = pd.DataFrame(columns=["a", "b"])
        target = tmp_path / "vacio.xlsx"

        export_dataset(df, target)

        releido = pd.read_excel(target, engine="openpyxl")
        assert releido.shape == (0, 2)


class TestExportParquet:
    def test_exporta_y_relee_con_pyarrow(self, tmp_path: Path) -> None:
        target = tmp_path / "salida.parquet"

        result = export_dataset(SAMPLE_DF, target)

        assert result == target.resolve()
        assert result.is_file()
        releido = pd.read_parquet(result, engine="pyarrow")
        pd.testing.assert_frame_equal(releido, SAMPLE_DF)

    def test_lectura_directa_pyarrow(self, tmp_path: Path) -> None:
        import pyarrow.parquet as pq  # noqa: PLC0415

        target = tmp_path / "directo.parquet"
        export_dataset(SAMPLE_DF, target)

        table = pq.read_table(target)
        assert table.num_rows == 3
        assert table.column_names == list(SAMPLE_DF.columns)


class TestExportErrors:
    @pytest.mark.parametrize("nombre", ["salida.txt", "salida.json", "salida", "salida.docx"])
    def test_extension_no_soportada(self, tmp_path: Path, nombre: str) -> None:
        with pytest.raises(ExportError, match="no soportado"):
            export_dataset(SAMPLE_DF, tmp_path / nombre)

    def test_ruta_sin_permisos(self, tmp_path: Path) -> None:
        """Exportar sobre un directorio existente falla con mensaje amigable."""
        destino = tmp_path / "es_un_directorio.csv"
        destino.mkdir()

        with pytest.raises(ExportError, match="No se pudo exportar"):
            export_dataset(SAMPLE_DF, destino)

    def test_ruta_en_directorio_inexistente(self, tmp_path: Path) -> None:
        destino = tmp_path / "no-existe" / "salida.csv"

        with pytest.raises(ExportError, match="No se pudo exportar"):
            export_dataset(SAMPLE_DF, destino)


# ---------------------------------------------------------------------------
# Sin Qt (comprobación AST)
# ---------------------------------------------------------------------------


class TestNoQtImports:
    def test_exporter_no_importa_qt(self) -> None:
        """`app/services/exporter.py` debe ser lógica pura: sin imports de Qt."""
        source = Path(__file__).resolve().parents[1] / "app" / "services" / "exporter.py"
        tree = ast.parse(source.read_text(encoding="utf-8"))

        prohibidos = {"PySide6", "PyQt5", "PyQt6", "QtCore", "QtGui", "QtWidgets", "Qt"}
        for nodo in ast.walk(tree):
            if isinstance(nodo, ast.Import):
                for alias in nodo.names:
                    raiz = alias.name.split(".")[0]
                    assert raiz not in prohibidos, f"Import de Qt prohibido: {alias.name}"
            elif isinstance(nodo, ast.ImportFrom):
                raiz = (nodo.module or "").split(".")[0]
                assert raiz not in prohibidos, f"Import de Qt prohibido: {nodo.module}"
