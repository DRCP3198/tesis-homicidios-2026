"""
geometrias.py — Creación de puntos geoespaciales y auditoría topológica.

Corresponde a las Fases R 6-7 (líneas 232-298) del código original:
    Fase 6: Conversión de coordenadas a puntos SF
    Fase 7: Primera auditoría topológica punto-en-polígono

Funciones principales:
    - crear_geodataframe_puntos(): Convierte coords a GeoDataFrame (Paso 4.3)
    - auditar_punto_en_poligono(): sjoin vectorizado (Paso 4.4)
    - separar_por_formato(): Diagnóstico de limbo (Paso 4.5)
"""
import geopandas as gpd
import numpy as np
import pandas as pd

from src.ingesta.config import CRS_OBJETIVO  # 4326 (WGS84)


# =========================================================================
# PASO 4.3 — Creación de puntos geoespaciales
# =========================================================================
def crear_geodataframe_puntos(df: pd.DataFrame) -> gpd.GeoDataFrame:
    """
    Convierte un DataFrame con columnas latitud/longitud a GeoDataFrame de puntos.

    Equivalencia R (líneas 235-260):
        homi_2010_2024_fin <- homi_2010_2024 %>%
            mutate(lat.new = as.numeric(X21), lon.new = as.numeric(X22)) %>%
            filter(!is.na(lat.new) & !is.na(lon.new))
        homi_2010_2024_fin$ID.temp <- 1:nrow(homi_2010_2024_fin)
        point_analisis <- data.frame(y = ...$lat.new, x = ...$lon.new)
        point_analisis <- st_as_sf(point_analisis, coords = c("x","y"), crs = ...)

    Mapeo R → Python:
        as.numeric()              →  pd.to_numeric(errors='coerce')
        filter(!is.na())          →  df.dropna(subset=[...])
        1:nrow(df)                →  range(1, len(df)+1)
        st_as_sf(coords=c(x,y))  →  gpd.GeoDataFrame(geometry=points_from_xy())

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame filtrado de Fase 3 con columnas 'latitud' y 'longitud'
        como strings.

    Returns
    -------
    gpd.GeoDataFrame
        GeoDataFrame con geometría de puntos (Point), columna 'ID_temp'
        secuencial, y columnas numéricas 'lat_num' / 'lon_num'.

    Raises
    ------
    KeyError
        Si las columnas 'latitud' o 'longitud' no existen.
    """
    for col in ("latitud", "longitud"):
        if col not in df.columns:
            raise KeyError(
                f"La columna '{col}' no existe en el DataFrame. "
                f"Columnas disponibles: {list(df.columns)}"
            )

    print("  [4.3] Creación de puntos geoespaciales")

    df = df.copy()

    # Preservar las cadenas originales para el algoritmo reparador (Paso 4.6)
    # Estas columnas serán necesarias para diagnosticar el formato decimal
    df["latitud_original"] = df["latitud"].astype(str)
    df["longitud_original"] = df["longitud"].astype(str)

    # Conversión numérica: as.numeric() → pd.to_numeric(errors='coerce')
    # errors='coerce' convierte valores no-numéricos a NaN (equivale a NA en R)
    df["lat_num"] = pd.to_numeric(df["latitud"], errors="coerce")
    df["lon_num"] = pd.to_numeric(df["longitud"], errors="coerce")

    n_antes = len(df)
    n_lat_nan = df["lat_num"].isna().sum()
    n_lon_nan = df["lon_num"].isna().sum()

    # filter(!is.na(lat.new) & !is.na(lon.new)) → dropna
    df = df.dropna(subset=["lat_num", "lon_num"])
    n_despues = len(df)

    print(f"        Registros entrada: {n_antes:,}")
    print(f"        NaN en latitud:  {n_lat_nan:,}")
    print(f"        NaN en longitud: {n_lon_nan:,}")
    print(f"        Registros con coordenadas válidas: {n_despues:,}")

    # Asignar ID temporal secuencial (≡ homi_2010_2024_fin$ID.temp <- 1:nrow(...))
    df = df.reset_index(drop=True)
    df["ID_temp"] = range(1, len(df) + 1)

    # Crear GeoDataFrame de puntos
    # Equivale a: st_as_sf(point_analisis, coords = c("x","y"), crs = st_crs(Provincia))
    # NOTA: points_from_xy recibe (x=longitud, y=latitud) — orden geográfico estándar
    gdf = gpd.GeoDataFrame(
        df,
        geometry=gpd.points_from_xy(df["lon_num"], df["lat_num"]),
        crs=f"EPSG:{CRS_OBJETIVO}",
    )

    print(f"        GeoDataFrame creado: {len(gdf):,} puntos en EPSG:{CRS_OBJETIVO}")

    return gdf


