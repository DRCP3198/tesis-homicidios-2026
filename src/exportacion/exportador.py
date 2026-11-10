r"""
exportador.py — Selección definitiva, tipado estricto y exportación multiformato.

Corresponde a las Fases R 10 y 13 (líneas 486-505 y 562-627) del script original:
    homi_Nueva_espacial <- st_as_sf(homi_Nueva, coords = c("lon.new", "lat.new"), crs = 4326)
    st_write(homi_Nueva_espacial, "homi_Nueva.shp", delete_layer = TRUE, quiet = TRUE)
    homi_Analisis_Final <- homi_Nueva %>% dplyr::select(codigo_caso = X2, ...)
    write.csv(homi_Analisis_Final, "homi_Final_Continental_Etiquetado.csv", row.names = FALSE)
    saveRDS(homi_Analisis_Final, file = "homi_Final_Continental_Etiquetado.rds")

Objetivo en Python (Pasos 5.1 a 5.4):
    Tomar la tabla georreferenciada de la Fase 4 (`homi_georreferenciado.parquet`),
    consolidar únicamente las **21 columnas limpias** definidas en el diccionario de
    datos, homologar las coordenadas reparadas (`lat_num`/`lon_num` → `latitud`/`longitud`),
    asignar tipos de datos óptimos (`string`, `datetime64[ns]`, `Int64`, `float64`,
    `category`) y exportar los tres artefactos definitivos en `data/processed/`:
      1. CSV plano UTF-8 (`homi_Final_Continental_Etiquetado.csv`) — interoperabilidad universal.
      2. Apache Parquet con Snappy (`homi_final.parquet`) — consumo analítico ultrarrápido (Fase 6).
      3. OGC GeoPackage (`homi_final.gpkg`) — cartografía vectorial moderna en un solo archivo.

En palabras simples:
    Este módulo es la "línea de empaque final" de nuestra fábrica de datos. Recibe la
    base reparada de la Fase 4 (que todavía conserva columnas internas de trabajo como
    `ID_temp` y las coordenadas viejas en texto), deja solo las 21 columnas oficiales
    con el tipo de dato exacto que corresponde a cada una y la guarda en tres formatos
    listos para tesis, Excel, Python y software SIG (QGIS / ArcGIS).
"""
# `from pathlib import Path` importa la clase Path para manejar rutas de carpetas y
# archivos como objetos inteligentes compatibles con Windows, Linux y macOS.
from pathlib import Path

# `geopandas` (alias `gpd`) es el equivalente en Python al paquete `sf` de R:
# permite convertir una tabla común en una capa geográfica con puntos/polígonos y CRS.
import geopandas as gpd

# `pandas` (alias `pd`) es la librería central de manipulación tabular (equivale a dplyr/tidyr).
import pandas as pd

# Importamos desde `config.py` todas las rutas y listas de columnas centralizadas
# para no escribir nombres ni rutas "quemadas" (hardcoded) dentro de las funciones.
from src.ingesta.config import (
    COLUMNAS_CATEGORICAS_FINALES,  # Lista de las 12 columnas de texto que pasarán a `category`.
    COLUMNAS_FINALES_21,           # Orden exacto de las 21 columnas del dataset final.
    CRS_OBJETIVO,                  # Código EPSG:4326 (sistema global WGS84 en grados decimales).
    MAPEO_COLUMNAS,                # Diccionario X2 -> codigo_caso (respaldo si entran nombres crudos).
    MAPEO_COORDENADAS_FINALES,     # Diccionario {"lat_num": "latitud", "lon_num": "longitud"}.
    PROCESSED_GEORREFERENCIADO,    # Ruta de entrada: data/processed/homi_georreferenciado.parquet.
    SALIDA_CSV_FINAL,              # Ruta de salida 5.2: homi_Final_Continental_Etiquetado.csv.
    SALIDA_GPKG_FINAL,             # Ruta de salida 5.4: homi_final.gpkg.
    SALIDA_PARQUET_FINAL,          # Ruta de salida 5.3: homi_final.parquet.
)

# Conjuntos internos de columnas por tipo de dato objetivo (prefijo "_" = constante privada del módulo).
# Definir estas listas arriba hace que la función de tipado sea fácil de leer y mantener.
_COLUMNAS_ENTERO_NULABLE: list[str] = [
    "anio_hecho",          # Año de ocurrencia (ej. 2010..2024).
    "AUX_HORA_SISTEMA",    # Hora registrada en sistema policial (0..23).
    "AUX_MINUTO_SISTEMA",  # Minuto registrado en sistema policial (0..59).
]

