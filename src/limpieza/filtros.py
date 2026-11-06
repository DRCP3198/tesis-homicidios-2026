"""
filtros.py — Módulo de filtrado temporal y geográfico.

Corresponde a la Fase 3 de la migración R → Python (líneas 132-150 del R):
    homi_2010_2024 <- homi_2010_2025 %>%
        mutate(anio_hecho = as.numeric(anio_hecho)) %>%
        drop_na(anio_hecho) %>%
        filter(anio_hecho <= 2024) %>%
        filter(!canton %in% c('GALAPAGOS','ISABELA','SANTA CRUZ','SAN CRISTOBAL'))

Funciones principales:
    - convertir_anio_a_entero(): Castea anio_hecho a int (Paso 3.1)
    - filtrar_anio(): Filtra registros por año máximo (Paso 3.2)
    - excluir_galapagos(): Separa continental vs. insular (Pasos 3.3 y 3.4)
    - guardar_intermedio_filtrado(): Persiste el resultado en Parquet (Paso 3.6)
    - cargar_intermedio_filtrado(): Carga el Parquet filtrado
"""
import pandas as pd

from src.ingesta.config import (
    ANIO_MAXIMO,            # 2024 — Año máximo a incluir en el análisis
    CANTONES_GALAPAGOS,     # ['GALAPAGOS', 'ISABELA', 'SANTA CRUZ', 'SAN CRISTOBAL']
    INTERIM_FILTRADO,       # data/interim/homi_filtrado_2024.parquet
    INTERIM_NORMALIZADO,    # data/interim/homi_normalizado.parquet (entrada)
)


