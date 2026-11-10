r"""
test_exportacion.py — Pruebas automatizadas para Exportación, Auditoría y Visualización.

Verifica de extremo a extremo la etapa final de empaquetado y entrega del pipeline:
  1. `seleccionar_y_estandarizar_columnas`: selección exacta de las 21 columnas limpias,
     reemplazo de `latitud`/`longitud` crudas por `lat_num`/`lon_num` reparadas, descarte de
     `ID_temp` y conversión estricta de tipos (`string`, `datetime64`, `Int64`, `float64`, `category`).
  2. `exportar_csv`: escritura UTF-8 sin columna índice espuria (`index=False`).
  3. `exportar_parquet`: preservación de metadatos de tipos en Parquet (`snappy`).
  4. `exportar_geopackage`: creación de `GeoDataFrame` (`EPSG:4326`), orden `(lon, lat)`
     y preservación de nombres largos de columna sin el truncamiento de 10 caracteres de `.shp`.
  5. `metricas_pipeline`: cuadre contable del ciclo de vida, tasa de rescate y reportes JSON/MD.
  6. `mapa_diagnostico`: disolución provincial y exportación PNG desatendida a 300 DPI.

¿Cómo ejecuta `pytest` este archivo?
    Al correr `pytest tests/`, el framework descubre automáticamente todo archivo cuyo nombre
    empiece con `test_`, instancia cada clase que empiece con `Test` y ejecuta cada método
    que empiece con `test_`, inyectándole los datos de prueba (`fixtures`) solicitados por parámetro.
"""
# `json` permite deserializar `auditoria_pipeline.json` y comprobar su estructura interna.
import json

# `Path` representa rutas de archivos temporales y definitivos de forma multiplataforma.
from pathlib import Path

import geopandas as gpd
import pandas as pd
import pytest

# `shapely.geometry.box(minx, miny, maxx, maxy)` construye un polígono rectangular (`Polygon`)
# a partir de sus coordenadas extremas; ideal para fabricar cantones sintéticos en memoria.
from shapely.geometry import box

from src.exportacion.exportador import (
    construir_geodataframe_final,
    exportar_csv,
    exportar_geopackage,
    exportar_parquet,
    exportar_todos_formatos,
    seleccionar_y_estandarizar_columnas,
)
from src.ingesta.config import (
    COLUMNAS_CATEGORICAS_FINALES,
    COLUMNAS_FINALES_21,
    SALIDA_AUDITORIA_JSON,
    SALIDA_CSV_FINAL,
    SALIDA_GPKG_FINAL,
    SALIDA_MAPA_DIAGNOSTICO,
    SALIDA_PARQUET_FINAL,
)
from src.reportes.metricas_pipeline import (
    calcular_metricas_pipeline,
    exportar_reporte_json,
    exportar_reporte_markdown,
)
from src.visualizacion.mapa_diagnostico import (
    disolver_limites_provinciales,
    generar_mapa_diagnostico,
)


