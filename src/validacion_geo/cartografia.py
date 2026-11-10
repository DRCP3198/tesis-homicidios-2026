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
    ARCHIVO_SHAPEFILE_CANTONES,     # data/raw/cartografia/nxcantones.shp
    CRS_OBJETIVO,                   # 4326 (WGS84)
    MAPEO_CARACTERES_CORRUPTOS_SHP, # {'Ð': 'N', 'ð': 'n'} (corrección de Ñ corrupta en shapefile)
    MAPEO_ZONAS_NO_DELIMITADAS_SHP, # Homologación legal de los 3 polígonos Código 90
    PROVINCIAS_EXCLUIR_MAPA,        # ['GALAPAGOS']
)
# Reutilizamos la MISMA función de limpieza de texto de la Fase 2, para que
# los nombres del mapa queden idénticos a los de la base de datos.
from src.utils.texto import normalizar_texto


# =========================================================================
# FUNCIÓN AUXILIAR: Reparación de bytes corruptos en nombres del Shapefile
# =========================================================================
def reparar_codificacion_shapefile(mapa: gpd.GeoDataFrame) -> pd.Series:
    """
    Corrige caracteres con codificación corrupta en la columna `DPA_DESCAN`
    del shapefile antes de aplicar `normalizar_texto()`, e imprime en consola
    una muestra explícita de los cantones reparados.

    ¿Por qué es necesario este paso?
        En `nxcantones.shp`, la letra "Ñ" quedó almacenada como el carácter
        islandés "Ð" (Eth mayúscula, U+00D0) en "RUMIÐAHUI" y "LOGROÐO".
        Cuando `unidecode("Ð")` intenta transliterar ese carácter a ASCII,
        lo convierte en "D" ("RUMIDAHUI", "LOGRODO"), provocando que ningún
        homicidio de Rumiñahui ("RUMINAHUI") o Logroño ("LOGRONO") coincida
        con su polígono en el `sjoin`. Al sustituir "Ð" → "N" primero, el
        nombre normalizado queda en "RUMINAHUI" y "LOGRONO".

    Parameters
    ----------
    mapa : gpd.GeoDataFrame
        GeoDataFrame recién leído del archivo `.shp` con columnas
        `DPA_DESPRO` y `DPA_DESCAN`.

    Returns
    -------
    pd.Series
        Serie de texto con los nombres de `DPA_DESCAN` ya reparados y
        normalizados en mayúsculas ASCII sin tildes (`CANTON_MAPA`).
    """
    # Convertimos la columna original a tipo string de Pandas para manipular texto de forma segura.
    serie_original = mapa["DPA_DESCAN"].astype(str)

    # Construimos una expresión regular uniendo las claves corruptas del diccionario (ej. "Ð|ð").
    # `"|".join(...)` une los caracteres con el operador OR ("|") de expresiones regulares.
    patron_corrupto = "|".join(MAPEO_CARACTERES_CORRUPTOS_SHP.keys())

    # `.str.contains(patron_corrupto, na=False)` devuelve True en las filas que tienen el carácter corrupto.
    mascara_corruptos = serie_original.str.contains(patron_corrupto, regex=True, na=False)

    # Aplicamos el reemplazo de cada carácter corrupto ("Ð" → "N", "ð" → "n") sobre toda la serie.
    serie_reparada = serie_original.copy()
    for char_corrupto, char_limpio in MAPEO_CARACTERES_CORRUPTOS_SHP.items():
        # `regex=False` hace reemplazo literal carácter por carácter (más rápido y seguro).
        serie_reparada = serie_reparada.str.replace(
            char_corrupto, char_limpio, regex=False
        )

    # Finalmente pasamos cada nombre reparado por `normalizar_texto` (strip + upper + unidecode).
    canton_mapa = serie_reparada.map(normalizar_texto)

    # Si detectamos filas con el carácter corrupto, imprimimos la muestra explícita en consola
    # para que el analista verifique visualmente cómo habría fallado sin la corrección.
    if mascara_corruptos.any():
        print("-" * 60)
        print("  [AUDITORÍA SHP] Corrección de caracteres corruptos en DPA_DESCAN:")
        print(
            f"  {'Provincia (SHP)':<18} | {'DPA_DESCAN (Crudo)':<14} | "
            f"{'Sin corrección':<14} | {'CANTON_MAPA (Corregido)':<14}"
        )
        print("  " + "-" * 66)
        # Iteramos únicamente por las filas afectadas (`mapa.loc[mascara_corruptos]`).
        for idx, fila in mapa.loc[mascara_corruptos].iterrows():
            prov_raw = str(fila.get("DPA_DESPRO", ""))
            can_raw = str(fila["DPA_DESCAN"])
            # Simulamos qué habría devuelto `normalizar_texto` directo sin corregir "Ð" → "N".
            sin_correccion = normalizar_texto(can_raw)
            con_correccion = canton_mapa.loc[idx]
            print(
                f"  {prov_raw:<18} | {can_raw:<14} | "
                f"{sin_correccion:<14} | {con_correccion:<14}"
            )
        print("-" * 60)

    return canton_mapa


