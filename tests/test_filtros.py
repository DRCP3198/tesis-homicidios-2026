"""
test_filtros.py — Tests para la Fase 3: Filtrado Temporal y Geográfico.

Verifica que:
1. La conversión de anio_hecho a entero funcione correctamente (Paso 3.1).
2. El filtro temporal excluya registros posteriores a 2024 (Paso 3.2).
3. La exclusión de Galápagos elimine los 4 cantones insulares (Paso 3.3).
4. Los registros insulares se separen correctamente (Paso 3.4).
5. El reporte de conteos valide la integridad de datos (Paso 3.5).
6. El ciclo Parquet guardar/cargar funcione (Paso 3.6).
7. NO existan registros > 2024 ni cantones insulares en el resultado (Paso 3.7).
"""
import pytest        # Framework de pruebas automatizadas.
import pandas as pd  # Manejo de DataFrames.

from src.ingesta.config import (
    ANIO_MAXIMO,
    CANTONES_GALAPAGOS,
    INTERIM_FILTRADO,
    INTERIM_NORMALIZADO,
)
from src.limpieza.filtros import (
    convertir_anio_a_entero,
    filtrar_anio,
    excluir_galapagos,
    guardar_intermedio_filtrado,
    cargar_intermedio_filtrado,
)
from src.reportes.reporte_control import imprimir_conteos


# =========================================================================
# FIXTURES: DataFrames simulados para pruebas unitarias
# =========================================================================
# `@pytest.fixture` define funciones que preparan datos de prueba reutilizables.
# Al estar fuera de las clases (a nivel de archivo), CUALQUIER clase de este
# archivo puede pedirlos simplemente poniendo su nombre como parámetro.
# Además, un fixture puede pedir a OTRO fixture (ver `df_convertido` y `df_filtrado_anio`),
# armando una cadena limpia paso por paso.
@pytest.fixture
def df_simulado() -> pd.DataFrame:
    """
    Crea un DataFrame de prueba que simula la estructura real con las
    21 columnas, incluyendo registros de distintos años y cantones
    insulares para validar todos los filtros.
    """
    # `["HOMICIDIO"] * 8` repite la lista 8 veces → ["HOMICIDIO", "HOMICIDIO", ...] (8 elementos).
    # `["URBANO", "RURAL"] * 4` → alterna URBANO, RURAL 4 veces = 8 elementos en total.
    return pd.DataFrame({
        # 13 columnas de texto
        "codigo_caso":          ["CASO-001", "CASO-002", "CASO-003", "CASO-004",
                                 "CASO-005", "CASO-006", "CASO-007", "CASO-008"],
        "tipo_delito":          ["HOMICIDIO"] * 8,
        "zona_tipo":            ["URBANO", "RURAL"] * 4,
        "lugar_especifico":     ["VIA PUBLICA"] * 8,
        "tipo_arma":            ["ARMA DE FUEGO"] * 8,
        "motivacion_detalle":   ["VIOLENCIA COMUNITARIA"] * 8,
        "causa_especifica":     ["VENGANZA"] * 8,
        "sexo_victima":         ["MASCULINO"] * 8,
        "nacionalidad_victima": ["ECUATORIANA"] * 8,
        # Incluye 2 cantones insulares (SANTA CRUZ, ISABELA) para probar la exclusión.
        "canton":               ["QUITO", "GUAYAQUIL", "CUENCA", "SANTA CRUZ",
                                 "ISABELA", "AMBATO", "LOJA", "QUITO"],
        "mes_hecho":            ["ENERO"] * 8,
        "dia_semana":           ["LUNES"] * 8,
        "provincia":            ["PICHINCHA", "GUAYAS", "AZUAY", "GALAPAGOS",
                                 "GALAPAGOS", "TUNGURAHUA", "LOJA", "PICHINCHA"],
        # 8 columnas no-texto (incluye 2 filas del año 2025 para probar el filtro temporal)
        "fecha_hecho":          ["2023-01-15", "2024-06-20", "2025-03-10",
                                 "2023-07-01", "2024-08-15", "2022-12-01",
                                 "2024-11-30", "2025-02-14"],
        "anio_hecho":           ["2023", "2024", "2025", "2023",
                                 "2024", "2022", "2024", "2025"],
        "hora_aproximada":      ["14", "22", "08", "16", "20", "11", "03", "19"],
        "edad_victima":         ["35", "28", "45", "31", "22", "50", "19", "40"],
        "latitud":              ["-0.1807", "-2.1894", "-2.8970", "-0.7453",
                                 "-0.9538", "-1.2491", "-3.9931", "-0.2200"],
        "longitud":             ["-78.4678", "-79.8891", "-79.0045", "-90.3116",
                                 "-90.9536", "-78.6168", "-79.2044", "-78.5124"],
        "AUX_HORA_SISTEMA":     ["14", "22", "08", "16", "20", "11", "03", "19"],
        "AUX_MINUTO_SISTEMA":   ["30", "45", "15", "00", "10", "55", "22", "38"],
    })


