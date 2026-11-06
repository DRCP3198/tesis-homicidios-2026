"""
ensamblaje.py — Ensamblaje final de la base georreferenciada.

Corresponde a la Fase R 9 (líneas 460-484) del código original:
    listo.corrcion.casos.posibles <- rbind(geo.corregir.1a, ..., geo.corregir.1g)
    listo.corrcion.casos.posibles$lat.new <- as.numeric(lat.final)
    listo.corrcion.casos.posibles <- select(-any_of(c("limpia.lat", ...)))
    homi_Nueva <- rbind(geo_correctos, listo.corrcion.casos.posibles, limbo)
    homi_Nueva <- mutate(lat.new = as.numeric(lat.new), ...) %>%
        filter(!is.na(lat.new) & !is.na(lon.new))

Funciones principales:
    - ensamblar_base_final(): Concatena y limpia todos los conjuntos (Paso 4.7)
    - guardar_artefactos_geo(): Exporta Parquet en interim/ y processed/ (Paso 4.8)
    - imprimir_reporte_geo(): Reporte estadístico de efectividad (equivale R Fase 11)
"""
import pandas as pd

from src.ingesta.config import (
    INTERIM_GEO_CORRECTOS,  # data/interim/geo_correctos.parquet
    PROCESSED_DIR,          # data/processed/
)


# Columnas auxiliares creadas durante la validación geoespacial que deben
# eliminarse del DataFrame final para mantener el esquema limpio.
# Equivale a: select(-any_of(c("limpia.lat", "lat.1", "lat.leng", ...))) en R
_COLUMNAS_AUXILIARES: list[str] = [
    "latitud_original",   # Cadena original antes de conversión numérica
    "longitud_original",  # Cadena original antes de conversión numérica
    "limpia_lat",         # Cadena limpia usada en reconstrucción decimal
    "lat_1",              # Parte entera de la reconstrucción
    "lat_2",              # Parte decimal de la reconstrucción
    "lat_leng",           # Longitud de la cadena (auxiliar R)
    "lat_final",          # Cadena final reconstruida antes de casteo
    "geometry",           # Columna GeoDataFrame que ya no se necesita
    "index_right",        # Columna residual creada por gpd.sjoin()
    "CANTON_MAPA",        # Columna del mapa unida por sjoin — ya no necesaria
    "_coincide",          # Máscara booleana de la auditoría topológica
    "_PROV_NORM",         # Columna normalizada temporal de provincias
]


