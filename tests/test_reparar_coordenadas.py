"""
test_reparar_coordenadas.py — Tests unitarios para la Fase 4: Validación Geoespacial.

Verifica que:
1. Las funciones de reconstrucción decimal produzcan cadenas con el formato
   correcto para los 4 escenarios (Paso 4.9).
2. El algoritmo reparador recupera registros con coordenadas corruptas
   usando coordenadas sintéticas conocidas dentro de cantones ecuatorianos.
3. La auditoría topológica (sjoin) clasifica correctamente correctos vs. a corregir.
4. El ensamblaje final preserva la integridad de los datos.

Estrategia de test con coordenadas sintéticas:
    Se usan cantones reales de Ecuador con coordenadas centroide conocidas,
    luego se "corrompe" la latitud eliminando el punto decimal para simular
    el error de digitación, y se verifica que el algoritmo la repare.
"""
import pandas as pd
import pytest

from src.limpieza.filtros import (
    cargar_intermedio_filtrado,
)
from src.validacion_geo.cartografia import cargar_mapa_cantonal
from src.validacion_geo.ensamblaje import ensamblar_base_final
from src.validacion_geo.geometrias import (
    auditar_punto_en_poligono,
    crear_geodataframe_puntos,
    separar_por_formato,
)
from src.validacion_geo.reparacion import (
    _limpiar_cadena_lat,
    reparar_coordenadas_corruptas,
    reconstruir_escenario_1,
    reconstruir_escenario_2,
    reconstruir_escenario_3,
    reconstruir_escenario_4,
    validar_reconstruccion_sjoin,
)


# =========================================================================
# FIXTURE: Mapa cantonal (cargado una sola vez por sesión de test)
# =========================================================================
@pytest.fixture(scope="module")
def mapa_cantonal():
    """Carga el mapa cantonal una sola vez para todos los tests del módulo."""
    try:
        return cargar_mapa_cantonal()
    except FileNotFoundError:
        pytest.skip("Shapefile no disponible. Verifica data/raw/cartografia/")


# =========================================================================
# DATOS SINTÉTICOS: Coordenadas centroide conocidas de cantones ecuatorianos
# =========================================================================
# Estos puntos fueron validados manualmente para garantizar que caen
# DENTRO de sus cantones respectivos en el shapefile nxcantones.shp.
# La latitud se representa como CADENA sin punto para simular el error.
#
# Tabla de referencia:
# Cantón         | Lat real   | Lon real    | Lat corrupta (sin punto)
# QUITO          |  -0.1807   | -78.4678    | "01807"  → neg ecuatorial
# GUAYAQUIL      |  -2.1894   | -79.8891    | "21894"  → neg sur
# CUENCA         |  -2.8970   | -79.0045    | "28970"  → neg sur
# IBARRA         |   0.3516   | -78.1223    | "3516"   → pos norte
# ESMERALDAS     |   0.9592   | -79.6536    | "09592"  → pos ecuatorial


# Registros base del DataFrame de prueba (21 columnas como en el pipeline real)
_COLUMNAS_SCHEMA = [
    "codigo_caso", "tipo_delito", "fecha_hecho", "anio_hecho", "mes_hecho",
    "dia_semana", "hora_aproximada", "provincia", "canton", "zona_tipo",
    "lugar_especifico", "tipo_arma", "motivacion_detalle", "causa_especifica",
    "edad_victima", "sexo_victima", "nacionalidad_victima",
    "latitud", "longitud", "AUX_HORA_SISTEMA", "AUX_MINUTO_SISTEMA",
]


def _crear_df_sintetico(
    canton: str,
    lat_str: str,
    lon_str: str,
    lat_num: float,
    lon_num: float,
) -> pd.DataFrame:
    """Crea un DataFrame sintético de un registro para testing."""
    return pd.DataFrame([{
        "codigo_caso": "TEST-001",
        "tipo_delito": "HOMICIDIO",
        "fecha_hecho": "2023-01-15",
        "anio_hecho": 2023,
        "mes_hecho": "ENERO",
        "dia_semana": "LUNES",
        "hora_aproximada": "14",
        "provincia": "TEST",
        "canton": canton,
        "zona_tipo": "URBANO",
        "lugar_especifico": "VIA PUBLICA",
        "tipo_arma": "FUEGO",
        "motivacion_detalle": "OTRO",
        "causa_especifica": "OTRO",
        "edad_victima": "35",
        "sexo_victima": "HOMBRE",
        "nacionalidad_victima": "ECUATORIANA",
        "latitud": lat_str,
        "longitud": lon_str,
        "AUX_HORA_SISTEMA": "14",
        "AUX_MINUTO_SISTEMA": "30",
        # Campos internos del pipeline
        "latitud_original": lat_str,
        "longitud_original": lon_str,
        "lat_num": lat_num,
        "lon_num": lon_num,
        "ID_temp": 1,
    }])