_COLUMNAS_FLOTANTES: list[str] = [
    "hora_aproximada",  # Admite horas decimales (ej. 19.5 = 19h30, 19.6667 = 19h40).
    "edad_victima",     # Admite decimales en lactantes (ej. 0.25 años = 3 meses) y valores vacíos NaN.
    "latitud",          # Coordenada geográfica Y validada/reparada en grados decimales.
    "longitud",         # Coordenada geográfica X validada/reparada en grados decimales.
]


# =========================================================================
# PASO 5.1 — Selección y renombrado definitivo de las 21 columnas limpias
# =========================================================================
def seleccionar_y_estandarizar_columnas(df: pd.DataFrame) -> pd.DataFrame:
    r"""
    Selecciona las 21 columnas definitivas, homologa coordenadas y asigna tipos óptimos.

    Equivalencia R (Fase 13, líneas 570-594):
        homi_Analisis_Final <- homi_Nueva %>%
          dplyr::select(
            codigo_caso = X2, tipo_delito = X4, ...,
            latitud_reparada = lat.new, longitud_reparada = lon.new, ...
          )

    Mapeo R → Python:
        df %>% select(nuevo = viejo, ...)  →  df[cols_origen].rename(columns={...})
        as.character(x)                    →  s.astype("string")
        as.Date(x)                         →  pd.to_datetime(s, errors="coerce")
        as.integer(x)                      →  pd.to_numeric(s, errors="coerce").astype("Int64")
        as.numeric(x)                      →  pd.to_numeric(s, errors="coerce").astype("float64")
        as.factor(x)                       →  s.astype("string").astype("category")

    ¿Por qué reemplazamos `latitud`/`longitud` por `lat_num`/`lon_num`?
        En `homi_georreferenciado.parquet` (salida de la Fase 4) coexisten:
          • `latitud` y `longitud`: los textos crudos originales del CSV (algunos sin punto decimal).
          • `lat_num` y `lon_num`: los números decimales ya validados y reparados en la Fase 4.
          • `ID_temp`: el identificador secuencial temporal usado en las auditorías espaciales.
        Aquí seleccionamos `lat_num` y `lon_num`, descartamos las cadenas crudas y `ID_temp`,
        y renombramos `lat_num` → `latitud` y `lon_num` → `longitud` para cumplir exactamente
        con las 21 variables documentadas en `docs/diccionario_datos.md`.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame proveniente de la Fase 4 (`homi_georreferenciado.parquet` o en memoria).

    Returns
    -------
    pd.DataFrame
        DataFrame depurado con exactamente 21 columnas ordenadas y tipadas.

    Raises
    ------
    ValueError
        Si el DataFrame de entrada está vacío o si quedan coordenadas nulas.
    KeyError
        Si falta alguna de las 21 columnas requeridas en el DataFrame de entrada.
    """
    print("  [5.1] Selección, homologación y tipado estricto de las 21 columnas finales")

    # ── Validación defensiva: evitar procesar una tabla vacía ──
    # `len(df) == 0` comprueba si el DataFrame tiene cero filas.
    if len(df) == 0:
        raise ValueError(
            "El DataFrame de entrada para la Fase 5 está vacío (0 filas). "
            "Verifique la salida de la Fase 4."
        )

    # Creamos una copia independiente (`.copy()`) para no alterar por accidente
    # el DataFrame que `main.py` mantiene en memoria (principio de inmutabilidad).
    df_trabajo = df.copy()

    # ── Respaldo de compatibilidad con nombres crudos heredados de R ──
    # Si alguien invoca esta función con columnas crudas ("X2", "X4", "lat.new", "lon.new"),
    # construimos un diccionario solo con las claves que existan y cuyo destino no exista aún.
    mapeo_respaldo = {
        col_cruda: col_limpia
        for col_cruda, col_limpia in {
            **MAPEO_COLUMNAS,
            "lat.new": "lat_num",
            "lon.new": "lon_num",
        }.items()
        if col_cruda in df_trabajo.columns and col_limpia not in df_trabajo.columns
    }
    if mapeo_respaldo:
        # `.rename(columns=...)` cambia los nombres de las columnas según el diccionario.
        df_trabajo = df_trabajo.rename(columns=mapeo_respaldo)

    # ── Construir la lista de 21 columnas de origen antes del renombrado final ──
    # Si la tabla trae `lat_num` y `lon_num` (salida estándar de la Fase 4), las elegimos
    # en la posición de `latitud` y `longitud`, descartando así las columnas `latitud`/`longitud`
    # de texto crudo y cualquier columna auxiliar como `ID_temp` o `geometry`.
    usar_coords_reparadas = (
        "lat_num" in df_trabajo.columns and "lon_num" in df_trabajo.columns
    )

    if usar_coords_reparadas:
        # Comprensión de lista: recorre `COLUMNAS_FINALES_21` en orden; cuando encuentra
        # "latitud" pone "lat_num", cuando encuentra "longitud" pone "lon_num", y el resto igual.
        mapeo_inverso_coords = {"latitud": "lat_num", "longitud": "lon_num"}
        columnas_origen = [
            mapeo_inverso_coords.get(col, col) for col in COLUMNAS_FINALES_21
        ]
    else:
        # Si ya venían como `latitud` y `longitud` numéricas, usamos la lista directa.
        columnas_origen = list(COLUMNAS_FINALES_21)

    # ── Verificar que no falte ninguna de las 21 columnas requeridas ──
    columnas_faltantes = [
        col for col in columnas_origen if col not in df_trabajo.columns
    ]
    if columnas_faltantes:
        raise KeyError(
            f"Faltan {len(columnas_faltantes)} columnas obligatorias para la Fase 5: "
            f"{columnas_faltantes}"
        )

    # ── Patrón arquitectónico: df[columnas_origen].rename(columns={...}) ──
    # En una sola expresión encadenada:
    #   1. `df_trabajo[columnas_origen]` filtra y ordena las 21 columnas deseadas
    #      (dejando fuera `ID_temp`, las coordenadas de texto crudo y extras).
    #   2. `.rename(columns=MAPEO_COORDENADAS_FINALES)` renombra `lat_num` → `latitud`
    #      y `lon_num` → `longitud` (si no están, pandas simplemente ignora esas claves).
    #   3. `.copy()` garantiza un bloque de memoria limpio y propio.
    df_final = (
        df_trabajo[columnas_origen]
        .rename(columns=MAPEO_COORDENADAS_FINALES)
        .copy()
    )

    # =====================================================================
    # CONVERSIÓN EXPLÍCITA DE TIPOS DE DATOS (CASTING)
    # =====================================================================

    # 1. Identificador policial → tipo `string` nativo de pandas (preserva pd.NA si existiera).
    df_final["codigo_caso"] = df_final["codigo_caso"].astype("string")

    # 2. Fecha exacta del hecho → tipo `datetime64[ns]` (permite series temporales en Fase 6).
    #    `errors="coerce"` convierte cualquier texto inválido en `NaT` (Not a Time) sin colapsar.
    df_final["fecha_hecho"] = pd.to_datetime(
        df_final["fecha_hecho"], errors="coerce"
    )

    # 3. Variables enteras → tipo `Int64` (con "I" mayúscula = entero nulable de pandas,
    #    que soporta valores faltantes `pd.NA` a diferencia del `int64` clásico de NumPy).
    for col_int in _COLUMNAS_ENTERO_NULABLE:
        # Primero convertimos a numérico decimal, redondeamos por seguridad y pasamos a Int64.
        df_final[col_int] = (
            pd.to_numeric(df_final[col_int], errors="coerce")
            .round()
            .astype("Int64")
        )

    # 4. Variables continuas/decimales → tipo `float64` (doble precisión IEEE 754).
    for col_float in _COLUMNAS_FLOTANTES:
        df_final[col_float] = pd.to_numeric(
            df_final[col_float], errors="coerce"
        ).astype("float64")

    # 5. Variables categóricas nominales (las 12 columnas de texto normalizadas en Fase 2)
    #    → tipo `category` (equivalente directo al `factor` de R).
    #    ¿Por qué pasar primero por `.astype("string")` y luego `.astype("category")`?
    #    Porque si una columna viene con mezcla de `object`/`None`/`NaN`, el paso intermedio
    #    por `"string"` unifica los textos y convierte los nulos limpiamente sin crear una
    #    categoría falsa llamada `"None"` o `"nan"`.
    for col_cat in COLUMNAS_CATEGORICAS_FINALES:
        df_final[col_cat] = (
            df_final[col_cat].astype("string").astype("category")
        )

    # ── Candado final de integridad espacial ──
    # Ningún registro en el entregable final puede tener latitud o longitud vacía (NaN).
    n_antes = len(df_final)
    df_final = df_final.dropna(subset=["latitud", "longitud"]).reset_index(drop=True)
    n_descartados_nan = n_antes - len(df_final)
    if n_descartados_nan > 0:
        print(f"        [AVISO] Filas eliminadas por latitud/longitud NaN: {n_descartados_nan:,}")

    if len(df_final) == 0:
        raise ValueError(
            "Tras validar coordenadas numéricas no quedaron registros válidos para exportar."
        )

    print(
        f"        Esquema consolidado: {len(df_final):,} filas × "
        f"{len(df_final.columns)} columnas limpias"
    )
    return df_final


