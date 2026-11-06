"""
cartografia.py — Carga y homologación del mapa base cantonal.

Corresponde a las Fases R 5 (líneas 206-229) del código original:
    Provincia <- read_sf("nxcantones.shp")
    Provincia <- st_transform(Provincia, crs = 4326)
    Provincia <- st_make_valid(Provincia)
    Provincia <- Provincia %>%
        mutate(CANTON_MAPA = iconv(str_to_upper(str_trim(DPA_DESCAN)),
                                   to = "ASCII//TRANSLIT")) %>%
        filter(DPA_DESPRO != "GALAPAGOS", DPA_DESPRO != "ZONA NO DELIMITADA")

Funciones principales:
    - cargar_mapa_cantonal(): Lectura + reproyección + validación (Pasos 4.1–4.2)
"""
import geopandas as gpd
import pandas as pd

from src.ingesta.config import (
    ARCHIVO_SHAPEFILE_CANTONES,  # data/raw/cartografia/nxcantones.shp
    CRS_OBJETIVO,               # 4326 (WGS84)
    PROVINCIAS_EXCLUIR_MAPA,    # ['GALAPAGOS', 'ZONA NO DELIMITADA']
)
from src.utils.texto import normalizar_texto


# =========================================================================
# PASO 4.1 — Carga del Shapefile cantonal
# =========================================================================
def cargar_mapa_cantonal(
    ruta_shp: str | None = None,
) -> gpd.GeoDataFrame:
    """
    Carga, reproyecta y homologa el mapa cantonal de Ecuador.

    Paso 4.1: Lee el shapefile, reproyecta a WGS84 (EPSG:4326) y
    repara geometrías inválidas.
    Paso 4.2: Crea CANTON_MAPA normalizado y excluye Galápagos +
    Zona No Delimitada.

    Equivalencia R (líneas 214-229):
        Provincia <- read_sf("nxcantones.shp")
        Provincia <- st_transform(Provincia, crs = 4326)
        Provincia <- st_make_valid(Provincia)
        Provincia <- Provincia %>%
            mutate(CANTON_MAPA = iconv(str_to_upper(str_trim(DPA_DESCAN)),
                                       to = "ASCII//TRANSLIT")) %>%
            filter(DPA_DESPRO != "GALAPAGOS",
                   DPA_DESPRO != "ZONA NO DELIMITADA")

    Mapeo R → Python:
        read_sf()           →  gpd.read_file()
        st_transform(4326)  →  gdf.to_crs(epsg=4326)
        st_make_valid()     →  gdf.geometry = gdf.make_valid()
        mutate(CANTON_MAPA) →  gdf['CANTON_MAPA'] = gdf['DPA_DESCAN'].map(...)
        filter(!= ...)      →  gdf[~gdf['DPA_DESPRO'].isin([...])]

    Parameters
    ----------
    ruta_shp : str or None
        Ruta al archivo .shp. Si es None, usa ARCHIVO_SHAPEFILE_CANTONES
        de config.py.

    Returns
    -------
    gpd.GeoDataFrame
        Mapa cantonal continental con columna CANTON_MAPA normalizada,
        en CRS WGS84, con geometrías válidas.

    Raises
    ------
    FileNotFoundError
        Si el archivo shapefile no existe.
    ValueError
        Si el GeoDataFrame resultante está vacío.
    """
    ruta = ruta_shp or str(ARCHIVO_SHAPEFILE_CANTONES)

    print("=" * 60)
    print("  FASE 4.1–4.2: CARGA Y HOMOLOGACIÓN CARTOGRÁFICA")
    print("=" * 60)
    print(f"  Leyendo shapefile: {ruta}")

    # ── Paso 4.1a: Lectura del shapefile ──
    # Equivale a: Provincia <- read_sf("nxcantones.shp")
    mapa = gpd.read_file(ruta)
    print(f"  Polígonos cargados: {len(mapa)}")
    print(f"  CRS original: {mapa.crs}")
    print(f"  Columnas: {list(mapa.columns)}")

    # ── Paso 4.1b: Reproyección a WGS84 ──
    # Equivale a: Provincia <- st_transform(Provincia, crs = 4326)
    # El shapefile original está en EPSG:32717 (UTM zona 17S).
    # Lo convertimos a EPSG:4326 (coordenadas geográficas lat/lon).
    mapa = mapa.to_crs(epsg=CRS_OBJETIVO)
    print(f"  CRS reproyectado: {mapa.crs}")

    # ── Paso 4.1c: Reparación de geometrías inválidas ──
    # Equivale a: Provincia <- st_make_valid(Provincia)
    # Corrige auto-intersecciones, vértices duplicados, etc.
    n_invalidas_antes = (~mapa.is_valid).sum()
    mapa.geometry = mapa.make_valid()
    n_invalidas_despues = (~mapa.is_valid).sum()
    print(f"  Geometrías reparadas: {n_invalidas_antes} → {n_invalidas_despues}")

    # ── Paso 4.2a: Crear columna CANTON_MAPA normalizada ──
    # Equivale a: mutate(CANTON_MAPA = iconv(str_to_upper(str_trim(DPA_DESCAN)),
    #                                        to = "ASCII//TRANSLIT"))
    # Aplica strip() + upper() + unidecode() usando la misma función
    # normalizar_texto() de src/utils/texto.py (ya usada en Fase 2).
    mapa["CANTON_MAPA"] = mapa["DPA_DESCAN"].map(normalizar_texto)
    print(f"  Cantones en mapa (total): {mapa['CANTON_MAPA'].nunique()}")

    # ── Paso 4.2b: Excluir Galápagos y Zona No Delimitada ──
    # Equivale a: filter(DPA_DESPRO != "GALAPAGOS",
    #                    DPA_DESPRO != "ZONA NO DELIMITADA")
    # Necesitamos normalizar DPA_DESPRO también para la comparación.
    mapa["_PROV_NORM"] = mapa["DPA_DESPRO"].map(normalizar_texto)
    n_antes = len(mapa)
    mapa = mapa[~mapa["_PROV_NORM"].isin(PROVINCIAS_EXCLUIR_MAPA)].copy()
    mapa = mapa.drop(columns=["_PROV_NORM"])
    n_despues = len(mapa)
    n_excluidos = n_antes - n_despues

    print(f"  Excluidos (Galápagos + Zona No Delim.): {n_excluidos}")
    print(f"  Cantones continental final: {mapa['CANTON_MAPA'].nunique()}")

    if len(mapa) == 0:
        raise ValueError(
            "El GeoDataFrame del mapa quedó vacío después de filtrar. "
            "Verifica que PROVINCIAS_EXCLUIR_MAPA no elimine todo."
        )

    print("=" * 60)
    return mapa
