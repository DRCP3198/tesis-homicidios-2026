"""
main.py — Orquestador del pipeline de preprocesamiento.

Ejecuta todas las fases en secuencia. Cada fase se activa
progresivamente a medida que se implementan los módulos.

Uso:
    python main.py

¿Qué es un "orquestador"?
    Es el "director de orquesta": este archivo NO contiene la lógica pesada
    (no limpia textos ni repara coordenadas él mismo), sino que llama en orden
    a las funciones de cada módulo de `src/` y le pasa el resultado de una
    fase a la siguiente, como una línea de ensamblaje.
"""

# ── Imports Fase 1: Ingesta ──
# Importa las funciones encargadas de cargar los datos originales
# de homicidios y guardar una copia intermedia con los nombres de
# las columnas estandarizados.
# Sintaxis `from paquete.modulo import funcion`:
#   src.ingesta.cargar_datos → equivale a la ruta src/ingesta/cargar_datos.py
#   (en Python las carpetas se separan con puntos "." al importar).
from src.ingesta.cargar_datos import (
    cargar_homicidios_raw,
    guardar_intermedio_renombrado,
)

# ── Imports Fase 2: Limpieza textual ──
# Importa las funciones de normalización de texto (strip + upper + unidecode)
# y la auditoría de caracteres especiales (tildes, eñes, diéresis).
from src.limpieza.normalizar_texto import (
    normalizar_todas_columnas,
    guardar_intermedio_normalizado,
)
from src.reportes.auditoria_caracteres import auditar_caracteres_especiales

# ── Imports Fase 3: Filtrado temporal y geográfico ──
# Importa las funciones de filtrado por año y exclusión de Galápagos,
# así como el reporte de control que audita los conteos en cada paso.
from src.limpieza.filtros import (
    convertir_anio_a_entero,
    excluir_galapagos,
    filtrar_anio,
    guardar_insular,
    guardar_intermedio_filtrado,
)
from src.reportes.reporte_control import imprimir_conteos

# ── Imports Fase 4: Validación Geoespacial ──
# Importa los módulos del pipeline geoespacial completo:
# cartografía, creación de puntos, auditoría topológica,
# algoritmo reparador (4 escenarios) y ensamblaje final.
from src.validacion_geo.cartografia import cargar_mapa_cantonal
from src.validacion_geo.ensamblaje import (
    ensamblar_base_final,
    guardar_artefactos_geo,
    imprimir_reporte_geo,
)
from src.validacion_geo.geometrias import (
    auditar_punto_en_poligono,
    crear_geodataframe_puntos,
    separar_por_formato,
)
from src.validacion_geo.reparacion import reparar_coordenadas_corruptas

# ── Imports Fase 5: Etiquetado Final, Exportación y Visualización ──
# Importa las librerías de tipos (`gpd`, `pd`) y los tres submódulos finales (Pasos 5.1 a 5.6):
#   1. exportador.py        → selección de 21 columnas, tipado estricto y escritura CSV/Parquet/GeoPackage.
#   2. metricas_pipeline.py → auditoría estadística del ciclo de vida completo (JSON + Markdown + consola).
#   3. mapa_diagnostico.py  → figura cartográfica desatendida (`Agg`) en alta resolución (300 DPI).
import geopandas as gpd
import pandas as pd

from src.exportacion.exportador import (
    exportar_todos_formatos,
    seleccionar_y_estandarizar_columnas,
)
from src.ingesta.config import PROCESSED_GEORREFERENCIADO
from src.reportes.metricas_pipeline import (
    ResumenAuditoriaPipeline,
    generar_auditoria_pipeline,
)
from src.visualizacion.mapa_diagnostico import generar_mapa_diagnostico

#pipeline = proceso general que coordina las etapas de preprocesamiento.
#ingesta = módulo encargado de cargar los datos originales.