# Alias semántico compatible con el boceto conceptual de `arquitectura_migracion_r_python.md`.
# En Python, asignar una función a otro nombre crea un sinónimo directo sin duplicar código.
etiquetar_columnas_finales = seleccionar_y_estandarizar_columnas


# =========================================================================
# PASO 5.2 — Exportación a formato CSV (interoperabilidad universal)
# =========================================================================
def exportar_csv(
    df: pd.DataFrame,
    ruta_salida: Path = SALIDA_CSV_FINAL,
) -> Path:
    r"""
    Exporta el dataset continental etiquetado a un archivo CSV plano en UTF-8.

    Equivalencia R (Fase 13, líneas 606-614):
        if (file.exists(archivo_csv)) {
          tryCatch(file.remove(archivo_csv), error = function(e) { ... })
        }
        write.csv(homi_Analisis_Final, archivo_csv, row.names = FALSE)

    Mapeo R → Python:
        write.csv(df, path, row.names = FALSE)  →  df.to_csv(path, index=False, encoding="utf-8")
        tryCatch(..., error = ...)              →  try: ... except PermissionError as exc: ...

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame final de 21 columnas ya estandarizado.
    ruta_salida : Path, optional
        Ruta destino del archivo CSV. Por defecto `data/processed/homi_Final_Continental_Etiquetado.csv`.

    Returns
    -------
    Path
        Ruta absoluta del archivo CSV generado.

    Raises
    ------
    PermissionError
        Si el archivo destino está bloqueado por otro programa (ej. Microsoft Excel).
    """
    print("  [5.2] Exportación a formato CSV (UTF-8)")

    # Convertimos a objeto Path por si quien llama a la función pasó un texto `str`.
    ruta_salida = Path(ruta_salida)

    # Creamos la carpeta `data/processed/` automáticamente si aún no existe:
    #   `parents=True` crea carpetas intermedias; `exist_ok=True` no falla si ya existe.
    ruta_salida.parent.mkdir(parents=True, exist_ok=True)

    # Bloque `try ... except`: equivalente al `tryCatch()` del script R (línea 607).
    # En Windows, si el usuario tiene el CSV abierto en Excel, el sistema operativo
    # bloquea el archivo y lanza `PermissionError`. Aquí capturamos ese error para
    # mostrar una explicación clara en español.
    try:
        # `index=False` evita que pandas escriba una columna extra "0, 1, 2..." al inicio
        # (exactamente igual que `row.names = FALSE` en R).
        # `encoding="utf-8"` asegura compatibilidad universal de caracteres.
        df.to_csv(ruta_salida, index=False, encoding="utf-8")
    except PermissionError as exc:
        raise PermissionError(
            f"No se pudo sobrescribir '{ruta_salida}'. "
            "Si el archivo CSV está abierto en Microsoft Excel u otro visor, "
            "ciérrelo y vuelva a ejecutar el pipeline."
        ) from exc

    # Calculamos el peso del archivo en megabytes (1 MB = 1024 * 1024 bytes) para el log.
    tamanio_mb = ruta_salida.stat().st_size / (1024 * 1024)
    print(f"        Guardado: {ruta_salida} ({tamanio_mb:.2f} MB)")
    return ruta_salida


