"""
main.py — Orquestador del pipeline de preprocesamiento.

Ejecuta todas las fases en secuencia. Cada fase se activa
progresivamente a medida que se implementan los módulos.

Uso:
    python main.py
"""

# ── Imports Fase 1: Ingesta ──
# Importa las funciones encargadas de cargar los datos originales
# de homicidios y guardar una copia intermedia con los nombres de
# las columnas estandarizados.
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
    filtrar_anio,
    excluir_galapagos,
    guardar_intermedio_filtrado,
    guardar_insular,
)
from src.reportes.reporte_control import imprimir_conteos

#pipeline = proceso general que coordina las etapas de preprocesamiento.
#ingesta = módulo encargado de cargar los datos originales.
   
def main():
    """Función principal encargada de ejecutar el pipeline de preprocesamiento."""


    # ── FASE 1: Ingesta y Renombrado ──
    # Carga los datos originales de homicidios y guarda
    # una versión intermedia con las columnas renombradas.
    df = cargar_homicidios_raw()
    guardar_intermedio_renombrado(df)

    # ── FASE 2: Limpieza y Normalización Textual ──
    # Aplica strip() + upper() + unidecode() a las 13 columnas de texto.
    # Equivale al bloque mutate() con iconv() + str_trim() + str_to_upper() del R.
    df = normalizar_todas_columnas(df)
    auditar_caracteres_especiales(df)
    guardar_intermedio_normalizado(df)

    # ── FASE 3: Filtrado temporal y geográfico ──
    # Aplica los filtros de año (≤2024) y excluye cantones insulares.
    # Equivale al bloque filter() del R (líneas 132-150).
    print("=" * 60)
    print("  FASE 3: FILTRADO TEMPORAL Y GEOGRÁFICO")
    print("=" * 60)

    # Guardamos referencia al df original para el reporte de control
    df_entrada_fase3 = df.copy()

    # Paso 3.1: Conversión de anio_hecho a entero
    df = convertir_anio_a_entero(df)
    df_post_conversion = df.copy()

    # Paso 3.2: Filtro temporal (anio_hecho <= 2024)
    df = filtrar_anio(df)
    df_post_filtro_anio = df.copy()

    # Pasos 3.3 y 3.4: Exclusión de Galápagos + separación insular
    df_continental, df_insular = excluir_galapagos(df)

    # Paso 3.4: Guardar registros insulares para trazabilidad
    guardar_insular(df_insular)

    # Paso 3.5: Reporte de conteos (auditoría de integridad)
    imprimir_conteos(
        df_original=df_entrada_fase3,
        df_post_conversion=df_post_conversion,
        df_post_filtro_anio=df_post_filtro_anio,
        df_continental=df_continental,
        df_insular=df_insular,
    )

    # Paso 3.6: Guardar intermedio continental filtrado
    guardar_intermedio_filtrado(df_continental)

    # ── FASE 4: Validación geoespacial ──
    # TODO: Sesiones 5-6

    # ── FASE 5: Etiquetado y exportación final ──
    # TODO: Sesión 7

    print("\n[OK] Pipeline Fases 1-3 completado exitosamente.")


if __name__ == "__main__":
    main()