@pytest.fixture
def df_convertido(df_simulado: pd.DataFrame) -> pd.DataFrame:
    """DataFrame con anio_hecho ya convertido a entero (salida Paso 3.1)."""
    # Este fixture recibe `df_simulado` y le aplica el Paso 3.1 automáticamente.
    return convertir_anio_a_entero(df_simulado)


@pytest.fixture
def df_filtrado_anio(df_convertido: pd.DataFrame) -> pd.DataFrame:
    """DataFrame con filtro temporal aplicado (salida Paso 3.2)."""
    # Y este recibe `df_convertido` y le aplica el Paso 3.2 (quedando listo para el Paso 3.3).
    return filtrar_anio(df_convertido)


# =========================================================================
# TESTS: Paso 3.1 — Conversión de anio_hecho a entero
# =========================================================================
class TestConvertirAnioAEntero:
    """Tests para convertir_anio_a_entero() — Paso 3.1."""

    def test_tipo_resultante(self, df_simulado: pd.DataFrame):
        """Verifica que anio_hecho sea de tipo Int64 tras la conversión."""
        resultado = convertir_anio_a_entero(df_simulado)
        # Int64 (nullable integer) es el tipo esperado.
        # is_integer_dtype(...) devuelve True para cualquier tipo entero de pandas/numpy.
        assert pd.api.types.is_integer_dtype(resultado["anio_hecho"]), (
            f"Se esperaba tipo entero, se obtuvo: {resultado['anio_hecho'].dtype}"
        )

    def test_preserva_valores_validos(self, df_simulado: pd.DataFrame):
        """Verifica que los valores numéricos válidos se preserven."""
        resultado = convertir_anio_a_entero(df_simulado)
        anios_presentes = set(resultado["anio_hecho"].dropna().tolist())
        # `x in conjunto` → comprueba que el año esté presente.
        assert 2023 in anios_presentes
        assert 2024 in anios_presentes
        assert 2025 in anios_presentes

    def test_elimina_valores_no_numericos(self):
        """Verifica que valores no-numéricos se eliminen tras dropna()."""
        df = pd.DataFrame({
            "anio_hecho": ["2023", "ABC", "2024", None, "2025"],
            "canton": ["QUITO"] * 5,
        })
        resultado = convertir_anio_a_entero(df)
        # "ABC" y None deben haberse convertido en NaN y luego eliminado con dropna().
        assert len(resultado) == 3
        assert set(resultado["anio_hecho"].tolist()) == {2023, 2024, 2025}

    def test_error_columna_faltante(self):
        """Verifica que lance KeyError si falta la columna anio_hecho."""
        df = pd.DataFrame({"otra_columna": [1, 2, 3]})
        # Esperamos que la función lance KeyError cuyo mensaje mencione "anio_hecho".
        with pytest.raises(KeyError, match="anio_hecho"):
            convertir_anio_a_entero(df)

    def test_no_altera_otras_columnas(self, df_simulado: pd.DataFrame):
        """Verifica que las demás columnas no se modifiquen."""
        resultado = convertir_anio_a_entero(df_simulado)
        assert resultado.loc[0, "canton"] == "QUITO"
        assert resultado.loc[0, "latitud"] == "-0.1807"

    def test_preserva_conteo_sin_nulos(self, df_simulado: pd.DataFrame):
        """Con datos limpios (sin NaN en anio), no debe eliminar filas."""
        resultado = convertir_anio_a_entero(df_simulado)
        # Todos los valores en df_simulado son numéricos válidos → entran 8, salen 8.
        assert len(resultado) == len(df_simulado)