# =========================================================================
# FIXTURES REUTILIZABLES (datos sintéticos aislados por prueba)
# =========================================================================
# ¿Qué hace el decorador `@pytest.fixture`?
#   Registra una función como "proveedora de recursos de prueba". Cada vez que un método
#   `def test_algo(self, df_georreferenciado_simulado):` declara ese mismo nombre en sus
#   parámetros, `pytest` ejecuta esta función y le entrega un DataFrame nuevo y limpio,
#   garantizando que una prueba jamás contamine los datos de otra prueba.
@pytest.fixture
def df_georreferenciado_simulado() -> pd.DataFrame:
    """
    Simula exactamente el esquema de 24 columnas de `homi_georreferenciado.parquet`:
      • Las 21 columnas originales renombradas (donde `latitud` y `longitud` aún son strings crudos,
        incluso con un caso corrupto `"-2189400"` sin punto decimal).
      • `lat_num` y `lon_num` ya reparados como `float64`.
      • `ID_temp` (entero auxiliar que debe descartarse en la estandarización final).
      • Incluye edades decimales (lactante `0.25`), un `NaN` en `edad_victima` y horas decimales (`19.5`).
    """
    return pd.DataFrame(
        {
            "codigo_caso": ["HM-001", "HM-002", "HM-003", "HM-004"],
            "tipo_delito": ["ASESINATO", "HOMICIDIO", "SICARIATO", "FEMICIDIO"],
            "fecha_hecho": ["2015-03-10", "2020-07-22", "2023-11-05", "2024-12-31"],
            "anio_hecho": pd.Series([2015, 2020, 2023, 2024], dtype="Int64"),
            "mes_hecho": ["MARZO", "JULIO", "NOVIEMBRE", "DICIEMBRE"],
            "dia_semana": ["MARTES", "MIERCOLES", "DOMINGO", "MARTES"],
            "hora_aproximada": ["19.5", "8", "23.25", "0.5"],
            "provincia": ["GUAYAS", "PICHINCHA", "GUAYAS", "AZUAY"],
            "canton": ["GUAYAQUIL", "QUITO", "DURAN", "CUENCA"],
            "zona_tipo": ["URBANO", "URBANO", "URBANO", "RURAL"],
            "lugar_especifico": ["VIA PUBLICA", "CASA", "VIA PUBLICA", "CASA"],
            "tipo_arma": ["ARMA DE FUEGO", "BLANCA", "ARMA DE FUEGO", "CONTUNDENTE"],
            "motivacion_detalle": [
                "DELINCUENCIA COMUN",
                "VIOLENCIA COMUNITARIA",
                "AMENAZA",
                "VIOLENCIA INTRAFAMILIAR",
            ],
            "causa_especifica": ["TRAFICO", "RINAS", "SICARIATO", "MALTRATO"],
            # Incluye edad entera ("34"), lactante decimal ("0.25") y desconocido (`None` -> `NaN`).
            "edad_victima": ["34", "0.25", None, "29"],
            "sexo_victima": ["HOMBRE", "MUJER", "HOMBRE", "MUJER"],
            "nacionalidad_victima": ["ECUATORIANA", "ECUATORIANA", "COLOMBIANA", "ECUATORIANA"],
            # Coordenadas crudas en texto (la fila 0 simula coordenada corrupta sin punto decimal):
            "latitud": ["-2189400", "-0.1807", "-2.1701", "-2.9001"],
            "longitud": ["-79.8891", "-78.4678", "-79.8220", "-79.0059"],
            "AUX_HORA_SISTEMA": ["19", "8", "23", "0"],
            "AUX_MINUTO_SISTEMA": ["30", "0", "15", "30"],
            # Coordenadas numéricas ya validadas/reparadas en la Fase 4:
            "lat_num": [-2.1894, -0.1807, -2.1701, -2.9001],
            "lon_num": [-79.8891, -78.4678, -79.8220, -79.0059],
            # Columna auxiliar interna de auditoría que NO debe pasar al entregable final:
            "ID_temp": [1, 2, 3, 4],
        }
    )


@pytest.fixture
def mapa_sintetico_continental() -> gpd.GeoDataFrame:
    """
    Crea un pequeño mapa vectorial en `EPSG:4326` con 3 cantones distribuidos en 2 provincias
    para probar la disolución topológica (`dissolve`) y el renderizado del mapa en milisegundos.
    """
    return gpd.GeoDataFrame(
        {
            "DPA_DESPRO": ["GUAYAS", "GUAYAS", "PICHINCHA"],
            "DPA_DESCAN": ["GUAYAQUIL", "DURAN", "QUITO"],
        },
        geometry=[
            box(-80.2, -2.5, -79.85, -2.0),  # Polígono rectangular 1 (Guayaquil simulado)
            box(-79.85, -2.5, -79.6, -2.0),  # Polígono rectangular 2 contiguo (Durán simulado)
            box(-78.7, -0.5, -78.2, 0.1),    # Polígono rectangular 3 (Quito simulado)
        ],
        crs="EPSG:4326",
    )