# =========================================================================
# TESTS UNITARIOS: Funciones de reconstrucción decimal (puras)
# =========================================================================
class TestReconstruccionEscenario1:
    """Tests del Escenario 1: X.XXXXXX (latitud positiva norte)."""

    def test_formato_basico(self):
        """Verifica la inserción de punto decimal en formato X.XXXXXX."""
        s = pd.Series(["136965"])     # Ibarra: 1.36965
        resultado = reconstruir_escenario_1(s)
        assert resultado.iloc[0] == "1.36965"

    def test_multiples_valores(self):
        """Verifica la reconstrucción de múltiples registros."""
        s = pd.Series(["3516", "9592", "123456"])
        resultado = reconstruir_escenario_1(s)
        assert resultado.iloc[0] == "3.516"
        assert resultado.iloc[1] == "9.592"
        assert resultado.iloc[2] == "1.23456"

    def test_cadena_corta(self):
        """Verifica comportamiento con cadena de un solo dígito."""
        s = pd.Series(["1"])
        resultado = reconstruir_escenario_1(s)
        assert resultado.iloc[0] == "1."

    def test_resultado_es_string(self):
        """Verifica que el resultado sea una Serie de strings."""
        s = pd.Series(["123456"])
        resultado = reconstruir_escenario_1(s)
        assert resultado.dtype == object  # dtype string en pandas


class TestReconstruccionEscenario2:
    """Tests del Escenario 2: 0.XXXXXX (positivo cerca del ecuador)."""

    def test_formato_basico(self):
        """Verifica la inserción de '0.' como prefijo."""
        s = pd.Series(["9592"])     # Esmeraldas: 0.9592
        resultado = reconstruir_escenario_2(s)
        assert resultado.iloc[0] == "0.9592"

    def test_quito_norte_ecuatorial(self):
        """Verifica coordenada positiva muy cercana al ecuador."""
        s = pd.Series(["01807"])    # +0.01807 cerca de la línea
        resultado = reconstruir_escenario_2(s)
        assert resultado.iloc[0] == "0.01807"

    def test_multiples_valores(self):
        """Verifica múltiples registros simultáneamente."""
        s = pd.Series(["5000", "1234"])
        resultado = reconstruir_escenario_2(s)
        assert resultado.iloc[0] == "0.5000"
        assert resultado.iloc[1] == "0.1234"


class TestReconstruccionEscenario3:
    """Tests del Escenario 3: -X.XXXXXX (latitud negativa sur) ← CRÍTICO."""

    def test_guayaquil(self):
        """Verifica la reconstrucción para Guayaquil (-2.1894)."""
        s = pd.Series(["21894"])
        resultado = reconstruir_escenario_3(s)
        assert resultado.iloc[0] == "-2.1894"

    def test_cuenca(self):
        """Verifica la reconstrucción para Cuenca (-2.8970)."""
        s = pd.Series(["28970"])
        resultado = reconstruir_escenario_3(s)
        assert resultado.iloc[0] == "-2.8970"

    def test_inserta_signo_negativo(self):
        """Verifica que el signo negativo se inserte correctamente."""
        s = pd.Series(["123456"])
        resultado = reconstruir_escenario_3(s)
        assert resultado.iloc[0].startswith("-")
        assert "." in resultado.iloc[0]

    def test_formato_completo(self):
        """Verifica la estructura completa '-X.XXXXXX'."""
        s = pd.Series(["497407"])
        resultado = reconstruir_escenario_3(s)
        assert resultado.iloc[0] == "-4.97407"

    def test_multiples_valores(self):
        """Verifica múltiples registros del hemisferio sur."""
        s = pd.Series(["28278", "901871", "890014"])
        resultado = reconstruir_escenario_3(s)
        assert resultado.iloc[0] == "-2.8278"
        assert resultado.iloc[1] == "-9.01871"
        assert resultado.iloc[2] == "-8.90014"


