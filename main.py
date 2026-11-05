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
    # TODO: Sesión 4

    # ── FASE 4: Validación geoespacial ──
    # TODO: Sesiones 5-6

    # ── FASE 5: Etiquetado y exportación final ──
    # TODO: Sesión 7

    print("\n[OK] Pipeline Fases 1-2 completado exitosamente.")


if __name__ == "__main__":
    main()
