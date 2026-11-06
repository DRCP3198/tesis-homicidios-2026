"""
texto.py — Funciones utilitarias reutilizables de limpieza de strings.

Centraliza las operaciones de normalización textual que se repiten
a lo largo del pipeline (strip, upper, remove accents).

Equivalencia R:
    iconv(str_to_upper(str_trim(x)), to = "ASCII//TRANSLIT")

Dependencia:
    unidecode >= 1.3  (definida en requirements.txt)

¿Por qué está en "utils" (utilidades)?
    Porque estas funciones NO pertenecen a una sola fase: se usan en la
    Fase 2 (normalizar columnas de la base de datos) y también en la
    Fase 4 (normalizar los nombres de cantones del mapa). Tenerlas en un
    solo lugar evita copiar y pegar código.
"""
# `re` = librería estándar de Python para "expresiones regulares" (regex).
# Una regex es un patrón de búsqueda de texto. Ej: "[áé]" significa
# "busca una á o una é en cualquier parte del texto".
import re

# `pandas` es LA librería de análisis de datos en Python (equivale a dplyr/tidyverse).
# `as pd` le pone un apodo corto: en lugar de escribir pandas.Series escribimos pd.Series.
import pandas as pd

# `unidecode` es una librería externa (se instala con pip) que convierte
# caracteres especiales a su versión ASCII más parecida: á→a, ñ→n, ü→u.
from unidecode import unidecode


# =========================================================================
# FUNCIÓN ESCALAR: normaliza un string individual
# =========================================================================
# "Escalar" significa que trabaja con UN SOLO valor a la vez (un texto),
# no con una columna entera.
#
# Anatomía de la definición de una función:
#   def                 → palabra clave para DEFINIR (crear) una función.
#   normalizar_texto    → el nombre de la función.
#   (texto: str)        → recibe un parámetro llamado "texto". El ": str" es
#                         un "type hint" (pista de tipo): indica que se espera
#                         un string (texto). Python NO lo obliga, es documentación.
#   -> str              → indica que la función DEVUELVE un string.
def normalizar_texto(texto: str) -> str:
    # Lo que va entre triple comillas al inicio de una función se llama
    # "docstring": es la documentación oficial de la función. Se puede ver
    # escribiendo help(normalizar_texto) en la consola de Python.
    """
    Normaliza una cadena de texto individual:
    1. strip() — Remueve espacios al inicio y final (≡ str_trim)
    2. upper() — Convierte a mayúsculas (≡ str_to_upper)
    3. unidecode() — Transliteración ASCII (≡ iconv to ASCII//TRANSLIT)

    Parameters
    ----------
    texto : str
        Cadena de texto a normalizar.

    Returns
    -------
    str
        Texto limpio: sin espacios extremos, en mayúsculas, sin tildes.

    Examples
    --------
    >>> normalizar_texto("  Guayaquíl  ")
    'GUAYAQUIL'
    >>> normalizar_texto("Ñuño")
    'NUNO'
    >>> normalizar_texto("SANTO DOMINGO DE LOS TSÁCHILAS")
    'SANTO DOMINGO DE LOS TSACHILAS'
    """
    # Si no es string (NaN, None, int), devolvemos tal cual
    # para que pandas lo trate como NA sin lanzar error.
    # isinstance(valor, tipo) → devuelve True si "valor" es del "tipo" indicado.
    # `not` invierte el resultado: "si texto NO es un string...".
    if not isinstance(texto, str):
        return texto  # `return` termina la función y devuelve ese valor.

    # 1. Strip (≡ str_trim en R)
    # elimina todos los espacios en blanco 
    # (así como tabulaciones \t o saltos de línea \n) 
    # que se encuentren al principio y al final
    # Ej: "  Quito  " → "Quito"   (los espacios del medio NO se tocan)
    texto = texto.strip()

    # 2. Upper (≡ str_to_upper en R)
    # Convierte todas las letras a MAYÚSCULAS. Ej: "Quito" → "QUITO"
    texto = texto.upper()

    # 3. Transliteración ASCII (≡ iconv(x, to="ASCII//TRANSLIT") en R)
    # unidecode convierte: á→a, é→e, ñ→n, ü→u, etc.
    # Ej: "GUAYAQUÍL" → "GUAYAQUIL",  "CAÑAR" → "CANAR"
    texto = unidecode(texto)

    return texto  # Devolvemos el texto ya limpio.