# =========================================================================
# PASO 3.1 — Conversión de anio_hecho a tipo entero
# =========================================================================
def convertir_anio_a_entero(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convierte la columna 'anio_hecho' de string a tipo entero.

    Equivalencia R:
        homi_2010_2025 <- homi_2010_2025 %>%
            mutate(anio_hecho = as.numeric(anio_hecho)) %>%
            drop_na(anio_hecho)

    Mapeo R → Python:
        as.numeric()  →  pd.to_numeric(errors='coerce')
        drop_na()     →  df.dropna(subset=['anio_hecho'])

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame con la columna 'anio_hecho' en formato string/object.

    Returns
    -------
    pd.DataFrame
        DataFrame con 'anio_hecho' convertida a Int64 (nullable integer),
        sin filas donde la conversión haya fallado (NaN).

    Raises
    ------
    KeyError
        Si la columna 'anio_hecho' no existe en el DataFrame.
    """
    if "anio_hecho" not in df.columns:
        raise KeyError(
            "La columna 'anio_hecho' no existe en el DataFrame. "
            f"Columnas disponibles: {list(df.columns)}"
        )

    registros_antes = len(df)

    # pd.to_numeric(errors='coerce') convierte valores no-numéricos a NaN
    # en lugar de lanzar error — equivale a as.numeric() de R que produce NA
    df = df.copy()  # Evitar SettingWithCopyWarning (buena práctica)
    df["anio_hecho"] = pd.to_numeric(df["anio_hecho"], errors="coerce")

    # Contar cuántos se convirtieron a NaN (valores no-numéricos)
    nulos_generados = df["anio_hecho"].isna().sum()

    # dropna() equivale a drop_na(anio_hecho) en R
    df = df.dropna(subset=["anio_hecho"])

    # Convertir a entero nullable (Int64) para mantener tipo semántico
    # Int64 (con I mayúscula) permite NaN a diferencia de int64
    df["anio_hecho"] = df["anio_hecho"].astype("Int64")

    registros_despues = len(df)
    eliminados = registros_antes - registros_despues

    print(f"  [3.1] Conversión anio_hecho → Int64")
    print(f"        Registros antes:  {registros_antes:,}")
    print(f"        Nulos generados:  {nulos_generados:,}")
    print(f"        Eliminados (NaN): {eliminados:,}")
    print(f"        Registros después: {registros_despues:,}")

    return df


# =========================================================================
# PASO 3.2 — Filtro temporal: año <= ANIO_MAXIMO
# =========================================================================
def filtrar_anio(
    df: pd.DataFrame,
    hasta: int | None = None,
) -> pd.DataFrame:
    """
    Filtra registros conservando solo aquellos con anio_hecho <= año máximo.

    Equivalencia R:
        homi_2010_2024 <- homi_2010_2025 %>%
            filter(anio_hecho <= 2024)

    Mapeo R → Python:
        filter(anio_hecho <= 2024)  →  df.query('anio_hecho <= 2024')

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame con 'anio_hecho' ya convertida a entero (salida de Paso 3.1).
    hasta : int or None
        Año máximo a conservar. Si es None, usa ANIO_MAXIMO de config.py (2024).

    Returns
    -------
    pd.DataFrame
        DataFrame filtrado sin registros posteriores al año límite.

    Raises
    ------
    KeyError
        Si la columna 'anio_hecho' no existe.
    ValueError
        Si 'anio_hecho' no es de tipo numérico.
    """
    if "anio_hecho" not in df.columns:
        raise KeyError(
            "La columna 'anio_hecho' no existe en el DataFrame. "
            f"Columnas disponibles: {list(df.columns)}"
        )

    # Verificar que la columna es numérica (debe venir del Paso 3.1)
    if not pd.api.types.is_numeric_dtype(df["anio_hecho"]):
        raise ValueError(
            f"La columna 'anio_hecho' tiene tipo '{df['anio_hecho'].dtype}', "
            "se esperaba tipo numérico. Ejecuta primero convertir_anio_a_entero()."
        )

    anio_limite = hasta if hasta is not None else ANIO_MAXIMO
    registros_antes = len(df)

    # df.query() es la equivalencia idiomática de dplyr::filter()
    # Usa una expresión string que es más legible para filtros simples
    df_filtrado = df.query("anio_hecho <= @anio_limite")

    registros_despues = len(df_filtrado)
    eliminados = registros_antes - registros_despues

    # Mostrar distribución de años excluidos para auditoría
    if eliminados > 0:
        excluidos = df.query("anio_hecho > @anio_limite")
        distribucion = excluidos["anio_hecho"].value_counts().sort_index()
        detalle_excluidos = ", ".join(
            f"{int(anio)}: {count}" for anio, count in distribucion.items()
        )
    else:
        detalle_excluidos = "(ninguno)"

    print(f"  [3.2] Filtro temporal: anio_hecho <= {anio_limite}")
    print(f"        Registros antes:   {registros_antes:,}")
    print(f"        Excluidos (>{anio_limite}): {eliminados:,} → {detalle_excluidos}")
    print(f"        Registros después: {registros_despues:,}")

    return df_filtrado


# =========================================================================
# PASOS 3.3 y 3.4 — Exclusión de Galápagos + Separación insular
# =========================================================================
def excluir_galapagos(
    df: pd.DataFrame,
    cantones_insular: list[str] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Separa registros continentales e insulares (Galápagos).

    Paso 3.3: Excluye cantones insulares del dataset principal.
    Paso 3.4: Aísla los registros insulares para trazabilidad.

    Equivalencia R:
        # Exclusión (línea ~145 del R):
        homi_2010_2024 <- homi_2010_2024 %>%
            filter(!canton %in% c('GALAPAGOS','ISABELA','SANTA CRUZ','SAN CRISTOBAL'))

    Mapeo R → Python:
        filter(!x %in% lista)  →  df[~df['canton'].isin(lista)]

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame ya filtrado temporalmente (salida de Paso 3.2).
    cantones_insular : list[str] or None
        Lista de cantones a excluir. Si es None, usa CANTONES_GALAPAGOS de config.py.

    Returns
    -------
    tuple[pd.DataFrame, pd.DataFrame]
        - df_continental: Registros de Ecuador continental (sin Galápagos).
        - df_insular: Registros insulares excluidos (para trazabilidad).

    Raises
    ------
    KeyError
        Si la columna 'canton' no existe.
    """
    if "canton" not in df.columns:
        raise KeyError(
            "La columna 'canton' no existe en el DataFrame. "
            f"Columnas disponibles: {list(df.columns)}"
        )

    cantones = cantones_insular if cantones_insular is not None else CANTONES_GALAPAGOS
    registros_antes = len(df)

    # ── Paso 3.3: Exclusión con ~isin() ──
    # ~df['canton'].isin(lista) es la negación lógica de .isin()
    # Equivale a: filter(!canton %in% c(...)) en R
    mascara_insular = df["canton"].isin(cantones)
    df_continental = df[~mascara_insular].copy()

    # ── Paso 3.4: Separar insular para trazabilidad ──
    # Guardamos los registros excluidos para auditoría posterior
    df_insular = df[mascara_insular].copy()

    registros_continental = len(df_continental)
    registros_insular = len(df_insular)

    # Detalle de cantones insulares encontrados
    if registros_insular > 0:
        detalle_insular = df_insular["canton"].value_counts()
        detalle_str = ", ".join(
            f"{canton}: {count}" for canton, count in detalle_insular.items()
        )
    else:
        detalle_str = "(ninguno encontrado)"

    print(f"  [3.3] Exclusión de Galápagos (cantones insulares)")
    print(f"        Cantones excluidos: {cantones}")
    print(f"        Registros antes:       {registros_antes:,}")
    print(f"        Registros insulares:   {registros_insular:,} → {detalle_str}")
    print(f"        Registros continental: {registros_continental:,}")

    return df_continental, df_insular


# =========================================================================
# PASO 3.6 — Guardar intermedio en Parquet
# =========================================================================
def guardar_intermedio_filtrado(df: pd.DataFrame) -> None:
    """
    Guarda el DataFrame filtrado en formato Parquet.

    Salida: data/interim/homi_filtrado_2024.parquet

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame continental, filtrado temporalmente y sin Galápagos.
    """
    INTERIM_FILTRADO.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(INTERIM_FILTRADO, index=False, engine="pyarrow")
    tamanio_kb = INTERIM_FILTRADO.stat().st_size / 1024
    print(f"  [3.6] Guardado intermedio: {INTERIM_FILTRADO}")
    print(f"        Tamaño: {tamanio_kb:.1f} KB")


def guardar_insular(df_insular: pd.DataFrame) -> None:
    """
    Guarda los registros insulares excluidos para trazabilidad.

    Salida: data/interim/homi_insular_excluido.parquet

    Parameters
    ----------
    df_insular : pd.DataFrame
        Registros de cantones de Galápagos excluidos del análisis.
    """
    ruta_insular = INTERIM_FILTRADO.parent / "homi_insular_excluido.parquet"
    ruta_insular.parent.mkdir(parents=True, exist_ok=True)
    df_insular.to_parquet(ruta_insular, index=False, engine="pyarrow")
    tamanio_kb = ruta_insular.stat().st_size / 1024
    print(f"  [3.4] Guardado insular (trazabilidad): {ruta_insular}")
    print(f"        Registros insulares guardados: {len(df_insular):,}")
    print(f"        Tamaño: {tamanio_kb:.1f} KB")


def cargar_intermedio_filtrado() -> pd.DataFrame:
    """
    Carga el archivo Parquet intermedio de datos filtrados.

    Returns
    -------
    pd.DataFrame
        DataFrame filtrado temporalmente y sin cantones insulares.

    Raises
    ------
    FileNotFoundError
        Si el archivo intermedio no existe.
    """
    if not INTERIM_FILTRADO.exists():
        raise FileNotFoundError(
            f"No existe el archivo intermedio: {INTERIM_FILTRADO}. "
            "Ejecuta primero la Fase 3 (filtros + guardar)."
        )
    return pd.read_parquet(INTERIM_FILTRADO, engine="pyarrow")


# =========================================================================
# EJECUCIÓN DIRECTA (para pruebas rápidas desde terminal)
# =========================================================================
if __name__ == "__main__":
    # Permite ejecutar: python -m src.limpieza.filtros
    print("Cargando datos de Fase 2 (homi_normalizado.parquet)...")

    if not INTERIM_NORMALIZADO.exists():
        raise FileNotFoundError(
            f"No existe {INTERIM_NORMALIZADO}. Ejecuta primero la Fase 2."
        )

    df = pd.read_parquet(INTERIM_NORMALIZADO, engine="pyarrow")

    print("=" * 60)
    print("  FASE 3: FILTRADO TEMPORAL Y GEOGRÁFICO")
    print("=" * 60)

    # Paso 3.1: Conversión de tipo
    df = convertir_anio_a_entero(df)

    # Paso 3.2: Filtro temporal
    df = filtrar_anio(df)

    # Pasos 3.3 y 3.4: Exclusión de Galápagos + separación insular
    df_continental, df_insular = excluir_galapagos(df)

    # Paso 3.4: Guardar insular para trazabilidad
    guardar_insular(df_insular)

    # Paso 3.6: Guardar intermedio continental
    guardar_intermedio_filtrado(df_continental)

    print("=" * 60)
    print("\n[OK] Fase 3 completada exitosamente.")

