"""
reparacion.py — Algoritmo reparador de coordenadas decimales corruptas.

Corresponde a la Fase R 8 (líneas 300-457) del código original — la fase
más delicada y crítica de todo el pipeline.

El problema: Algunas coordenadas de latitud fueron digitadas sin punto
decimal (ej: "214589" en lugar de "2.14589" o "-2.14589"), lo que las
convierte en números astronómicos que caen fuera del mapa.

La solución: Reconstruir el punto decimal probando 4 escenarios de
formato, y validar cada reconstrucción mediante sjoin contra el mapa
cantonal para confirmar que el punto reparado cae dentro de su cantón.

Los 4 Escenarios (replicando el R original):
    1. X.XXXXXX   → Latitud positiva (Norte del Ecuador)
    2. 0.XXXXXX   → Latitud positiva cercana a la línea ecuatorial
    3. -X.XXXXXX  → Latitud negativa (Sur) ← EL MÁS CRÍTICO
    4. -0.XXXXXX  → Latitud negativa cercana a la línea ecuatorial

Funciones principales:
    - reconstruir_escenario_1(): Formato X.XXXXXX
    - reconstruir_escenario_2(): Formato 0.XXXXXX
    - reconstruir_escenario_3(): Formato -X.XXXXXX
    - reconstruir_escenario_4(): Formato -0.XXXXXX
    - validar_reconstruccion_sjoin(): Prueba sjoin tras reparación
    - reparar_coordenadas_corruptas(): Orquestador secuencial
"""
import geopandas as gpd
import numpy as np
import pandas as pd

from src.ingesta.config import CRS_OBJETIVO  # 4326 (WGS84)


# =========================================================================
# FUNCIONES AUXILIARES: Limpieza de cadena numérica
# =========================================================================
def _limpiar_cadena_lat(serie_lat: pd.Series) -> pd.Series:
    r"""
    Limpia la cadena de latitud eliminando puntos y signos negativos.

    Equivalencia R (líneas 321-323):
        limpia.lat = gsub("\\\\.", "", as.character(lat.new))
        limpia.lat = gsub("-", "", limpia.lat)
        limpia.lat = as.numeric(limpia.lat)

    Mapeo R → Python:
        gsub("[.]", "", x)  ->  x.str.replace(r'\.', '', regex=True)
        gsub("-", "", x)    ->  x.str.replace('-', '', regex=False)

    Parameters
    ----------
    serie_lat : pd.Series
        Columna de latitud como string.

    Returns
    -------
    pd.Series
        Cadena numérica limpia (sin puntos ni signos).
    """
    limpia = serie_lat.astype(str)
    limpia = limpia.str.replace(r"\.", "", regex=True)
    limpia = limpia.str.replace("-", "", regex=False)
    return limpia


# =========================================================================
# ESCENARIO 1: Formato "X.XXXXXX" (Positivo — Hemisferio Norte)
# =========================================================================
def reconstruir_escenario_1(limpia_lat: pd.Series) -> pd.Series:
    """
    Reconstruye latitud con formato X.XXXXXX (positivo).

    Escenario para coordenadas al norte de la línea ecuatorial.
    Toma el primer dígito como parte entera y el resto como decimales.

    Equivalencia R (líneas 343-348):
        lat.1 = str_sub(limpia.lat, 1, 1)
        lat.leng = str_length(limpia.lat)
        lat.2 = str_sub(limpia.lat, 2, lat.leng)
        lat.final = paste0(lat.1, ".", lat.2)

    Mapeo R → Python:
        str_sub(x, 1, 1)       →  x.str[0]   (primer carácter)
        str_sub(x, 2, len)     →  x.str[1:]   (resto)
        paste0(a, ".", b)      →  a + "." + b

    Parameters
    ----------
    limpia_lat : pd.Series
        Cadena numérica limpia (sin puntos ni signos).

    Returns
    -------
    pd.Series
        Latitud reconstruida como string: "X.XXXXXX"

    Examples
    --------
    >>> reconstruir_escenario_1(pd.Series(["136965"]))
    0    1.36965
    dtype: object
    """
    parte_entera = limpia_lat.str[0]        # str_sub(x, 1, 1)
    parte_decimal = limpia_lat.str[1:]      # str_sub(x, 2, len)
    return parte_entera + "." + parte_decimal