# =========================================================================
# TESTS: Paso 3.2 — Filtro temporal
# =========================================================================
class TestFiltrarAnio:
    """Tests para filtrar_anio() — Paso 3.2."""

    def test_excluye_2025(self, df_convertido: pd.DataFrame):
        """Verifica que NO existan registros con año > 2024."""
        resultado = filtrar_anio(df_convertido)
        # El valor máximo de la columna no puede superar ANIO_MAXIMO (2024).
        assert resultado["anio_hecho"].max() <= ANIO_MAXIMO, (
            f"Se encontraron registros con año > {ANIO_MAXIMO}: "
            f"máximo encontrado = {resultado['anio_hecho'].max()}"
        )

    def test_conserva_2024_y_anteriores(self, df_convertido: pd.DataFrame):
        """Verifica que se conserven registros de 2024 y años anteriores."""
        resultado = filtrar_anio(df_convertido)
        anios = set(resultado["anio_hecho"].tolist())
        # Importante: el filtro es `<= 2024` (no `< 2024`), así que 2024 SÍ debe quedarse.
        assert 2024 in anios, "Se perdieron registros de 2024"
        assert 2023 in anios, "Se perdieron registros de 2023"
        assert 2022 in anios, "Se perdieron registros de 2022"

    def test_no_registros_posteriores_a_2024(self, df_convertido: pd.DataFrame):
        """
        Paso 3.7 — Verificación crítica:
        Confirma que NINGÚN registro tenga anio_hecho > 2024.
        """
        resultado = filtrar_anio(df_convertido)
        registros_futuros = resultado.query("anio_hecho > 2024")
        assert len(registros_futuros) == 0, (
            f"FALLO CRÍTICO: Se encontraron {len(registros_futuros)} registros "
            f"con año > 2024. Años: {registros_futuros['anio_hecho'].unique()}"
        )

    def test_conteo_esperado(self, df_convertido: pd.DataFrame):
        """Verifica que se eliminen exactamente los registros de 2025."""
        # Contamos cuántos 2025 había antes y verificamos que falten exactamente esos.
        n_2025 = (df_convertido["anio_hecho"] == 2025).sum()
        resultado = filtrar_anio(df_convertido)
        assert len(resultado) == len(df_convertido) - n_2025

    def test_filtro_personalizado(self, df_convertido: pd.DataFrame):
        """Verifica que el parámetro 'hasta' funcione correctamente."""
        resultado = filtrar_anio(df_convertido, hasta=2023)
        assert resultado["anio_hecho"].max() <= 2023

    def test_error_columna_faltante(self):
        """Verifica que lance KeyError si falta anio_hecho."""
        df = pd.DataFrame({"otra_columna": [1, 2, 3]})
        with pytest.raises(KeyError, match="anio_hecho"):
            filtrar_anio(df)

    def test_error_tipo_no_numerico(self):
        """Verifica que lance ValueError si anio_hecho es string."""
        # Si alguien olvida llamar primero a convertir_anio_a_entero(), debe avisar con ValueError.
        df = pd.DataFrame({"anio_hecho": ["2023", "2024"]})
        with pytest.raises(ValueError, match="tipo numérico"):
            filtrar_anio(df)