# =========================================================================
# PASO 4.7 — Ensamblaje y limpieza final
# =========================================================================
def ensamblar_base_final(
    geo_correctos: pd.DataFrame,
    reparados_esc1: pd.DataFrame,
    reparados_esc2: pd.DataFrame,
    reparados_esc3: pd.DataFrame,
    reparados_esc4: pd.DataFrame,
    limbo_formato_correcto: pd.DataFrame,
    no_reparados: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """
    Consolida todos los conjuntos de datos en la base georreferenciada final.

    Equivalencia R (líneas 466-484):
        listo.corrcion.casos.posibles <- rbind(geo.corregir.1a, geo.corregir.1b,
                                               geo.corregir.1f, geo.corregir.1g)
        listo.corrcion.casos.posibles$lat.new <- as.numeric(lat.final)
        listo.corrcion.casos.posibles <- select(-any_of(c(...)))
        homi_Nueva <- rbind(geo_correctos, listo.corrcion.casos.posibles,
                            limbo_formato_correcto)
        homi_Nueva <- mutate(lat.new = as.numeric(lat.new), ...) %>%
            filter(!is.na(lat.new) & !is.na(lon.new))

    Mapeo R → Python:
        rbind(a, b, c, ...)      →  pd.concat([a, b, c, ...], ignore_index=True)
        select(-any_of(cols))    →  df.drop(columns=cols, errors='ignore')
        filter(!is.na(lat/lon))  →  df.dropna(subset=['lat_num', 'lon_num'])

    Parameters
    ----------
    geo_correctos : pd.DataFrame
        Registros correctos de la primera auditoría topológica (Paso 4.4).
    reparados_esc1 : pd.DataFrame
        Registros reparados por escenario 1 — X.XXXXXX positivo (Paso 4.6).
    reparados_esc2 : pd.DataFrame
        Registros reparados por escenario 2 — 0.XXXXXX positivo (Paso 4.6).
    reparados_esc3 : pd.DataFrame
        Registros reparados por escenario 3 — -X.XXXXXX negativo (Paso 4.6).
    reparados_esc4 : pd.DataFrame
        Registros reparados por escenario 4 — -0.XXXXXX negativo (Paso 4.6).
    limbo_formato_correcto : pd.DataFrame
        Registros con punto decimal que cayeron fuera de cantón (Paso 4.5).
    no_reparados : pd.DataFrame or None
        Registros que ningún escenario pudo rescatar. Se excluyen del
        ensamblaje pero se reportan para auditoría.

    Returns
    -------
    pd.DataFrame
        Base consolidada y limpia con columnas 'lat_num' / 'lon_num' como
        coordenadas numéricas definitivas, lista para exportación.

    Raises
    ------
    ValueError
        Si todos los DataFrames de entrada están vacíos.
    """
    print("  [4.7] Ensamblaje y limpieza final")

    # ── Catalogar las partes con sus tamaños ──
    partes_etiquetadas = {
        "geo_correctos":          geo_correctos,
        "reparados_esc1":         reparados_esc1,
        "reparados_esc2":         reparados_esc2,
        "reparados_esc3":         reparados_esc3,
        "reparados_esc4":         reparados_esc4,
        "limbo_formato_correcto": limbo_formato_correcto,
    }

    for etiqueta, df_parte in partes_etiquetadas.items():
        print(f"        {etiqueta:<30}: {len(df_parte):>7,}")

    if no_reparados is not None:
        print(f"        {'no_reparados (excluidos)':<30}: {len(no_reparados):>7,}")

    # ── pd.concat() — equivale a rbind() de R ──
    # Filtramos DataFrames vacíos para evitar warnings en concat()
    partes_no_vacias = [
        df for df in partes_etiquetadas.values() if len(df) > 0
    ]

    if len(partes_no_vacias) == 0:
        raise ValueError(
            "Todos los DataFrames de entrada están vacíos. "
            "No hay registros para ensamblar."
        )

    # ignore_index=True reinicia el índice secuencialmente — equivale al
    # reindexado implícito que hace R al hacer rbind() sobre data.frames
    df_ensamblado = pd.concat(partes_no_vacias, ignore_index=True)
    print(f"        {'─' * 45}")
    print(f"        Total ensamblado (antes de limpieza): {len(df_ensamblado):,}")

    # ── Eliminar columnas auxiliares ──
    # Equivale a: select(-any_of(c("limpia.lat", "lat.1", "lat.leng", ...)))
    cols_presentes = [c for c in _COLUMNAS_AUXILIARES if c in df_ensamblado.columns]
    if cols_presentes:
        df_ensamblado = df_ensamblado.drop(columns=cols_presentes)

    # ── Forzar tipos numéricos en coordenadas ──
    # Equivale a: mutate(lat.new = as.numeric(lat.new), lon.new = as.numeric(lon.new))
    df_ensamblado["lat_num"] = pd.to_numeric(
        df_ensamblado["lat_num"], errors="coerce"
    )
    df_ensamblado["lon_num"] = pd.to_numeric(
        df_ensamblado["lon_num"], errors="coerce"
    )

    # ── Filtro de integridad final ──
    # Equivale a: filter(!is.na(lat.new) & !is.na(lon.new))
    n_antes = len(df_ensamblado)
    df_ensamblado = df_ensamblado.dropna(subset=["lat_num", "lon_num"])
    n_despues = len(df_ensamblado)
    n_eliminados_nan = n_antes - n_despues

    if n_eliminados_nan > 0:
        print(f"        Eliminados por NaN lat/lon: {n_eliminados_nan:,}")

    print(f"        REGISTROS GEORREFERENCIADOS FINALES: {n_despues:,}")

    return df_ensamblado


# =========================================================================
# PASO 4.8 — Exportación de artefactos geoespaciales
# =========================================================================
def guardar_artefactos_geo(
    geo_correctos: pd.DataFrame,
    df_final: pd.DataFrame,
) -> None:
    """
    Exporta los artefactos de la Fase 4 en formato Parquet.

    Genera:
      • data/interim/geo_correctos.parquet  — registros correctos iniciales
      • data/processed/homi_georreferenciado.parquet — base final consolidada

    Equivalencia R (líneas 498-504):
        st_write(homi_Nueva_espacial, "homi_Nueva.shp", delete_layer=TRUE)
        write.csv(homi_Nueva, "homi_Nueva_limpio7.csv", row.names=FALSE)
        saveRDS(homi_Nueva, file = "homi_2010_2024_2.rds")
    En Python usamos Parquet como formato binario moderno (reemplaza RDS).

    Parameters
    ----------
    geo_correctos : pd.DataFrame
        Registros correctos de la primera auditoría topológica.
    df_final : pd.DataFrame
        Base consolidada final post-ensamblaje y limpieza.
    """
    print("  [4.8] Exportación de artefactos geoespaciales")

    # ── geo_correctos.parquet (interim/) ──
    INTERIM_GEO_CORRECTOS.parent.mkdir(parents=True, exist_ok=True)
    geo_correctos.to_parquet(INTERIM_GEO_CORRECTOS, index=False, engine="pyarrow")
    tamanio_kb = INTERIM_GEO_CORRECTOS.stat().st_size / 1024
    print(f"        Guardado: {INTERIM_GEO_CORRECTOS}")
    print(f"        Tamaño: {tamanio_kb:.1f} KB | Registros: {len(geo_correctos):,}")

    # ── homi_georreferenciado.parquet (processed/) ──
    ruta_final = PROCESSED_DIR / "homi_georreferenciado.parquet"
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    df_final.to_parquet(ruta_final, index=False, engine="pyarrow")
    tamanio_kb = ruta_final.stat().st_size / 1024
    print(f"        Guardado: {ruta_final}")
    print(f"        Tamaño: {tamanio_kb:.1f} KB | Registros: {len(df_final):,}")


# =========================================================================
# REPORTE ESTADÍSTICO — equivale a R Fase 11 (líneas 510-519)
# =========================================================================
def imprimir_reporte_geo(
    n_procesados: int,
    n_correctos: int,
    n_reparados_total: int,
    n_limbo: int,
    n_no_reparados: int,
    n_final: int,
) -> None:
    """
    Imprime el reporte estadístico de efectividad de la Fase 4.

    Equivalencia R (líneas 510-519):
        print(paste("-> Homicidios procesados:", nrow(homi_2010_2024)))
        print(paste("-> Total rescatados perfectos:", nrow(geo_correctos)))
        print(paste("-> Total rescatados por algoritmo:", nrow(reparados)))
        print(paste("TOTAL DE REGISTROS GEORREFERENCIADOS:", nrow(homi_Nueva)))
        print(paste("Efectividad total:", round(...*100, 2), "%"))

    Parameters
    ----------
    n_procesados : int
        Total de registros que entraron al pipeline de la Fase 4.
    n_correctos : int
        Registros que pasaron la primera auditoría sin corrección.
    n_reparados_total : int
        Total de registros reparados por los 4 escenarios del algoritmo.
    n_limbo : int
        Registros en limbo con formato correcto (punto decimal pero fuera).
    n_no_reparados : int
        Registros que ningún escenario pudo rescatar (excluidos).
    n_final : int
        Total de registros en la base georreferenciada final.
    """
    efectividad = (n_final / n_procesados * 100) if n_procesados > 0 else 0.0

    print("=" * 60)
    print("  REPORTE DE VERIFICACIÓN — FASE 4: VALIDACIÓN GEOESPACIAL")
    print("=" * 60)
    print(f"  {'Homicidios procesados (entrada):':<42} {n_procesados:>7,}")
    print(f"  {'Rescatados perfectos (1ra auditoría):':<42} {n_correctos:>7,}")
    print(f"  {'Rescatados por algoritmo (4 escenarios):':<42} {n_reparados_total:>7,}")
    print(f"  {'Limbo con coordenadas retenidos:':<42} {n_limbo:>7,}")
    print(f"  {'No reparados (excluidos):':<42} {n_no_reparados:>7,}")
    print(f"  {'─' * 52}")
    print(f"  {'TOTAL GEORREFERENCIADOS:':<42} {n_final:>7,}")
    print(f"  Efectividad total del pipeline: {efectividad:.2f}%")
    print("=" * 60)

