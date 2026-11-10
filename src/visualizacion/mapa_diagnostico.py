r"""
mapa_diagnostico.py — Generación del mapa diagnóstico de validación continental (Paso 5.6).

Corresponde a la Fase R 12 (líneas 522-557) del script original:
    Mapa_Provincias <- Mapa_Completo %>%
      filter(DPA_DESPRO != "GALAPAGOS") %>%
      group_by(DPA_DESPRO) %>%
      summarize(.groups = "drop")

    ggplot() +
      geom_sf(data = Mapa_Provincias, fill = "gray96", color = "black", size = 0.4) +
      geom_jitter(data = test_mapa, aes(geometry = geometry),
                  stat = "sf_coordinates", alpha = 0.4, color = "darkred", size = 0.8) +
      theme_minimal() +
      labs(title = "Distribución Geográfica de Homicidios en Ecuador", ...)

Objetivo en Python (Paso 5.6):
    Generar de forma 100% desatendida (sin abrir ventanas emergentes que bloqueen la
    consola) una figura cartográfica en alta resolución (`dpi=300`) lista para tesis:
      • Capa base cantonal: polígonos continentales en gris neutro claro (`#E0E0E0`)
        con bordes internos blancos delgados (`edgecolor="white"`).
      • Capa de referencia provincial: contornos provinciales disueltos (`dissolve`)
        en gris grafito suave para facilitar la lectura territorial.
      • Capa de eventos: puntos georreferenciados en rojo carmesí con transparencia
        controlada (`alpha`), tamaño fino (`markersize`) y micro-desplazamiento
        determinista (`jitter` con semilla fija) para evitar la superposición ciega
        de eventos ocurridos en una misma esquina o centroide barrial.
      • Salida física: `reports/figuras/mapa_diagnostico_continental.png` a `300 DPI`.

En palabras simples:
    Es la "prueba visual" de que las Fases 4 y 5 funcionaron bien: si alguna coordenada
    hubiera quedado corrupta o invertida, veríamos puntos flotando en el Océano Pacífico
    o en otro continente. Al ver la nube de puntos rojos ajustada con precisión sobre
    el territorio continental del Ecuador, validamos visualmente la calidad espacial.
"""
# `from pathlib import Path` maneja rutas de archivos en cualquier sistema operativo.
from pathlib import Path

# Configuramos el motor gráfico "Agg" (Anti-Grain Geometry) ANTES de importar `pyplot`.
# ¿Por qué es fundamental esto?
#   Por defecto, Matplotlib intenta abrir una ventana interactiva en pantalla (TkAgg/QtAgg),
#   lo cual puede bloquear scripts automatizados o fallar en servidores sin monitor.
#   `"Agg"` dibuja directamente en memoria y guarda el archivo PNG sin abrir ventanas.
import matplotlib

matplotlib.use("Agg")

import geopandas as gpd  # noqa: E402 — importado después de fijar el backend Agg.
from matplotlib.lines import Line2D  # noqa: E402 — para crear el ícono de punto/línea en la leyenda.
from matplotlib.patches import Patch  # noqa: E402 — para crear el rectángulo gris en la leyenda.
import matplotlib.pyplot as plt  # noqa: E402 — interfaz de dibujo científico tipo MATLAB/ggplot.
import numpy as np  # noqa: E402 — generador numérico vectorizado para el micro-jitter reproducible.
import pandas as pd  # noqa: E402

from src.ingesta.config import (
    CRS_OBJETIVO,                # EPSG:4326 (WGS84).
    PROCESSED_GEORREFERENCIADO,  # Respaldo de entrada si aún no se corrió el Paso 5.3.
    SALIDA_MAPA_DIAGNOSTICO,     # Ruta destino: reports/figuras/mapa_diagnostico_continental.png.
    SALIDA_PARQUET_FINAL,        # Entrada preferida: data/processed/homi_final.parquet.
)
from src.validacion_geo.cartografia import cargar_mapa_cantonal


