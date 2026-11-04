"""
test_ingesta.py — Tests para la Fase 1: Ingesta y Renombrado.

Verifica que:
1. El CSV se lee correctamente.
2. Todas las columnas se renombran según MAPEO_COLUMNAS.
3. No se pierden registros en la carga.
4. El formato Parquet intermedio se guarda y carga correctamente.
"""
import pytest
import pandas as pd
from pathlib import Path

from src.ingesta.config import (
    ARCHIVO_HOMICIDIOS_CSV,
    MAPEO_COLUMNAS,
    INTERIM_RENOMBRADO,
)
from src.ingesta.cargar_datos import (
    cargar_homicidios_raw,
    guardar_intermedio_renombrado,
    cargar_intermedio_renombrado,
)


class TestCargarDatos:
    """Tests de la función cargar_homicidios_raw()."""

    def test_csv_existe(self):
        """Verifica que el archivo CSV fuente existe."""
        assert ARCHIVO_HOMICIDIOS_CSV.exists(), (
            f"No se encontró el CSV fuente: {ARCHIVO_HOMICIDIOS_CSV}"
        )

    def test_carga_exitosa(self):
        """Verifica que la carga no lance errores y devuelva un DataFrame."""
        df = cargar_homicidios_raw()
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0, "El DataFrame está vacío"

    def test_columnas_renombradas(self):
        """Verifica que TODAS las columnas del mapeo estén presentes."""
        df = cargar_homicidios_raw()
        columnas_esperadas = set(MAPEO_COLUMNAS.values())
        columnas_obtenidas = set(df.columns)
        assert columnas_esperadas == columnas_obtenidas, (
            f"Columnas faltantes: {columnas_esperadas - columnas_obtenidas}\n"
            f"Columnas extra: {columnas_obtenidas - columnas_esperadas}"
        )

    def test_21_columnas(self):
        """Verifica que el DataFrame tenga exactamente 21 columnas."""
        df = cargar_homicidios_raw()
        assert len(df.columns) == 21, f"Se esperaban 21 columnas, se obtuvieron {len(df.columns)}"

    def test_sin_columnas_originales(self):
        """Verifica que no queden columnas con nombres originales (X2, X4, etc.)."""
        df = cargar_homicidios_raw()
        columnas_crudas = [c for c in df.columns if c.startswith("X") and c[1:].isdigit()]
        assert len(columnas_crudas) == 0, (
            f"Columnas sin renombrar encontradas: {columnas_crudas}"
        )


class TestGuardarIntermedio:
    """Tests del ciclo guardar/cargar Parquet."""

    def test_guardar_y_cargar_parquet(self):
        """Verifica que el ciclo Parquet preserve los datos."""
        df_original = cargar_homicidios_raw()
        guardar_intermedio_renombrado(df_original)

        assert INTERIM_RENOMBRADO.exists(), "El archivo Parquet no se creó"

        df_cargado = cargar_intermedio_renombrado()
        assert df_original.shape == df_cargado.shape, (
            f"Forma original {df_original.shape} != cargada {df_cargado.shape}"
        )
        assert list(df_original.columns) == list(df_cargado.columns), (
            "Las columnas no coinciden entre original y cargado"
        )


class TestUtilTexto:
    """Tests para las funciones utilitarias de texto."""

    def test_normalizar_texto(self):
        from src.utils.texto import normalizar_texto

        assert normalizar_texto("  Guayaquíl  ") == "GUAYAQUIL"
        assert normalizar_texto("SANTO DOMINGO DE LOS TSÁCHILAS") == "SANTO DOMINGO DE LOS TSACHILAS"
        assert normalizar_texto("Ñuño") == "NUNO"
        assert normalizar_texto("  quito  ") == "QUITO"

    def test_contiene_caracteres_especiales(self):
        from src.utils.texto import contiene_caracteres_especiales

        assert contiene_caracteres_especiales("Guayaquíl") is True
        assert contiene_caracteres_especiales("GUAYAQUIL") is False
        assert contiene_caracteres_especiales("Ñuño") is True