# =========================================================================
# FUNCIÓN VECTORIZADA: normaliza una columna completa de pandas
# =========================================================================
# "Vectorizada" significa que trabaja sobre una columna completa de una vez,
# en lugar de valor por valor escrito a mano con un for.
def normalizar_columna(serie: pd.Series) -> pd.Series: #estructura de datos unidimensional (de pandas) que funciona como una columna
    """
    Aplica la normalización textual completa a una columna (pd.Series).

    Cadena de transformaciones (en una sola operación vectorizada):
        strip()  →  upper()  →  unidecode()

    Equivalencia R:
        mutate(columna = iconv(str_to_upper(str_trim(columna)),
                               to = "ASCII//TRANSLIT"))

    Parameters
    ----------
    serie : pd.Series
        Columna de texto a normalizar. Los valores NA se preservan.

    Returns
    -------
    pd.Series
        Columna normalizada: mayúsculas, sin tildes, sin espacios extremos.

    Examples
    --------
    >>> import pandas as pd
    >>> s = pd.Series(["  Guayaquíl  ", "Ñuño", None, "QUITO"])
    >>> normalizar_columna(s).tolist()
    ['GUAYAQUIL', 'NUNO', None, 'QUITO']
    """
    # .map(funcion) → recorre CADA valor de la columna y le aplica la función
    #                 indicada, devolviendo una nueva columna con los resultados.
    #                 Es como un for automático: para cada celda, normalizar_texto(celda).
    #                 OJO: se pasa el NOMBRE de la función sin paréntesis
    #                 (normalizar_texto, no normalizar_texto()), porque no la
    #                 ejecutamos nosotros: se la entregamos a .map() para que él la use.
    # na_action="ignore" → si una celda está vacía (NaN/None), NO le aplica la
    #                      función y la deja vacía tal cual (evita errores).
    return serie.map(normalizar_texto, na_action="ignore") #agara mi serie pandas y ejecuta un map


# =========================================================================
# FUNCIÓN DE VERIFICACIÓN: detecta caracteres especiales residuales
# =========================================================================
# Patrón Regex idéntico al del código R (línea 158):
# patron_especial <- "[áéíóúÁÉÍÓÚñÑüÜ]"
#
# Explicación del patrón:
#   r"..."  → la "r" delante significa "raw string" (texto crudo): Python NO
#             interpreta las barras invertidas "\" como caracteres especiales.
#             Es buena práctica usarla SIEMPRE en expresiones regulares.
#   [ ... ] → en regex, los corchetes significan "CUALQUIERA de estos caracteres".
#             Así, el patrón coincide si el texto tiene al menos UNA tilde, eñe o diéresis.
#   ": str" → type hint para indicar que esta constante es un texto.
PATRON_CARACTERES_ESPECIALES: str = r"[áéíóúÁÉÍÓÚñÑüÜ]"


def contiene_caracteres_especiales(texto: str) -> bool:
    """
    Verifica si un texto contiene tildes, eñes u otros caracteres especiales.

    Equivalencia R:
        grepl("[áéíóúÁÉÍÓÚñÑüÜ]", texto)

    Parameters
    ----------
    texto : str
        Cadena a verificar.

    Returns
    -------
    bool
        True si contiene caracteres especiales.
    """
    # Si el valor no es texto (ej: NaN o un número), no puede tener tildes.
    if not isinstance(texto, str):
        return False

    # re.search(patron, texto) → busca el patrón en CUALQUIER parte del texto.
    #   - Si lo encuentra, devuelve un objeto "Match" (coincidencia).
    #   - Si no lo encuentra, devuelve None (nada).
    # bool(...) → convierte ese resultado en True/False:
    #   un objeto Match se convierte en True, None se convierte en False.
    return bool(re.search(PATRON_CARACTERES_ESPECIALES, texto))
