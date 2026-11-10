"""
test_normalizar_texto.py — Tests para la Fase 2: Limpieza y Normalización Textual.

Verifica que:
1. La función normalizar_texto() elimine correctamente tildes, eñes y diéresis.
2. La función normalizar_columna() opere sobre pd.Series completas.
3. El pipeline normalizar_todas_columnas() procese las 13 columnas.
4. La auditoría de caracteres detecte problemas antes y confirme limpieza después.
"""
import pytest
import pandas as pd

from src.utils.texto import (
    normalizar_texto,
    normalizar_columna,
    contiene_caracteres_especiales,
    PATRON_CARACTERES_ESPECIALES,
)
from src.ingesta.config import COLUMNAS_TEXTO_NORMALIZAR
from src.limpieza.normalizar_texto import (
    homologar_cantones_por_provincia,
    normalizar_todas_columnas,
)
from src.reportes.auditoria_caracteres import auditar_caracteres_especiales


# =========================================================================
# TESTS UNITARIOS: normalizar_texto() — Función escalar
# =========================================================================
# Un "test unitario" prueba UNA sola pieza pequeña de código (una función)
# de manera aislada, con entradas chiquitas inventadas por nosotros, sin
# depender de archivos grandes ni bases de datos externas.
class TestNormalizarTexto:
    """Tests de la función normalizar_texto() en src/utils/texto.py."""

    def test_elimina_tildes_vocales(self):
        """Verifica la remoción de todas las vocales acentuadas."""
        # Cada `assert A == B` verifica que la función devuelva exactamente lo esperado.
        assert normalizar_texto("áéíóú") == "AEIOU"
        assert normalizar_texto("ÁÉÍÓÚ") == "AEIOU"

    def test_elimina_ene(self):
        """Verifica que la eñe se convierta a N."""
        assert normalizar_texto("Ñuño") == "NUNO"
        assert normalizar_texto("ñ") == "N"
        assert normalizar_texto("SEÑOR") == "SENOR"

    def test_elimina_dieresis(self):
        """Verifica que la diéresis (ü/Ü) se convierta a U."""
        assert normalizar_texto("güero") == "GUERO"
        assert normalizar_texto("PINGÜINO") == "PINGUINO"

    def test_strip_espacios(self):
        """Verifica la remoción de espacios al inicio y final."""
        assert normalizar_texto("  Guayaquíl  ") == "GUAYAQUIL"
        assert normalizar_texto("  quito  ") == "QUITO"
        # \t = tabulación, \n = salto de línea; strip() también los elimina.
        assert normalizar_texto("\t CUENCA \n") == "CUENCA"

    def test_mayusculas(self):
        """Verifica la conversión a mayúsculas."""
        assert normalizar_texto("guayaquil") == "GUAYAQUIL"
        assert normalizar_texto("santo domingo") == "SANTO DOMINGO"

    def test_cadena_completa(self):
        """Verifica la normalización completa de nombres geográficos ecuatorianos."""
        assert normalizar_texto("SANTO DOMINGO DE LOS TSÁCHILAS") == "SANTO DOMINGO DE LOS TSACHILAS"
        assert normalizar_texto("  Esmeraldas  ") == "ESMERALDAS"
        assert normalizar_texto("Portoviejo") == "PORTOVIEJO"
        assert normalizar_texto("Zamora-Chinchipe") == "ZAMORA-CHINCHIPE"

    def test_texto_ya_limpio(self):
        """Verifica que un texto ya normalizado no cambie."""
        # Propiedad de "idempotencia": aplicar la limpieza una segunda vez no cambia nada.
        assert normalizar_texto("QUITO") == "QUITO"
        assert normalizar_texto("GUAYAQUIL") == "GUAYAQUIL"

    def test_valor_no_string(self):
        """Verifica que valores no-string (NaN, None, int) pasen sin error."""
        # Para None siempre se compara con `is None` (identidad), no con `==`.
        assert normalizar_texto(None) is None
        assert normalizar_texto(42) == 42
        assert normalizar_texto(3.14) == 3.14

    def test_string_vacio(self):
        """Verifica el comportamiento con string vacío."""
        assert normalizar_texto("") == ""
        assert normalizar_texto("   ") == ""  # Solo espacios → queda vacío "".

    def test_caracteres_mixtos(self):
        """Verifica mezcla de acentos y caracteres ASCII normales."""
        assert normalizar_texto("Café123") == "CAFE123"
        assert normalizar_texto("Niño-2024") == "NINO-2024"