# =========================================================================
# FUNCIÓN AUXILIAR 1 — Disolución de cantones a límites provinciales
# =========================================================================
def disolver_limites_provinciales(mapa_cantones: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    r"""
    Fusiona los polígonos cantonales por provincia para obtener los bordes provinciales.

    Equivalencia R (Fase 12, líneas 532-535):
        Mapa_Provincias <- Mapa_Completo %>%
          filter(DPA_DESPRO != "GALAPAGOS") %>%
          group_by(DPA_DESPRO) %>%
          summarize(.groups = "drop")

    Mapeo R → Python:
        group_by(DPA_DESPRO) %>% summarize()  →  mapa.dissolve(by="DPA_DESPRO", as_index=False)

    Parameters
    ----------
    mapa_cantones : gpd.GeoDataFrame
        Capa cartográfica cantonal continental ya homologada en `EPSG:4326`.

    Returns
    -------
    gpd.GeoDataFrame
        Capa con un polígono/multipolígono unificado por cada provincia continental.
    """
    # Si el mapa trae la columna oficial de provincia `DPA_DESPRO`, fusionamos por ella;
    # si no existiera (ej. un mapa sintético minimalista en un test unitario), devolvemos copia.
    if "DPA_DESPRO" not in mapa_cantones.columns:
        return mapa_cantones.copy()

    # `.dissolve(by=...)` une geométricamente todos los cantones de la misma provincia,
    # borrando las fronteras internas entre cantones y dejando solo el contorno provincial.
    return mapa_cantones.dissolve(by="DPA_DESPRO", as_index=False)


# =========================================================================
# FUNCIÓN AUXILIAR 2 — Construcción de puntos de eventos con micro-jitter
# =========================================================================
def _preparar_eventos_para_ploteo(
    eventos: pd.DataFrame | gpd.GeoDataFrame,
    jitter_grados: float = 0.0035,
    semilla: int = 42,
    crs_epsg: int = CRS_OBJETIVO,
) -> gpd.GeoDataFrame:
    """
    Prepara un `GeoDataFrame` temporal de eventos aplicando un micro-jitter reproducible.

    ¿Qué hace `jitter_grados = 0.0035`?
        Equivale al `geom_jitter()` del script R (línea 548). En el ecuador terrestre,
        `0.0035°` son ~380 metros: a escala nacional es imperceptible al ojo humano,
        pero evita que decenas de crímenes registrados en el mismo punto exacto se tapen
        unos a otros, permitiendo apreciar la densidad real en ciudades como Guayaquil o Quito.
        IMPORTANTE: se aplica sobre copias temporales; los datos exportados NO se alteran.
    """
    if len(eventos) == 0:
        raise ValueError("No hay eventos georreferenciados para graficar (0 filas).")

    # Extraemos vectores numéricos X (longitud) e Y (latitud) según el tipo de entrada.
    if isinstance(eventos, gpd.GeoDataFrame) and eventos.geometry is not None:
        gdf_temp = eventos.to_crs(epsg=crs_epsg) if eventos.crs else eventos.set_crs(epsg=crs_epsg)
        lon = gdf_temp.geometry.x.to_numpy(dtype="float64", copy=True)
        lat = gdf_temp.geometry.y.to_numpy(dtype="float64", copy=True)
    else:
        # Soportamos tanto nombres finales (`longitud`/`latitud`) como de Fase 4 (`lon_num`/`lat_num`).
        col_lon = "longitud" if "longitud" in eventos.columns else "lon_num"
        col_lat = "latitud" if "latitud" in eventos.columns else "lat_num"
        if col_lon not in eventos.columns or col_lat not in eventos.columns:
            raise KeyError(
                "El DataFrame de eventos debe contener ('latitud', 'longitud') o ('lat_num', 'lon_num')."
            )
        lon = pd.to_numeric(eventos[col_lon], errors="coerce").to_numpy(dtype="float64")
        lat = pd.to_numeric(eventos[col_lat], errors="coerce").to_numpy(dtype="float64")

    # Filtramos cualquier par inválido antes de construir geometrías.
    mascara_valida = ~(np.isnan(lon) | np.isnan(lat))
    lon = lon[mascara_valida]
    lat = lat[mascara_valida]

    if len(lon) == 0:
        raise ValueError("Todas las coordenadas de eventos son NaN; no se puede generar el mapa.")

    # Si `jitter_grados > 0`, sumamos un desplazamiento uniforme en [-jitter, +jitter].
    # `np.random.default_rng(semilla)` usa una semilla fija (42) para que cada vez que
    # corras el script obtengas EXACTAMENTE la misma imagen pixel por pixel (reproducibilidad).
    if jitter_grados > 0:
        generador = np.random.default_rng(semilla)
        lon = lon + generador.uniform(-jitter_grados, jitter_grados, size=len(lon))
        lat = lat + generador.uniform(-jitter_grados, jitter_grados, size=len(lat))

    return gpd.GeoDataFrame(
        geometry=gpd.points_from_xy(lon, lat),
        crs=f"EPSG:{crs_epsg}",
    )


# =========================================================================
# PASO 5.6 — Mapa diagnóstico de validación con calidad de publicación
# =========================================================================
def generar_mapa_diagnostico(
    eventos: pd.DataFrame | gpd.GeoDataFrame,
    mapa_cantones: gpd.GeoDataFrame,
    ruta_salida: Path = SALIDA_MAPA_DIAGNOSTICO,
    dpi: int = 300,
    color_base: str = "#E0E0E0",
    color_borde_canton: str = "white",
    color_borde_provincia: str = "#616161",
    color_eventos: str = "#C62828",
    alpha_eventos: float = 0.25,
    markersize_eventos: float = 1.6,
    jitter_grados: float = 0.0035,
) -> Path:
    r"""
    Construye y exporta el mapa diagnóstico de homicidios sobre Ecuador continental.

    Especificación visual (Paso 5.6):
      • Capa 1 (Base cantonal): polígonos en gris neutro claro (`#E0E0E0`) con bordes
        blancos delgados (`edgecolor="white"`).
      • Capa 2 (Referencia provincial): contornos provinciales disueltos en gris grafito
        delgado (`#616161`) para dar jerarquía cartográfica.
      • Capa 3 (Eventos): puntos en rojo carmesí (`#C62828`) con transparencia (`alpha=0.25`),
        tamaño controlado (`markersize=1.6`) y micro-jitter determinista anti-solapamiento.
      • Acabado editorial: grilla de coordenadas tenue, título formal, subtítulo con conteo
        muestral `n`, leyenda explícita y exportación a `dpi=300`.

    Parameters
    ----------
    eventos : pd.DataFrame or gpd.GeoDataFrame
        Registros finales georreferenciados (DataFrame con `latitud`/`longitud` o GeoDataFrame).
    mapa_cantones : gpd.GeoDataFrame
        Cartografía cantonal continental homologada en `EPSG:4326`.
    ruta_salida : Path, optional
        Ruta donde se guardará el PNG (`reports/figuras/mapa_diagnostico_continental.png`).
    dpi : int, optional
        Resolución en puntos por pulgada para impresión académica (por defecto `300`).
    color_base : str, optional
        Color hexadecimal de relleno para los polígonos base (`"#E0E0E0"`).
    color_borde_canton : str, optional
        Color de los límites cantonales internos (`"white"`).
    color_borde_provincia : str, optional
        Color de los límites provinciales externos (`"#616161"`).
    color_eventos : str, optional
        Color de los puntos de homicidios (`"#C62828"`).
    alpha_eventos : float, optional
        Opacidad de cada punto entre 0 y 1 (`0.25` permite percibir densidad por acumulación).
    markersize_eventos : float, optional
        Tamaño de cada marcador puntual (`1.6`).
    jitter_grados : float, optional
        Amplitud del micro-desplazamiento visual en grados decimales (`0.0035`).

    Returns
    -------
    Path
        Ruta absoluta de la figura PNG generada.
    """
    print(f"  [5.6] Generando mapa diagnóstico continental ({dpi} DPI)")

    if len(mapa_cantones) == 0:
        raise ValueError("El GeoDataFrame `mapa_cantones` está vacío; no hay capa base.")

    ruta_salida = Path(ruta_salida)
    ruta_salida.parent.mkdir(parents=True, exist_ok=True)

    # Homologamos el CRS del mapa base a EPSG:4326 por seguridad.
    mapa_base = (
        mapa_cantones.to_crs(epsg=CRS_OBJETIVO)
        if mapa_cantones.crs and mapa_cantones.crs.to_epsg() != CRS_OBJETIVO
        else mapa_cantones.copy()
    )

    # Preparamos los contornos provinciales y la capa puntual de eventos.
    mapa_provincias = disolver_limites_provinciales(mapa_base)
    gdf_eventos = _preparar_eventos_para_ploteo(
        eventos,
        jitter_grados=jitter_grados,
    )
    n_eventos = len(gdf_eventos)

    # ── Inicializar lienzo Matplotlib de proporción vertical acorde al Ecuador continental ──
    # `figsize=(9.5, 10.5)` en pulgadas × `300 DPI` produce una imagen nítida de ~2850 × 3150 px.
    fig, ax = plt.subplots(figsize=(9.5, 10.5), dpi=dpi)
    fig.patch.set_facecolor("white")     # Fondo exterior blanco puro (estilo documento académico).
    ax.set_facecolor("#F8FAFC")          # Fondo sutilísimo del recuadro geográfico.

    # ── Grilla de referencia geográfica (al fondo, zorder=0) ──
    ax.grid(
        True,
        linestyle="--",
        linewidth=0.45,
        color="#CBD5E1",
        alpha=0.75,
        zorder=0,
    )
    ax.set_axisbelow(True)

    # ── CAPA 1: Polígonos cantonales en gris neutro claro con bordes blancos (zorder=1) ──
    mapa_base.plot(
        ax=ax,
        color=color_base,
        edgecolor=color_borde_canton,
        linewidth=0.35,
        zorder=1,
    )

    # ── CAPA 2: Límites provinciales disueltos para jerarquía territorial (zorder=2) ──
    # `.boundary` dibuja únicamente las líneas del borde sin tapar el relleno cantonal inferior.
    mapa_provincias.boundary.plot(
        ax=ax,
        color=color_borde_provincia,
        linewidth=0.70,
        zorder=2,
    )

    # ── CAPA 3: Eventos georreferenciados en rojo con transparencia controlada (zorder=3) ──
    # `linewidth=0` quita el reborde de cada punto individual para evitar "empastamiento" visual.
    gdf_eventos.plot(
        ax=ax,
        color=color_eventos,
        alpha=alpha_eventos,
        markersize=markersize_eventos,
        marker="o",
        linewidth=0,
        zorder=3,
    )

    # ── Encuadre geográfico ajustado al territorio continental con margen estético ──
    minx, miny, maxx, maxy = mapa_base.total_bounds
    margen_x = (maxx - minx) * 0.04
    margen_y = (maxy - miny) * 0.04
    ax.set_xlim(minx - margen_x, maxx + margen_x)
    ax.set_ylim(miny - margen_y, maxy + margen_y)

    # ── Títulos formales y etiquetas de ejes ──
    ax.set_title(
        "Distribución Geográfica de Homicidios Intencionales\nEcuador Continental (2010–2024)",
        fontsize=13.5,
        fontweight="bold",
        color="#1E293B",
        pad=22,
    )
    # Subtítulo técnico ubicado justo debajo del título principal en coordenadas del eje (0..1).
    ax.text(
        0.5,
        1.012,
        f"Validación topológica punto-en-polígono | n = {n_eventos:,} registros georreferenciados (WGS84 / EPSG:4326)",
        transform=ax.transAxes,
        ha="center",
        va="bottom",
        fontsize=9.2,
        color="#475569",
    )

    ax.set_xlabel("Longitud (°)", fontsize=10, color="#334155", labelpad=8)
    ax.set_ylabel("Latitud (°)", fontsize=10, color="#334155", labelpad=8)
    ax.tick_params(axis="both", labelsize=8.5, colors="#475569")

    # Estilizado sobrio del marco exterior (spines).
    for spine in ax.spines.values():
        spine.set_edgecolor("#CBD5E1")
        spine.set_linewidth(0.8)

    # ── Leyenda cartográfica explícita ──
    # Construimos los símbolos de la leyenda manualmente para que el punto rojo de muestra
    # sea perfectamente visible en la caja de leyenda aunque en el mapa tenga `alpha=0.25`.
    elementos_leyenda = [
        Patch(
            facecolor=color_base,
            edgecolor=color_borde_canton,
            linewidth=0.8,
            label="Polígonos cantonales (INEC)",
        ),
        Line2D(
            [0],
            [0],
            color=color_borde_provincia,
            linewidth=1.1,
            label="Límites provinciales unificados",
        ),
        Line2D(
            [0],
            [0],
            marker="o",
            color="none",
            markerfacecolor=color_eventos,
            markeredgecolor="none",
            markersize=6.0,
            alpha=0.85,
            label=f"Homicidios validados (n = {n_eventos:,})",
        ),
    ]
    leyenda = ax.legend(
        handles=elementos_leyenda,
        loc="lower right",  # Esquina sureste (zona exterior amazónica libre de solapamiento).
        frameon=True,
        facecolor="white",
        edgecolor="#CBD5E1",
        framealpha=0.95,
        fontsize=8.8,
        title="Simbología",
        title_fontsize=9.2,
        borderpad=0.7,
    )
    leyenda.get_title().set_fontweight("bold")

    # Pie de nota metodológica discreto en el margen inferior de la figura.
    fig.text(
        0.5,
        0.01,
        "Fuente: Pipeline de Preprocesamiento Espacial Migrado R → Python | "
        "Nota: micro-jitter visual (±0.0035°) aplicado solo para representación de densidad.",
        ha="center",
        fontsize=7.6,
        color="#64748B",
        style="italic",
    )

    # ── Guardado físico en alta resolución y liberación inmediata de memoria RAM ──
    fig.savefig(
        ruta_salida,
        dpi=dpi,
        bbox_inches="tight",
        facecolor="white",
    )
    # `plt.close(fig)` cierra el lienzo en memoria; es indispensable en ejecución desatendida
    # y durante suites de pruebas (`pytest`) para no acumular figuras abiertas en RAM.
    plt.close(fig)

    tamanio_kb = ruta_salida.stat().st_size / 1024
    print(f"        Mapa guardado: {ruta_salida} ({tamanio_kb:.1f} KB | {dpi} DPI)")
    return ruta_salida


# =========================================================================
# EJECUCIÓN AUTÓNOMA DESDE ARTEFACTOS PROCESADOS
# =========================================================================
def ejecutar_visualizacion_autonoma() -> Path:
    """
    Carga el dataset procesado y el shapefile cantonal y genera el mapa diagnóstico.

    Uso directo desde terminal:
        python -m src.visualizacion.mapa_diagnostico
    """
    ruta_datos = (
        SALIDA_PARQUET_FINAL
        if SALIDA_PARQUET_FINAL.exists()
        else PROCESSED_GEORREFERENCIADO
    )
    if not ruta_datos.exists():
        raise FileNotFoundError(
            f"No se encontró dataset georreferenciado en '{ruta_datos}'. "
            "Ejecute primero hasta la Fase 4 o 5."
        )

    df_eventos = pd.read_parquet(ruta_datos)
    mapa = cargar_mapa_cantonal()
    return generar_mapa_diagnostico(df_eventos, mapa)


if __name__ == "__main__":
    ejecutar_visualizacion_autonoma()

