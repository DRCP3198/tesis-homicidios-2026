"""
reporte_control.py — Módulo de auditoría y conteos de control.

Corresponde a la Fase R 4 (líneas 190-203) del código original:
    cat("Total registros originales:", nrow(homi_2010_2025_raw), "\n")
    cat("Total registros filtrados:", nrow(homi_2010_2024), "\n")
    cat("Registros excluidos:", nrow(homi_2010_2025_raw) - nrow(homi_2010_2024), "\n")

Objetivo:
    Construir un reporte estructurado que compare métricas de los registros
    originales vs. filtrados vs. excluidos, permitiendo auditar y validar
    la integridad del pipeline de filtrado (Fase 3).

En palabras simples: es la "contabilidad" de la Fase 3. Verifica que
ningún registro se haya perdido "misteriosamente": todo lo que entró debe
ser igual a lo que salió + lo que se excluyó a propósito.

Funciones principales:
    - imprimir_conteos(): Reporte detallado de Fase 3 (Paso 3.5)
    - imprimir_reporte_final(): Reporte completo post-pipeline (Fase 5)
"""
# dataclass: decorador para crear clases que solo guardan datos, sin escribir
#            el constructor a mano. field: configura atributos con valores por defecto.
from dataclasses import dataclass, field

import pandas as pd


# =========================================================================
# ESTRUCTURA DE DATOS PARA EL REPORTE DE CONTROL
# =========================================================================
# @dataclass (decorador) genera automáticamente:
#   - El constructor __init__ → permite crear objetos así:
#       MetricasFase(nombre_fase="Filtro", registros=100)
#   - El método __repr__ → al imprimir el objeto se ve legible:
#       MetricasFase(nombre_fase='Filtro', registros=100, descripcion='')
#   - El método __eq__ → permite comparar dos objetos con "==".
@dataclass
class MetricasFase:
    """Almacena las métricas de una etapa del pipeline."""

    nombre_fase: str        # Nombre de la etapa (ej. "Filtro temporal").
    registros: int          # Cuántos registros quedaron en esa etapa.
    descripcion: str = ""   # Texto opcional; si no se da, queda vacío "".


@dataclass  # Mismo decorador: crea constructor, __repr__ y __eq__ automáticamente.
class ReporteControl:
    """
    Resultado completo de la auditoría de conteos de la Fase 3.

    Atributos
    ---------
    registros_originales : int
        Total de registros al inicio de la Fase 3 (salida de Fase 2).
    registros_post_conversion : int
        Registros tras convertir anio_hecho y eliminar NaN.
    registros_post_filtro_anio : int
        Registros tras aplicar filtro temporal (<= ANIO_MAXIMO).
    registros_continental : int
        Registros finales (continental, sin Galápagos).
    registros_insular : int
        Registros insulares excluidos (Galápagos).
    registros_excluidos_anio : int
        Registros eliminados por año > ANIO_MAXIMO.
    registros_excluidos_conversion : int
        Registros eliminados por fallo en conversión numérica.
    anios_excluidos : dict
        Distribución de años excluidos {año: conteo}.
    cantones_insular : dict
        Distribución de cantones insulares {cantón: conteo}.
    integridad_ok : bool
        True si la suma de partes coincide con el total original.
    """

    # Todos los atributos tienen un valor por defecto (= 0, = False...), así
    # se puede crear un ReporteControl() vacío y llenarlo después.
    registros_originales: int = 0
    registros_post_conversion: int = 0
    registros_post_filtro_anio: int = 0
    registros_continental: int = 0
    registros_insular: int = 0
    registros_excluidos_anio: int = 0
    registros_excluidos_conversion: int = 0
    # dict = diccionario {clave: valor}. Con field(default_factory=dict) cada
    # objeto recibe su PROPIO diccionario vacío (no compartido con otros objetos).
    anios_excluidos: dict = field(default_factory=dict)
    cantones_insular: dict = field(default_factory=dict)
    integridad_ok: bool = False


