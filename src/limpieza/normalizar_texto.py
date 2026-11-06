"""
normalizar_texto.py — Módulo de limpieza y normalización textual.

Corresponde a la Fase 2 de la migración R → Python (líneas 81-130 del R):
    homi_2010_2025 <- homi_2010_2025 %>%
        mutate(
            columna = iconv(str_to_upper(str_trim(columna)),
                            to = "ASCII//TRANSLIT"),
            ...
        )

Funciones principales:
    - normalizar_todas_columnas(): Aplica strip + upper + unidecode
      a las 13 columnas de texto definidas en config.py.
"""
import pandas as pd

from src.ingesta.config import (
    COLUMNAS_TEXTO_NORMALIZAR,  # Lista de las 13 columnas de texto
    INTERIM_NORMALIZADO,        # Ruta de salida: data/interim/homi_normalizado.parquet
    INTERIM_RENOMBRADO,         # Ruta de entrada: data/interim/homi_renombrado.parquet
)
from src.utils.texto import normalizar_columna


# =========================================================================
# FUNCIÓN PRINCIPAL: Normaliza todas las columnas de texto
# =========================================================================
def normalizar_todas_columnas(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aplica la normalización textual a las 13 columnas de texto del dataset.

    Equivalencia R (líneas 83-130):
        homi_2010_2025 <- homi_2010_2025 %>%
            mutate(
                codigo_caso = iconv(str_to_upper(str_trim(codigo_caso)),
                                    to = "ASCII//TRANSLIT"),
                tipo_delito = iconv(str_to_upper(str_trim(tipo_delito)),
                                    to = "ASCII//TRANSLIT"),
                ...  # 13 columnas en total
            )

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame con columnas ya renombradas (salida de Fase 1).

    Returns
    -------
    pd.DataFrame
        DataFrame con las 13 columnas de texto normalizadas:
        mayúsculas, sin tildes/eñes/diéresis, sin espacios extremos.

    Raises
    ------
    KeyError
        Si alguna de las 13 columnas esperadas no existe en el DataFrame.
    """
    print("=" * 60)
    print("  FASE 2: LIMPIEZA Y NORMALIZACIÓN TEXTUAL")
    print("=" * 60)

    # ── Verificar que todas las columnas de texto existen ──
    columnas_faltantes = set(COLUMNAS_TEXTO_NORMALIZAR) - set(df.columns) #set me coje una lista y me transofrma a una estructura de datos comparable/operable con el operador -
    if columnas_faltantes:
        raise KeyError( #quivalente a throw new Exception(...) en Java
            f"Columnas de texto no encontradas (a normalizar) en el DataFrame: {columnas_faltantes}. "
            f"Columnas disponibles: {list(df.columns)}"
        )

    # ── Aplicar normalización columna por columna ──
    # Equivalente a cada línea del mutate() de R:
    #   columna = iconv(str_to_upper(str_trim(columna)), to = "ASCII//TRANSLIT")
    for columna in COLUMNAS_TEXTO_NORMALIZAR:
        valores_antes = df[columna].dropna().unique()[:3]  # Muestra para el log
        # df[columna]: Selecciona toda esa columna del DataFrame.
        # .dropna(): Borra temporalmente los valores nulos (NaN o vacíos) para que no molesten
        #.unique(): Saca solo los valores únicos (quita repetidos, ideal para ver patrones rápido).
        # [:3]: Recorta y se queda solo con los primeros 3 ejemplos.
        df[columna] = normalizar_columna(df[columna]) #Internamente hace un map de la columna (tipo serie) aplicando a su vez la funcion individual de normalizacion para cada dato
        valores_despues = df[columna].dropna().unique()[:3] #Unicamente para ver el resultado

        print(f"  [OK] {columna:<25} | Antes: {list(valores_antes)}")
        print(f"       {'':25} | Después: {list(valores_despues)}")

    print("-" * 60)
    print(f"  Columnas normalizadas: {len(COLUMNAS_TEXTO_NORMALIZAR)}")
    print(f"  Total registros: {len(df):,}")
    print("=" * 60)

    return df


# =========================================================================
# FUNCIONES DE PERSISTENCIA: guardar y cargar el intermedio normalizado
# =========================================================================
def guardar_intermedio_normalizado(df: pd.DataFrame) -> None:
    """
    Guarda el DataFrame normalizado en formato Parquet.

    Salida: data/interim/homi_normalizado.parquet

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame con columnas de texto ya normalizadas.
    """
    INTERIM_NORMALIZADO.parent.mkdir(parents=True, exist_ok=True)
    # INTERIM_NORMALIZADO: Es una variable de tipo pathlib.Path, usado para amnejar rutas
    # .parent: Agarra la ruta, es decir, ignora el nombre del archivo final
    # .mkdir(parents=True, exist_ok=True) Crea la ruta en caso de no exisitir

    df.to_parquet(INTERIM_NORMALIZADO, index=False, engine="pyarrow")
    # Coje los datos df y guarda el DataFrame en formato Parquet
    # index=False: Le dice a Pandas que no guarde el índice numérico de las filas
    # engine="pyarrow": Especifica el "motor" o biblioteca que se encargará de traducir y comprimir
    tamanio_kb = INTERIM_NORMALIZADO.stat().st_size / 1024
    print(f"  Guardado intermedio: {INTERIM_NORMALIZADO}")
    print(f"  Tamaño: {tamanio_kb:.1f} KB")


def cargar_intermedio_normalizado() -> pd.DataFrame:
    """
    Carga el archivo Parquet intermedio de datos normalizados.

    Returns
    -------
    pd.DataFrame
        DataFrame previamente normalizado y guardado.

    Raises
    ------
    FileNotFoundError
        Si el archivo intermedio no existe.
    """
    if not INTERIM_NORMALIZADO.exists():
        raise FileNotFoundError(
            f"No existe el archivo intermedio: {INTERIM_NORMALIZADO}. "
            "Ejecuta primero la Fase 2 (normalizar_todas_columnas + guardar)."
        )
    return pd.read_parquet(INTERIM_NORMALIZADO, engine="pyarrow") #Saco y devuelvo mis datos guardados, en tipo dataframe


# =========================================================================
# EJECUCIÓN DIRECTA (para pruebas rápidas desde terminal)
# =========================================================================
if __name__ == "__main__":
    # Permite ejecutar: python -m src.limpieza.normalizar_texto
    print("Cargando datos de Fase 1 (homi_renombrado.parquet)...")

    if not INTERIM_RENOMBRADO.exists():
        raise FileNotFoundError(
            f"No existe {INTERIM_RENOMBRADO}. Ejecuta primero la Fase 1."
        )

    df = pd.read_parquet(INTERIM_RENOMBRADO, engine="pyarrow")
    df = normalizar_todas_columnas(df)
    guardar_intermedio_normalizado(df)
    print("\n[OK] Fase 2 completada exitosamente.")

