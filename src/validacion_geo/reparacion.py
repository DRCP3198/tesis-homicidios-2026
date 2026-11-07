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

¿Por qué exactamente esos 4 formatos?
    Porque Ecuador continental abarca desde ~1.4° Norte (Esmeraldas/Carchi)
    hasta ~5.0° Sur (Loja/Zamora). Eso significa que TODA latitud válida en
    Ecuador cae obligatoriamente en uno de estos 4 moldes:
        1.  X.XXXXXX   → Norte lejos de la línea (ej.  1.25° en Esmeraldas)
        2.  0.XXXXXX   → Norte pegado a la línea (ej.  0.35° en Ibarra)
        3. -X.XXXXXX   → Sur lejos de la línea   (ej. -2.18° en Guayaquil) ← ¡la mayoría!
        4. -0.XXXXXX   → Sur pegado a la línea   (ej. -0.18° en Quito)

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
import geopandas as gpd  # Tablas geoespaciales y unión punto-polígono (sjoin).
import numpy as np       # Operaciones numéricas base.
import pandas as pd      # Tablas y columnas de datos (DataFrame, Series).

from src.ingesta.config import CRS_OBJETIVO  # 4326 (WGS84)


# =========================================================================
# FUNCIONES AUXILIARES: Limpieza de cadena numérica
# =========================================================================
# El guión bajo "_" al inicio del nombre (_limpiar_cadena_lat) es una
# convención de Python: indica que es una función INTERNA ("privada") de este
# archivo; los demás módulos no deberían necesitar llamarla directamente.
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
    # .astype(str) → asegura que todos los valores sean texto.
    limpia = serie_lat.astype(str)
    # .str.replace(viejo, nuevo) → en cada celda reemplaza `viejo` por `nuevo`.
    # Aquí reemplazamos cualquier punto "." por "" (nada = lo borra).
    # Ej: "-2.18.94" → "-21894"
    limpia = limpia.str.replace(r"\.", "", regex=True)
    # Ahora borramos cualquier signo menos "-". regex=False porque "-" es un
    # carácter literal simple, no hace falta expresión regular.
    # Ej: "-21894" → "21894" (solo quedan dígitos puros, listos para rearmar).
    limpia = limpia.str.replace("-", "", regex=False)
    return limpia


# =========================================================================
# ESCENARIO 1: Formato "X.XXXXXX" (Positivo — Hemisferio Norte)
# =========================================================================
# Nota de diseño: las 4 funciones de reconstrucción son "FUNCIONES PURAS":
# reciben una columna de texto y devuelven otra columna nueva sin modificar
# nada externo. Eso permite probarlas de forma aislada y muy rápida.
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
    # OJO con las posiciones: en R se cuenta desde 1, en Python desde 0.
    #   limpia_lat = "136965"
    #   .str[0]  → carácter en posición 0 (el primero): "1"
    #   .str[1:] → desde la posición 1 hasta el final ("slicing"): "36965"
    parte_entera = limpia_lat.str[0]        # str_sub(x, 1, 1)
    parte_decimal = limpia_lat.str[1:]      # str_sub(x, 2, len)
    # El operador "+" entre columnas de texto pega (concatena) fila por fila:
    #   "1" + "." + "36965"  →  "1.36965"
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
    # ¿Por qué hace falta este escenario aparte del 1?
    # Porque cuando alguien escribió 0.9592 sin punto ("09592") y R lo pasó
    # por as.numeric(), el cero inicial desapareció → quedó "9592".
    # El Escenario 1 armaría "9.592" (en Colombia/Venezuela), mientras que este
    # vuelve a anteponer el "0." perdido → "0.9592" (Esmeraldas).
    parte_1 = limpia_lat.str[0]   # Primer dígito (ej. "9")
    parte_2 = limpia_lat.str[1:]  # Resto de dígitos (ej. "592")
    # "0." + "9" + "592" → "0.9592"
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
    # Ejemplo con Guayaquil (limpia_lat = "21894"):
    parte_entera = limpia_lat.str[0]    # "2"
    parte_decimal = limpia_lat.str[1:]  # "1894"
    # "-" + "2" + "." + "1894"  →  "-2.1894"
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
    # Igual que el Escenario 2, pero al SUR de la línea ecuatorial:
    # Ej. Quito está en -0.1807 → sin punto ni cero quedó "1807"
    # → aquí rearmamos "-0." + "1" + "807" = "-0.1807".
    parte_1 = limpia_lat.str[0]
    parte_2 = limpia_lat.str[1:]
    return "-0." + parte_1 + parte_2