# =========================================================================
# PASO 5.3 — Exportación a formato Apache Parquet (analítica de alto rendimiento)
# =========================================================================
def exportar_parquet(
    df: pd.DataFrame,
    ruta_salida: Path = SALIDA_PARQUET_FINAL,
    compresion: str = "snappy",
) -> Path:
    r"""
    Exporta el dataset final a formato columnar Apache Parquet con compresión Snappy.

    Equivalencia R (Fase 10 y 13, líneas 504 y 615):
        saveRDS(homi_Analisis_Final, file = "homi_Final_Continental_Etiquetado.rds")

    ¿Por qué Parquet reemplaza a `.rds`?
        • Conserva intactos los metadatos de tipos (`datetime64`, `Int64`, `float64`,
          diccionarios de `category` y `string`), algo que el CSV pierde por completo.
        • Almacenamiento columnar comprimido con `snappy`: ocupa ~4-6 veces menos espacio
          en disco que el CSV y se carga en milisegundos en la Fase 6 (Series Temporales).
        • Es un estándar abierto legible desde Python (Pandas, Polars, DuckDB), R (`arrow`) y Spark.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame final de 21 columnas con tipos optimizados.
    ruta_salida : Path, optional
        Ruta destino del Parquet. Por defecto `data/processed/homi_final.parquet`.
    compresion : str, optional
        Algoritmo de compresión de bloques (por defecto `"snappy"`).

    Returns
    -------
    Path
        Ruta absoluta del archivo Parquet generado.
    """
    print(f"  [5.3] Exportación a formato Parquet (pyarrow + {compresion})")

    ruta_salida = Path(ruta_salida)
    ruta_salida.parent.mkdir(parents=True, exist_ok=True)

    # `engine="pyarrow"` utiliza la implementación oficial en C++ de Apache Arrow,
    # preservando el esquema exacto de pandas (categorías, fechas y enteros nulables)
    # dentro de los metadatos internos del archivo Parquet.
    df.to_parquet(
        ruta_salida,
        index=False,
        engine="pyarrow",
        compression=compresion,
    )

    tamanio_mb = ruta_salida.stat().st_size / (1024 * 1024)
    print(f"        Guardado: {ruta_salida} ({tamanio_mb:.2f} MB)")
    return ruta_salida