# =========================================================================
# FUNCIÓN AUXILIAR: Homologación legal de las antiguas "Zonas No Delimitadas"
# =========================================================================
def homologar_zonas_no_delimitadas_shp(mapa: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Integra cartográficamente los 3 polígonos catalogados en `nxcantones.shp`
    bajo el código INEC `90` (`DPA_DESPRO == "ZONA NO DELIMITADA"`) hacia su
    jurisdicción provincial y cantonal vigente según las Leyes de Fijación de
    Límites Territoriales Internos (2015–2017) y la zonificación SENPLADES/INEC.

    ¿Por qué homologar estos 3 polígonos en vez de eliminarlos del mapa?
        1. Si se eliminan del mapa continental, quedan 3 "huecos" geográficos
           dentro del Ecuador continental y los 117 homicidios ocurridos allí
           no intersectan ningún polígono en el `sjoin` (cayendo todos al limbo).
        2. Al asignar cada polígono a su provincia y cantón legal:
           • `MANGA DEL CURA` (`9003`)  → `MANABI` / `EL CARMEN` (Ley R.O.S. N.° 994, 2017)
           • `LAS GOLONDRINAS` (`9001`) → `IMBABURA` / `COTACACHI` (Ley R.O.S. N.° 999, 2017)
           • `EL PIEDRERO` (`9004`)     → `CANAR` / `LA TRONCAL` (SENPLADES Distrito 03D03)
           la auditoría punto-en-polígono valida automáticamente los casos cuya
           jurisdicción coincide y deja en el limbo únicamente las discrepancias
           reales de lindero intercantonal o interprovincial.

    Parameters
    ----------
    mapa : gpd.GeoDataFrame
        GeoDataFrame del shapefile cantonal con la columna `CANTON_MAPA` creada.

    Returns
    -------
    gpd.GeoDataFrame
        GeoDataFrame con `DPA_DESPRO` y `CANTON_MAPA` actualizados para las
        3 antiguas Zonas No Delimitadas.
    """
    mapa = mapa.copy()
    filas_homologadas: list[tuple[str, str, str, str, str]] = []

    for zona_znd, (prov_oficial, canton_oficial, sustento) in MAPEO_ZONAS_NO_DELIMITADAS_SHP.items():
        # Buscamos el polígono cuyo CANTON_MAPA coincida con la antigua Zona No Delimitada.
        mascara = mapa["CANTON_MAPA"] == zona_znd
        if mascara.any():
            for idx in mapa.index[mascara]:
                cod_dpa = str(mapa.loc[idx, "DPA_CANTON"]) if "DPA_CANTON" in mapa.columns else "90XX"
                filas_homologadas.append(
                    (cod_dpa, zona_znd, prov_oficial, canton_oficial, sustento)
                )
            # Actualizamos tanto la provincia del mapa (`DPA_DESPRO`) como el cantón (`CANTON_MAPA`).
            mapa.loc[mascara, "DPA_DESPRO"] = prov_oficial
            mapa.loc[mascara, "CANTON_MAPA"] = canton_oficial

    if filas_homologadas:
        print("-" * 60)
        print("  [AUDITORÍA ZND] Incorporación legal de antiguas Zonas No Delimitadas (Código 90):")
        print(
            f"  {'DPA':<6} | {'Zona original (SHP)':<17} | "
            f"{'Jurisdicción asignada':<22} | {'Sustento Legal / Normativo'}"
        )
        print("  " + "-" * 96)
        for cod, z_orig, prov_dest, can_dest, norma in filas_homologadas:
            destino = f"{prov_dest} - {can_dest}"
            print(f"  {cod:<6} | {z_orig:<17} | {destino:<22} | {norma}")
        print("-" * 60)

    return mapa


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
    # Aplica reparación de bytes corruptos ('Ð' → 'N' en RUMIÐAHUI / LOGROÐO)
    # seguida de strip() + upper() + unidecode() usando normalizar_texto()
    # de src/utils/texto.py (ya usada en Fase 2).
    #
    # DPA_DESCAN = columna del shapefile con el nombre del cantón.
    # reparar_codificacion_shapefile(mapa) → repara 'Ð', imprime la muestra
    # en consola y devuelve la serie normalizada para CANTON_MAPA.
    mapa["CANTON_MAPA"] = reparar_codificacion_shapefile(mapa)
    # .nunique() → número de cantones distintos antes de integrar las ZND.
    print(f"  Cantones en mapa (antes de integrar ZND): {mapa['CANTON_MAPA'].nunique()}")

    # ── Paso 4.2b: Integrar legalmente las antiguas Zonas No Delimitadas (Código 90) ──
    # Asigna MANGA DEL CURA -> MANABI/EL CARMEN, LAS GOLONDRINAS -> IMBABURA/COTACACHI
    # y EL PIEDRERO -> CANAR/LA TRONCAL según las Leyes de Fijación de Límites (2015-2017).
    mapa = homologar_zonas_no_delimitadas_shp(mapa)

    # ── Paso 4.2c: Excluir Galápagos (región insular) ──
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

    print(f"  Excluidos insulares (Galápagos): {n_excluidos}")
    print(f"  Polígonos continentales activos: {len(mapa)} ({mapa['CANTON_MAPA'].nunique()} cantones únicos)")

    # Control de seguridad: si por algún error el filtro borró todo el mapa,
    # detenemos el programa con un mensaje claro (sin mapa no se puede validar nada).
    if len(mapa) == 0:
        raise ValueError(
            "El GeoDataFrame del mapa quedó vacío después de filtrar. "
            "Verifica que PROVINCIAS_EXCLUIR_MAPA no elimine todo."
        )

    print("=" * 60)
    return mapa  # Devolvemos el mapa limpio, listo para la auditoría topológica.
