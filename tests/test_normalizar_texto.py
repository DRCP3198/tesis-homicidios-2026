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
from src.limpieza.normalizar_texto import normalizar_todas_columnas
from src.reportes.auditoria_caracteres import auditar_caracteres_especiales


# =========================================================================
# TESTS UNITARIOS: normalizar_texto() — Función escalar
# =========================================================================
class TestNormalizarTexto:
    """Tests de la función normalizar_texto() en src/utils/texto.py."""

    def test_elimina_tildes_vocales(self):
        """Verifica la remoción de todas las vocales acentuadas."""
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
        assert normalizar_texto("QUITO") == "QUITO"
        assert normalizar_texto("GUAYAQUIL") == "GUAYAQUIL"

    def test_valor_no_string(self):
        """Verifica que valores no-string (NaN, None, int) pasen sin error."""
        assert normalizar_texto(None) is None
        assert normalizar_texto(42) == 42
        assert normalizar_texto(3.14) == 3.14

    def test_string_vacio(self):
        """Verifica el comportamiento con string vacío."""
        assert normalizar_texto("") == ""
        assert normalizar_texto("   ") == ""

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
        serie = pd.Series(["  Guayaquíl  ", "Ñuño", "QUITO"])
        resultado = normalizar_columna(serie)
        assert resultado.tolist() == ["GUAYAQUIL", "NUNO", "QUITO"]

    def test_serie_con_nulos(self):
        """Verifica que los valores NA se preserven correctamente."""
        serie = pd.Series(["  Guayaquíl  ", None, "Ñuño", pd.NA])
        resultado = normalizar_columna(serie)
        assert resultado.iloc[0] == "GUAYAQUIL"
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
        serie = pd.Series(["á", "é", "í"], index=[10, 20, 30])
        resultado = normalizar_columna(serie)
        assert list(resultado.index) == [10, 20, 30]
        assert resultado.tolist() == ["A", "E", "I"]


# =========================================================================
# TESTS DE INTEGRACIÓN: normalizar_todas_columnas() — Pipeline completo
# =========================================================================
class TestNormalizarTodasColumnas:
    """Tests del pipeline completo de normalización."""

    @pytest.fixture
    def df_simulado(self) -> pd.DataFrame:
        """
        Crea un DataFrame de prueba que simula la estructura real
        con las 21 columnas (13 de texto + 8 no-texto).
        """
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

    def test_normaliza_13_columnas(self, df_simulado: pd.DataFrame):
        """Verifica que las 13 columnas de texto se normalicen."""
        resultado = normalizar_todas_columnas(df_simulado)

        # Verificar cada columna de texto
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