# =========================================================================
# ESCENARIO 2: Formato "0.XXXXXX" (Positivo — Cerca del Ecuador)
# =========================================================================
def reconstruir_escenario_2(limpia_lat: pd.Series) -> pd.Series:
    """
    Reconstruye latitud con formato 0.XXXXXX (positivo, cercano al ecuador).

    Para coordenadas extremadamente próximas al norte de la línea ecuatorial
    que comienzan con cero absoluto.

    Equivalencia R (líneas 377-380):
        lat.final = paste0(0, ".", lat.1, lat.2)

    Parameters
    ----------
    limpia_lat : pd.Series
        Cadena numérica limpia.

    Returns
    -------
    pd.Series
        Latitud reconstruida: "0.XXXXXXX"
    """
    parte_1 = limpia_lat.str[0]
    parte_2 = limpia_lat.str[1:]
    return "0." + parte_1 + parte_2


# =========================================================================
# ESCENARIO 3: Formato "-X.XXXXXX" (Negativo — Hemisferio Sur) ← CRÍTICO
# =========================================================================
def reconstruir_escenario_3(limpia_lat: pd.Series) -> pd.Series:
    """
    Reconstruye latitud con formato -X.XXXXXX (negativo — Hemisferio Sur).

    **ESCENARIO HISTÓRICAMENTE CRÍTICO PARA ECUADOR:** La inmensa mayoría
    del territorio continental ecuatoriano (Guayaquil, Cuenca, Amazonía)
    está en el Hemisferio Sur, por lo que su latitud DEBE comenzar con
    signo negativo.

    Equivalencia R (líneas 406-409):
        lat.1 = str_sub(limpia.lat, 1, 1)
        lat.2 = str_sub(limpia.lat, 2, lat.leng)
        lat.final = paste0("-", lat.1, ".", lat.2)

    Mapeo R → Python:
        paste0("-", a, ".", b)  →  "-" + a + "." + b

    Parameters
    ----------
    limpia_lat : pd.Series
        Cadena numérica limpia.

    Returns
    -------
    pd.Series
        Latitud reconstruida: "-X.XXXXXX"

    Examples
    --------
    >>> reconstruir_escenario_3(pd.Series(["214589"]))
    0    -2.14589
    dtype: object
    """
    parte_entera = limpia_lat.str[0]
    parte_decimal = limpia_lat.str[1:]
    return "-" + parte_entera + "." + parte_decimal


# =========================================================================
# ESCENARIO 4: Formato "-0.XXXXXX" (Negativo — Cerca del Ecuador Sur)
# =========================================================================
def reconstruir_escenario_4(limpia_lat: pd.Series) -> pd.Series:
    """
    Reconstruye latitud con formato -0.XXXXXX (negativo, cercano al ecuador).

    Para provincias y cantones inmediatamente al sur de la línea del Ecuador
    cuya latitud inicia con "-0." (ej: Quito sur, Santo Domingo).

    Equivalencia R (líneas 434-437):
        lat.final = paste0("-0.", lat.1, lat.2)

    Parameters
    ----------
    limpia_lat : pd.Series
        Cadena numérica limpia.

    Returns
    -------
    pd.Series
        Latitud reconstruida: "-0.XXXXXXX"
    """
    parte_1 = limpia_lat.str[0]
    parte_2 = limpia_lat.str[1:]
    return "-0." + parte_1 + parte_2


