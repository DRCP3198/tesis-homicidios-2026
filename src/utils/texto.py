"""
texto.py — Funciones utilitarias reutilizables de limpieza de strings.

Centraliza las operaciones de normalización textual que se repiten
a lo largo del pipeline (strip, upper, remove accents).

Equivalencia R:
    iconv(str_to_upper(str_trim(x)), to = "ASCII//TRANSLIT")
"""
import re
import unicodedata


def normalizar_texto(texto: str) -> str:
    """
    Normaliza una cadena de texto individual:
    1. strip() — Remueve espacios al inicio y final (≡ str_trim)
    2. upper() — Convierte a mayúsculas (≡ str_to_upper)
    3. Elimina acentos/tildes (≡ iconv to ASCII//TRANSLIT)

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
    if not isinstance(texto, str):
        return texto

    # 1. Strip (≡ str_trim en R)
    texto = texto.strip()

    # 2. Upper (≡ str_to_upper en R)
    texto = texto.upper()

    # 3. Eliminar acentos (≡ iconv(x, to="ASCII//TRANSLIT") en R)
    # NFD descompone caracteres: é → e + ´ (combining accent)
    # Luego filtramos los combining marks, dejando solo la letra base.
    texto = unicodedata.normalize("NFD", texto)
    texto = re.sub(r"[\u0300-\u036f]", "", texto)

    # Caso especial: Ñ → N (NFD de Ñ = N + ̃  ya se resuelve arriba)
    # Verificación adicional por si hay Ñ precompuestas residuales
    texto = texto.replace("Ñ", "N").replace("ñ", "n")

    return texto


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
    patron = r"[áéíóúÁÉÍÓÚñÑüÜ]"
    return bool(re.search(patron, texto))

