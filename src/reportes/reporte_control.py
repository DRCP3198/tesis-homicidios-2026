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

Funciones principales:
    - imprimir_conteos(): Reporte detallado de Fase 3 (Paso 3.5)
    - imprimir_reporte_final(): Reporte completo post-pipeline (Fase 5)
"""
from dataclasses import dataclass, field

import pandas as pd


# =========================================================================
# ESTRUCTURA DE DATOS PARA EL REPORTE DE CONTROL
# =========================================================================
@dataclass
class MetricasFase:
    """Almacena las métricas de una etapa del pipeline."""

    nombre_fase: str
    registros: int
    descripcion: str = ""


@dataclass
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

    registros_originales: int = 0
    registros_post_conversion: int = 0
    registros_post_filtro_anio: int = 0
    registros_continental: int = 0
    registros_insular: int = 0
    registros_excluidos_anio: int = 0
    registros_excluidos_conversion: int = 0
    anios_excluidos: dict = field(default_factory=dict)
    cantones_insular: dict = field(default_factory=dict)
    integridad_ok: bool = False


# =========================================================================
# PASO 3.5 — Reporte de conteos (Fase 3)
# =========================================================================
def imprimir_conteos(
    df_original: pd.DataFrame,
    df_post_conversion: pd.DataFrame,
    df_post_filtro_anio: pd.DataFrame,
    df_continental: pd.DataFrame,
    df_insular: pd.DataFrame,
    anio_maximo: int = 2024,
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
    n_original = len(df_original)
    n_post_conv = len(df_post_conversion)
    n_post_anio = len(df_post_filtro_anio)
    n_continental = len(df_continental)
    n_insular = len(df_insular)

    n_excluidos_conv = n_original - n_post_conv
    n_excluidos_anio = n_post_conv - n_post_anio

    # Distribución de años excluidos
    if n_excluidos_anio > 0 and "anio_hecho" in df_post_conversion.columns:
        excluidos_anio = df_post_conversion.query("anio_hecho > @anio_maximo")
        anios_dist = (
            excluidos_anio["anio_hecho"]
            .value_counts()
            .sort_index()
            .to_dict()
        )
    else:
        anios_dist = {}

    # Distribución de cantones insulares
    if n_insular > 0 and "canton" in df_insular.columns:
        cantones_dist = df_insular["canton"].value_counts().to_dict()
    else:
        cantones_dist = {}

    # ── Verificación de integridad ──
    # La suma de todas las partes debe coincidir con el total original:
    # original = excluidos_conversion + excluidos_anio + insular + continental
    suma_partes = n_excluidos_conv + n_excluidos_anio + n_insular + n_continental
    integridad = suma_partes == n_original

    # ── Construir reporte ──
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
    print("=" * 60)
    print("  REPORTE DE CONTROL — FASE 3: FILTRADO")
    print("=" * 60)
    print(f"  {'Métrica':<40} {'Conteo':>10}")
    print(f"  {'-' * 40} {'-' * 10}")
    print(f"  {'Registros originales (entrada Fase 3)':<40} {n_original:>10,}")
    print(f"  {'(-) Eliminados por conversión NaN':<40} {n_excluidos_conv:>10,}")
    print(f"  {'(=) Post-conversión anio_hecho':<40} {n_post_conv:>10,}")
    print(f"  {'(-) Excluidos por año > ' + str(anio_maximo):<40} {n_excluidos_anio:>10,}")
    print(f"  {'(=) Post-filtro temporal':<40} {n_post_anio:>10,}")
    print(f"  {'(-) Registros insulares (Galápagos)':<40} {n_insular:>10,}")
    print(f"  {'(=) REGISTROS CONTINENTAL FINAL':<40} {n_continental:>10,}")
    print(f"  {'-' * 40} {'-' * 10}")

    # Detalle de exclusiones
    if anios_dist:
        print(f"\n  Detalle de años excluidos:")
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
        print(f"       Diferencia: {abs(suma_partes - n_original)}")

    # Porcentaje de retención
    if n_original > 0:
        retencion = (n_continental / n_original) * 100
        print(f"\n  Tasa de retención: {retencion:.2f}% "
              f"({n_continental:,} de {n_original:,})")

    print("=" * 60)

    return reporte


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

    if "anio_hecho" in df_final.columns:
        anio_min = df_final["anio_hecho"].min()
        anio_max = df_final["anio_hecho"].max()
        print(f"  Rango temporal: {anio_min} — {anio_max}")

    if "provincia" in df_final.columns:
        n_provincias = df_final["provincia"].nunique()
        print(f"  Provincias únicas: {n_provincias}")

    if "canton" in df_final.columns:
        n_cantones = df_final["canton"].nunique()
        print(f"  Cantones únicos: {n_cantones}")

    print("=" * 60)