# =========================================================================
# TESTS: Pasos 3.3 y 3.4 — Exclusión de Galápagos
# =========================================================================
class TestExcluirGalapagos:
    """Tests para excluir_galapagos() — Pasos 3.3 y 3.4."""

    def test_sin_cantones_insulares(self, df_filtrado_anio: pd.DataFrame):
        """
        Paso 3.7 — Verificación crítica:
        Confirma que NINGÚN cantón insular esté en el resultado continental.
        """
        # El "_" recibe el segundo valor devuelto (df_insular) cuando no lo vamos a usar
        # en esta prueba; es una convención estándar de Python ("variable descartable").
        df_continental, _ = excluir_galapagos(df_filtrado_anio)
        cantones_insulares_presentes = df_continental[
            df_continental["canton"].isin(CANTONES_GALAPAGOS)
        ]
        assert len(cantones_insulares_presentes) == 0, (
            f"FALLO CRÍTICO: Se encontraron {len(cantones_insulares_presentes)} "
            f"registros de cantones insulares en el resultado continental. "
            f"Cantones: {cantones_insulares_presentes['canton'].unique()}"
        )

    def test_insular_separado(self, df_filtrado_anio: pd.DataFrame):
        """Verifica que los registros insulares se aíslen correctamente."""
        _, df_insular = excluir_galapagos(df_filtrado_anio)
        if len(df_insular) > 0:
            # Todos los registros insulares deben ser de cantones de Galápagos
            # (ningún cantón continental se debe haber colado en df_insular).
            for canton in df_insular["canton"].unique():
                assert canton in CANTONES_GALAPAGOS, (
                    f"El cantón '{canton}' no es insular pero está en df_insular"
                )

    def test_suma_partes_igual_total(self, df_filtrado_anio: pd.DataFrame):
        """Verifica que continental + insular = total filtrado."""
        # Ley de conservación: nada desaparece al partir una tabla en dos.
        df_continental, df_insular = excluir_galapagos(df_filtrado_anio)
        total = len(df_continental) + len(df_insular)
        assert total == len(df_filtrado_anio), (
            f"continental ({len(df_continental)}) + insular ({len(df_insular)}) "
            f"= {total} != filtrado ({len(df_filtrado_anio)})"
        )

    def test_exclusion_personalizada(self, df_filtrado_anio: pd.DataFrame):
        """Verifica que se pueda excluir una lista personalizada de cantones."""
        custom_list = ["QUITO"]
        df_continental, df_insular = excluir_galapagos(
            df_filtrado_anio, cantones_insular=custom_list
        )
        # .values devuelve los valores como arreglo; `all(...)` verifica que TODOS sean True.
        assert "QUITO" not in df_continental["canton"].values
        assert all(df_insular["canton"] == "QUITO")

    def test_error_columna_faltante(self):
        """Verifica que lance KeyError si falta la columna canton."""
        df = pd.DataFrame({"otra_columna": [1, 2, 3]})
        with pytest.raises(KeyError, match="canton"):
            excluir_galapagos(df)

    def test_sin_insulares_en_datos(self):
        """Verifica comportamiento cuando no hay cantones insulares."""
        df = pd.DataFrame({
            "canton": ["QUITO", "GUAYAQUIL", "CUENCA"],
        })
        df_continental, df_insular = excluir_galapagos(df)
        assert len(df_continental) == 3
        assert len(df_insular) == 0


