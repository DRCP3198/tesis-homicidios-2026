"""
cargar_datos.py — Módulo de ingesta y renombrado de datos.

Equivale a las Fases 1-3 (líneas 1-77) del código R original:
  - readRDS(nombre_archivo) → pd.read_csv(...)
  - rename(nuevo = original) → df.rename(columns=MAPEO_COLUMNAS)

Funciones principales:
  - cargar_homicidios_raw(): Lee el CSV fuente, aplica tipos y renombra columnas.
"""
import pandas as pd

from src.ingesta.config import (
    ARCHIVO_HOMICIDIOS_CSV,    # Constante de ruta y nombre del archivo original de homicidios
    MAPEO_COLUMNAS,            # diccionario para reetiquetado de las columnas
    INTERIM_RENOMBRADO,        # Constante de la ruta y nombre para guardar el archivo intermedio
)

# Defino la funcion mediante "def", ingresa tipo string o None, y por defeto es None.abs
# DataFrame es basicamente un tipo de dato compuesto, donde puedo manejar columnas, filas, etc 
def cargar_homicidios_raw(ruta_csv: str | None = None) -> pd.DataFrame:
    """
    Lee el archivo CSV fuente de homicidios y renombra las columnas.

    Equivalencia R:
        homi_2010_2025_raw <- readRDS(nombre_archibo_original_rds)
        homi_2010_2025 <- homi_2010_2025_raw %>% rename(...)

    Parameters
    ----------
    ruta_csv : str or None
        Ruta al archivo CSV. Si es None, usa la ruta por defecto de config.py.

    Returns
    -------
    pd.DataFrame
        DataFrame con las 21 columnas renombradas a nombres descriptivos.
    """
    ruta = ruta_csv or ARCHIVO_HOMICIDIOS_CSV #Ingreso una ruta especifica o toma la constante de config.py 

    print("=" * 60) #imprime una linea de 60 signos de igual
    print("  FASE 1: INGESTA Y RENOMBRADO DE DATOS")
    print("=" * 60) #imprime una linea de 60 signos de igual
    print(f"  Leyendo: {ruta}") #Usamos f-string (la 'f' al inicio) para incrustar variables y expresiones

    # ── Lectura del CSV con tipos explícitos ──
    # Leemos TODO como string inicialmente para evitar que pandas
    # interprete mal las coordenadas corruptas (ej: "214589" sin punto).
    # La conversión de tipos se hará en fases posteriores de forma controlada.
    df = pd.read_csv(
        ruta,
        dtype=str,           # Leer todo como texto (equivale a stringsAsFactors=FALSE en R)
        encoding="utf-8",    # Encoding estándar
        na_values=["", "NA", "N/A", "null", "NULL"],  # Valores que R trata como NA
    )

    print(f"  Registros cargados: {len(df):,}")
    print(f"  Columnas originales ({len(df.columns)}): {list(df.columns)}")

    # ── Verificar que todas las columnas esperadas existen ──
    columnas_faltantes = set(MAPEO_COLUMNAS.keys()) - set(df.columns) #del diccionario verifico, comparando las llaves con las del csv
    #set me sirve para comparar colecciones de datos, en este caso los nombres de las columnas
    # en caso de no haver alguna coincidencia, lanza un error. E imprime las faltantes
    if columnas_faltantes:
        raise ValueError(
            f"Columnas faltantes en el CSV: {columnas_faltantes}. "
            f"Columnas disponibles: {list(df.columns)}"
        )

    # ── Renombrar columnas (equivale a dplyr::rename()) ──
    df = df.rename(columns=MAPEO_COLUMNAS) #agaro mi dataframe y le aplico el diccionario clave valor

    # ── Seleccionar solo las columnas mapeadas (descartar extras si existen) ──
    columnas_finales = list(MAPEO_COLUMNAS.values()) #obtengo los valores del diccionario
    df = df[columnas_finales] #selecciono solo las columnas mapeadas

    print(f"  Columnas renombradas ({len(df.columns)}): {list(df.columns)}")
    print(f"  Primeras 3 filas:")
    print(df.head(3).to_string(index=False))
    print("=" * 60)

    return df


def guardar_intermedio_renombrado(df: pd.DataFrame) -> None:
    """
    Guarda el DataFrame renombrado en formato Parquet en data/interim/.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame con columnas ya renombradas.
    """

    #Guarda ya renombrado bonito
    INTERIM_RENOMBRADO.parent.mkdir(parents=True, exist_ok=True) #Si no existe la carpeta, la crea.
    df.to_parquet(INTERIM_RENOMBRADO, index=False, engine="pyarrow") #lo guarda 
    print(f"  Guardado intermedio: {INTERIM_RENOMBRADO}")
    print(f"  Tamaño: {INTERIM_RENOMBRADO.stat().st_size / 1024:.1f} KB")


def cargar_intermedio_renombrado() -> pd.DataFrame:
    """
    Carga el archivo Parquet intermedio de datos renombrados.

    Returns
    -------
    pd.DataFrame
        DataFrame previamente renombrado y guardado.
    """
    if not INTERIM_RENOMBRADO.exists(): 
        raise FileNotFoundError(
            f"No existe el archivo intermedio: {INTERIM_RENOMBRADO}. "
            "Ejecuta primero cargar_homicidios_raw() y guardar_intermedio_renombrado()."
        )
    return pd.read_parquet(INTERIM_RENOMBRADO, engine="pyarrow") #devuelvo mi tipo parquet renombrado