# =========================================================================
# TESTS UNITARIOS: normalizar_columna() — Función vectorizada
# =========================================================================
class TestNormalizarColumna:
    """Tests de la función normalizar_columna() para pd.Series."""

    def test_serie_basica(self):
        """Verifica la normalización de una Serie simple."""
        # pd.Series([...]) crea una columna suelta de pandas a partir de una lista.
        serie = pd.Series(["  Guayaquíl  ", "Ñuño", "QUITO"])
        resultado = normalizar_columna(serie)
        # .tolist() convierte la columna de vuelta a lista para compararla con ==.
        assert resultado.tolist() == ["GUAYAQUIL", "NUNO", "QUITO"]

    def test_serie_con_nulos(self):
        """Verifica que los valores NA se preserven correctamente."""
        # pd.NA es el valor nulo propio de pandas (similar al NA de R).
        serie = pd.Series(["  Guayaquíl  ", None, "Ñuño", pd.NA])
        resultado = normalizar_columna(serie)
        # .iloc[n] → accede al elemento en la POSICIÓN n (0 = primero, 1 = segundo...).
        assert resultado.iloc[0] == "GUAYAQUIL"
        # pd.isna(x) → True si x es nulo (sirve tanto para None como para NaN y pd.NA).
        assert pd.isna(resultado.iloc[1])
        assert resultado.iloc[2] == "NUNO"
        assert pd.isna(resultado.iloc[3])

    def test_serie_vacia(self):
        """Verifica el comportamiento con Serie vacía."""
        serie = pd.Series([], dtype=str)
        resultado = normalizar_columna(serie)
        assert len(resultado) == 0

    def test_preserva_indice(self):
        """Verifica que el índice original se mantenga."""
        # index=[10, 20, 30] asigna etiquetas personalizadas a las filas.
        serie = pd.Series(["á", "é", "í"], index=[10, 20, 30])
        resultado = normalizar_columna(serie)
        assert list(resultado.index) == [10, 20, 30]
        assert resultado.tolist() == ["A", "E", "I"]