# =========================================================================
# VALIDACIÓN: sjoin tras reconstrucción
# =========================================================================
def validar_reconstruccion_sjoin(
    df: pd.DataFrame,              # Filas candidatas a reparar.
    lat_reconstruida: pd.Series,   # La nueva latitud propuesta por un escenario.
    mapa: gpd.GeoDataFrame,        # El mapa de cantones contra el que probamos.
) -> set[int]:                     # Devuelve un CONJUNTO con los ID_temp rescatados.
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
    # Si no hay filas que probar, devolvemos un conjunto vacío set().
    if len(df) == 0:
        return set()

    # Convertir latitud reconstruida a numérico
    # Ej: "-2.1894" → -2.1894 | "1." (cadena rota) → 1.0 | basura → NaN
    lat_num = pd.to_numeric(lat_reconstruida, errors="coerce")

    # Filtrar registros con latitud válida
    # .notna() → True donde NO es nulo. "&" = "Y" lógico fila por fila
    # (en pandas se usa "&" entre columnas booleanas, NO la palabra `and`).
    validos = lat_num.notna() & df["lon_num"].notna()
    if validos.sum() == 0:  # Ninguna fila tuvo ambas coordenadas válidas.
        return set()

    df_validos = df[validos].copy()
    lat_valida = lat_num[validos]

    # Crear GeoDataFrame de puntos con la latitud reconstruida
    # Equivale a: st_as_sf(data.frame(y=..., x=...), coords=c("x","y"), crs=...)
    # Usamos la longitud que ya teníamos (lon_num) + la NUEVA latitud propuesta.
    gdf_prueba = gpd.GeoDataFrame(
        df_validos,
        geometry=gpd.points_from_xy(df_validos["lon_num"], lat_valida),
        crs=f"EPSG:{CRS_OBJETIVO}",
    )

    # sjoin vectorizado (reemplaza el bucle R completo)
    # how="inner" → aquí solo nos interesan los puntos que SÍ cayeron dentro
    #               de algún polígono del mapa; los que caen en el mar o en
    #               otro país se descartan directo (más rápido que "left").
    resultado = gpd.sjoin(
        gdf_prueba,
        mapa[["CANTON_MAPA", "geometry"]],
        how="inner",
        predicate="intersects",
    )

    # Filtrar donde cantón reportado == cantón geográfico
    # ¡Esta es la prueba de fuego! No basta con que el punto caiga en Ecuador:
    # tiene que caer específicamente en el MISMO cantón que dice el registro.
    # Si la reparación de Guayaquil cayó dentro del polígono de GUAYAQUIL → ¡rescatado!
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

    # Si no llegó ningún registro sin punto decimal, devolvemos 5 tablas vacías.
    if len(geo_corregir_decimales) == 0:
        print("        No hay registros con decimales corruptos para reparar.")
        vacio = pd.DataFrame()
        return vacio, vacio, vacio, vacio, vacio

    # ── Preparación: limpiar cadena de latitud ──
    # Equivale a: gsub("\\.", "", ...) + gsub("-", "", ...)
    df = geo_corregir_decimales.copy()
    # Dejamos solo los dígitos puros en una columna auxiliar "limpia_lat".
    df["limpia_lat"] = _limpiar_cadena_lat(df["latitud_original"])

    # `pendientes` es la "bolsa" de casos aún no resueltos. A medida que cada
    # escenario rescata registros, los sacamos de `pendientes` para que el
    # siguiente escenario no los vuelva a evaluar (evita duplicados).
    pendientes = df.copy()
    n_total = len(pendientes)

    # Lista de parejas (nombre_para_imprimir, función_a_ejecutar).
    # En Python las funciones son objetos como cualquier otro: se pueden guardar
    # dentro de una lista y recorrerlas con un `for` para no repetir 4 veces el
    # mismo bloque de código (principio DRY: "Don't Repeat Yourself").
    escenarios = [
        ("Escenario 1: X.XXXXXX  (positivo Norte)", reconstruir_escenario_1),
        ("Escenario 2: 0.XXXXXX  (positivo Ecuador)", reconstruir_escenario_2),
        ("Escenario 3: -X.XXXXXX (negativo Sur) ← CRÍTICO", reconstruir_escenario_3),
        ("Escenario 4: -0.XXXXXX (negativo Ecuador)", reconstruir_escenario_4),
    ]

    # Lista donde iremos guardando los DataFrames rescatados por cada escenario.
    # `: list[pd.DataFrame]` indica que es una lista cuyos elementos son DataFrames.
    resultados: list[pd.DataFrame] = []

    # Desempaquetamos cada tupla de la lista en `nombre` (texto) y `fn_reconstruir` (función).
    for nombre, fn_reconstruir in escenarios:
        # Si los escenarios anteriores ya rescataron TODO, no queda nada que probar:
        # guardamos una tabla vacía para este escenario y `continue` salta a la siguiente vuelta.
        if len(pendientes) == 0:
            resultados.append(pd.DataFrame())
            continue

        # Reconstruir latitud según el escenario
        # Llamamos a la función del turno actual (escenario 1, luego 2, luego 3, luego 4).
        lat_reconstruida = fn_reconstruir(pendientes["limpia_lat"])

        # Validar contra el mapa con sjoin
        # Nos devuelve los ID_temp cuya latitud reconstruida SÍ cayó en su cantón.
        ids_rescatados = validar_reconstruccion_sjoin(
            pendientes, lat_reconstruida, mapa
        )

        # Separar rescatados del pool de pendientes
        # Equivale a: geo.corregir.1X <- geo.corregir.1 %>% filter(ID.temp %in% correctos3)
        rescatados = pendientes[pendientes["ID_temp"].isin(ids_rescatados)].copy()

        # Actualizar lat_num con el valor reparado para los rescatados
        # ¡Muy importante! Antes tenían la latitud vieja corrupta en lat_num
        # (ej. 21894.0); aquí la sobreescribimos con la latitud ya reparada (-2.1894).
        if len(rescatados) > 0:
            lat_reparada = fn_reconstruir(rescatados["limpia_lat"])
            rescatados["lat_num"] = pd.to_numeric(lat_reparada, errors="coerce")

        # Los rescatados salen del pool
        # Equivale a: geo.corregir.1 <- geo.corregir.1 %>% filter(!(ID.temp %in% correctos3))
        # Así en la siguiente vuelta `pendientes` solo tiene los que siguen fallando.
        pendientes = pendientes[~pendientes["ID_temp"].isin(ids_rescatados)].copy()

        # Guardamos la tabla de rescatados de este escenario en la lista.
        resultados.append(rescatados)
        print(f"        {nombre}: {len(rescatados):,} rescatados "
              f"({len(pendientes):,} pendientes)")

    # Limpiar columna auxiliar de todos los DataFrames
    # enumerate(lista) → recorre la lista dándonos posición E ítem: (0, esc1), (1, esc2)...
    # Usamos `i` para sobreescribir `resultados[i]` sin la columna temporal "limpia_lat".
    for i, r in enumerate(resultados):
        if len(r) > 0 and "limpia_lat" in r.columns:
            resultados[i] = r.drop(columns=["limpia_lat"])

    if len(pendientes) > 0 and "limpia_lat" in pendientes.columns:
        pendientes = pendientes.drop(columns=["limpia_lat"])

    # sum(...) suma la cantidad de filas rescatadas en los 4 escenarios.
    n_total_rescatados = sum(len(r) for r in resultados)
    n_no_reparados = len(pendientes)  # Lo que quedó en `pendientes` tras los 4 intentos.

    print(f"        {'─' * 45}")
    print(f"        Total rescatados: {n_total_rescatados:,} de {n_total:,}")
    print(f"        No reparados: {n_no_reparados:,}")

    return (
        resultados[0],  # Escenario 1 (índice 0 de la lista)
        resultados[1],  # Escenario 2 (índice 1 de la lista)
        resultados[2],  # Escenario 3 (índice 2 de la lista)
        resultados[3],  # Escenario 4 (índice 3 de la lista)
        pendientes,     # No reparados (ej. coordenadas 0, 0 irrecuperables)
    )