# =========================================================================
# PASO 3.5 — Reporte de conteos (Fase 3)
# =========================================================================
def imprimir_conteos(
    df_original: pd.DataFrame,          # Tabla al INICIO de la Fase 3.
    df_post_conversion: pd.DataFrame,   # Tabla tras convertir el año a número.
    df_post_filtro_anio: pd.DataFrame,  # Tabla tras quitar los años > 2024.
    df_continental: pd.DataFrame,       # Tabla final continental.
    df_insular: pd.DataFrame,           # Registros de Galápagos apartados.
    anio_maximo: int = 2024,            # Año límite usado en el filtro.
) -> ReporteControl:
    """
    Construye e imprime un reporte detallado comparando registros
    originales vs. filtrados vs. excluidos en la Fase 3.

    Equivalencia R (líneas 190-203):
        cat("Total registros originales:", nrow(homi_2010_2025_raw), "\\n")
        cat("Total registros filtrados:", nrow(homi_2010_2024), "\\n")
        cat("Registros excluidos:", nrow(...) - nrow(...), "\\n")

    Mapeo R → Python:
        nrow()    →  len(df) o df.shape[0]
        cat(...)  →  print(f"...")

    Parameters
    ----------
    df_original : pd.DataFrame
        DataFrame al inicio de Fase 3 (salida de Fase 2, antes de filtrar).
    df_post_conversion : pd.DataFrame
        DataFrame tras conversión de anio_hecho a entero (Paso 3.1).
    df_post_filtro_anio : pd.DataFrame
        DataFrame tras filtro temporal (Paso 3.2).
    df_continental : pd.DataFrame
        DataFrame continental final (Paso 3.3).
    df_insular : pd.DataFrame
        Registros insulares excluidos (Paso 3.4).
    anio_maximo : int
        Año límite utilizado en el filtro.

    Returns
    -------
    ReporteControl
        Objeto con todas las métricas calculadas y un flag de integridad.
    """
    # ── Calcular métricas ──
    # len(tabla) = número de filas (equivale a nrow() en R).
    n_original = len(df_original)
    n_post_conv = len(df_post_conversion)
    n_post_anio = len(df_post_filtro_anio)
    n_continental = len(df_continental)
    n_insular = len(df_insular)

    # Las exclusiones se calculan por diferencia entre etapas consecutivas.
    n_excluidos_conv = n_original - n_post_conv    # Perdidos al convertir el año.
    n_excluidos_anio = n_post_conv - n_post_anio   # Perdidos por año > 2024.

    # Distribución de años excluidos
    # `and` → ambas condiciones deben cumplirse.
    if n_excluidos_anio > 0 and "anio_hecho" in df_post_conversion.columns:
        # Filas con año mayor al límite ("@" = variable de Python dentro de query).
        excluidos_anio = df_post_conversion.query("anio_hecho > @anio_maximo")
        # Se encadenan métodos (uno tras otro) dentro de paréntesis para leerlo mejor:
        anios_dist = (
            excluidos_anio["anio_hecho"]
            .value_counts()   # Cuenta cuántas filas hay por cada año.
            .sort_index()     # Ordena por año.
            .to_dict()        # Convierte el resultado a diccionario {2025: 9171}.
        )
    else:
        anios_dist = {}  # Diccionario vacío: no hubo años excluidos.

    # Distribución de cantones insulares
    if n_insular > 0 and "canton" in df_insular.columns:
        cantones_dist = df_insular["canton"].value_counts().to_dict()
    else:
        cantones_dist = {}

    # ── Verificación de integridad ──
    # La suma de todas las partes debe coincidir con el total original:
    # original = excluidos_conversion + excluidos_anio + insular + continental
    suma_partes = n_excluidos_conv + n_excluidos_anio + n_insular + n_continental
    # "==" compara; el resultado (True/False) se guarda en `integridad`.
    integridad = suma_partes == n_original

    # ── Construir reporte ──
    # Creamos el objeto pasándole cada valor por su nombre (gracias a @dataclass).
    reporte = ReporteControl(
        registros_originales=n_original,
        registros_post_conversion=n_post_conv,
        registros_post_filtro_anio=n_post_anio,
        registros_continental=n_continental,
        registros_insular=n_insular,
        registros_excluidos_anio=n_excluidos_anio,
        registros_excluidos_conversion=n_excluidos_conv,
        anios_excluidos=anios_dist,
        cantones_insular=cantones_dist,
        integridad_ok=integridad,
    )

    # ── Imprimir reporte ──
    # Formatos usados dentro de las f-strings:
    #   {texto:<40} → texto alineado a la IZQUIERDA ocupando 40 espacios.
    #   {numero:>10,} → número alineado a la DERECHA en 10 espacios, con separador de miles.
    print("=" * 60)
    print("  REPORTE DE CONTROL — FASE 3: FILTRADO")
    print("=" * 60)
    print(f"  {'Métrica':<40} {'Conteo':>10}")
    print(f"  {'-' * 40} {'-' * 10}")
    print(f"  {'Registros originales (entrada Fase 3)':<40} {n_original:>10,}")
    print(f"  {'(-) Eliminados por conversión NaN':<40} {n_excluidos_conv:>10,}")
    print(f"  {'(=) Post-conversión anio_hecho':<40} {n_post_conv:>10,}")
    # str(numero) convierte el número a texto para poder unirlo con "+".
    print(f"  {'(-) Excluidos por año > ' + str(anio_maximo):<40} {n_excluidos_anio:>10,}")
    print(f"  {'(=) Post-filtro temporal':<40} {n_post_anio:>10,}")
    print(f"  {'(-) Registros insulares (Galápagos)':<40} {n_insular:>10,}")
    print(f"  {'(=) REGISTROS CONTINENTAL FINAL':<40} {n_continental:>10,}")
    print(f"  {'-' * 40} {'-' * 10}")

    # Detalle de exclusiones
    # Un diccionario vacío {} se evalúa como False → solo imprime si hay datos.
    if anios_dist:
        print(f"\n  Detalle de años excluidos:")
        # sorted(...) ordena las parejas (año, cantidad) por año.
        for anio, count in sorted(anios_dist.items()):
            print(f"    Año {int(anio)}: {count:,} registros")

    if cantones_dist:
        print(f"\n  Detalle de cantones insulares excluidos:")
        for canton, count in cantones_dist.items():
            print(f"    {canton}: {count:,} registros")

    # Verificación de integridad
    print(f"\n  {'─' * 50}")
    if integridad:
        print(f"  [OK] Verificación de integridad: PASÓ")
        print(f"       {n_excluidos_conv} + {n_excluidos_anio} + "
              f"{n_insular} + {n_continental} = {suma_partes} "
              f"(== {n_original} original)")
    else:
        print(f"  [ERROR] Verificación de integridad: FALLÓ")
        print(f"       Suma de partes: {suma_partes} != Original: {n_original}")
        # abs(x) → valor absoluto (quita el signo negativo).
        print(f"       Diferencia: {abs(suma_partes - n_original)}")

    # Porcentaje de retención
    # (Se verifica > 0 para no dividir para cero, lo cual daría error.)
    if n_original > 0:
        retencion = (n_continental / n_original) * 100
        print(f"\n  Tasa de retención: {retencion:.2f}% "
              f"({n_continental:,} de {n_original:,})")

    print("=" * 60)

    return reporte  # Devolvemos el objeto para poder usarlo en los tests.