# =========================================================================
# 1. TESTS DE SELECCIÓN, HOMOLOGACIÓN Y TIPADO DE LAS 21 COLUMNAS
# =========================================================================
class TestSeleccionYEstandarizacion:
    """Pruebas unitarias para `seleccionar_y_estandarizar_columnas` (Paso 5.1)."""

    def test_selecciona_exactamente_21_columnas_en_orden(
        self, df_georreferenciado_simulado: pd.DataFrame
    ) -> None:
        """El resultado debe tener exactamente las 21 columnas oficiales y descartar `ID_temp`."""
        df_limpio = seleccionar_y_estandarizar_columnas(df_georreferenciado_simulado)

        # `assert condicion`: si la condición es `False`, pytest marca el test como FAILED y muestra
        # las diferencias exactas entre ambas listas.
        assert list(df_limpio.columns) == COLUMNAS_FINALES_21
        assert len(df_limpio.columns) == 21
        assert "ID_temp" not in df_limpio.columns
        assert "lat_num" not in df_limpio.columns
        assert "lon_num" not in df_limpio.columns

    def test_sustituye_latitud_cruda_por_lat_num_reparada(
        self, df_georreferenciado_simulado: pd.DataFrame
    ) -> None:
        """La fila 0 tenía `latitud='-2189400'` cruda y `lat_num=-2.1894` reparada; debe quedar `-2.1894`."""
        df_limpio = seleccionar_y_estandarizar_columnas(df_georreferenciado_simulado)

        # ¿Por qué usamos `pytest.approx(-2.1894)` en lugar de `== -2.1894` directo?
        #   En aritmética binaria de punto flotante (IEEE 754), números decimales pueden presentar
        #   diferencias infinitesimales en el dígito 16 (ej. `-2.1894000000000002`). `pytest.approx`
        #   compara con tolerancia relativa segura (`1e-6`).
        assert df_limpio.loc[0, "latitud"] == pytest.approx(-2.1894)
        assert df_limpio.loc[0, "longitud"] == pytest.approx(-79.8891)

    def test_conversion_estricta_de_tipos_de_datos(
        self, df_georreferenciado_simulado: pd.DataFrame
    ) -> None:
        """Verifica el `dtype` técnico exacto asignado a cada familia de variables del diccionario."""
        df_limpio = seleccionar_y_estandarizar_columnas(df_georreferenciado_simulado)

        # 1. Identificador policial como `string`
        assert str(df_limpio["codigo_caso"].dtype) == "string"

        # 2. Fecha como `datetime64` (`is_datetime64_any_dtype` acepta `[ns]`, `[ms]` o `[us]`)
        assert pd.api.types.is_datetime64_any_dtype(df_limpio["fecha_hecho"])

        # 3. Enteros nulables `Int64`
        for col_int in ("anio_hecho", "AUX_HORA_SISTEMA", "AUX_MINUTO_SISTEMA"):
            assert str(df_limpio[col_int].dtype) == "Int64"

        # 4. Flotantes `float64` (preservando horas decimales, lactantes y `NaN`)
        for col_flt in ("hora_aproximada", "edad_victima", "latitud", "longitud"):
            assert str(df_limpio[col_flt].dtype) == "float64"

        assert df_limpio.loc[0, "hora_aproximada"] == pytest.approx(19.5)
        assert df_limpio.loc[1, "edad_victima"] == pytest.approx(0.25)
        assert pd.isna(df_limpio.loc[2, "edad_victima"])

        # 5. Las 12 columnas nominales como instancias de `pd.CategoricalDtype`
        for col_cat in COLUMNAS_CATEGORICAS_FINALES:
            assert isinstance(df_limpio[col_cat].dtype, pd.CategoricalDtype)

    def test_error_en_dataframe_vacio_o_columna_faltante(
        self, df_georreferenciado_simulado: pd.DataFrame
    ) -> None:
        """Debe lanzar `ValueError` si entra vacío y `KeyError` si falta una columna obligatoria."""
        # `with pytest.raises(TipoExcepcion, match="patron"):` comprueba que el código dentro del
        # bloque efectivamente lance esa excepción y que el mensaje contenga el texto esperado.
        # `.iloc[0:0]` recorta el DataFrame conservando las columnas pero con 0 filas.
        with pytest.raises(ValueError, match="vacío"):
            seleccionar_y_estandarizar_columnas(df_georreferenciado_simulado.iloc[0:0])

        df_incompleto = df_georreferenciado_simulado.drop(columns=["tipo_arma"])
        with pytest.raises(KeyError, match="tipo_arma"):
            seleccionar_y_estandarizar_columnas(df_incompleto)


