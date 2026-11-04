"""
main.py — Orquestador del pipeline de preprocesamiento.

Ejecuta todas las fases en secuencia. Cada fase se activa
progresivamente a medida que se implementan los módulos.

Uso:
    python main.py
"""
from src.ingesta.cargar_datos import (
    cargar_homicidios_raw,
    guardar_intermedio_renombrado,
)


def main():
    """Pipeline principal de preprocesamiento."""

    # ── FASE 1: Ingesta y Renombrado ──
    df = cargar_homicidios_raw()
    guardar_intermedio_renombrado(df)

    # ── FASE 2: Limpieza textual ──
    # TODO: Sesión 3

    # ── FASE 3: Filtrado temporal y geográfico ──
    # TODO: Sesión 4

    # ── FASE 4: Validación geoespacial ──
    # TODO: Sesiones 5-6

    # ── FASE 5: Etiquetado y exportación final ──
    # TODO: Sesión 7

    print("\n[OK] Pipeline Fase 1 completado exitosamente.")


if __name__ == "__main__":
    main()
