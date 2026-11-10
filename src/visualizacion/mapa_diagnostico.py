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
    Generar de forma 100% desatendida (sin abrir ventanas interactivas que bloqueen la
    ejecución automatizada) una figura cartográfica en alta resolución (`dpi=300`) lista para tesis:
      • Capa base cantonal: polígonos continentales en gris neutro claro (`#E0E0E0`)
        con bordes internos blancos delgados (`edgecolor="white"`).
      • Capa de referencia provincial: contornos provinciales disueltos (`dissolve`)
        en gris grafito (`#616161`) para facilitar la lectura territorial.
      • Capa de eventos: puntos georreferenciados en rojo carmesí con transparencia
        controlada (`alpha`), tamaño fino (`markersize`) y micro-desplazamiento
        determinista (`jitter` con semilla fija) para mitigar el solapamiento visual (*overplotting*)
        de eventos ocurridos en una misma intersección vial o centroide urbano.
      • Salida física: `reports/figuras/mapa_diagnostico_continental.png` a `300 DPI`.

En palabras simples:
    Es la verificación visual final del pipeline espacial. Si hubiera quedado alguna
    coordenada invertida o con el punto decimal mal ubicado, aparecerían puntos fuera
    del continente o sobre el océano. Comprobar visualmente que los 38,565 eventos se
    ajustan a la silueta cantonal y provincial del Ecuador confirma la validez de la Fase 4.
