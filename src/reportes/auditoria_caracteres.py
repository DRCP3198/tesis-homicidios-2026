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

En palabras simples: es un "control de calidad". La Fase 2 dice que limpió
todo; este módulo lo comprueba fila por fila y avisa si algo se escapó.
"""
# `re`: librería estándar para buscar patrones de texto (expresiones regulares).
import re

# `dataclass` y `field` vienen del módulo estándar `dataclasses`:
#   - dataclass: decorador que crea clases "contenedoras de datos" de forma rápida.
#   - field: permite configurar atributos especiales (ej. listas vacías por defecto).
from dataclasses import dataclass, field

import pandas as pd

from src.ingesta.config import COLUMNAS_TEXTO_NORMALIZAR  # Las 13 columnas de texto
from src.utils.texto import PATRON_CARACTERES_ESPECIALES  # El patrón "[áéíóúÁÉÍÓÚñÑüÜ]"


# =========================================================================
# ESTRUCTURA DE DATOS PARA EL REPORTE
# =========================================================================
# ¿Qué es un DECORADOR?
#   Es una línea que empieza con "@" y va justo encima de una clase o función.
#   "Decora" (modifica o agrega funcionalidad) a lo que está debajo, sin que
#   tengamos que escribir ese código extra a mano.
#
# ¿Qué es una CLASE?
#   Es un "molde" para crear objetos. Por ejemplo, la clase HallazgoColumna
#   define que todo hallazgo tendrá: columna, total_filas_afectadas, ejemplos
#   e indices_filas. Cada vez que creamos un HallazgoColumna(...) obtenemos un
#   objeto (una "ficha") con esos datos llenos.
@dataclass
#decorador que implementa automaticamente funciones estandar como:
# El constructor (__init__)
# El equivalente al toString() de Java (en Python se llama __repr__)
# comparación (__eq__)
# observacion todos los atributos son publicos por defectos
class HallazgoColumna:
    """Almacena los hallazgos de caracteres especiales en una columna."""

    # Cada línea "nombre: tipo" declara un ATRIBUTO (un dato que guarda el objeto).
    columna: str                 # Nombre de la columna con problemas (ej. "canton").
    total_filas_afectadas: int   # Cuántas filas tienen tildes/eñes en esa columna.
    # field(default_factory=list) → si no se entrega este dato al crear el objeto,
    # se crea automáticamente una lista vacía NUEVA para cada objeto.
    # (No se puede escribir "= []" directamente, porque todos los objetos
    # compartirían la MISMA lista y se mezclarían los datos.)
    ejemplos: list[str] = field(default_factory=list)       # Algunos valores problemáticos.
    indices_filas: list[int] = field(default_factory=list)  # Números de fila de esos valores.


@dataclass  # Mismo decorador: genera automáticamente constructor, __repr__ y __eq__.
class ReporteAuditoria:
    """Resultado completo de la auditoría de caracteres especiales."""

    columnas_revisadas: int      # Cuántas columnas se revisaron en total.
    columnas_con_problemas: int  # Cuántas de ellas tenían al menos un carácter especial.
    # Lista de objetos HallazgoColumna (una "ficha" por cada columna con problemas).
    hallazgos: list[HallazgoColumna] = field(default_factory=list)
    limpio: bool = True          # True = no se encontró nada; False = hay problemas.
    # Ejemplo de uso:
    #   r = ReporteAuditoria(columnas_revisadas=13, columnas_con_problemas=0)
    #   r.limpio   → True (valor por defecto)


# =========================================================================
# FUNCIÓN PRINCIPAL DE AUDITORÍA
# =========================================================================
def auditar_caracteres_especiales(
    df: pd.DataFrame,                 # La tabla a revisar.
    columnas: list[str] | None = None,  # Qué columnas revisar (None = las 13 por defecto).
    max_ejemplos: int = 5,            # Cuántos ejemplos mostrar como máximo por columna.
) -> ReporteAuditoria:                # Devuelve un objeto ReporteAuditoria.
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

    Raises
    ------
    KeyError
        Si alguna columna solicitada no existe en el DataFrame.
    """
    # `is None` es la forma correcta de preguntar "¿esta variable está vacía (None)?".
    if columnas is None:
        columnas = COLUMNAS_TEXTO_NORMALIZAR  # Usamos las 13 columnas por defecto.

    # Verificar que las columnas existen
    # set(A) - set(B) → elementos que están en A pero no en B (columnas inexistentes).
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

    # Creamos el objeto reporte "vacío" (gracias al @dataclass, basta con
    # pasar los valores por nombre; limpio=True y hallazgos=[] por defecto).
    reporte = ReporteAuditoria(
        columnas_revisadas=len(columnas),
        columnas_con_problemas=0,
    )

    # re.compile(patron) → "pre-compila" la expresión regular una sola vez.
    # Así, al usarla miles de veces (una por fila) es más rápida que
    # interpretarla de nuevo en cada búsqueda.
    patron_compilado = re.compile(PATRON_CARACTERES_ESPECIALES)

    # Recorremos cada columna a revisar.
    for col in columnas:
        # Equivalente R: grepl(patron_especial, homi_2010_2024[[col]])
        # .str.contains() devuelve True/False por fila (NaN para NA)
        #
        # Desglose de esta línea:
        #   df[col]          → toma la columna completa.
        #   .dropna()        → quita las celdas vacías (no pueden tener tildes).
        #   .apply(funcion)  → aplica la función a cada valor y junta los resultados.
        #   lambda x: ...    → "lambda" crea una función pequeña SIN nombre, en una
        #                      sola línea. Aquí "x" es cada valor de la columna.
        #                      Equivale a escribir:
        #                          def tiene_especial(x):
        #                              return bool(patron_compilado.search(str(x)))
        #   str(x)           → convierte el valor a texto por seguridad.
        #   .search(...)     → busca el patrón; devuelve coincidencia o None.
        #   bool(...)        → convierte eso en True (hay tilde) / False (no hay).
        # Resultado: una "máscara" = columna de True/False del mismo tamaño.
        mascara = df[col].dropna().apply(
            lambda x: bool(patron_compilado.search(str(x)))
        )

        # Obtener los índices originales de las filas con problemas
        # Equivalente R: which(grepl(...))
        #   mascara[mascara] → filtra la máscara quedándose solo con los True.
        #   .index           → los números de fila (índices) de esos True.
        #   .tolist()        → los convierte en una lista normal de Python.
        indices_problemas = mascara[mascara].index.tolist()

        # Si la lista tiene al menos un elemento, esta columna tiene problemas.
        if len(indices_problemas) > 0:
            reporte.limpio = False               # Marcamos que el dataset NO está limpio.
            reporte.columnas_con_problemas += 1  # "+= 1" significa "súmale 1 al valor actual".

            # Extraer ejemplos (equivalente R: head(filas_con_problemas, 5))
            # indices_problemas[:max_ejemplos] → los primeros N índices.
            # df.loc[filas, columna] → selecciona celdas por número de fila y nombre de columna.
            ejemplos = df.loc[indices_problemas[:max_ejemplos], col].tolist()

            # Creamos una "ficha" HallazgoColumna con la información de esta columna.
            hallazgo = HallazgoColumna(
                columna=col,
                total_filas_afectadas=len(indices_problemas),
                ejemplos=ejemplos,
                indices_filas=indices_problemas[:max_ejemplos],
            )
            # .append(x) → agrega x al final de la lista de hallazgos del reporte.
            reporte.hallazgos.append(hallazgo)

            # Imprimir hallazgo (equivalente R: print(paste0("⚠️ Columna...", col)))
            print(f"  [ALERTA] Columna: '{col}'")
            # zip(lista1, lista2) → recorre DOS listas al mismo tiempo, en pareja:
            #   (indice1, ejemplo1), (indice2, ejemplo2), ...
            # strict=False → si las listas tuvieran distinto tamaño, no lanza error.
            for idx, ejemplo in zip(
                indices_problemas[:max_ejemplos], ejemplos, strict=False
            ):
                print(f"      - Fila [{idx}]: '{ejemplo}'")
            # Si hay más problemas de los que mostramos, indicamos cuántos faltan.
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
    else:  # `else` = "en caso contrario" (si reporte.limpio es False).
        print(
            f"  [ERROR] Se encontraron problemas en {reporte.columnas_con_problemas} "
            f"de {reporte.columnas_revisadas} columnas revisadas."
        )
    print("=" * 60)

    return reporte  # Devolvemos el objeto con todos los resultados.