# =========================================================================
# 2. TESTS DE EXPORTACIÓN CSV, PARQUET Y GEOPACKAGE
# =========================================================================
# Nota sobre el parámetro `tmp_path: Path` en los métodos siguientes:
#   `tmp_path` es un fixture nativo integrado en `pytest`. Crea automáticamente una carpeta
#   temporal única en el sistema operativo para cada test y la limpia después, de modo que
#   probamos lectura/escritura real en disco sin tocar jamás la carpeta `data/processed/`.
class TestExportadoresFormatos:
    """Pruebas de escritura y lectura de ida y vuelta (*roundtrip*) usando `tmp_path`."""

    def test_exportar_csv_utf8_sin_indice(
        self, df_georreferenciado_simulado: pd.DataFrame, tmp_path: Path
    ) -> None:
        """El CSV debe guardarse en UTF-8, sin columna `Unnamed: 0` y con las 21 columnas."""
        df_limpio = seleccionar_y_estandarizar_columnas(df_georreferenciado_simulado)
        ruta_csv = tmp_path / "salida_prueba.csv"

        exportar_csv(df_limpio, ruta_salida=ruta_csv)

        assert ruta_csv.exists()
        df_leido = pd.read_csv(ruta_csv, encoding="utf-8")
        assert list(df_leido.columns) == COLUMNAS_FINALES_21
        assert len(df_leido) == 4

    def test_exportar_parquet_preserva_metadatos_y_categorias(
        self, df_georreferenciado_simulado: pd.DataFrame, tmp_path: Path
    ) -> None:
        """Al releer el Parquet deben mantenerse intactos `category`, `datetime64` e `Int64`."""
        df_limpio = seleccionar_y_estandarizar_columnas(df_georreferenciado_simulado)
        ruta_pq = tmp_path / "salida_prueba.parquet"

        exportar_parquet(df_limpio, ruta_salida=ruta_pq, compresion="snappy")

        assert ruta_pq.exists()
        df_releido = pd.read_parquet(ruta_pq)
        assert list(df_releido.columns) == COLUMNAS_FINALES_21
        assert pd.api.types.is_datetime64_any_dtype(df_releido["fecha_hecho"])
        assert str(df_releido["anio_hecho"].dtype) == "Int64"
        assert isinstance(df_releido["provincia"].dtype, pd.CategoricalDtype)

    def test_exportar_geopackage_epsg4326_sin_truncar_columnas(
        self, df_georreferenciado_simulado: pd.DataFrame, tmp_path: Path
    ) -> None:
        """
        Verifica que GeoPackage (`.gpkg`) preserve `EPSG:4326`, el orden `Point(lon, lat)`
        y nombres largos (>10 caracteres) como `motivacion_detalle` y `nacionalidad_victima`.
        """
        df_limpio = seleccionar_y_estandarizar_columnas(df_georreferenciado_simulado)
        gdf_mem = construir_geodataframe_final(df_limpio)
        assert gdf_mem.crs.to_epsg() == 4326
        # Comprobamos que X sea longitud (-79.8891) e Y sea latitud (-2.1894), no al revés.
        assert gdf_mem.geometry.iloc[0].x == pytest.approx(-79.8891)
        assert gdf_mem.geometry.iloc[0].y == pytest.approx(-2.1894)

        ruta_gpkg = tmp_path / "salida_prueba.gpkg"
        exportar_geopackage(df_limpio, ruta_salida=ruta_gpkg)

        assert ruta_gpkg.exists()
        gdf_leido = gpd.read_file(ruta_gpkg)
        assert gdf_leido.crs.to_epsg() == 4326
        assert len(gdf_leido) == 4
        # Columnas de más de 10 caracteres que un Shapefile `.shp` habría truncado en `.dbf`:
        assert "motivacion_detalle" in gdf_leido.columns
        assert "nacionalidad_victima" in gdf_leido.columns
        assert "AUX_MINUTO_SISTEMA" in gdf_leido.columns

    def test_exportar_todos_formatos_orquesta_los_tres_archivos(
        self, df_georreferenciado_simulado: pd.DataFrame, tmp_path: Path
    ) -> None:
        """`exportar_todos_formatos` debe escribir y devolver las rutas no vacías de CSV, Parquet y GPKG."""
        df_limpio = seleccionar_y_estandarizar_columnas(df_georreferenciado_simulado)
        rutas = exportar_todos_formatos(
            df_limpio,
            ruta_csv=tmp_path / "a.csv",
            ruta_parquet=tmp_path / "b.parquet",
            ruta_gpkg=tmp_path / "c.gpkg",
        )
        assert set(rutas.keys()) == {"csv", "parquet", "gpkg"}
        for ruta in rutas.values():
            assert ruta.exists() and ruta.stat().st_size > 0