# =========================================================================
# REPORTE FINAL DEL PIPELINE (para Fase 5 — uso futuro)
# =========================================================================
def imprimir_reporte_final(df_final: pd.DataFrame) -> None:
    """
    Imprime un reporte estadístico final del pipeline completo.

    Este reporte se utiliza al final de la Fase 5 (Exportación) para
    mostrar las métricas de calidad del dataset procesado.

    Equivalencia R (líneas 530-570):
        cat("=== REPORTE ESTADÍSTICO FINAL ===\\n")
        cat("Total registros finales:", nrow(homi_final), "\\n")
        ...

    Parameters
    ----------
    df_final : pd.DataFrame
        DataFrame final procesado (salida completa del pipeline).
    """
    print("=" * 60)
    print("  REPORTE ESTADÍSTICO FINAL")
    print("=" * 60)
    print(f"  Total registros finales: {len(df_final):,}")
    print(f"  Columnas: {len(df_final.columns)}")

    # Cada bloque solo se ejecuta si la columna existe en la tabla.
    if "anio_hecho" in df_final.columns:
        anio_min = df_final["anio_hecho"].min()  # .min() → valor más pequeño.
        anio_max = df_final["anio_hecho"].max()  # .max() → valor más grande.
        print(f"  Rango temporal: {anio_min} — {anio_max}")

    if "provincia" in df_final.columns:
        # .nunique() → cuántos valores DISTINTOS hay en la columna.
        n_provincias = df_final["provincia"].nunique()
        print(f"  Provincias únicas: {n_provincias}")

    if "canton" in df_final.columns:
        n_cantones = df_final["canton"].nunique()
        print(f"  Cantones únicos: {n_cantones}")

    print("=" * 60)
