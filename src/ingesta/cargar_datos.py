"""
cargar_datos.py — Módulo de ingesta y renombrado de datos.

Equivale a las Fases 1-3 (líneas 1-77) del código R original:
  - readRDS(nombre_archivo) → pd.read_csv(...)
  - rename(nuevo = original) → df.rename(columns=MAPEO_COLUMNAS)

Funciones principales:
  - cargar_homicidios_raw(): Lee el CSV fuente, aplica tipos y renombra columnas.
  - guardar_intermedio_renombrado(): Guarda el resultado en Parquet.
  - cargar_intermedio_renombrado(): Vuelve a leer ese Parquet.
"""
# pandas: librería principal de manejo de tablas de datos (DataFrames).
import pandas as pd

# Traemos constantes definidas en config.py (rutas y diccionario de nombres).
# Los paréntesis permiten importar varias cosas escribiendo una por línea.
from src.ingesta.config import (
    ARCHIVO_HOMICIDIOS_CSV,    # Constante de ruta y nombre del archivo original de homicidios
    MAPEO_COLUMNAS,            # diccionario para reetiquetado de las columnas
    INTERIM_RENOMBRADO,        # Constante de la ruta y nombre para guardar el archivo intermedio
)

# Defino la funcion mediante "def", ingresa tipo string o None, y por defeto es None.abs
# DataFrame es basicamente un tipo de dato compuesto, donde puedo manejar columnas, filas, etc 
#
# Detalle de la firma de la función:
#   ruta_csv: str | None  → el parámetro puede ser un texto (str) O nada (None).
#                           La barra "|" significa "o".
#   = None                → valor por defecto: si llamo cargar_homicidios_raw()
#                           sin argumentos, ruta_csv valdrá None.
#   -> pd.DataFrame       → la función devuelve una tabla de pandas.
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

    Raises
    ------
    ValueError
        Si al CSV le falta alguna de las 21 columnas esperadas.
    """
    # El operador `or` devuelve el primer valor "verdadero":
    #   - Si ruta_csv tiene un texto → se usa ese texto.
    #   - Si ruta_csv es None (falso) → se usa ARCHIVO_HOMICIDIOS_CSV.
    ruta = ruta_csv or ARCHIVO_HOMICIDIOS_CSV #Ingreso una ruta especifica o toma la constante de config.py 

    print("=" * 60) #imprime una linea de 60 signos de igual
    print("  FASE 1: INGESTA Y RENOMBRADO DE DATOS")
    print("=" * 60) #imprime una linea de 60 signos de igual
    print(f"  Leyendo: {ruta}") #Usamos f-string (la 'f' al inicio) para incrustar variables y expresiones

    # ── Lectura del CSV con tipos explícitos ──
    # Leemos TODO como string inicialmente para evitar que pandas
    # interprete mal las coordenadas corruptas (ej: "214589" sin punto).
    # La conversión de tipos se hará en fases posteriores de forma controlada.
    #
    # pd.read_csv(...) → lee un archivo CSV y lo convierte en un DataFrame (tabla).
    df = pd.read_csv(
        ruta,                # Ruta del archivo a leer.
        dtype=str,           # Leer todo como texto (equivale a stringsAsFactors=FALSE en R)
        encoding="utf-8",    # Encoding estándar (permite leer tildes y eñes correctamente)
        na_values=["", "NA", "N/A", "null", "NULL"],  # Valores que R trata como NA
        # ↑ Cualquier celda con alguno de estos textos se considerará "vacía" (NaN).
    )

    # len(df) → cuenta el número de FILAS de la tabla (equivale a nrow() en R).
    # {valor:,} → formatea el número con separador de miles: 47739 → 47,739
    print(f"  Registros cargados: {len(df):,}")
    # df.columns → los nombres de las columnas. list(...) los convierte en lista para imprimir.
    print(f"  Columnas originales ({len(df.columns)}): {list(df.columns)}")

    # ── Verificar que todas las columnas esperadas existen ──
    columnas_faltantes = set(MAPEO_COLUMNAS.keys()) - set(df.columns) #del diccionario verifico, comparando las llaves con las del csv
    #set me sirve para comparar colecciones de datos, en este caso los nombres de las columnas
    # en caso de no haver alguna coincidencia, lanza un error. E imprime las faltantes
    #
    # Detalle:
    #   MAPEO_COLUMNAS.keys() → las claves del diccionario ("X2", "X4", ...).
    #   set(...)              → convierte a "conjunto" (colección sin repetidos
    #                           que permite operaciones matemáticas de conjuntos).
    #   A - B                 → "diferencia": elementos que están en A pero NO en B.
    #   Resultado: las columnas que esperábamos y que NO vinieron en el CSV.
    #
    # `if columnas_faltantes:` → un conjunto vacío se evalúa como False,
    # y uno con elementos como True. Entra al if solo si falta alguna columna.
    if columnas_faltantes:
        # `raise` lanza (provoca) un error a propósito y detiene el programa.
        # ValueError es el tipo de error para "valor inválido".
        raise ValueError(
            f"Columnas faltantes en el CSV: {columnas_faltantes}. "
            f"Columnas disponibles: {list(df.columns)}"
        )

    # ── Renombrar columnas (equivale a dplyr::rename()) ──
    # df.rename(columns=diccionario) → cambia el nombre de cada columna según
    # el diccionario {nombre_viejo: nombre_nuevo}. Devuelve una tabla NUEVA,
    # por eso la volvemos a guardar en `df`.
    df = df.rename(columns=MAPEO_COLUMNAS) #agaro mi dataframe y le aplico el diccionario clave valor

    # ── Seleccionar solo las columnas mapeadas (descartar extras si existen) ──
    # MAPEO_COLUMNAS.values() → los valores del diccionario ("codigo_caso", ...).
    columnas_finales = list(MAPEO_COLUMNAS.values()) #obtengo los valores del diccionario
    # df[lista_de_columnas] → selecciona solo esas columnas y en ese orden
    # (equivale a select() en R).
    df = df[columnas_finales] #selecciono solo las columnas mapeadas

    print(f"  Columnas renombradas ({len(df.columns)}): {list(df.columns)}")
    print(f"  Primeras 3 filas:")
    # df.head(3)        → toma las 3 primeras filas (equivale a head(df, 3) en R).
    # .to_string(index=False) → convierte la tabla a texto para imprimir,
    #                           sin mostrar la columna de índice (0, 1, 2...).
    print(df.head(3).to_string(index=False))
    print("=" * 60)

    return df  # Devolvemos la tabla ya renombrada.


# `-> None` indica que la función NO devuelve nada; solo realiza una acción
# (en este caso, guardar un archivo en disco).
def guardar_intermedio_renombrado(df: pd.DataFrame) -> None:
    """
    Guarda el DataFrame renombrado en formato Parquet en data/interim/.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame con columnas ya renombradas.
    """

    #Guarda ya renombrado bonito
    # INTERIM_RENOMBRADO.parent → la carpeta que contiene al archivo (data/interim).
    # .mkdir(...) → crea esa carpeta.
    #   parents=True  → crea también las carpetas superiores si no existen.
    #   exist_ok=True → si la carpeta ya existe, no lanza error.
    INTERIM_RENOMBRADO.parent.mkdir(parents=True, exist_ok=True) #Si no existe la carpeta, la crea.
    # df.to_parquet(...) → guarda la tabla en formato Parquet (equivale a saveRDS en R).
    #   index=False      → no guarda la columna de índice numérico de las filas.
    #   engine="pyarrow" → la librería que se encarga de escribir el archivo.
    df.to_parquet(INTERIM_RENOMBRADO, index=False, engine="pyarrow") #lo guarda 
    print(f"  Guardado intermedio: {INTERIM_RENOMBRADO}")
    # .stat() → obtiene información del archivo en disco.
    # .st_size → su tamaño en bytes. Dividido para 1024 → kilobytes (KB).
    # {valor:.1f} → muestra el número con 1 decimal.
    print(f"  Tamaño: {INTERIM_RENOMBRADO.stat().st_size / 1024:.1f} KB")


def cargar_intermedio_renombrado() -> pd.DataFrame:
    """
    Carga el archivo Parquet intermedio de datos renombrados.

    Returns
    -------
    pd.DataFrame
        DataFrame previamente renombrado y guardado.

    Raises
    ------
    FileNotFoundError
        Si el archivo intermedio todavía no ha sido generado.
    """
    # .exists() → devuelve True si el archivo existe en disco.
    # `not` lo invierte: entra al if cuando el archivo NO existe.
    if not INTERIM_RENOMBRADO.exists(): 
        # FileNotFoundError = tipo de error estándar para "archivo no encontrado".
        raise FileNotFoundError(
            f"No existe el archivo intermedio: {INTERIM_RENOMBRADO}. "
            "Ejecuta primero cargar_homicidios_raw() y guardar_intermedio_renombrado()."
        )
    # pd.read_parquet(...) → lee el archivo Parquet y lo devuelve como DataFrame
    # (equivale a readRDS en R).
    return pd.read_parquet(INTERIM_RENOMBRADO, engine="pyarrow") #devuelvo mi tipo parquet renombrado
