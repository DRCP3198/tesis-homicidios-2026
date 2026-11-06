"""
texto.py — Funciones utilitarias reutilizables de limpieza de strings.

Centraliza las operaciones de normalización textual que se repiten
a lo largo del pipeline (strip, upper, remove accents).

Equivalencia R:
    iconv(str_to_upper(str_trim(x)), to = "ASCII//TRANSLIT")

Dependencia:
    unidecode >= 1.3  (definida en requirements.txt)
"""
import re

import pandas as pd
from unidecode import unidecode


# =========================================================================
# FUNCIÓN ESCALAR: normaliza un string individual
# =========================================================================
def normalizar_texto(texto: str) -> str:
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
    if not isinstance(texto, str):
        return texto

    # 1. Strip (≡ str_trim en R)
    # elimina todos los espacios en blanco 
    # (así como tabulaciones \t o saltos de línea \n) 
    # que se encuentren al principio y al final
    texto = texto.strip()

    # 2. Upper (≡ str_to_upper en R)
    texto = texto.upper()

    # 3. Transliteración ASCII (≡ iconv(x, to="ASCII//TRANSLIT") en R)
    # unidecode convierte: á→a, é→e, ñ→n, ü→u, etc.
    texto = unidecode(texto)

    return texto


# =========================================================================
# FUNCIÓN VECTORIZADA: normaliza una columna completa de pandas
# =========================================================================
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
    return serie.map(normalizar_texto, na_action="ignore") #agara mi serie pandas y ejecuta un map


# =========================================================================
# FUNCIÓN DE VERIFICACIÓN: detecta caracteres especiales residuales
# =========================================================================
# Patrón Regex idéntico al del código R (línea 158):
# patron_especial <- "[áéíóúÁÉÍÓÚñÑüÜ]"
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
    if not isinstance(texto, str):
        return False
    return bool(re.search(PATRON_CARACTERES_ESPECIALES, texto))