# ¿Por qué todos los parámetros de `ejecutar_exportacion_final` tienen `| None = None`?
#   • `pd.DataFrame | None = None` indica un parámetro OPCIONAL: puede recibir el objeto en
#     memoria (cuando lo llama `main()` tras terminar la Fase 4) o puede omitirse (`None`).
#   • Si se omite, la propia función carga automáticamente desde disco los artefactos Parquet
#     y el shapefile cantonal, permitiendo re-ejecutar solo la etapa final sin repetir Fases 1-4.
def ejecutar_exportacion_final(
    df_georreferenciado: pd.DataFrame | None = None,
    mapa_cantones: gpd.GeoDataFrame | None = None,
    n_brutos_iniciales: int | None = None,
    n_excluidos_temporal: int | None = None,
    n_excluidos_insular: int | None = None,
    n_universo_filtrado: int | None = None,
    n_geo_correctos: int | None = None,
    n_rescatados_algoritmo: int | None = None,
    n_limbo_retenidos: int | None = None,
    n_descartados_irreversibles: int | None = None,
    detalle_escenarios: dict[str, int] | None = None,
) -> tuple[pd.DataFrame, ResumenAuditoriaPipeline]:
    """
    Orquesta los Pasos 5.1 a 5.6 (Etiquetado Final, Exportación, Auditoría y Mapa).

    Puede invocarse al final de `main()` pasando los objetos en memoria, o bien de
    manera independiente (`ejecutar_exportacion_final()`) leyendo `data/processed/homi_georreferenciado.parquet`.
    """
    print("=" * 60)
    print("  FASE 5: ETIQUETADO FINAL, EXPORTACIÓN Y VISUALIZACIÓN")
    print("=" * 60)

    # Carga perezosa (lazy fallback): solo lee de disco si el dato no vino ya en RAM.
    if df_georreferenciado is None:
        df_georreferenciado = pd.read_parquet(PROCESSED_GEORREFERENCIADO)

    if mapa_cantones is None:
        mapa_cantones = cargar_mapa_cantonal()

    # Paso 5.1: Proyecta únicamente las 21 columnas limpias, renombra `lat_num`/`lon_num`
    # hacia `latitud`/`longitud`, descarta `ID_temp` y convierte cada columna a su dtype óptimo.
    df_etiquetado = seleccionar_y_estandarizar_columnas(df_georreferenciado)

    # Pasos 5.2, 5.3 y 5.4: Persiste simultáneamente CSV (UTF-8), Parquet (Snappy) y GeoPackage (EPSG:4326).
    exportar_todos_formatos(df_etiquetado)

    # Paso 5.5: Calcula métricas extremo a extremo, verifica cuadre contable y escribe JSON + Markdown.
    resumen_auditoria = generar_auditoria_pipeline(
        df_final=df_etiquetado,
        n_brutos_iniciales=n_brutos_iniciales,
        n_excluidos_temporal=n_excluidos_temporal,
        n_excluidos_insular=n_excluidos_insular,
        n_universo_filtrado=n_universo_filtrado,
        n_geo_correctos=n_geo_correctos,
        n_rescatados_algoritmo=n_rescatados_algoritmo,
        n_limbo_retenidos=n_limbo_retenidos,
        n_descartados_irreversibles=n_descartados_irreversibles,
        detalle_escenarios=detalle_escenarios,
    )

    # Paso 5.6: Renderiza el mapa diagnóstico sobre cantones y provincias disueltas a 300 DPI.
    generar_mapa_diagnostico(df_etiquetado, mapa_cantones)

    # Devuelve una tupla `(DataFrame_final, ResumenAuditoriaPipeline)` para inspección o tests.
    return df_etiquetado, resumen_auditoria


