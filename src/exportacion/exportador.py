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
    Este módulo es la etapa final de empaquetado de datos. Recibe la base reparada
    de la Fase 4 (que todavía conserva columnas auxiliares de trabajo como `ID_temp`
    y las coordenadas originales sin reparar en formato texto), selecciona únicamente
    las 21 columnas oficiales con el tipo de dato técnico que le corresponde a cada
    variable y persiste la tabla en disco en tres formatos complementarios: texto
    tabular (CSV), binario columnar (Parquet) y vectorial geoespacial (GeoPackage).
"""
# Nota sobre `r"""` al inicio de los docstrings:
#   El prefijo `r` significa "raw string" (cadena cruda). Le indica a Python que trate las
#   barras invertidas `\` literalmente como texto y NO como secuencias de escape (`\n`, `\t`),
#   evitando advertencias `SyntaxWarning` cuando documentamos rutas de Windows o expresiones regex.

# `from pathlib import Path` importa la clase `Path` de la librería estándar `pathlib`
# para representar rutas de carpetas y archivos como objetos multiplataforma.
from pathlib import Path

# `geopandas` (alias `gpd`) extiende a Pandas para trabajar con geometrías espaciales
# (puntos, líneas, polígonos) y sistemas de coordenadas CRS; equivale al paquete `sf` de R.
import geopandas as gpd

# `pandas` (alias `pd`) es la librería base de estructuras tabulares (`DataFrame` y `Series`);
# equivale al ecosistema `dplyr` / `tidyr` / `readr` de R.
import pandas as pd

# Importamos desde `config.py` las constantes globales (rutas, listas de columnas y CRS)
# para mantener un único punto de configuración en todo el proyecto.
from src.ingesta.config import (
    COLUMNAS_CATEGORICAS_FINALES,  # Lista de las 12 columnas nominales que se convertirán a `category`.
    COLUMNAS_FINALES_21,           # Lista ordenada de las 21 columnas del dataset final.
    CRS_OBJETIVO,                  # Código entero `4326` (sistema geodésico mundial WGS84).
    MAPEO_COLUMNAS,                # Diccionario `{"X2": "codigo_caso", ...}` por compatibilidad con crudos.
    MAPEO_COORDENADAS_FINALES,     # Diccionario `{"lat_num": "latitud", "lon_num": "longitud"}`.
    PROCESSED_GEORREFERENCIADO,    # Ruta de entrada: `data/processed/homi_georreferenciado.parquet`.
    SALIDA_CSV_FINAL,              # Ruta de salida 5.2: `homi_Final_Continental_Etiquetado.csv`.
    SALIDA_GPKG_FINAL,             # Ruta de salida 5.4: `homi_final.gpkg`.
    SALIDA_PARQUET_FINAL,          # Ruta de salida 5.3: `homi_final.parquet`.
)

# ── Constantes privadas del módulo (convención: guion bajo inicial `_`) ──
# En Python no existe la palabra reservada `private` (como en Java o C#). Por convención
# PEP 8, iniciar un nombre con `_` indica a otros desarrolladores que esta variable es de
# uso interno exclusivo de `exportador.py` y no forma parte de su interfaz externa.
# Anotación de tipo `list[str]`: declara explícitamente que es una lista cuyos elementos son cadenas `str`.
_COLUMNAS_ENTERO_NULABLE: list[str] = [
    "anio_hecho",          # Año cronológico del evento (2010..2024).
    "AUX_HORA_SISTEMA",    # Hora entera registrada en sistema (0..23).
    "AUX_MINUTO_SISTEMA",  # Minuto entero registrado en sistema (0..59).
]

_COLUMNAS_FLOTANTES: list[str] = [
    "hora_aproximada",  # Hora expresada en decimales (ej. 19.5 = 19h30, 19.6667 = 19h40).
    "edad_victima",     # Edad en años; requiere `float64` porque incluye decimales en lactantes (ej. 0.25) y `NaN`.
    "latitud",          # Coordenada geográfica Y validada/reparada en grados decimales.
    "longitud",         # Coordenada geográfica X validada/reparada en grados decimales.
]


# =========================================================================
# PASO 5.1 — Selección y renombrado definitivo de las 21 columnas limpias
# =========================================================================
# Anotaciones de tipo (Type Hints) en la firma `def funcion(df: pd.DataFrame) -> pd.DataFrame:`:
#   • `df: pd.DataFrame`  → el parámetro de entrada `df` debe ser una tabla `DataFrame` de Pandas.
#   • `-> pd.DataFrame`   → la función devuelve como resultado un nuevo `DataFrame` de Pandas.
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

    ¿Por qué sustituimos `latitud`/`longitud` por `lat_num`/`lon_num`?
        En `homi_georreferenciado.parquet` (salida de la Fase 4) coexisten 24 columnas:
          • `latitud` y `longitud`: cadenas de texto originales del CSV crudo (algunas sin punto decimal).
          • `lat_num` y `lon_num`: coordenadas numéricas (`float64`) ya validadas y reparadas en Fase 4.
          • `ID_temp`: llave entera secuencial creada solo para auditar intersecciones espaciales.
        Aquí tomamos `lat_num` y `lon_num`, descartamos las cadenas crudas e `ID_temp`, y
        renombramos `lat_num` → `latitud` y `lon_num` → `longitud` para obtener las 21 columnas
        exactas documentadas en `docs/diccionario_datos.md`.

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

    # ── 1. Validación defensiva de entrada vacía ──
    # `len(df)` devuelve el número de filas del DataFrame (equivale a `nrow(df)` en R).
    # Si entran 0 filas, detenemos la ejecución temprano lanzando una excepción `ValueError`.
    if len(df) == 0:
        raise ValueError(
            "El DataFrame de entrada para la Fase 5 está vacío (0 filas). "
            "Verifique la salida de la Fase 4."
        )

    # ── 2. Copia defensiva en memoria ──
    # En Python, pasar un DataFrame a una función pasa una REFERENCIA al mismo objeto en RAM.
    # Si modificáramos `df` directamente, alteraríamos la variable original fuera de esta función.
    # `.copy()` reserva un DataFrame independiente para trabajar sin efectos secundarios.
    df_trabajo = df.copy()

    # ── 3. Respaldo de compatibilidad con nombres heredados del script R ──
    # Desglose técnico de esta comprensión de diccionario (dict comprehension):
    #   • `{**MAPEO_COLUMNAS, "lat.new": "lat_num", "lon.new": "lon_num"}`:
    #       El operador `**` desempaqueta todos los pares `clave: valor` de `MAPEO_COLUMNAS`
    #       dentro de un diccionario temporal nuevo y le añade dos equivalencias extra de R.
    #   • `.items()`: entrega cada par `(col_cruda, col_limpia)` para iterar en el `for`.
    #   • `if col_cruda in df_trabajo.columns and col_limpia not in df_trabajo.columns`:
    #       Solo incluye el renombrado si la columna vieja existe en la tabla Y el nombre
    #       nuevo todavía no existe (evitando crear dos columnas con el mismo nombre).
    mapeo_respaldo = {
        col_cruda: col_limpia
        for col_cruda, col_limpia in {
            **MAPEO_COLUMNAS,
            "lat.new": "lat_num",
            "lon.new": "lon_num",
        }.items()
        if col_cruda in df_trabajo.columns and col_limpia not in df_trabajo.columns
    }
    # En Python, un diccionario no vacío evalúa como `True`; uno vacío `{}` evalúa como `False`.
    if mapeo_respaldo:
        # `.rename(columns=...)` devuelve un DataFrame con los encabezados actualizados.
        df_trabajo = df_trabajo.rename(columns=mapeo_respaldo)

    # ── 4. Determinar qué columnas de coordenadas seleccionar ──
    # Verificamos con el operador `in` si ambas columnas numéricas reparadas en la Fase 4
    # están disponibles dentro del índice de columnas `df_trabajo.columns`.
    usar_coords_reparadas = (
        "lat_num" in df_trabajo.columns and "lon_num" in df_trabajo.columns
    )

    if usar_coords_reparadas:
        # Si existen `lat_num` y `lon_num`, armamos la lista `columnas_origen` sustituyendo
        # temporalmente `"latitud"` por `"lat_num"` y `"longitud"` por `"lon_num"`.
        # ¿Cómo funciona `diccionario.get(clave, valor_por_defecto)`?
        #   • Si `col` es `"latitud"`, lo encuentra en `mapeo_inverso_coords` y devuelve `"lat_num"`.
        #   • Si `col` es `"codigo_caso"`, NO está en `mapeo_inverso_coords`, así que devuelve
        #     el segundo argumento (`col`, es decir `"codigo_caso"` intacto).
        # Así conservamos el orden exacto de las 21 columnas y dejamos fuera las cadenas crudas.
        mapeo_inverso_coords = {"latitud": "lat_num", "longitud": "lon_num"}
        columnas_origen = [
            mapeo_inverso_coords.get(col, col) for col in COLUMNAS_FINALES_21
        ]
    else:
        # Si el DataFrame ya venía con `latitud` y `longitud` limpias (sin `lat_num`/`lon_num`),
        # copiamos la lista estándar con `list(...)`.
        columnas_origen = list(COLUMNAS_FINALES_21)

    # ── 5. Auditoría de completitud de esquema (21 columnas obligatorias) ──
    # Comprensión de lista que recolecta cualquier columna requerida que no esté presente.
    columnas_faltantes = [
        col for col in columnas_origen if col not in df_trabajo.columns
    ]
    if columnas_faltantes:
        # `KeyError` es la excepción estándar en Python/Pandas cuando falta una llave o columna.
        raise KeyError(
            f"Faltan {len(columnas_faltantes)} columnas obligatorias para la Fase 5: "
            f"{columnas_faltantes}"
        )

    # ── 6. Selección estructural y renombrado definitivo ──
    # Desglose paso a paso del encadenamiento de métodos (method chaining):
    #   1. `df_trabajo[columnas_origen]`:
    #        Indexación con lista de nombres: proyecta únicamente esas 21 columnas en ese
    #        orden exacto, descartando automáticamente `ID_temp`, `latitud`/`longitud` crudas
    #        y cualquier otra columna residual.
    #   2. `.rename(columns=MAPEO_COORDENADAS_FINALES)`:
    #        Renombra `"lat_num"` → `"latitud"` y `"lon_num"` → `"longitud"`.
    #        (Si esas claves no estaban porque entró por el `else`, Pandas las ignora sin error).
    #   3. `.copy()`:
    #        Materializa el nuevo DataFrame en memoria para evitar advertencias `SettingWithCopyWarning`.
    df_final = (
        df_trabajo[columnas_origen]
        .rename(columns=MAPEO_COORDENADAS_FINALES)
        .copy()
    )

    # =====================================================================
    # 7. CONVERSIÓN EXPLÍCITA DE TIPOS DE DATOS (TYPE CASTING)
    # =====================================================================

    # 7.1 Identificador policial → `string` (StringDtype de Pandas).
    #     A diferencia de `object` (que puede mezclar cualquier tipo de objeto Python),
    #     `"string"` garantiza que toda celda sea texto o el valor faltante tipado `pd.NA`.
    df_final["codigo_caso"] = df_final["codigo_caso"].astype("string")

    # 7.2 Fecha del incidente → `datetime64[ns]`.
    #     `pd.to_datetime(..., errors="coerce")` parsea cadenas ISO `"YYYY-MM-DD"` a fechas reales.
    #     El parámetro `errors="coerce"` convierte fechas malformadas en `NaT` (Not a Time)
    #     en lugar de abortar la ejecución con un `ValueError`.
    df_final["fecha_hecho"] = pd.to_datetime(
        df_final["fecha_hecho"], errors="coerce"
    )

    # 7.3 Variables discretas enteras → `Int64` (entero nulable de 64 bits).
    #     Recorremos la lista `_COLUMNAS_ENTERO_NULABLE` con un bucle `for`:
    #       • `pd.to_numeric(..., errors="coerce")`: convierte textos como `"20"` a número (`20.0`).
    #       • `.round()`: redondea cualquier residuo flotante antes del casteo entero.
    #       • `.astype("Int64")`: convierte al tipo entero nulable de Pandas (con "I" mayúscula).
    for col_int in _COLUMNAS_ENTERO_NULABLE:
        df_final[col_int] = (
            pd.to_numeric(df_final[col_int], errors="coerce")
            .round()
            .astype("Int64")
        )

    # 7.4 Variables continuas decimales → `float64` (punto flotante IEEE 754 de 64 bits).
    #     Preserva fracciones horarias (`19.5`), edades decimales de lactantes (`0.25`),
    #     valores desconocidos (`NaN`) y toda la precisión decimal de `latitud` y `longitud`.
    for col_float in _COLUMNAS_FLOTANTES:
        df_final[col_float] = pd.to_numeric(
            df_final[col_float], errors="coerce"
        ).astype("float64")

    # 7.5 Variables nominales de baja cardinalidad → `category` (CategoricalDtype).
    #     Desglose técnico de `.astype("string").astype("category")`:
    #       • Si hiciéramos `.astype(str)` (tipo `str` básico de Python), un valor nulo `None`
    #         se transformaría en la palabra literal `"None"`, creando una categoría falsa.
    #       • En cambio, `.astype("string")` convierte `None`/`np.nan` en `pd.NA` real, y al
    #         encadenar `.astype("category")`, los valores faltantes permanecen como nulos
    #         mientras los textos válidos se codifican en un diccionario compacto de categorías.
    for col_cat in COLUMNAS_CATEGORICAS_FINALES:
        df_final[col_cat] = (
            df_final[col_cat].astype("string").astype("category")
        )

    # ── 8. Candado final de integridad espacial ──
    # Desglose de `df_final.dropna(subset=["latitud", "longitud"]).reset_index(drop=True)`:
    #   • `.dropna(subset=["latitud", "longitud"])`: elimina únicamente las filas donde
    #     `latitud` O `longitud` sean `NaN` (no elimina filas si `edad_victima` es `NaN`,
    #     porque `edad_victima` no está en `subset`).
    #   • `.reset_index(drop=True)`: renumera el índice de filas desde `0, 1, 2, ..., N-1`
    #     sin huecos, y `drop=True` descarta el índice viejo para no insertarlo como columna extra.
    n_antes = len(df_final)
    df_final = df_final.dropna(subset=["latitud", "longitud"]).reset_index(drop=True)
    n_descartados_nan = n_antes - len(df_final)
    if n_descartados_nan > 0:
        print(f"        [AVISO] Filas eliminadas por latitud/longitud NaN: {n_descartados_nan:,}")

    if len(df_final) == 0:
        raise ValueError(
            "Tras validar coordenadas numéricas no quedaron registros válidos para exportar."
        )

    # `{len(df_final):,}` formatea el entero con separador de miles (ej. `38,565`).
    print(
        f"        Esquema consolidado: {len(df_final):,} filas × "
        f"{len(df_final.columns)} columnas limpias"
    )
    return df_final


# Alias funcional: en Python las funciones son "objetos de primera clase", por lo que
# asignar `etiquetar_columnas_finales = seleccionar_y_estandarizar_columnas` hace que ambos
# nombres apunten exactamente a la misma función en memoria (mantiene compatibilidad con
# el diagrama conceptual de la guía de arquitectura sin duplicar código).
etiquetar_columnas_finales = seleccionar_y_estandarizar_columnas


# =========================================================================
# PASO 5.2 — Exportación a formato CSV (interoperabilidad universal)
# =========================================================================
# Parámetro con valor por defecto `ruta_salida: Path = SALIDA_CSV_FINAL`:
#   Si quien llama a `exportar_csv(df)` omite el segundo argumento, Python usa automáticamente
#   `SALIDA_CSV_FINAL`. En los tests unitarios podemos pasar una ruta temporal `tmp_path / "x.csv"`.
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
        Ruta del archivo CSV generado.

    Raises
    ------
    PermissionError
        Si el archivo destino está bloqueado por otro proceso del sistema operativo (ej. Excel).
    """
    print("  [5.2] Exportación a formato CSV (UTF-8)")

    # Normalizamos `ruta_salida` a un objeto `Path` (por si el llamador pasó un `str` común).
    ruta_salida = Path(ruta_salida)

    # Garantizamos que exista la carpeta contenedora (`ruta_salida.parent`, ej. `data/processed/`):
    #   • `parents=True`: crea todos los directorios padre necesarios si no existen.
    #   • `exist_ok=True`: si la carpeta ya existe, continúa sin lanzar `FileExistsError`.
    ruta_salida.parent.mkdir(parents=True, exist_ok=True)

    # Manejo robusto de bloqueo de archivos (`try ... except PermissionError as exc:`):
    #   En Windows, abrir un CSV en Microsoft Excel adquiere un bloqueo exclusivo (file lock)
    #   a nivel de sistema operativo. Si intentamos sobrescribirlo, Python recibe `PermissionError`.
    #   Capturamos ese error específico y relanzamos una explicación clara conservando la causa
    #   técnica original mediante `from exc` (exception chaining).
    try:
        # `index=False` impide escribir el índice numérico (0, 1, 2...) como primera columna
        # anónima (equivale exactamente a `row.names = FALSE` en R).
        # `encoding="utf-8"` fija la codificación estándar internacional de caracteres.
        df.to_csv(ruta_salida, index=False, encoding="utf-8")
    except PermissionError as exc:
        raise PermissionError(
            f"No se pudo sobrescribir '{ruta_salida}'. "
            "Si el archivo CSV está abierto en Microsoft Excel u otro visor, "
            "ciérrelo y vuelva a ejecutar el pipeline."
        ) from exc

    # `.stat().st_size` consulta al sistema de archivos el tamaño exacto en bytes;
    # dividir entre `1024 * 1024` (1,048,576 bytes) lo expresa en Megabytes (MiB).
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

    ¿Por qué Parquet reemplaza técnicamente a `.rds`?
        • Esquema embebido (self-describing): almacena en sus metadatos internos el tipo exacto
          de cada columna (`datetime64[ns]`, `Int64`, `float64`, diccionarios `category` y `string`).
          Al hacer `pd.read_parquet(...)` en la Fase 6, la tabla se reconstruye idéntica sin re-parsear.
        • Orientación por columnas + compresión `snappy`: agrupa valores homogéneos contiguos en disco,
          reduciendo el tamaño de ~6.5 MB (CSV) a ~1.3 MB y acelerando lecturas selectivas de columnas.
        • Interoperabilidad abierta: compatible con Pandas, Polars, DuckDB, Spark y el paquete `arrow` de R.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame final de 21 columnas con tipos optimizados.
    ruta_salida : Path, optional
        Ruta destino del Parquet. Por defecto `data/processed/homi_final.parquet`.
    compresion : str, optional
        Códec de compresión de páginas Parquet (por defecto `"snappy"`, óptimo en velocidad/ratio).

    Returns
    -------
    Path
        Ruta del archivo Parquet generado.
    """
    print(f"  [5.3] Exportación a formato Parquet (pyarrow + {compresion})")

    ruta_salida = Path(ruta_salida)
    ruta_salida.parent.mkdir(parents=True, exist_ok=True)

    # `df.to_parquet(...)`:
    #   • `index=False`: no serializa el RangeIndex secuencial innecesario.
    #   • `engine="pyarrow"`: usa el motor C++ de Apache Arrow para escritura vectorizada.
    #   • `compression=compresion`: aplica compresión Snappy por bloques columnares.
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
    Convierte el DataFrame tabular final en un `GeoDataFrame` espacial con CRS `EPSG:4326`.

    Equivalencia R (Fase 10, línea 495):
        homi_Nueva_espacial <- st_as_sf(homi_Nueva, coords = c("lon.new", "lat.new"), crs = 4326)

    Convención matemática del orden `(X, Y)` en SIG:
        En geometría cartesiana y en librerías geoespaciales (`sf`, `GeoPandas`, `GDAL`, `PostGIS`),
        toda coordenada puntual se construye siempre en orden `(X, Y)`:
          • `X` = `longitud` (desplazamiento Este-Oeste respecto a Greenwich; ej. `-79.8891`).
          • `Y` = `latitud`  (desplazamiento Norte-Sur respecto al Ecuador; ej. `-2.1894`).
        Invertir el orden situaría los puntos en el océano Antártico; por eso pasamos
        explícitamente `gpd.points_from_xy(df["longitud"], df["latitud"])`.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame con las columnas numéricas `longitud` y `latitud`.
    crs_epsg : int, optional
        Código numérico EPSG del sistema de referencia espacial (`4326` = WGS84).

    Returns
    -------
    gpd.GeoDataFrame
        Tabla espacial que conserva las 21 columnas + la columna activa `geometry` de tipo `Point`.

    Raises
    ------
    KeyError
        Si el DataFrame no contiene `latitud` o `longitud`.
    ValueError
        Si alguna fila presenta `NaN` en `latitud` o `longitud`.
    """
    # Recorremos la tupla `("latitud", "longitud")` verificando existencia de ambas columnas.
    for col_coord in ("latitud", "longitud"):
        if col_coord not in df.columns:
            raise KeyError(
                f"No se encontró la columna '{col_coord}' para construir el GeoDataFrame."
            )

    # Desglose de `df["latitud"].isna().any()`:
    #   • `.isna()` devuelve una Serie booleana (`True` donde hay `NaN`, `False` donde hay número).
    #   • `.any()` devuelve `True` si AL MENOS UNA fila es `True` (equivale a `any(is.na(x))` en R).
    if df["latitud"].isna().any() or df["longitud"].isna().any():
        raise ValueError(
            "Existen valores NaN en 'latitud' o 'longitud'. "
            "Filtre o repare las coordenadas antes de construir el GeoDataFrame."
        )

    # `gpd.points_from_xy(x, y)` construye en C (mediante Shapely 2 / GEOS vectorizado) un
    # `GeometryArray` con objetos `Point(lon, lat)` sin iterar fila por fila en Python.
    geometria_puntos = gpd.points_from_xy(df["longitud"], df["latitud"])

    # Instanciamos el `GeoDataFrame` acoplando:
    #   • `df.copy()`: copia de las 21 columnas de atributos.
    #   • `geometry=geometria_puntos`: designa la columna geométrica activa.
    #   • `crs=f"EPSG:{crs_epsg}"`: asigna metadatos de proyección `"EPSG:4326"`.
    gdf = gpd.GeoDataFrame(
        df.copy(),
        geometry=geometria_puntos,
        crs=f"EPSG:{crs_epsg}",
    )
    return gdf


# Anotación de unión de tipos `datos: pd.DataFrame | gpd.GeoDataFrame`:
#   El operador `|` (introducido en Python 3.10) significa "puede ser A o B".
#   Permite que esta función acepte indistintamente una tabla normal `DataFrame`
#   (y ella misma construya los puntos) o un `GeoDataFrame` ya armado.
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

    Justificación arquitectónica (`.gpkg` frente al formato legado `.shp`):
        El formato ESRI Shapefile (`.shp`) presenta restricciones técnicas obsoletas:
          1. Su tabla de atributos dBASE (`.dbf`) trunca todo nombre de columna a 10 caracteres
             ASCII (`motivacion_detalle` → `motivacion`, `nacionalidad_victima` → `nacionalid`).
          2. Requiere múltiples archivos acoplados (`.shp`, `.shx`, `.dbf`, `.prj`, `.cpg`); si
             falta uno al copiar la carpeta, la capa queda inutilizable.
          3. No almacena tipos `datetime` completos con hora ni supera 2 GB por componente.
        **OGC GeoPackage (`.gpkg`)** encapsula geometrías WKB, índice espacial R-tree, CRS y
        atributos con nombres íntegros en UTF-8 dentro de **un único contenedor SQLite**,
        soportado de forma nativa en QGIS, ArcGIS Pro, GeoPandas, PostGIS y `sf` de R.

    Parameters
    ----------
    datos : pd.DataFrame or gpd.GeoDataFrame
        Tabla estandarizada de 21 columnas o GeoDataFrame con geometría puntual.
    ruta_salida : Path, optional
        Ruta destino del archivo `.gpkg`. Por defecto `data/processed/homi_final.gpkg`.
    nombre_capa : str, optional
        Nombre de la tabla espacial interna dentro del GeoPackage.
    crs_epsg : int, optional
        Código EPSG objetivo (por defecto `4326`).

    Returns
    -------
    Path
        Ruta del archivo `.gpkg` generado.
    """
    print("  [5.4] Exportación geoespacial a OGC GeoPackage (.gpkg, EPSG:4326)")

    ruta_salida = Path(ruta_salida)
    ruta_salida.parent.mkdir(parents=True, exist_ok=True)

    # `isinstance(objeto, Clase)` comprueba en tiempo de ejecución si `datos` ya es un `GeoDataFrame`.
    if isinstance(datos, gpd.GeoDataFrame) and datos.geometry is not None:
        gdf_salida = datos.copy()
        # Si el GeoDataFrame no tenía CRS declarado (`None`), se lo asignamos con `.set_crs()`;
        # si tenía otro CRS distinto (ej. UTM `32717`), lo reproyectamos matemáticamente con `.to_crs()`.
        if gdf_salida.crs is None:
            gdf_salida = gdf_salida.set_crs(epsg=crs_epsg)
        elif gdf_salida.crs.to_epsg() != crs_epsg:
            gdf_salida = gdf_salida.to_crs(epsg=crs_epsg)
    else:
        # Si entró un `pd.DataFrame` tabular común, delegamos la creación espacial al helper anterior.
        gdf_salida = construir_geodataframe_final(datos, crs_epsg=crs_epsg)

    # Equivalente limpio a `delete_layer = TRUE` de `sf::st_write()`:
    # Si existe un `.gpkg` de una ejecución previa, `.unlink()` elimina el archivo anterior
    # para escribir un contenedor SQLite limpio y compacto desde cero.
    if ruta_salida.exists():
        try:
            ruta_salida.unlink()
        except PermissionError as exc:
            raise PermissionError(
                f"No se pudo actualizar '{ruta_salida}'. "
                "Si el archivo está abierto en QGIS o ArcGIS, ciérrelo e intente de nuevo."
            ) from exc

    # `.to_file(..., driver="GPKG", layer=nombre_capa)` invoca el motor vectorial GDAL/pyogrio
    # en C++ para escribir las 38,565 geometrías puntuales y sus 21 atributos en pocos segundos.
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
# `-> dict[str, Path]` indica que devuelve un diccionario cuyas claves son cadenas
# (`"csv"`, `"parquet"`, `"gpkg"`) y cuyos valores son objetos `Path` con las rutas creadas.
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
    # Invocamos cada función especializada y capturamos la ruta verificada que retorna.
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
# `-> tuple[pd.DataFrame, dict[str, Path]]`: devuelve una tupla de 2 posiciones:
#   1) el DataFrame ya estandarizado y 2) el diccionario de rutas exportadas.
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
    # `not ruta_entrada.exists()` comprueba si el archivo Parquet previo aún no existe en disco.
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


# Bloque estándar de punto de entrada en Python:
#   • Si otro módulo importa este archivo (`from src.exportacion.exportador import ...`),
#     `__name__` vale `"src.exportacion.exportador"` y este `if` NO se ejecuta.
#   • Si el usuario ejecuta este módulo directamente (`python -m src.exportacion.exportador`),
#     Python asigna `"__main__"` a `__name__` y entra al bloque ejecutando la exportación.
if __name__ == "__main__":
    ejecutar_exportacion_autonoma()