class TestReconstruccionEscenario4:
    """Tests del Escenario 4: -0.XXXXXX (negativo cercano al ecuador)."""

    def test_quito_sur_ecuatorial(self):
        """Verifica la reconstrucción para cantones cerca de Quito sur."""
        s = pd.Series(["1807"])     # -0.1807 aproximado
        resultado = reconstruir_escenario_4(s)
        assert resultado.iloc[0] == "-0.1807"

    def test_inserta_prefijo_negativo(self):
        """Verifica que '-0.' se inserte como prefijo."""
        s = pd.Series(["2345"])
        resultado = reconstruir_escenario_4(s)
        assert resultado.iloc[0] == "-0.2345"

    def test_multiples_valores(self):
        """Verifica múltiples registros negativos ecuatoriales."""
        s = pd.Series(["5000", "9999"])
        resultado = reconstruir_escenario_4(s)
        assert resultado.iloc[0] == "-0.5000"
        assert resultado.iloc[1] == "-0.9999"


# =========================================================================
# TESTS UNITARIOS: Función de limpieza de cadena
# =========================================================================
class TestLimpiarCadenaLat:
    """Tests para _limpiar_cadena_lat()."""

    def test_elimina_punto(self):
        """Verifica la eliminación del punto decimal."""
        s = pd.Series(["-2.1894"])
        resultado = _limpiar_cadena_lat(s)
        assert resultado.iloc[0] == "21894"

    def test_elimina_signo_negativo(self):
        """Verifica la eliminación del signo negativo."""
        s = pd.Series(["-2.8970"])
        resultado = _limpiar_cadena_lat(s)
        assert resultado.iloc[0] == "28970"

    def test_positivo_sin_signos(self):
        """Verifica que positivos sin punto queden como están."""
        s = pd.Series(["136965"])
        resultado = _limpiar_cadena_lat(s)
        assert resultado.iloc[0] == "136965"

    def test_multiple_puntos(self):
        """Verifica limpieza de cadenas con múltiples puntos."""
        s = pd.Series(["2.18.94"])
        resultado = _limpiar_cadena_lat(s)
        assert "." not in resultado.iloc[0]


# =========================================================================
# TESTS DE INTEGRACIÓN: Escenarios con mapa real
# =========================================================================
class TestValidacionSjoin:
    """Tests de validar_reconstruccion_sjoin() con datos reales."""

    def test_escenario3_guayaquil(self, mapa_cantonal):
        """
        [CRÍTICO] Verifica que el Escenario 3 repara la latitud de Guayaquil.

        Coordenada real: lat=-2.1894, lon=-79.8891
        Latitud corrupta: "21894" (sin punto ni signo)
        Latitud reconstruida: "-2.1894"
        """
        df_prueba = _crear_df_sintetico(
            canton="GUAYAQUIL",
            lat_str="21894",
            lon_str="-79.8891",
            lat_num=-2.1894,
            lon_num=-79.8891,
        )
        # Limpiar la cadena como lo hace el pipeline
        df_prueba["limpia_lat"] = _limpiar_cadena_lat(pd.Series(["21894"]))

        lat_reconstruida = reconstruir_escenario_3(df_prueba["limpia_lat"])
        ids_rescatados = validar_reconstruccion_sjoin(df_prueba, lat_reconstruida, mapa_cantonal)
        assert 1 in ids_rescatados, (
            "FALLO CRÍTICO: El Escenario 3 no pudo reparar la latitud de GUAYAQUIL. "
            f"lat_reconstruida='{lat_reconstruida.iloc[0]}'"
        )

    def test_escenario3_cuenca(self, mapa_cantonal):
        """Verifica que el Escenario 3 repara la latitud de Cuenca."""
        df_prueba = _crear_df_sintetico(
            canton="CUENCA",
            lat_str="28970",
            lon_str="-79.0045",
            lat_num=-2.8970,
            lon_num=-79.0045,
        )
        df_prueba["limpia_lat"] = _limpiar_cadena_lat(pd.Series(["28970"]))
        lat_rec = reconstruir_escenario_3(df_prueba["limpia_lat"])
        ids = validar_reconstruccion_sjoin(df_prueba, lat_rec, mapa_cantonal)
        assert 1 in ids, (
            f"El Escenario 3 no reparó CUENCA. lat='{lat_rec.iloc[0]}'"
        )

    def test_escenario4_quito(self, mapa_cantonal):
        """Verifica que el Escenario 4 repara latitud de QUITO (negativo ecuatorial)."""
        # Quito está a ~-0.1807 lat
        df_prueba = _crear_df_sintetico(
            canton="QUITO",
            lat_str="1807",
            lon_str="-78.4678",
            lat_num=-0.1807,
            lon_num=-78.4678,
        )
        df_prueba["limpia_lat"] = _limpiar_cadena_lat(pd.Series(["1807"]))
        lat_rec = reconstruir_escenario_4(df_prueba["limpia_lat"])
        ids = validar_reconstruccion_sjoin(df_prueba, lat_rec, mapa_cantonal)
        assert 1 in ids, (
            f"El Escenario 4 no reparó QUITO. lat='{lat_rec.iloc[0]}'"
        )

    def test_canton_incorrecto_no_rescata(self, mapa_cantonal):
        """
        Verifica que un punto en cantón erróneo NO se rescata.
        Coordenada de Guayaquil reportada como QUITO → no debe validar.
        """
        df_prueba = _crear_df_sintetico(
            canton="QUITO",          # Canton incorrecto para estas coords
            lat_str="21894",
            lon_str="-79.8891",
            lat_num=-2.1894,
            lon_num=-79.8891,
        )
        df_prueba["limpia_lat"] = _limpiar_cadena_lat(pd.Series(["21894"]))
        lat_rec = reconstruir_escenario_3(df_prueba["limpia_lat"])
        ids = validar_reconstruccion_sjoin(df_prueba, lat_rec, mapa_cantonal)
        assert 1 not in ids, (
            "Un punto de GUAYAQUIL con cantón='QUITO' no debería rescatarse."
        )