# =========================================================================
# TESTS: Paso 3.5 — Reporte de conteos
# =========================================================================
class TestReporteControl:
    """Tests para imprimir_conteos() — Paso 3.5."""

    def test_reporte_integridad(self, df_simulado: pd.DataFrame):
        """Verifica que el reporte detecte la integridad de los datos."""
        df_conv = convertir_anio_a_entero(df_simulado)
        df_anio = filtrar_anio(df_conv)
        df_cont, df_ins = excluir_galapagos(df_anio)

        reporte = imprimir_conteos(
            df_original=df_simulado,
            df_post_conversion=df_conv,
            df_post_filtro_anio=df_anio,
            df_continental=df_cont,
            df_insular=df_ins,
        )
        assert reporte.integridad_ok, (
            "La verificación de integridad falló: "
            f"la suma de partes no coincide con el original"
        )

    def test_conteos_correctos(self, df_simulado: pd.DataFrame):
        """Verifica que los conteos del reporte sean coherentes."""
        df_conv = convertir_anio_a_entero(df_simulado)
        df_anio = filtrar_anio(df_conv)
        df_cont, df_ins = excluir_galapagos(df_anio)

        reporte = imprimir_conteos(
            df_original=df_simulado,
            df_post_conversion=df_conv,
            df_post_filtro_anio=df_anio,
            df_continental=df_cont,
            df_insular=df_ins,
        )
        assert reporte.registros_originales == len(df_simulado)
        assert reporte.registros_continental == len(df_cont)
        assert reporte.registros_insular == len(df_ins)


# =========================================================================
# TESTS: Paso 3.7 — Validaciones Críticas sobre Datos Reales
# =========================================================================
class TestValidacionDatosReales:
    """
    Tests de integración que validan el resultado REAL del pipeline
    contra los datos del Parquet producido por la Fase 2.

    Estas pruebas cargan homi_normalizado.parquet, ejecutan el pipeline
    completo de Fase 3, y verifican las invariantes críticas.
    """

    @pytest.fixture
    def pipeline_fase3(self) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Ejecuta el pipeline completo de Fase 3 sobre datos reales."""
        # `pytest.skip(...)` salta la prueba (en vez de fallarla) si todavía
        # no se han generado los archivos de las fases previas.
        if not INTERIM_NORMALIZADO.exists():
            pytest.skip(
                f"No existe {INTERIM_NORMALIZADO}. "
                "Ejecuta primero las Fases 1 y 2."
            )
        df = pd.read_parquet(INTERIM_NORMALIZADO, engine="pyarrow")
        df = convertir_anio_a_entero(df)
        df = filtrar_anio(df)
        df_continental, df_insular = excluir_galapagos(df)
        return df_continental, df_insular

    def test_sin_registros_posteriores_2024_datos_reales(
        self, pipeline_fase3: tuple[pd.DataFrame, pd.DataFrame]
    ):
        """
        [CRÍTICO] Verifica sobre datos REALES que no existan
        registros con anio_hecho > 2024 en el dataset filtrado.
        """
        df_continental, _ = pipeline_fase3
        registros_futuros = df_continental.query("anio_hecho > 2024")
        assert len(registros_futuros) == 0, (
            f"FALLO CRÍTICO en datos reales: {len(registros_futuros)} "
            f"registros con año > 2024"
        )

    def test_sin_cantones_insulares_datos_reales(
        self, pipeline_fase3: tuple[pd.DataFrame, pd.DataFrame]
    ):
        """
        [CRÍTICO] Verifica sobre datos REALES que no existan
        cantones insulares en el dataset continental.
        """
        df_continental, _ = pipeline_fase3
        insulares_presentes = df_continental[
            df_continental["canton"].isin(CANTONES_GALAPAGOS)
        ]
        assert len(insulares_presentes) == 0, (
            f"FALLO CRÍTICO en datos reales: {len(insulares_presentes)} "
            f"registros insulares en el resultado continental"
        )

    def test_anio_hecho_es_entero_datos_reales(
        self, pipeline_fase3: tuple[pd.DataFrame, pd.DataFrame]
    ):
        """Verifica que anio_hecho sea de tipo entero en datos reales."""
        df_continental, _ = pipeline_fase3
        assert pd.api.types.is_integer_dtype(df_continental["anio_hecho"])

    def test_sin_nulos_en_anio_datos_reales(
        self, pipeline_fase3: tuple[pd.DataFrame, pd.DataFrame]
    ):
        """Verifica que no haya NaN en anio_hecho en datos reales."""
        df_continental, _ = pipeline_fase3
        assert df_continental["anio_hecho"].isna().sum() == 0