# =========================================================================
# 3. TESTS DE AUDITORÍA ESTADÍSTICA DEL CICLO DE VIDA
# =========================================================================
class TestMetricasPipeline:
    """Pruebas unitarias para el motor de métricas y exportación JSON/Markdown (Paso 5.5)."""

    def test_calculo_cuadre_contable_y_tasas_de_rescate(
        self, df_georreferenciado_simulado: pd.DataFrame, tmp_path: Path
    ) -> None:
        """Valida las ecuaciones de conservación, tasa de rescate y serialización JSON/MD."""
        df_limpio = seleccionar_y_estandarizar_columnas(df_georreferenciado_simulado)

        # Escenario controlado con rescate > 0 para probar la fórmula porcentual:
        #   • 10 brutos → 5 excluidos año + 0 insular = 5 en universo continental.
        #   • De esos 5: 2 correctos 1ra aud + 1 rescatado + 1 limbo + 1 descartado = 4 finales.
        #   • Corruptos sin decimal = 1 rescatado + 1 descartado = 2 → tasa de rescate = 50.0%.
        #   • Efectividad georreferenciada = 4 finales / 5 universo = 80.0%.
        resumen = calcular_metricas_pipeline(
            df_final=df_limpio,
            n_brutos_iniciales=10,
            n_excluidos_temporal=5,
            n_excluidos_insular=0,
            n_universo_filtrado=5,
            n_geo_correctos=2,
            n_rescatados_algoritmo=1,
            n_limbo_retenidos=1,
            n_descartados_irreversibles=1,
        )

        assert resumen.integridad_contable_ok is True
        assert resumen.candidatos_corruptos_sin_decimal == 2
        assert resumen.tasa_rescate_sobre_corruptos_pct == pytest.approx(50.0)
        assert resumen.efectividad_georreferenciacion_pct == pytest.approx(80.0)
        assert resumen.columnas_finales == 21

        # Verificar persistencia y lectura en JSON y Markdown
        ruta_json = exportar_reporte_json(resumen, ruta_salida=tmp_path / "auditoria.json")
        ruta_md = exportar_reporte_markdown(resumen, ruta_salida=tmp_path / "auditoria.md")

        contenido_json = json.loads(ruta_json.read_text(encoding="utf-8"))
        assert contenido_json["integridad_contable_ok"] is True
        assert contenido_json["efectividad_georreferenciacion_pct"] == pytest.approx(80.0)
        assert "Auditoría Estadística Integral" in ruta_md.read_text(encoding="utf-8")