# =========================================================================
# VALIDACIÓN: sjoin tras reconstrucción
# =========================================================================
def validar_reconstruccion_sjoin(
    df: pd.DataFrame,
    lat_reconstruida: pd.Series,
    mapa: gpd.GeoDataFrame,
) -> set[int]:
    """
    Valida una reconstrucción de latitud mediante sjoin contra el mapa.

    Crea puntos con la latitud reconstruida, ejecuta sjoin contra los
    polígonos cantonales, y devuelve los ID_temp de los registros cuyo
    punto reparado cae dentro del polígono de su cantón reportado.

    **[OPTIMIZACIÓN vs. R]:** Un solo sjoin vectorizado reemplaza el
    bucle for(j in 1:length(cantones)) del código R original.

    Equivalencia R (líneas 350-367, 382-397, 411-426, 439-454):
        point_analisis_cX <- data.frame(y = as.numeric(lat.final), x = lon.new)
        point_analisis_cX <- st_as_sf(point_analisis_cX, coords = c("x","y"), ...)
        for(j in 1:length(cantones.cX)) {
            ...
            dentro <- pts.eval[apply(st_intersects(...), 1, any), ]
            correctos3 <- c(correctos3, dentro$ID.temp)
        }

    Parameters
    ----------
    df : pd.DataFrame
        Registros a validar, con columnas 'lon_num', 'canton', 'ID_temp'.
    lat_reconstruida : pd.Series
        Serie con la latitud reconstruida como string.
    mapa : gpd.GeoDataFrame
        Mapa cantonal con columna 'CANTON_MAPA'.

    Returns
    -------
    set[int]
        Conjunto de ID_temp de los registros exitosamente reparados.
    """
    if len(df) == 0:
        return set()

    # Convertir latitud reconstruida a numérico
    lat_num = pd.to_numeric(lat_reconstruida, errors="coerce")

    # Filtrar registros con latitud válida
    validos = lat_num.notna() & df["lon_num"].notna()
    if validos.sum() == 0:
        return set()

    df_validos = df[validos].copy()
    lat_valida = lat_num[validos]

    # Crear GeoDataFrame de puntos con la latitud reconstruida
    # Equivale a: st_as_sf(data.frame(y=..., x=...), coords=c("x","y"), crs=...)
    gdf_prueba = gpd.GeoDataFrame(
        df_validos,
        geometry=gpd.points_from_xy(df_validos["lon_num"], lat_valida),
        crs=f"EPSG:{CRS_OBJETIVO}",
    )

    # sjoin vectorizado (reemplaza el bucle R completo)
    resultado = gpd.sjoin(
        gdf_prueba,
        mapa[["CANTON_MAPA", "geometry"]],
        how="inner",
        predicate="intersects",
    )

    # Filtrar donde cantón reportado == cantón geográfico
    ids_rescatados = set(
        resultado.loc[
            resultado["canton"] == resultado["CANTON_MAPA"], "ID_temp"
        ].unique()
    )

    return ids_rescatados