# =========================================================================
# TESTS DE INTEGRACIÓN: Pipeline completo de reparación
# =========================================================================
class TestReparacionCompleta:
    """Tests del orquestador reparar_coordenadas_corruptas()."""

    def _make_pool_corruptos(self) -> pd.DataFrame:
        """Crea un pool de registros con coordenadas corruptas (sin punto)."""
        rows = [
            # Escenario 3: negativo sur
            {
                "canton": "GUAYAQUIL", "latitud_original": "21894",
                "longitud_original": "-79.8891", "lat_num": -2.1894,
                "lon_num": -79.8891, "ID_temp": 1,
            },
            {
                "canton": "CUENCA", "latitud_original": "28970",
                "longitud_original": "-79.0045", "lat_num": -2.8970,
                "lon_num": -79.0045, "ID_temp": 2,
            },
            # Escenario 4: negativo ecuatorial
            {
                "canton": "QUITO", "latitud_original": "1807",
                "longitud_original": "-78.4678", "lat_num": -0.1807,
                "lon_num": -78.4678, "ID_temp": 3,
            },
        ]
        df = pd.DataFrame(rows)
        # Agregar campos textuales mínimos
        for col in ["codigo_caso", "tipo_delito", "provincia"]:
            df[col] = "TEST"
        df["limpia_lat"] = _limpiar_cadena_lat(df["latitud_original"])
        return df

    def test_rescata_registros_corruptos(self, mapa_cantonal):
        """Verifica que el orquestador rescata al menos un registro corrupto."""
        df_corruptos = self._make_pool_corruptos()
        esc1, esc2, esc3, esc4, no_rep = reparar_coordenadas_corruptas(
            df_corruptos, mapa_cantonal
        )
        total_rescatados = sum(len(d) for d in [esc1, esc2, esc3, esc4])
        assert total_rescatados > 0, (
            "El algoritmo no rescató ningún registro corrupto."
        )

    def test_escenario3_domina_sur(self, mapa_cantonal):
        """Verifica que el Escenario 3 rescata registros del hemisferio sur."""
        df_corruptos = self._make_pool_corruptos()
        esc1, esc2, esc3, esc4, no_rep = reparar_coordenadas_corruptas(
            df_corruptos, mapa_cantonal
        )
        # Guayaquil y Cuenca son del Hemisferio Sur → deben estar en esc3
        ids_esc3 = set(esc3["ID_temp"].tolist()) if len(esc3) > 0 else set()
        assert len(ids_esc3) > 0, (
            "El Escenario 3 (negativo sur) no rescató ningún registro. "
            "Es el escenario más crítico para Ecuador."
        )

    def test_no_duplicados_entre_escenarios(self, mapa_cantonal):
        """Verifica que un mismo ID_temp no aparezca en dos escenarios."""
        df_corruptos = self._make_pool_corruptos()
        esc1, esc2, esc3, esc4, _ = reparar_coordenadas_corruptas(
            df_corruptos, mapa_cantonal
        )
        todos_ids = []
        for df_esc in [esc1, esc2, esc3, esc4]:
            if len(df_esc) > 0:
                todos_ids.extend(df_esc["ID_temp"].tolist())
        assert len(todos_ids) == len(set(todos_ids)), (
            "Se encontraron ID_temp duplicados entre escenarios. "
            "Un registro fue rescatado por más de un escenario."
        )

    def test_dataset_vacio_sin_error(self, mapa_cantonal):
        """Verifica que un dataset vacío no lance errores."""
        df_vacio = pd.DataFrame(columns=[
            "canton", "latitud_original", "lon_num",
            "lat_num", "ID_temp", "limpia_lat",
        ])
        esc1, esc2, esc3, esc4, no_rep = reparar_coordenadas_corruptas(
            df_vacio, mapa_cantonal
        )
        for df_esc in [esc1, esc2, esc3, esc4, no_rep]:
            assert len(df_esc) == 0


