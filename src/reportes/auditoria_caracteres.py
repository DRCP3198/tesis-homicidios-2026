"""
auditoria_caracteres.py — Verificación de caracteres especiales residuales.

Corresponde a la auditoría de tildes y eñes del código R (líneas 153-186):
    patron_especial <- "[áéíóúÁÉÍÓÚñÑüÜ]"
    for (col in columnas_texto) {
        filas_con_problemas <- which(grepl(patron_especial, homi_2010_2024[[col]]))
        ...
    }

Objetivo:
    Después de aplicar la normalización textual (Fase 2), verificar
    mediante Regex que NO queden tildes, eñes ni diéresis en ninguna
    columna de texto del dataset.
"""
import re
from dataclasses import dataclass, field

import pandas as pd

from src.ingesta.config import COLUMNAS_TEXTO_NORMALIZAR
from src.utils.texto import PATRON_CARACTERES_ESPECIALES


# =========================================================================
# ESTRUCTURA DE DATOS PARA EL REPORTE
# =========================================================================
@dataclass
#decorador que implementa automaticamente funciones estandar como:
# El constructor (__init__)
# El equivalente al toString() de Java (en Python se llama __repr__)
# comparación (__eq__)
# observacion todos los atributos son publicos por defectos
class HallazgoColumna:
    """Almacena los hallazgos de caracteres especiales en una columna."""

    columna: str
    total_filas_afectadas: int
    ejemplos: list[str] = field(default_factory=list)
    indices_filas: list[int] = field(default_factory=list)


@dataclass
class ReporteAuditoria:
    """Resultado completo de la auditoría de caracteres especiales."""

    columnas_revisadas: int
    columnas_con_problemas: int
    hallazgos: list[HallazgoColumna] = field(default_factory=list)
    limpio: bool = True


# =========================================================================
# FUNCIÓN PRINCIPAL DE AUDITORÍA
# =========================================================================
def auditar_caracteres_especiales(
    df: pd.DataFrame,
    columnas: list[str] | None = None,
    max_ejemplos: int = 5,
) -> ReporteAuditoria:
    """
    Verifica que no existan tildes, eñes o diéresis en las columnas de texto.

    Equivalencia R (líneas 153-186):
        patron_especial <- "[áéíóúÁÉÍÓÚñÑüÜ]"
        for (col in columnas_texto) {
            filas_con_problemas <- which(grepl(patron_especial, homi[[col]]))
            if (length(filas_con_problemas) > 0) { ... }
        }

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame a auditar (idealmente después de la normalización).
    columnas : list[str] or None
        Lista de columnas a revisar. Si es None, usa las 13 de config.py.
    max_ejemplos : int
        Número máximo de valores problemáticos a mostrar por columna.

    Returns
    -------
    ReporteAuditoria
        Objeto con los hallazgos detallados. Si `reporte.limpio` es True,
        no se encontraron caracteres especiales.
    """
    if columnas is None:
        columnas = COLUMNAS_TEXTO_NORMALIZAR

    # Verificar que las columnas existen
    columnas_faltantes = set(columnas) - set(df.columns)
    if columnas_faltantes:
        raise KeyError(
            f"Columnas no encontradas en el DataFrame: {columnas_faltantes}"
        )

    print("=" * 60)
    print("  AUDITORÍA DE CARACTERES ESPECIALES (TILDES Y EÑES)")
    print("=" * 60)
    print(f"  Patrón Regex: {PATRON_CARACTERES_ESPECIALES}")
    print(f"  Columnas a revisar: {len(columnas)}")
    print("-" * 60)

    reporte = ReporteAuditoria(
        columnas_revisadas=len(columnas),
        columnas_con_problemas=0,
    )

    patron_compilado = re.compile(PATRON_CARACTERES_ESPECIALES)

    for col in columnas:
        # Equivalente R: grepl(patron_especial, homi_2010_2024[[col]])
        # .str.contains() devuelve True/False por fila (NaN para NA)
        mascara = df[col].dropna().apply(
            lambda x: bool(patron_compilado.search(str(x)))
        )

        # Obtener los índices originales de las filas con problemas
        # Equivalente R: which(grepl(...))
        indices_problemas = mascara[mascara].index.tolist()

        if len(indices_problemas) > 0:
            reporte.limpio = False
            reporte.columnas_con_problemas += 1

            # Extraer ejemplos (equivalente R: head(filas_con_problemas, 5))
            ejemplos = df.loc[indices_problemas[:max_ejemplos], col].tolist()

            hallazgo = HallazgoColumna(
                columna=col,
                total_filas_afectadas=len(indices_problemas),
                ejemplos=ejemplos,
                indices_filas=indices_problemas[:max_ejemplos],
            )
            reporte.hallazgos.append(hallazgo)

            # Imprimir hallazgo (equivalente R: print(paste0("⚠️ Columna...", col)))
            print(f"  [ALERTA] Columna: '{col}'")
            for idx, ejemplo in zip(
                indices_problemas[:max_ejemplos], ejemplos, strict=False
            ):
                print(f"      - Fila [{idx}]: '{ejemplo}'")
            if len(indices_problemas) > max_ejemplos:
                restantes = len(indices_problemas) - max_ejemplos
                print(f"      ... y {restantes} registros más en esta columna.")
            print("-" * 60)

    # Mensaje final (equivalente R: if (!hallazgos) print("¡Felicidades!..."))
    if reporte.limpio:
        print(
            "  [OK] No se encontraron eñes ni tildes ocultas "
            "en las columnas de texto."
        )
    else:
        print(
            f"  [ERROR] Se encontraron problemas en {reporte.columnas_con_problemas} "
            f"de {reporte.columnas_revisadas} columnas revisadas."
        )
    print("=" * 60)

    return reporte