# =========================================================================
# TESTS DE INTEGRACIÓN: normalizar_todas_columnas() — Pipeline completo
# =========================================================================
# Un "test de integración" prueba cómo funcionan VARIAS piezas juntas
# (ej. normalizar_todas_columnas llamando internamente a normalizar_columna y config).
class TestNormalizarTodasColumnas:
    """Tests del pipeline completo de normalización."""

    # ¿Qué es `@pytest.fixture`?
    #   Es un decorador de pytest que marca a una función como "proveedora de
    #   datos de prueba". Cualquier test que ponga `df_simulado` entre sus
    #   paréntesis recibirá automáticamente un DataFrame NUEVO y limpio creado
    #   por esta función, sin tener que copiar y pegar la tabla en cada test.
    @pytest.fixture
    def df_simulado(self) -> pd.DataFrame:
        """
        Crea un DataFrame de prueba que simula la estructura real
        con las 21 columnas (13 de texto + 8 no-texto).
        """
        # pd.DataFrame({columna: [valores...]}) crea una tabla desde un diccionario.
        return pd.DataFrame({
            # 13 columnas de texto (con tildes y eñes intencionalmente)
            "codigo_caso":          ["  ABC-001  ", "DEF-002"],
            "tipo_delito":          ["Homicidio", "Asesinato"],
            "zona_tipo":            ["URBANO", "Rural"],
            "lugar_especifico":     ["Vía Pública", "Domicilio"],
            "tipo_arma":            ["Arma de Fuego", "Arma Blanca"],
            "motivacion_detalle":   ["Violencia Comunitaria", "Riñas"],
            "causa_especifica":     ["Venganza", "Robo"],
            "sexo_victima":         ["Masculino", "Femenino"],
            "nacionalidad_victima": ["Ecuatoriana", "Colombiana"],
            "canton":               ["  Guayaquíl  ", "Quito"],
            "mes_hecho":            ["Enero", "Febrero"],
            "dia_semana":           ["Lunes", "Martes"],
            "provincia":            ["GUAYAS", "Pichincha"],
            # 8 columnas no-texto (no deben ser afectadas)
            "fecha_hecho":          ["2023-01-15", "2023-02-20"],
            "anio_hecho":           ["2023", "2023"],
            "hora_aproximada":      ["14", "22"],
            "edad_victima":         ["35", "28"],
            "latitud":              ["-2.1894", "-0.1807"],
            "longitud":             ["-79.8891", "-78.4678"],
            "AUX_HORA_SISTEMA":     ["14", "22"],
            "AUX_MINUTO_SISTEMA":   ["30", "45"],
        })

    # pytest ve el parámetro `df_simulado` y le inyecta lo que devuelve el fixture de arriba.
    def test_normaliza_13_columnas(self, df_simulado: pd.DataFrame):
        """Verifica que las 13 columnas de texto se normalicen."""
        resultado = normalizar_todas_columnas(df_simulado)

        # Verificar cada columna de texto y cada celda dentro de ella.
        for col in COLUMNAS_TEXTO_NORMALIZAR:
            for valor in resultado[col].dropna():
                assert valor == valor.upper(), (
                    f"Columna '{col}' tiene valor no-mayúscula: '{valor}'"
                )
                assert not contiene_caracteres_especiales(valor), (
                    f"Columna '{col}' aún tiene caracteres especiales: '{valor}'"
                )

    def test_guayaquil_normalizado(self, df_simulado: pd.DataFrame):
        """Verifica que 'Guayaquíl' → 'GUAYAQUIL'."""
        resultado = normalizar_todas_columnas(df_simulado)
        # .loc[fila, columna] → accede a la celda de la fila 0 en la columna "canton".
        assert resultado.loc[0, "canton"] == "GUAYAQUIL"

    def test_columnas_no_texto_intactas(self, df_simulado: pd.DataFrame):
        """Verifica que las columnas no-texto NO sean modificadas."""
        resultado = normalizar_todas_columnas(df_simulado)
        assert resultado.loc[0, "latitud"] == "-2.1894"
        assert resultado.loc[0, "longitud"] == "-79.8891"
        assert resultado.loc[0, "anio_hecho"] == "2023"

    def test_forma_preservada(self, df_simulado: pd.DataFrame):
        """Verifica que no se agreguen ni eliminen filas o columnas."""
        resultado = normalizar_todas_columnas(df_simulado)
        assert resultado.shape == df_simulado.shape

    def test_error_columna_faltante(self):
        """Verifica que lance KeyError si falta una columna de texto."""
        df_incompleto = pd.DataFrame({"codigo_caso": ["ABC"]})
        # `with pytest.raises(TipoDeError, match="texto"):` → esta prueba PASA
        # solo si el código de adentro efectivamente lanza ese error y su mensaje
        # contiene "Columnas de texto no encontradas". Si NO lanzara error, fallaría.
        with pytest.raises(KeyError, match="Columnas de texto no encontradas"):
            normalizar_todas_columnas(df_incompleto)