# =========================================================================
# TESTS: Separación por formato (Paso 4.5)
# =========================================================================
class TestSepararPorFormato:
    """Tests de separar_por_formato()."""

    def test_con_punto_va_al_limbo(self):
        """Registros con punto decimal van a limbo_formato_correcto."""
        df = pd.DataFrame({
            "latitud_original": ["-2.1894", "-0.1807", "1.3696"],
            "canton": ["GUAYAQUIL", "QUITO", "IBARRA"],
        })
        limbo, decimales = separar_por_formato(df)
        assert len(limbo) == 3
        assert len(decimales) == 0

    def test_sin_punto_va_a_reparar(self):
        """Registros sin punto decimal van a geo_corregir_decimales."""
        df = pd.DataFrame({
            "latitud_original": ["21894", "1807", "3516"],
            "canton": ["GUAYAQUIL", "QUITO", "IBARRA"],
        })
        limbo, decimales = separar_por_formato(df)
        assert len(limbo) == 0
        assert len(decimales) == 3

    def test_mixto_separacion_correcta(self):
        """Verifica la separación correcta de registros mixtos."""
        df = pd.DataFrame({
            "latitud_original": ["-2.1894", "21894", "-0.1807", "1807"],
            "canton": ["G", "G", "Q", "Q"],
        })
        limbo, decimales = separar_por_formato(df)
        assert len(limbo) == 2
        assert len(decimales) == 2

    def test_vacio_sin_error(self):
        """Verifica comportamiento con DataFrame vacío."""
        df = pd.DataFrame({"latitud_original": [], "canton": []})
        limbo, decimales = separar_por_formato(df)
        assert len(limbo) == 0
        assert len(decimales) == 0


