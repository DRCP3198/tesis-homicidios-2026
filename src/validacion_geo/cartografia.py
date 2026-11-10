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

En palabras simples: este módulo abre el mapa digital de los cantones del
Ecuador, lo convierte al sistema de coordenadas GPS (latitud/longitud),
"repara" los bordes mal dibujados y deja los nombres de los cantones en el
mismo formato que la base de homicidios (MAYÚSCULAS, sin tildes), para que
después se puedan comparar.
"""
# geopandas: extensión de pandas para trabajar con MAPAS (equivale al paquete sf de R).
# Su tabla principal es el GeoDataFrame: un DataFrame normal + una columna
# especial llamada "geometry" que guarda la forma de cada fila (punto, polígono...).
import geopandas as gpd
import pandas as pd

from src.ingesta.config import (
    ARCHIVO_SHAPEFILE_CANTONES,  # data/raw/cartografia/nxcantones.shp
    CRS_OBJETIVO,               # 4326 (WGS84)
    PROVINCIAS_EXCLUIR_MAPA,    # ['GALAPAGOS', 'ZONA NO DELIMITADA']
)
# Reutilizamos la MISMA función de limpieza de texto de la Fase 2, para que
# los nombres del mapa queden idénticos a los de la base de datos.
from src.utils.texto import normalizar_texto


# =========================================================================
# PASO 4.1 — Carga del Shapefile cantonal
# =========================================================================
def cargar_mapa_cantonal(
    ruta_shp: str | None = None,  # Ruta opcional al .shp; si no se da, usa la de config.py.
) -> gpd.GeoDataFrame:            # Devuelve un GeoDataFrame (tabla con geometrías).
    """
    Carga, reproyecta y homologa el mapa cantonal de Ecuador.

    Paso 4.1: Lee el shapefile, reproyecta a WGS84 (World Geodetic System 1984)
    Es el modelo matemático estándar que describe la forma de la Tierra como un elipsoide tridimensional 
    (EPSG:4326, (European Petroleum Survey Group): Fue una organización técnica petrolera europea
    creó un registro numérico universal donde cada sistema de coordenadas, elipsoide y proyección del mundo tiene un código único.) y
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
    # Si nos pasan una ruta la usamos; si no (None), usamos la de config.py.
    # str(...) convierte el objeto Path a texto.
    ruta = ruta_shp or str(ARCHIVO_SHAPEFILE_CANTONES)

    print("=" * 60)
    print("  FASE 4.1–4.2: CARGA Y HOMOLOGACIÓN CARTOGRÁFICA")
    print("=" * 60)
    print(f"  Leyendo shapefile: {ruta}")

    # ── Paso 4.1a: Lectura del shapefile ──
    # Equivale a: Provincia <- read_sf("nxcantones.shp")
    # gpd.read_file(ruta) → abre el mapa y lo carga como GeoDataFrame.
    # Cada FILA es un cantón; la columna "geometry" guarda su polígono (su contorno).
    mapa = gpd.read_file(ruta)
    print(f"  Polígonos cargados: {len(mapa)}")    # Cuántos cantones (filas) hay.
    print(f"  CRS original: {mapa.crs}")           # .crs → sistema de coordenadas del mapa.
    # IMPRIME CRS original: EPSG:32717
    # no utiliza grados angulares de una esfera, sino una cuadrícula plana donde la unidad de medida oficial es el metro.
    print(f"  Columnas: {list(mapa.columns)}")

    # ── Paso 4.1b: Reproyección a WGS84 ──
    # Equivale a: Provincia <- st_transform(Provincia, crs = 4326)
    # El shapefile original está en EPSG:32717 (UTM zona 17S).
    # Lo convertimos a EPSG:4326 (coordenadas geográficas lat/lon).
    #
    # ¿Por qué? EPSG:32717 mide en METROS (ej. x=500000, y=9750000), pero
    # nuestras coordenadas de homicidios están en GRADOS (ej. -2.18, -79.88).
    # Para poder comparar puntos con polígonos, ambos deben estar en el mismo
    # sistema. .to_crs() recalcula todas las coordenadas del mapa a grados.
    mapa = mapa.to_crs(epsg=CRS_OBJETIVO)
    print(f"  CRS reproyectado: {mapa.crs}")

    # ── Paso 4.1c: Reparación de geometrías inválidas ──
    # Equivale a: Provincia <- st_make_valid(Provincia)
    # Corrige auto-intersecciones, vértices duplicados, etc.
    #
    # mapa.is_valid → columna True/False: True si el polígono está bien dibujado.
    # ~ invierte (True↔False) → ahora True significa "inválido".
    # .sum() → cuenta cuántos True hay → número de polígonos inválidos.
    n_invalidas_antes = (~mapa.is_valid).sum()
    # mapa.make_valid() → devuelve las geometrías corregidas.
    # Las asignamos de vuelta a la columna de geometría del mapa.
    mapa.geometry = mapa.make_valid() #agara los poligonos y corrige si hay inconsistencias
    n_invalidas_despues = (~mapa.is_valid).sum()  # Debería ser 0 tras la reparación.
    print(f"  Geometrías reparadas: {n_invalidas_antes} (antes) → {n_invalidas_despues} (despues)")

    # ── Paso 4.2a: Crear columna CANTON_MAPA normalizada ──
    # Equivale a: mutate(CANTON_MAPA = iconv(str_to_upper(str_trim(DPA_DESCAN)),
    #                                        to = "ASCII//TRANSLIT"))
    # Aplica strip() + upper() + unidecode() usando la misma función
    # normalizar_texto() de src/utils/texto.py (ya usada en Fase 2).
    #
    # DPA_DESCAN = columna del shapefile con el nombre del cantón.
    # .map(normalizar_texto) → aplica la función a cada nombre, uno por uno.
    # El resultado se guarda en una columna NUEVA llamada CANTON_MAPA.
    mapa["CANTON_MAPA"] = mapa["DPA_DESCAN"].map(normalizar_texto)
    # .nunique() → número de cantones distintos.
    print(f"  Cantones en mapa (total): {mapa['CANTON_MAPA'].nunique()}")

    # ── Paso 4.2b: Excluir Galápagos y Zona No Delimitada ──
    # Equivale a: filter(DPA_DESPRO != "GALAPAGOS",
    #                    DPA_DESPRO != "ZONA NO DELIMITADA")
    # Necesitamos normalizar DPA_DESPRO también para la comparación.
    # (Ej: en el shapefile viene "CAÑAR" con Ñ; normalizado queda "CANAR").
    #
    # Creamos una columna TEMPORAL "_PROV_NORM" (el "_" inicial es una
    # convención para indicar que es auxiliar/interna).
    mapa["_PROV_NORM"] = mapa["DPA_DESPRO"].map(normalizar_texto)
    n_antes = len(mapa)
    # .isin(lista) → True si la provincia está en la lista a excluir.
    # ~ invierte → nos quedamos con las provincias que NO están en la lista.
    # .copy() → copia independiente para evitar advertencias de pandas.
    mapa = mapa[~mapa["_PROV_NORM"].isin(PROVINCIAS_EXCLUIR_MAPA)].copy()
    # .drop(columns=[...]) → elimina la columna temporal, ya no la necesitamos.
    mapa = mapa.drop(columns=["_PROV_NORM"])
    n_despues = len(mapa)
    n_excluidos = n_antes - n_despues  # Cuántos polígonos se quitaron.

    print(f"  Excluidos (Galápagos + Zona No Delim.): {n_excluidos}")
    print(f"  Cantones continental final: {mapa['CANTON_MAPA'].nunique()}")

    # Control de seguridad: si por algún error el filtro borró todo el mapa,
    # detenemos el programa con un mensaje claro (sin mapa no se puede validar nada).
    if len(mapa) == 0:
        raise ValueError(
            "El GeoDataFrame del mapa quedó vacío después de filtrar. "
            "Verifica que PROVINCIAS_EXCLUIR_MAPA no elimine todo."
        )

    print("=" * 60)
    return mapa  # Devolvemos el mapa limpio, listo para la auditoría topológica.