# =========================================================================
# TESTS DE AUDITORÍA: auditar_caracteres_especiales()
# =========================================================================
class TestAuditoriaCaracteres:
    """Tests de la función de auditoría de caracteres especiales."""

    def test_datos_sucios_detectados(self):
        """Verifica que se detecten tildes en datos NO normalizados."""
        df = pd.DataFrame({
            "canton": ["Guayaquíl", "Quito", "Cuenca"],
            "provincia": ["GUAYAS", "PICHINCHA", "AZUAY"],
        })
        reporte = auditar_caracteres_especiales(
            df, columnas=["canton", "provincia"]
        )
        # Accedemos a los atributos del objeto `ReporteAuditoria` con punto "."
        assert not reporte.limpio
        assert reporte.columnas_con_problemas == 1
        assert reporte.hallazgos[0].columna == "canton"

    def test_datos_limpios_ok(self):
        """Verifica que datos ya normalizados pasen la auditoría."""
        df = pd.DataFrame({
            "canton": ["GUAYAQUIL", "QUITO", "CUENCA"],
            "provincia": ["GUAYAS", "PICHINCHA", "AZUAY"],
        })
        reporte = auditar_caracteres_especiales(
            df, columnas=["canton", "provincia"]
        )
        assert reporte.limpio
        assert reporte.columnas_con_problemas == 0
        assert len(reporte.hallazgos) == 0

    def test_multiples_columnas_afectadas(self):
        """Verifica detección en múltiples columnas simultáneamente."""
        df = pd.DataFrame({
            "canton": ["Guayaquíl"],
            "provincia": ["Pichinchá"],
        })
        reporte = auditar_caracteres_especiales(
            df, columnas=["canton", "provincia"]
        )
        assert reporte.columnas_con_problemas == 2

    def test_error_columna_inexistente(self):
        """Verifica error si se pasa una columna que no existe."""
        df = pd.DataFrame({"canton": ["QUITO"]})
        with pytest.raises(KeyError, match="Columnas no encontradas"):
            auditar_caracteres_especiales(df, columnas=["inexistente"])


# =========================================================================
# TESTS DE HOMOLOGACIÓN TOPONÍMICA: homologar_cantones_por_provincia()
# =========================================================================
class TestHomologacionCantonesPorProvincia:
    """
    Verifica la homologación de variantes de escritura de cantones desambiguando
    por la pareja (provincia, canton), especialmente el caso crítico de
    'SAN MIGUEL DE SALCEDO' en Cotopaxi ('SALCEDO') vs. Bolívar ('SAN MIGUEL').
    """

    def test_desambigua_san_miguel_de_salcedo_cotopaxi_vs_bolivar(self):
        """
        En COTOPAXI 'SAN MIGUEL DE SALCEDO' debe pasar a 'SALCEDO', mientras
        que en BOLIVAR debe pasar a 'SAN MIGUEL'.
        """
        df = pd.DataFrame({
            "codigo_caso": ["92611", "92067"],
            "fecha_hecho": ["2024-06-15", "2024-05-20"],
            "provincia":   ["COTOPAXI", "BOLIVAR"],
            "canton":      ["SAN MIGUEL DE SALCEDO", "SAN MIGUEL DE SALCEDO"],
            "latitud":     ["-1.0715", "-1.7061"],
            "longitud":    ["-78.5908", "-79.1175"],
        })
        resultado = homologar_cantones_por_provincia(df.copy())
        assert resultado.loc[0, "canton"] == "SALCEDO"
        assert resultado.loc[1, "canton"] == "SAN MIGUEL"

    def test_homologa_pueblo_viejo_y_orellana(self):
        """
        Verifica 'PUEBLO VIEJO' -> 'PUEBLOVIEJO' en Los Ríos y
        'PUERTO FRANCISCO DE ORELLANA' -> 'ORELLANA' en Orellana.
        """
        df = pd.DataFrame({
            "provincia": ["LOS RIOS", "ORELLANA", "PICHINCHA"],
            "canton": [
                "PUEBLO VIEJO",
                "PUERTO FRANCISCO DE ORELLANA",
                "RUMINAHUI",
            ],
        })
        resultado = homologar_cantones_por_provincia(df.copy())
        assert resultado["canton"].tolist() == [
            "PUEBLOVIEJO",
            "ORELLANA",
            "RUMINAHUI",
        ]