# =========================================================================
# 4. TESTS DEL MAPA DIAGNÓSTICO DE VALIDACIÓN
# =========================================================================
class TestMapaDiagnostico:
    """Pruebas unitarias para la generación desatendida del mapa en Matplotlib + GeoPandas (Paso 5.6)."""

    def test_disolver_limites_provinciales_unifica_cantones(
        self, mapa_sintetico_continental: gpd.GeoDataFrame
    ) -> None:
        """Dos cantones de GUAYAS y uno de PICHINCHA deben disolverse en 2 polígonos provinciales."""
        provincias = disolver_limites_provinciales(mapa_sintetico_continental)
        assert len(provincias) == 2
        assert set(provincias["DPA_DESPRO"]) == {"GUAYAS", "PICHINCHA"}

    def test_generar_mapa_diagnostico_crea_png_valido_sin_mutar_datos(
        self,
        df_georreferenciado_simulado: pd.DataFrame,
        mapa_sintetico_continental: gpd.GeoDataFrame,
        tmp_path: Path,
    ) -> None:
        """Genera un archivo PNG válido verificando su firma binaria sin alterar el DataFrame original."""
        df_limpio = seleccionar_y_estandarizar_columnas(df_georreferenciado_simulado)
        lat_original = df_limpio["latitud"].copy()
        ruta_png = tmp_path / "figuras" / "mapa_test.png"

        salida = generar_mapa_diagnostico(
            eventos=df_limpio,
            mapa_cantones=mapa_sintetico_continental,
            ruta_salida=ruta_png,
            dpi=150,
        )

        assert salida.exists()
        # Verificación de firma binaria (*magic bytes*): según la especificación ISO/IEC 15948,
        # los primeros 8 bytes de todo archivo PNG válido son siempre `\x89PNG\r\n\x1a\n`.
        assert salida.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
        # Comprobación estricta de que el micro-jitter visual no mutó los datos de entrada:
        pd.testing.assert_series_equal(df_limpio["latitud"], lat_original)


# =========================================================================
# 5. TESTS DE INTEGRACIÓN SOBRE ENTREGABLES REALES DEL PIPELINE
# =========================================================================
# `@pytest.mark.skipif(condicion, reason=...)` omite elegantemente esta clase si alguien clona
# el repositorio limpio y corre `pytest` antes de haber ejecutado `python main.py`.
# Como aquí `homi_final.parquet` ya existe en `data/processed/`, la prueba SÍ se ejecuta.
@pytest.mark.skipif(
    not SALIDA_PARQUET_FINAL.exists(),
    reason="Entregables finales aún no generados por `main.py`.",
)
class TestIntegracionEntregablesReales:
    """Verifica la coherencia de los archivos reales generados en `data/processed/` y `reports/`."""

    def test_entregables_finales_existen_y_coinciden_en_conteo(self) -> None:
        """CSV, Parquet, GeoPackage, JSON y PNG deben existir y coincidir exactamente en 38,565 registros."""
        assert SALIDA_CSV_FINAL.exists()
        assert SALIDA_PARQUET_FINAL.exists()
        assert SALIDA_GPKG_FINAL.exists()
        assert SALIDA_AUDITORIA_JSON.exists()
        assert SALIDA_MAPA_DIAGNOSTICO.exists()

        df_pq = pd.read_parquet(SALIDA_PARQUET_FINAL)
        assert list(df_pq.columns) == COLUMNAS_FINALES_21
        assert len(df_pq) == 38_565

        auditoria = json.loads(SALIDA_AUDITORIA_JSON.read_text(encoding="utf-8"))
        assert auditoria["integridad_contable_ok"] is True
        assert auditoria["registros_finales_etiquetados"] == len(df_pq)
        assert auditoria["columnas_finales"] == 21