# =========================================================================
# ORQUESTADOR: Ejecución secuencial de los 4 escenarios
# =========================================================================
def reparar_coordenadas_corruptas(
    geo_corregir_decimales: pd.DataFrame,
    mapa: gpd.GeoDataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Ejecuta secuencialmente los 4 escenarios de reparación decimal.

    Replica la lógica del bucle R for(i in 1:10) con los escenarios
    i=1, i=2, i=6, i=7 (en el R usaban esos índices). Cada escenario
    intenta reparar los registros restantes y los registros rescatados
    se retiran del pool para el siguiente escenario.

    Equivalencia R (líneas 336-457):
        for(i in 1:10) {
            if(i == 1) { ... escenario X.XXXXXX ... }
            if(i == 2) { ... escenario 0.XXXXXX ... }
            if(i == 6) { ... escenario -X.XXXXXX ... }
            if(i == 7) { ... escenario -0.XXXXXX ... }
        }

    Parameters
    ----------
    geo_corregir_decimales : pd.DataFrame
        Registros sin punto decimal que necesitan reparación.
    mapa : gpd.GeoDataFrame
        Mapa cantonal para validación sjoin.

    Returns
    -------
    tuple de 5 DataFrames:
        - reparados_esc1: Rescatados por escenario 1 (X.XXXXXX)
        - reparados_esc2: Rescatados por escenario 2 (0.XXXXXX)
        - reparados_esc3: Rescatados por escenario 3 (-X.XXXXXX)
        - reparados_esc4: Rescatados por escenario 4 (-0.XXXXXX)
        - no_reparados: Registros que ningún escenario pudo rescatar
    """
    print("  [4.6] Algoritmo reparador de coordenadas decimales")

    if len(geo_corregir_decimales) == 0:
        print("        No hay registros con decimales corruptos para reparar.")
        vacio = pd.DataFrame()
        return vacio, vacio, vacio, vacio, vacio

    # ── Preparación: limpiar cadena de latitud ──
    # Equivale a: gsub("\\.", "", ...) + gsub("-", "", ...)
    df = geo_corregir_decimales.copy()
    df["limpia_lat"] = _limpiar_cadena_lat(df["latitud_original"])

    pendientes = df.copy()
    n_total = len(pendientes)

    escenarios = [
        ("Escenario 1: X.XXXXXX  (positivo Norte)", reconstruir_escenario_1),
        ("Escenario 2: 0.XXXXXX  (positivo Ecuador)", reconstruir_escenario_2),
        ("Escenario 3: -X.XXXXXX (negativo Sur) ← CRÍTICO", reconstruir_escenario_3),
        ("Escenario 4: -0.XXXXXX (negativo Ecuador)", reconstruir_escenario_4),
    ]

    resultados: list[pd.DataFrame] = []

    for nombre, fn_reconstruir in escenarios:
        if len(pendientes) == 0:
            resultados.append(pd.DataFrame())
            continue

        # Reconstruir latitud según el escenario
        lat_reconstruida = fn_reconstruir(pendientes["limpia_lat"])

        # Validar contra el mapa con sjoin
        ids_rescatados = validar_reconstruccion_sjoin(
            pendientes, lat_reconstruida, mapa
        )

        # Separar rescatados del pool de pendientes
        rescatados = pendientes[pendientes["ID_temp"].isin(ids_rescatados)].copy()

        # Actualizar lat_num con el valor reparado para los rescatados
        if len(rescatados) > 0:
            lat_reparada = fn_reconstruir(rescatados["limpia_lat"])
            rescatados["lat_num"] = pd.to_numeric(lat_reparada, errors="coerce")

        # Los rescatados salen del pool
        pendientes = pendientes[~pendientes["ID_temp"].isin(ids_rescatados)].copy()

        resultados.append(rescatados)
        print(f"        {nombre}: {len(rescatados):,} rescatados "
              f"({len(pendientes):,} pendientes)")

    # Limpiar columna auxiliar de todos los DataFrames
    for i, r in enumerate(resultados):
        if len(r) > 0 and "limpia_lat" in r.columns:
            resultados[i] = r.drop(columns=["limpia_lat"])

    if len(pendientes) > 0 and "limpia_lat" in pendientes.columns:
        pendientes = pendientes.drop(columns=["limpia_lat"])

    n_total_rescatados = sum(len(r) for r in resultados)
    n_no_reparados = len(pendientes)

    print(f"        {'─' * 45}")
    print(f"        Total rescatados: {n_total_rescatados:,} de {n_total:,}")
    print(f"        No reparados: {n_no_reparados:,}")

    return (
        resultados[0],  # Escenario 1
        resultados[1],  # Escenario 2
        resultados[2],  # Escenario 3
        resultados[3],  # Escenario 4
        pendientes,     # No reparados
    )