"""
from pathlib import Path

# ── Configuración de renderizado sin interfaz gráfica (Headless Backend) ──
# `matplotlib.use("Agg")` selecciona el motor de rasterización en C++ "Anti-Grain Geometry"
# ANTES de importar `matplotlib.pyplot`.
# ¿Por qué debe ejecutarse antes de `import matplotlib.pyplot as plt`?
#   Al importar `pyplot`, Matplotlib intenta conectarse al servidor de ventanas del sistema
#   operativo (`TkAgg` o `QtAgg`). En ejecuciones automatizadas, pruebas con `pytest` o
#   terminales remotas, abrir ventanas gráficas puede congelar el proceso esperando clic del usuario.
#   Con `"Agg"`, todo el dibujo ocurre en un búfer de memoria RAM y se exporta directo a `.png`.
import matplotlib

matplotlib.use("Agg")

# Nota sobre el comentario `# noqa: E402`:
#   Los analizadores de estilo (linters como `ruff` o `flake8`) avisan con el código `E402`
#   cuando un `import` aparece después de una instrucción ejecutable (`matplotlib.use("Agg")`).
#   `# noqa: E402` documenta que este orden es intencional y técnicamente obligatorio aquí.
import geopandas as gpd  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402 — primitiva gráfica para símbolos de línea/punto en la leyenda.
from matplotlib.patches import Patch  # noqa: E402 — primitiva gráfica para polígonos de muestra en la leyenda.
import matplotlib.pyplot as plt  # noqa: E402 — interfaz de creación de figuras (`Figure`) y ejes (`Axes`).
import numpy as np  # noqa: E402 — operaciones vectorizadas sobre arreglos numéricos contiguos (`ndarray`).
import pandas as pd  # noqa: E402

from src.ingesta.config import (
    CRS_OBJETIVO,                # Código entero `4326` (WGS84).
    PROCESSED_GEORREFERENCIADO,  # Respaldo de entrada si se invoca antes del Paso 5.3.
    SALIDA_MAPA_DIAGNOSTICO,     # Ruta destino: `reports/figuras/mapa_diagnostico_continental.png`.
    SALIDA_PARQUET_FINAL,        # Entrada principal: `data/processed/homi_final.parquet`.
)
from src.validacion_geo.cartografia import cargar_mapa_cantonal


# =========================================================================
# FUNCIÓN AUXILIAR 1 — Disolución topológica de cantones a provincias
# =========================================================================
def disolver_limites_provinciales(mapa_cantones: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    r"""
    Fusiona geométricamente los polígonos cantonales por provincia (`unary_union` por grupo).

    Equivalencia R (Fase 12, líneas 532-535):
        Mapa_Provincias <- Mapa_Completo %>%
          filter(DPA_DESPRO != "GALAPAGOS") %>%
          group_by(DPA_DESPRO) %>%
          summarize(.groups = "drop")

    Mapeo R → Python:
        group_by(DPA_DESPRO) %>% summarize()  →  mapa.dissolve(by="DPA_DESPRO", as_index=False)

    ¿Qué hace `dissolve` a nivel geométrico?
        Agrupa todas las filas que comparten el mismo valor en `DPA_DESPRO` (ej. todos los
        cantones de `"GUAYAS"`) y calcula su unión espacial (`shapely.unary_union`), eliminando
        las aristas internas compartidas entre cantones vecinos y conservando únicamente el
        perímetro exterior de cada provincia.

    Parameters
    ----------
    mapa_cantones : gpd.GeoDataFrame
        Capa cartográfica cantonal continental en `EPSG:4326`.

    Returns
    -------
    gpd.GeoDataFrame
        Capa con una fila geométrica unificada por cada provincia continental.
    """
    # Validación defensiva: si se pasa un mapa sintético de prueba sin columna `DPA_DESPRO`,
    # devolvemos una copia intacta en lugar de interrumpir con `KeyError`.
    if "DPA_DESPRO" not in mapa_cantones.columns:
        return mapa_cantones.copy()

    # `as_index=False` mantiene `DPA_DESPRO` como columna normal de la tabla en vez de
    # convertirla en el índice del GeoDataFrame (equivalente a `.groups = "drop"` en `dplyr`).
    return mapa_cantones.dissolve(by="DPA_DESPRO", as_index=False)


# =========================================================================
# FUNCIÓN AUXILIAR 2 — Preparación de puntos de eventos con micro-jitter
# =========================================================================
def _preparar_eventos_para_ploteo(
    eventos: pd.DataFrame | gpd.GeoDataFrame,
    jitter_grados: float = 0.0035,
    semilla: int = 42,
    crs_epsg: int = CRS_OBJETIVO,
) -> gpd.GeoDataFrame:
    """
    Construye un `GeoDataFrame` temporal de eventos aplicando un micro-jitter reproducible.

    Fundamento técnico del parámetro `jitter_grados = 0.0035`:
        Equivale a `geom_jitter(..., stat = "sf_coordinates")` del script R (línea 548).
        En la latitud ecuatorial, `1°` equivale a ~111.32 km, por lo que `0.0035°` representa
        ~390 metros: imperceptible a escala nacional (1:4,000,000), pero suficiente para
        desacoplar visualmente decenas de registros con coordenadas idénticas y revelar
        gradientes reales de concentración espacial mediante transparencia (`alpha`).
        GARANTÍA DE INMUTABILIDAD: opera sobre arreglos NumPy nuevos (`copy=True`); las
        coordenadas del dataset original NUNCA se modifican.
    """
    if len(eventos) == 0:
        raise ValueError("No hay eventos georreferenciados para graficar (0 filas).")

    # Caso A: `eventos` ya entra como un `GeoDataFrame` con columna `geometry` activa.
    if isinstance(eventos, gpd.GeoDataFrame) and eventos.geometry is not None:
        gdf_temp = eventos.to_crs(epsg=crs_epsg) if eventos.crs else eventos.set_crs(epsg=crs_epsg)
        # `.geometry.x` extrae todas las longitudes; `.to_numpy(dtype="float64", copy=True)`
        # crea un arreglo contiguo en C independiente de la tabla original.
        lon = gdf_temp.geometry.x.to_numpy(dtype="float64", copy=True)
        lat = gdf_temp.geometry.y.to_numpy(dtype="float64", copy=True)
    else:
        # Caso B: `eventos` entra como `pd.DataFrame` tabular (acepta tanto nombres finales
        # `longitud`/`latitud` como nombres intermedios de Fase 4 `lon_num`/`lat_num`).
        col_lon = "longitud" if "longitud" in eventos.columns else "lon_num"
        col_lat = "latitud" if "latitud" in eventos.columns else "lat_num"
        if col_lon not in eventos.columns or col_lat not in eventos.columns:
            raise KeyError(
                "El DataFrame de eventos debe contener ('latitud', 'longitud') o ('lat_num', 'lon_num')."
            )
        lon = pd.to_numeric(eventos[col_lon], errors="coerce").to_numpy(dtype="float64", copy=True)
        lat = pd.to_numeric(eventos[col_lat], errors="coerce").to_numpy(dtype="float64", copy=True)

    # Filtrado vectorizado en NumPy de posibles valores `NaN`:
    #   • `np.isnan(lon) | np.isnan(lat)`: `True` donde falte longitud O (`|`) falte latitud.
    #   • `~(...)`: niega la máscara para quedarnos únicamente con pares `(lon, lat)` completos.
    mascara_valida = ~(np.isnan(lon) | np.isnan(lat))
    lon = lon[mascara_valida]
    lat = lat[mascara_valida]

    if len(lon) == 0:
        raise ValueError("Todas las coordenadas de eventos son NaN; no se puede generar el mapa.")

    # Aplicación de ruido uniforme acotado y reproducible:
    #   • `np.random.default_rng(semilla)` instancia el generador pseudoaleatorio moderno PCG64
    #     de NumPy inicializado con `semilla=42` (produce exactamente la misma secuencia en cada corrida).
    #   • `generador.uniform(-a, +a, size=N)` genera `N` desplazamientos independientes en `[-a, +a]`.
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

    Arquitectura de capas superpuestas (controladas mediante `zorder` ascendente):
      • `zorder=0` — Grilla cartográfica de paralelos y meridianos en trazo discontinuo tenue.
      • `zorder=1` — Capa base cantonal: 216 cantones en gris neutro claro (`#E0E0E0`) con
                     límites internos blancos (`edgecolor="white"`).
      • `zorder=2` — Contornos provinciales disueltos (`#616161`) para jerarquía administrativa.
      • `zorder=3` — Nube puntual de homicidios (`#C62828`, `alpha=0.25`, `markersize=1.6`).

    Parameters
    ----------
    eventos : pd.DataFrame or gpd.GeoDataFrame
        Registros finales georreferenciados.
    mapa_cantones : gpd.GeoDataFrame
        Cartografía cantonal continental homologada en `EPSG:4326`.
    ruta_salida : Path, optional
        Ruta donde se escribirá el archivo PNG (`reports/figuras/mapa_diagnostico_continental.png`).
    dpi : int, optional
        Puntos por pulgada (*Dots Per Inch*); `300` es el estándar editorial para tesis impresas.
    color_base : str, optional
        Color hexadecimal de relleno de los polígonos cantonales (`"#E0E0E0"`).
    color_borde_canton : str, optional
        Color de las divisiones cantonales (`"white"`).
    color_borde_provincia : str, optional
        Color de los bordes provinciales unificados (`"#616161"`).
    color_eventos : str, optional
        Color de los eventos puntuales (`"#C62828"`).
    alpha_eventos : float, optional
        Opacidad en `[0.0, 1.0]` (`0.25` evita saturación y visibiliza densidad espacial).
    markersize_eventos : float, optional
        Área en puntos tipográficos de cada marcador (`1.6`).
    jitter_grados : float, optional
        Semiamplitud del micro-desplazamiento visual en grados (`0.0035`).

    Returns
    -------
    Path
        Ruta del archivo PNG exportado.
    """
    print(f"  [5.6] Generando mapa diagnóstico continental ({dpi} DPI)")

    if len(mapa_cantones) == 0:
        raise ValueError("El GeoDataFrame `mapa_cantones` está vacío; no hay capa base.")

    ruta_salida = Path(ruta_salida)
    ruta_salida.parent.mkdir(parents=True, exist_ok=True)

    # Garantizamos que la cartografía base esté proyectada en WGS84 (`EPSG:4326`).
    mapa_base = (
        mapa_cantones.to_crs(epsg=CRS_OBJETIVO)
        if mapa_cantones.crs and mapa_cantones.crs.to_epsg() != CRS_OBJETIVO
        else mapa_cantones.copy()
    )

    # Derivamos la capa de contornos provinciales y la capa puntual de eventos.
    mapa_provincias = disolver_limites_provinciales(mapa_base)
    gdf_eventos = _preparar_eventos_para_ploteo(
        eventos,
        jitter_grados=jitter_grados,
    )
    n_eventos = len(gdf_eventos)

    # ── 1. Creación orientada a objetos de Figura (`fig`) y Ejes (`ax`) ──
    # `plt.subplots(figsize=(ancho, alto), dpi=...)` devuelve una tupla de dos objetos:
    #   • `fig` (`Figure`): el lienzo exterior completo (márgenes, fondo general, pie de página).
    #   • `ax`  (`Axes`):   el recuadro cartesiano donde GeoPandas dibuja las capas espaciales.
    # A `300 DPI`, `figsize=(9.5, 10.5)` genera un mapa de alta definición (~2850 × 3150 píxeles).
    fig, ax = plt.subplots(figsize=(9.5, 10.5), dpi=dpi)
    fig.patch.set_facecolor("white")   # Color blanco puro en el margen exterior del documento.
    ax.set_facecolor("#F8FAFC")        # Gris azulado ultra claro para el fondo exterior al mapa.

    # ── 2. Grilla de referencia geográfica (`zorder=0`: nivel más profundo) ──
    ax.grid(
        True,
        linestyle="--",    # Línea segmentada suave.
        linewidth=0.45,    # Grosor fino para no competir visualmente con los polígonos.
        color="#CBD5E1",
        alpha=0.75,
        zorder=0,
    )
    # `set_axisbelow(True)` asegura que las líneas de la grilla nunca se dibujen encima del mapa.
    ax.set_axisbelow(True)

    # ── 3. CAPA 1: Polígonos cantonales (`zorder=1`) ──
    mapa_base.plot(
        ax=ax,                        # Dibuja sobre nuestro sistema de ejes `ax`.
        color=color_base,             # Relleno gris claro neutro `#E0E0E0`.
        edgecolor=color_borde_canton, # Bordes internos blancos delgados.
        linewidth=0.35,
        zorder=1,
    )

    # ── 4. CAPA 2: Límites provinciales disueltos (`zorder=2`) ──
    # `.boundary` extrae únicamente los anillos lineales (`LineString`/`MultiLineString`) de cada
    # provincia sin relleno interior, para no tapar las divisiones cantonales blancas de la Capa 1.
    mapa_provincias.boundary.plot(
        ax=ax,
        color=color_borde_provincia,
        linewidth=0.70,
        zorder=2,
    )

    # ── 5. CAPA 3: Eventos georreferenciados (`zorder=3`, capa superior) ──
    # `linewidth=0` desactiva el trazo perimetral de cada círculo individual para que la
    # superposición de miles de puntos con `alpha=0.25` produzca una transición limpia de densidad.
    gdf_eventos.plot(
        ax=ax,
        color=color_eventos,
        alpha=alpha_eventos,
        markersize=markersize_eventos,
        marker="o",
        linewidth=0,
        zorder=3,
    )

    # ── 6. Encuadre espacial basado en la caja envolvente (`total_bounds`) ──
    # `.total_bounds` devuelve un arreglo de 4 números `[min_lon, min_lat, max_lon, max_lat]`
    # con las coordenadas extremas del Ecuador continental. Añadimos un 4% de aire perimetral.
    minx, miny, maxx, maxy = mapa_base.total_bounds
    margen_x = (maxx - minx) * 0.04
    margen_y = (maxy - miny) * 0.04
    ax.set_xlim(minx - margen_x, maxx + margen_x)
    ax.set_ylim(miny - margen_y, maxy + margen_y)

    # ── 7. Jerarquía tipográfica: título, subtítulo técnico y ejes ──
    ax.set_title(
        "Distribución Geográfica de Homicidios Intencionales\nEcuador Continental (2010–2024)",
        fontsize=13.5,
        fontweight="bold",
        color="#1E293B",
        pad=22,  # Separación vertical en puntos para alojar debajo el subtítulo técnico.
    )

    # `transform=ax.transAxes` cambia el sistema de referencia de este texto: en vez de usar
    # grados de longitud/latitud, `(0.5, 1.012)` significa "centrado al 50% del ancho y apenas
    # por encima (101.2%) del borde superior del recuadro".
    ax.text(
        0.5,
        1.012,
        f"Validación topológica punto-en-polígono | n = {n_eventos:,} registros georreferenciados (WGS84 / EPSG:4326)",
        transform=ax.transAxes,
        ha="center",  # Alineación horizontal centrada (`horizontalalignment`).
        va="bottom",  # Alineación vertical apoyada en la base (`verticalalignment`).
        fontsize=9.2,
        color="#475569",
    )

    ax.set_xlabel("Longitud (°)", fontsize=10, color="#334155", labelpad=8)
    ax.set_ylabel("Latitud (°)", fontsize=10, color="#334155", labelpad=8)
    ax.tick_params(axis="both", labelsize=8.5, colors="#475569")

    # `ax.spines` contiene los 4 bordes del recuadro (`top`, `bottom`, `left`, `right`).
    for spine in ax.spines.values():
        spine.set_edgecolor("#CBD5E1")
        spine.set_linewidth(0.8)

    # ── 8. Construcción manual de leyenda cartográfica clara (`handles`) ──
    # ¿Por qué construimos `Patch` y `Line2D` explícitos en vez de `legend=True` automático?
    #   Porque en el mapa los puntos tienen `markersize=1.6` y `alpha=0.25`; si Matplotlib
    #   copiara ese tamaño diminuto dentro de la leyenda sería casi invisible. Con `Line2D`
    #   mostramos un marcador representativo nítido (`markersize=6.0`, `alpha=0.85`).
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
            color="none",                # `"none"` oculta la línea y deja únicamente el marcador circular.
            markerfacecolor=color_eventos,
            markeredgecolor="none",
            markersize=6.0,
            alpha=0.85,
            label=f"Homicidios validados (n = {n_eventos:,})",
        ),
    ]
    # `loc="lower right"` ubica la leyenda en el cuadrante sureste exterior al territorio
    # ecuatoriano, donde no cubre ningún cantón ni clúster de eventos.
    leyenda = ax.legend(
        handles=elementos_leyenda,
        loc="lower right",
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

    # Nota metodológica al pie del lienzo (`fig.text` usa coordenadas relativas `0..1` de toda la figura).
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

    # ── 9. Exportación rasterizada y liberación explícita de memoria ──
    # `bbox_inches="tight"` recorta márgenes blancos sobrantes sin cortar títulos ni etiquetas.
    fig.savefig(
        ruta_salida,
        dpi=dpi,
        bbox_inches="tight",
        facecolor="white",
    )
    # `plt.close(fig)` destruye el objeto `Figure` de la memoria interna de Matplotlib;
    # evita fugas de RAM cuando se invoca repetidamente desde scripts o suites de tests.
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
    # Priorizamos `homi_final.parquet` (Paso 5.3); si aún no existe, usamos `homi_georreferenciado.parquet` (Fase 4).
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