# =========================================================================
# PASO 5.4 — Construcción del GeoDataFrame y exportación a GeoPackage (.gpkg)
# =========================================================================
def construir_geodataframe_final(
    df: pd.DataFrame,
    crs_epsg: int = CRS_OBJETIVO,
) -> gpd.GeoDataFrame:
    r"""
    Convierte el DataFrame tabular final en un `GeoDataFrame` con CRS `EPSG:4326`.

    Equivalencia R (Fase 10, línea 495):
        homi_Nueva_espacial <- st_as_sf(homi_Nueva, coords = c("lon.new", "lat.new"), crs = 4326)

    ¡Atención al orden de las coordenadas!
        En cartografía matemática, el plano cartesiano es `(X, Y)`:
          • Eje X (horizontal) = `longitud` (Este-Oeste, ej. -79.88 en Guayaquil).
          • Eje Y (vertical)   = `latitud`  (Norte-Sur, ej. -2.18 en Guayaquil).
        Por eso `gpd.points_from_xy(df["longitud"], df["latitud"])` recibe PRIMERO
        la longitud y SEGUNDO la latitud, exactamente igual que `coords = c("lon.new", "lat.new")` en R.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame con las columnas numéricas `longitud` y `latitud`.
    crs_epsg : int, optional
        Código EPSG del Sistema de Referencia de Coordenadas (por defecto `4326` = WGS84).

    Returns
    -------
    gpd.GeoDataFrame
        Capa vectorial de puntos lista para exportar o graficar.

    Raises
    ------
    KeyError
        Si el DataFrame no contiene las columnas `latitud` y `longitud`.
    ValueError
        Si existen coordenadas `NaN` en `latitud` o `longitud`.
    """
    # Verificamos que ambas columnas de coordenadas estén presentes.
    for col_coord in ("latitud", "longitud"):
        if col_coord not in df.columns:
            raise KeyError(
                f"No se encontró la columna '{col_coord}' para construir el GeoDataFrame."
            )

    # Verificamos que no existan valores vacíos (NaN) antes de crear geometrías Point.
    if df["latitud"].isna().any() or df["longitud"].isna().any():
        raise ValueError(
            "Existen valores NaN en 'latitud' o 'longitud'. "
            "Filtre o repare las coordenadas antes de construir el GeoDataFrame."
        )

    # `gpd.points_from_xy(x, y)` crea de forma vectorizada (en C, sin bucles `for`)
    # un arreglo de objetos geométricos `Point(longitud, latitud)` para todas las filas.
    geometria_puntos = gpd.points_from_xy(df["longitud"], df["latitud"])

    # Empaquetamos los atributos + la columna `geometry` + el CRS `EPSG:4326` en un GeoDataFrame.
    gdf = gpd.GeoDataFrame(
        df.copy(),
        geometry=geometria_puntos,
        crs=f"EPSG:{crs_epsg}",
    )
    return gdf