def main():
    """Función principal encargada de ejecutar el pipeline de preprocesamiento."""

    # ── FASE 1: Ingesta y Renombrado ──
    # Carga los datos originales de homicidios y guarda
    # una versión intermedia con las columnas renombradas.
    df = cargar_homicidios_raw()         # Lee el CSV crudo y renombra las 21 columnas.
    guardar_intermedio_renombrado(df)    # Guarda data/interim/homi_renombrado.parquet.

    # ── FASE 2: Limpieza y Normalización Textual ──
    # Aplica strip() + upper() + unidecode() a las 13 columnas de texto.
    # Equivale al bloque mutate() con iconv() + str_trim() + str_to_upper() del R.
    df = normalizar_todas_columnas(df)   # MAYÚSCULAS + sin tildes/eñes + sin espacios extra.
    auditar_caracteres_especiales(df)    # Verifica con regex que no haya quedado ni una tilde.
    guardar_intermedio_normalizado(df)   # Guarda data/interim/homi_normalizado.parquet.

    # ── FASE 3: Filtrado temporal y geográfico ──
    # Aplica los filtros de año (<=2024) y excluye cantones insulares.
    # Equivale al bloque filter() del R (líneas 132-150).
    print("=" * 60)
    print("  FASE 3: FILTRADO TEMPORAL Y GEOGRÁFICO")
    print("=" * 60)

    # Guardamos una "foto" (.copy()) de la tabla antes de cada paso, para que
    # al final `imprimir_conteos` pueda comparar cuántos registros había en cada etapa.
    df_entrada_fase3 = df.copy()

    # Paso 3.1: Conversión de anio_hecho a entero
    df = convertir_anio_a_entero(df)
    df_post_conversion = df.copy()

    # Paso 3.2: Filtro temporal (anio_hecho <= 2024)
    df = filtrar_anio(df)
    df_post_filtro_anio = df.copy()

    # Pasos 3.3 y 3.4: Exclusión de Galápagos + separación insular
    # `excluir_galapagos` devuelve 2 tablas a la vez; las recibimos separadas por coma.
    df_continental, df_insular = excluir_galapagos(df)
    guardar_insular(df_insular)  # Guarda los insulares aparte para no perder trazabilidad.

    # Paso 3.5: Reporte de conteos (auditoría de integridad)
    # Comprueba que: originales == eliminados + insulares + continentales.
    imprimir_conteos(
        df_original=df_entrada_fase3,
        df_post_conversion=df_post_conversion,
        df_post_filtro_anio=df_post_filtro_anio,
        df_continental=df_continental,
        df_insular=df_insular,
    )

    # Paso 3.6: Guardar intermedio continental filtrado
    guardar_intermedio_filtrado(df_continental)  # data/interim/homi_filtrado_2024.parquet

    # ── FASE 4: Validación Geoespacial Completa ──
    # Corresponde a las Fases R 5-9 (líneas 206-484).
    print("=" * 60)
    print("  FASE 4: VALIDACIÓN GEOESPACIAL COMPLETA")
    print("=" * 60)

    # Pasos 4.1–4.2: Carga y homologación del mapa cantonal
    # Abre nxcantones.shp, pasa a WGS84, repara polígonos y quita Galápagos.
    mapa = cargar_mapa_cantonal()

    # Paso 4.3: Crear GeoDataFrame de puntos desde coordenadas
    # Convierte latitud/longitud en objetos geométricos Point y asigna ID_temp.
    gdf_puntos = crear_geodataframe_puntos(df_continental)
    n_entrada_fase4 = len(gdf_puntos)  # Total de puntos que entraron a validarse.

    # Paso 4.4: Primera auditoría topológica (sjoin vectorizado)
    # Separa los que caen DENTRO de su cantón (geo_correctos) vs. FUERA (geo_corregir).
    geo_correctos, geo_corregir = auditar_punto_en_poligono(gdf_puntos, mapa)

    # Paso 4.5: Separar por formato decimal
    # De los que cayeron fuera: ¿tienen punto decimal (limbo) o les falta (a reparar)?
    limbo_formato_correcto, geo_corregir_decimales = separar_por_formato(
        geo_corregir
    )

    # Paso 4.6: Algoritmo reparador de coordenadas corruptas (4 escenarios)
    # Prueba en orden: X.XXX → 0.XXX → -X.XXX → -0.XXX y valida cada intento con sjoin.
    esc1, esc2, esc3, esc4, no_reparados = reparar_coordenadas_corruptas(
        geo_corregir_decimales, mapa
    )
    # Suma total de casos rescatados entre los 4 escenarios.
    n_reparados_total = sum(len(d) for d in [esc1, esc2, esc3, esc4])

    # Paso 4.7: Ensamblaje y limpieza final
    # Une correctos + reparados + limbo, borra columnas auxiliares y filtra NaN.
    df_georreferenciado = ensamblar_base_final(
        geo_correctos=geo_correctos,
        reparados_esc1=esc1,
        reparados_esc2=esc2,
        reparados_esc3=esc3,
        reparados_esc4=esc4,
        limbo_formato_correcto=limbo_formato_correcto,
        no_reparados=no_reparados,
    )

    # Paso 4.8: Exportar artefactos Parquet
    # Guarda geo_correctos.parquet (interim) y homi_georreferenciado.parquet (processed).
    guardar_artefactos_geo(geo_correctos, df_georreferenciado)

    # Reporte estadístico de la Fase 4
    imprimir_reporte_geo(
        n_procesados=n_entrada_fase4,
        n_correctos=len(geo_correctos),
        n_reparados_total=n_reparados_total,
        n_limbo=len(limbo_formato_correcto),
        n_no_reparados=len(no_reparados),
        n_final=len(df_georreferenciado),
    )

    # ── FASE 5: Etiquetado final, exportación multiformato, auditoría y mapa ──
    # Corresponde a las Fases R 10-13 (líneas 486-627): concluye la migración completa.
    # Armamos un diccionario con cuántos registros rescató individualmente cada uno
    # de los 4 escenarios decimales para dejarlo documentado en `auditoria_pipeline.json`.
    detalle_escenarios = {
        "escenario_1_positivo_entero": len(esc1),
        "escenario_2_positivo_cero": len(esc2),
        "escenario_3_negativo_entero": len(esc3),
        "escenario_4_negativo_cero": len(esc4),
    }
    # Pasamos los objetos ya cargados en memoria (`df_georreferenciado`, `mapa`) y los
    # conteos exactos de cada etapa para verificar el cuadre contable de extremo a extremo.
    ejecutar_exportacion_final(
        df_georreferenciado=df_georreferenciado,
        mapa_cantones=mapa,
        n_brutos_iniciales=len(df_entrada_fase3),                                # Total inicial (Fase 1)
        n_excluidos_temporal=len(df_entrada_fase3) - len(df_post_filtro_anio),   # Excluidos por año > 2024 o NaN
        n_excluidos_insular=len(df_insular),                                     # Excluidos por Galápagos
        n_universo_filtrado=len(df_continental),                                 # Universo continental 2010-2024
        n_geo_correctos=len(geo_correctos),                                      # Validados al 1er sjoin
        n_rescatados_algoritmo=n_reparados_total,                                # Rescatados por los 4 escenarios
        n_limbo_retenidos=len(limbo_formato_correcto),                           # Con punto decimal retenidos
        n_descartados_irreversibles=len(df_continental) - len(df_georreferenciado),  # Irrecuperables excluidos
        detalle_escenarios=detalle_escenarios,
    )

    print("\n[OK] Pipeline completo (Fases 1 a 5) ejecutado exitosamente.")


# Punto de entrada del programa:
# Cuando ejecutas `python main.py` en la terminal, Python pone "__main__" en
# la variable especial `__name__` y entra aquí llamando a main().
if __name__ == "__main__":
    main()