# =========================================================================
# TESTS: Ensamblaje final (Paso 4.7)
# =========================================================================
class TestEnsamblaje:
    """Tests de ensamblar_base_final()."""

    def _make_df(self, n: int, start_id: int = 1) -> pd.DataFrame:
        """Crea un DataFrame de prueba con n registros."""
        return pd.DataFrame({
            "ID_temp": range(start_id, start_id + n),
            "canton": ["QUITO"] * n,
            "lat_num": [-0.18] * n,
            "lon_num": [-78.46] * n,
        })

    def test_ensamblaje_basico(self):
        """Verifica que pd.concat() de las partes produzca la suma correcta."""
        df1 = self._make_df(10, 1)
        df2 = self._make_df(5, 11)
        vacio = pd.DataFrame()

        resultado = ensamblar_base_final(df1, vacio, vacio, df2, vacio, vacio)
        assert len(resultado) == 15

    def test_elimina_columnas_auxiliares(self):
        """Verifica que columnas auxiliares sean eliminadas."""
        df = self._make_df(5, 1)
        df["latitud_original"] = "-2.18"   # Columna auxiliar
        df["CANTON_MAPA"] = "GUAYAQUIL"    # Columna residual de sjoin
        df["index_right"] = 0              # Columna residual de sjoin

        vacio = pd.DataFrame()
        resultado = ensamblar_base_final(df, vacio, vacio, vacio, vacio, vacio)

        assert "latitud_original" not in resultado.columns
        assert "CANTON_MAPA" not in resultado.columns
        assert "index_right" not in resultado.columns

    def test_elimina_filas_nan_coords(self):
        """Verifica que filas con NaN en lat/lon sean eliminadas."""
        df = self._make_df(5, 1)
        df.loc[0, "lat_num"] = float("nan")
        df.loc[1, "lon_num"] = float("nan")

        vacio = pd.DataFrame()
        resultado = ensamblar_base_final(df, vacio, vacio, vacio, vacio, vacio)
        assert len(resultado) == 3  # Se eliminaron 2 filas con NaN

    def test_error_todos_vacios(self):
        """Verifica que ValueError se lanza si todas las partes están vacías."""
        vacio = pd.DataFrame()
        with pytest.raises(ValueError, match="vacíos"):
            ensamblar_base_final(vacio, vacio, vacio, vacio, vacio, vacio)

    def test_preserva_columnas_originales(self):
        """Verifica que las columnas no-auxiliares se preservan."""
        df = self._make_df(3, 1)
        df["canton"] = "QUITO"

        vacio = pd.DataFrame()
        resultado = ensamblar_base_final(df, vacio, vacio, vacio, vacio, vacio)
        assert "canton" in resultado.columns
        assert "lat_num" in resultado.columns
        assert "lon_num" in resultado.columns


# =========================================================================
# TEST DE INTEGRACIÓN REAL: Pipeline completo sobre datos reales (Paso 4.9)
# =========================================================================
class TestPipelineCompletoReal:
    """
    Test de integración que ejecuta el pipeline completo de Fase 4 sobre
    los datos reales de homi_filtrado_2024.parquet.
    """

    @pytest.fixture
    def datos_filtrados(self):
        """Carga los datos reales de Fase 3 si existen."""
        try:
            return cargar_intermedio_filtrado()
        except FileNotFoundError:
            pytest.skip(
                "No existe homi_filtrado_2024.parquet. "
                "Ejecuta primero las Fases 1–3."
            )

    def test_crear_puntos_datos_reales(self, datos_filtrados):
        """Verifica que se creen puntos geoespaciales válidos."""
        gdf = crear_geodataframe_puntos(datos_filtrados)
        assert len(gdf) > 0
        assert "ID_temp" in gdf.columns
        assert "lat_num" in gdf.columns
        assert "lon_num" in gdf.columns
        assert gdf.crs is not None

    def test_id_temp_unico(self, datos_filtrados):
        """Verifica que ID_temp sea único en el GeoDataFrame."""
        gdf = crear_geodataframe_puntos(datos_filtrados)
        assert gdf["ID_temp"].nunique() == len(gdf), (
            "ID_temp contiene valores duplicados."
        )

    def test_auditoria_produce_dos_grupos(self, datos_filtrados, mapa_cantonal):
        """Verifica que la auditoría topológica produce correctos + a corregir."""
        gdf = crear_geodataframe_puntos(datos_filtrados)
        correctos, corregir = auditar_punto_en_poligono(gdf, mapa_cantonal)
        total = len(correctos) + len(corregir)
        assert total == len(gdf), (
            f"Pérdida de registros: {len(gdf)} entrada != {total} salida"
        )

    def test_sin_duplicados_correctos_corregir(self, datos_filtrados, mapa_cantonal):
        """Verifica que un ID_temp no aparezca en ambos grupos."""
        gdf = crear_geodataframe_puntos(datos_filtrados)
        correctos, corregir = auditar_punto_en_poligono(gdf, mapa_cantonal)

        ids_correctos = set(correctos["ID_temp"])
        ids_corregir = set(corregir["ID_temp"])
        interseccion = ids_correctos & ids_corregir

        assert len(interseccion) == 0, (
            f"Se encontraron {len(interseccion)} IDs en ambos grupos: "
            f"{list(interseccion)[:5]}"
        )