def exportar_geopackage(
    datos: pd.DataFrame | gpd.GeoDataFrame,
    ruta_salida: Path = SALIDA_GPKG_FINAL,
    nombre_capa: str = "homicidios_continental_2010_2024",
    crs_epsg: int = CRS_OBJETIVO,
) -> Path:
    r"""
    Exporta la capa vectorial de eventos al estándar abierto OGC GeoPackage (`.gpkg`).

    Equivalencia R (Fase 10, línea 500):
        st_write(homi_Nueva_espacial, "homi_Nueva.shp", delete_layer = TRUE, quiet = TRUE)

    Nota arquitectónica — ¿Por qué `.gpkg` reemplaza al formato legado `.shp` (Shapefile)?
        El formato ESRI Shapefile fue diseñado en los años 90 y sufre limitaciones severas:
          1. Trunca los nombres de columna a 10 caracteres (`motivacion_detalle` → `motivacion`,
             `nacionalidad_victima` → `nacionalid`), rompiendo la trazabilidad del diccionario.
          2. Dispersa el mapa en 4 a 7 archivos sueltos (`.shp`, `.shx`, `.dbf`, `.prj`, `.cpg`).
          3. Límite físico de 2 GB y problemas históricos de codificación con caracteres UTF-8.
        **GeoPackage (`.gpkg`)** almacena geometrías, atributos con nombres completos, tipos de
        fecha/numéricos, índice espacial R-tree y proyección CRS dentro de **un único archivo**
        SQLite estandarizado por el Open Geospatial Consortium (OGC), nativo en QGIS y ArcGIS Pro.

    Parameters
    ----------
    datos : pd.DataFrame or gpd.GeoDataFrame
        Tabla estandarizada (se convierte automáticamente a GeoDataFrame) o GeoDataFrame ya creado.
    ruta_salida : Path, optional
        Ruta destino del GeoPackage. Por defecto `data/processed/homi_final.gpkg`.
    nombre_capa : str, optional
        Nombre interno de la tabla espacial dentro del contenedor GeoPackage.
    crs_epsg : int, optional
        Código EPSG a utilizar si `datos` es un `pd.DataFrame` (por defecto `4326`).

    Returns
    -------
    Path
        Ruta absoluta del archivo `.gpkg` generado.
    """
    print("  [5.4] Exportación geoespacial a OGC GeoPackage (.gpkg, EPSG:4326)")

    ruta_salida = Path(ruta_salida)
    ruta_salida.parent.mkdir(parents=True, exist_ok=True)

    # `isinstance(obj, Clase)` comprueba de qué tipo es un objeto.
    # Si ya nos pasaron un GeoDataFrame con geometría activa, verificamos su CRS;
    # si nos pasaron un DataFrame común de pandas, construimos el GeoDataFrame aquí mismo.
    if isinstance(datos, gpd.GeoDataFrame) and datos.geometry is not None:
        gdf_salida = datos.copy()
        if gdf_salida.crs is None:
            gdf_salida = gdf_salida.set_crs(epsg=crs_epsg)
        elif gdf_salida.crs.to_epsg() != crs_epsg:
            gdf_salida = gdf_salida.to_crs(epsg=crs_epsg)
    else:
        gdf_salida = construir_geodataframe_final(datos, crs_epsg=crs_epsg)

    # Si existía un archivo `.gpkg` previo de una corrida anterior, lo reemplazamos
    # limpiamente para evitar capas huérfanas (equivalente a `delete_layer = TRUE` en R).
    if ruta_salida.exists():
        try:
            ruta_salida.unlink()  # `.unlink()` borra el archivo previo del disco.
        except PermissionError as exc:
            raise PermissionError(
                f"No se pudo actualizar '{ruta_salida}'. "
                "Si el archivo está abierto en QGIS o ArcGIS, ciérrelo e intente de nuevo."
            ) from exc

    # `to_file(..., driver="GPKG")` escribe la base espacial completa usando pyogrio/GDAL.
    gdf_salida.to_file(ruta_salida, driver="GPKG", layer=nombre_capa)

    tamanio_mb = ruta_salida.stat().st_size / (1024 * 1024)
    print(
        f"        Guardado: {ruta_salida} ({tamanio_mb:.2f} MB | "
        f"capa='{nombre_capa}' | CRS={gdf_salida.crs})"
    )
    return ruta_salida