# =========================================================================
# PASO 4.4 — Primera Auditoría Topológica (sjoin vectorizado)
# =========================================================================
def auditar_punto_en_poligono(
    gdf_puntos: gpd.GeoDataFrame,
    mapa: gpd.GeoDataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Verifica si cada punto cae dentro del polígono del cantón reportado.

    **[OPTIMIZACIÓN CRÍTICA vs. R]:**
    El código R usa un bucle for(j in 1:length(cantones)) con st_intersects()
    cantón por cantón (O(n×m)). Aquí reemplazamos TODO el bucle por un ÚNICO
    gpd.sjoin() vectorizado que usa un índice espacial R-tree internamente,
    reduciendo la complejidad a O(n log m).

    Equivalencia R (líneas 265-298):
        for(j in 1:length(cantones.puntos)) {
            base.canton <- filter(CANTON_HECHO == cantones.puntos[j])
            poligono.canton <- Provincia %>% filter(CANTON_MAPA == ...)
            aux.dentro.polig <- st_intersects(puntos.evaluar, poligono.canton)
            dentro.polig <- puntos.evaluar[apply(aux.dentro.polig, 1, any), ]
            correctos <- c(correctos, dentro.polig$ID.temp)
        }
        geo_correctos <- filter(ID.temp %in% correctos)
        geo.corregir.master <- filter(!(ID.temp %in% correctos))

    Mapeo R → Python:
        st_intersects(sparse=FALSE)  →  gpd.sjoin(predicate='intersects')
        for(j in 1:n)                →  UN SOLO sjoin vectorizado
        filter(ID.temp %in% ...)     →  df[df['ID_temp'].isin(...)]

    Parameters
    ----------
    gdf_puntos : gpd.GeoDataFrame
        GeoDataFrame de puntos con columnas 'canton' y 'ID_temp'.
    mapa : gpd.GeoDataFrame
        GeoDataFrame del mapa cantonal con columna 'CANTON_MAPA'.

    Returns
    -------
    tuple[pd.DataFrame, pd.DataFrame]
        - geo_correctos: Registros cuya coordenada cae DENTRO de su cantón.
        - geo_corregir: Registros cuya coordenada cae FUERA de su cantón.
    """
    print("  [4.4] Auditoría topológica: punto-en-polígono (sjoin vectorizado)")

    n_total = len(gdf_puntos)

    # ── sjoin global: UNA sola operación reemplaza todo el bucle R ──
    # predicate='intersects' equivale a st_intersects()
    # how='left' para preservar TODOS los puntos (los que no caigan en ningún
    # polígono tendrán NaN en las columnas del mapa)
    resultado_sjoin = gpd.sjoin(
        gdf_puntos,
        mapa[["CANTON_MAPA", "geometry"]],
        how="left",
        predicate="intersects",
    )

    # ── Comparar cantón reportado vs. cantón geográfico ──
    # Un punto es "correcto" si el cantón que reporta la base de datos
    # coincide con el cantón del polígono donde cae geométricamente.
    resultado_sjoin["_coincide"] = (
        resultado_sjoin["canton"] == resultado_sjoin["CANTON_MAPA"]
    )

    # Obtener IDs de los registros correctos (coincidencia cantón-polígono)
    ids_correctos = set(
        resultado_sjoin.loc[resultado_sjoin["_coincide"], "ID_temp"].unique()
    )

    # ── Separar correctos vs. a corregir ──
    # Equivale a:
    #   geo_correctos <- filter(ID.temp %in% correctos)
    #   geo.corregir.master <- filter(!(ID.temp %in% correctos))
    mascara_correctos = gdf_puntos["ID_temp"].isin(ids_correctos)
    geo_correctos = gdf_puntos[mascara_correctos].copy()
    geo_corregir = gdf_puntos[~mascara_correctos].copy()

    # Convertir de GeoDataFrame a DataFrame plano (ya no necesitamos geometría
    # para los correctos; la geometría de 'a corregir' se reconstruirá)
    geo_correctos_df = pd.DataFrame(geo_correctos.drop(columns="geometry"))
    geo_corregir_df = pd.DataFrame(geo_corregir.drop(columns="geometry"))

    n_correctos = len(geo_correctos_df)
    n_corregir = len(geo_corregir_df)

    pct_correctos = (n_correctos / n_total * 100) if n_total > 0 else 0

    # Equivale a: print(paste0("Calidad de data inicial perfecta: ", ...))
    print(f"        Total puntos evaluados: {n_total:,}")
    print(f"        Correctos (dentro de su cantón): {n_correctos:,} "
          f"({pct_correctos:.2f}%)")
    print(f"        A corregir (fuera de su cantón): {n_corregir:,} "
          f"({100 - pct_correctos:.2f}%)")

    return geo_correctos_df, geo_corregir_df


# =========================================================================
# PASO 4.5 — Separación por formato (diagnóstico de limbo)
# =========================================================================
def separar_por_formato(
    geo_corregir: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    r"""
    Separa registros a corregir según si su latitud tiene punto decimal o no.

    Equivalencia R (líneas 309-313):
        limbo_formato_correcto <- geo.corregir.master %>%
            filter(grepl("[.]", as.character(lat.new)))
        geo.corregir.1 <- geo.corregir.master %>%
            filter(!grepl("[.]", as.character(lat.new)))

    Mapeo R → Python:
        grepl("[.]", x)  equiv  x.str.contains(r'\.', regex=True)

    Parameters
    ----------
    geo_corregir : pd.DataFrame
        Registros cuyas coordenadas no coinciden con su cantón reportado.

    Returns
    -------
    tuple[pd.DataFrame, pd.DataFrame]
        - limbo_formato_correcto: Tienen punto decimal (coordenada formateada
          pero fuera de su cantón, posiblemente por error de límites).
        - geo_corregir_decimales: SIN punto decimal (coordenada corrupta
          que requiere reparación del algoritmo decimal).
    """
    print("  [4.5] Separación por formato de coordenadas")

    if len(geo_corregir) == 0:
        print("        No hay registros a corregir.")
        return pd.DataFrame(), pd.DataFrame()

    # Inspeccionar si la cadena de latitud original tiene punto decimal
    # Equivale a: grepl("\\.", as.character(lat.new))
    tiene_punto = geo_corregir["latitud_original"].str.contains(
        r"\.", regex=True, na=False
    )

    limbo_formato_correcto = geo_corregir[tiene_punto].copy()
    geo_corregir_decimales = geo_corregir[~tiene_punto].copy()

    print(f"        Con punto decimal (limbo): {len(limbo_formato_correcto):,}")
    print(f"        Sin punto decimal (reparar): {len(geo_corregir_decimales):,}")

    return limbo_formato_correcto, geo_corregir_decimales