# =========================================================================
# ORQUESTADOR DE EXPORTACIÓN MULTIFORMATO (Pasos 5.2 + 5.3 + 5.4)
# =========================================================================
def exportar_todos_formatos(
    df_etiquetado: pd.DataFrame,
    ruta_csv: Path = SALIDA_CSV_FINAL,
    ruta_parquet: Path = SALIDA_PARQUET_FINAL,
    ruta_gpkg: Path = SALIDA_GPKG_FINAL,
) -> dict[str, Path]:
    """
    Ejecuta en secuencia la escritura de los tres formatos finales (CSV, Parquet y GeoPackage).

    Parameters
    ----------
    df_etiquetado : pd.DataFrame
        DataFrame de 21 columnas producido por `seleccionar_y_estandarizar_columnas()`.
    ruta_csv : Path, optional
        Ruta de salida para el archivo CSV UTF-8.
    ruta_parquet : Path, optional
        Ruta de salida para el archivo Parquet comprimido con Snappy.
    ruta_gpkg : Path, optional
        Ruta de salida para el archivo vectorial GeoPackage.

    Returns
    -------
    dict[str, Path]
        Diccionario con las rutas generadas bajo las claves `"csv"`, `"parquet"` y `"gpkg"`.
    """
    # Ejecutamos cada exportador especializado y guardamos su ruta resultante.
    archivo_csv = exportar_csv(df_etiquetado, ruta_salida=ruta_csv)
    archivo_parquet = exportar_parquet(df_etiquetado, ruta_salida=ruta_parquet)
    archivo_gpkg = exportar_geopackage(df_etiquetado, ruta_salida=ruta_gpkg)

    return {
        "csv": archivo_csv,
        "parquet": archivo_parquet,
        "gpkg": archivo_gpkg,
    }


# =========================================================================
# EJECUCIÓN AUTÓNOMA DESDE EL ARTEFACTO GEORREFERENCIADO
# =========================================================================
def ejecutar_exportacion_autonoma(
    ruta_entrada: Path = PROCESSED_GEORREFERENCIADO,
) -> tuple[pd.DataFrame, dict[str, Path]]:
    """
    Carga `homi_georreferenciado.parquet`, estandariza las 21 columnas y exporta todo.

    Permite ejecutar únicamente la etapa de exportación sin volver a correr el resto del pipeline:
        python -m src.exportacion.exportador

    Parameters
    ----------
    ruta_entrada : Path, optional
        Ruta del archivo Parquet georreferenciado de entrada.

    Returns
    -------
    tuple[pd.DataFrame, dict[str, Path]]
        Tupla con `(df_etiquetado, rutas_exportadas)`.
    """
    ruta_entrada = Path(ruta_entrada)
    if not ruta_entrada.exists():
        raise FileNotFoundError(
            f"No existe el artefacto georreferenciado de entrada: '{ruta_entrada}'. "
            "Ejecute primero `python main.py`."
        )

    print("=" * 65)
    print("  EJECUCIÓN AUTÓNOMA — EXPORTADOR MULTIFORMATO")
    print("=" * 65)
    df_georreferenciado = pd.read_parquet(ruta_entrada)
    df_etiquetado = seleccionar_y_estandarizar_columnas(df_georreferenciado)
    rutas = exportar_todos_formatos(df_etiquetado)
    print("=" * 65)
    return df_etiquetado, rutas


# Si este archivo se ejecuta directamente en consola (`python -m src.exportacion.exportador`),
# lanza la exportación leyendo la base georreferenciada.
if __name__ == "__main__":
    ejecutar_exportacion_autonoma()

