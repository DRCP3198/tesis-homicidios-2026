r"""
metricas_pipeline.py — Auditoría estadística integral del ciclo de vida del pipeline (Paso 5.5).

Corresponde a las Fases R 11 y 13 (líneas 507-520 y 617-626) del script original:
    print(paste("-> Homicidios procesados (2010-2024):", nrow(homi_2010_2024)))
    print(paste("-> Total rescatados perfectos a la primera:", nrow(geo_correctos)))
    print(paste("-> Total rescatados por algoritmo de texto:", nrow(listo.corrcion.casos.posibles)))
    print(paste("-> Casos en limbo con coordenadas correctas retenidos:", nrow(limbo_formato_correcto)))
    print(paste("TOTAL DE REGISTROS GEORREFERENCIADOS:", nrow(homi_Nueva)))
    print(paste("Efectividad total de la base:", round((nrow(homi_Nueva) / nrow(homi_2010_2024)) * 100, 2), "%"))

Objetivo en Python (Paso 5.5):
    Consolidar en un solo reporte auditable todo el recorrido de los datos desde el CSV
    bruto inicial (Fase 1) hasta el dataset etiquetado definitivo (Fase 5):
      • Conteos globales del ciclo de vida (brutos → post-filtro temporal/insular → finales).
      • Desglose geoespacial y tasa de rescate del algoritmo reparador decimal (Fase 4)
        frente a coordenadas descartadas irreversibles.
      • Efectividad general de georreferenciación (%) sobre el universo continental de análisis.
      • Metadatos descriptivos del entregable final (columnas, tipos, rango temporal, cobertura).
      • Persistencia estructurada en JSON (`reports/auditoria_pipeline.json`) y resumen ejecutivo
        en Markdown (`reports/auditoria_pipeline.md`) listo para incorporar en la tesis.

En palabras simples:
    Es el "acta de cierre contable" de todo el preprocesamiento. Demuestra con números
    verificables cuántos registros entraron al sistema, por qué salió cada registro
    excluido, cuántos rescató el algoritmo geoespacial y cuál es la efectividad final
    del dataset que alimentará los modelos de series temporales (Fase 6).
"""
# `asdict` convierte un objeto `@dataclass` en un diccionario común de Python `{clave: valor}`,
# ideal para guardarlo directamente como archivo JSON.
from dataclasses import asdict, dataclass, field

# `datetime` y `timezone` permiten registrar la fecha y hora exacta (UTC) en que se corrió la auditoría.
from datetime import datetime, timezone

# `json` es la librería estándar de Python para leer y escribir archivos `.json`.
import json

# `Path` maneja rutas de archivos de forma segura en cualquier sistema operativo.
from pathlib import Path

import pandas as pd

from src.ingesta.config import (
    INTERIM_FILTRADO,          # Salida Fase 3: homi_filtrado_2024.parquet (universo continental).
    INTERIM_GEO_CORRECTOS,     # Salida Fase 4: geo_correctos.parquet (1ra auditoría espacial).
    INTERIM_INSULAR_EXCLUIDO,  # Salida Fase 3: homi_insular_excluido.parquet (Galápagos).
    INTERIM_RENOMBRADO,        # Salida Fase 1: homi_renombrado.parquet (universo bruto inicial).
    PROCESSED_GEORREFERENCIADO,
    SALIDA_AUDITORIA_JSON,     # Salida 5.5 JSON: reports/auditoria_pipeline.json.
    SALIDA_AUDITORIA_MD,       # Salida 5.5 Markdown: reports/auditoria_pipeline.md.
    SALIDA_PARQUET_FINAL,      # Salida 5.3 Parquet: data/processed/homi_final.parquet.
)


# =========================================================================
# ESTRUCTURA DE DATOS DE LA AUDITORÍA INTEGRAL
# =========================================================================
# `@dataclass` genera automáticamente el constructor `__init__`, la representación
# legible `__repr__` y la comparación `__eq__` a partir de los atributos declarados abajo.
@dataclass
class ResumenAuditoriaPipeline:
    """
    Contenedor tipado con todas las métricas del ciclo de vida del pipeline (Fases 1 a 5).

    Se puede inspeccionar en código (ej. `resumen.efectividad_georreferenciacion_pct`)
    o serializar directamente a JSON mediante `resumen.to_dict()`.
    """

    # ── 1. Metadatos de ejecución ──
    fecha_generacion_utc: str = ""  # Marca temporal ISO-8601 en UTC de la corrida.

    # ── 2. Conteos globales del ciclo de vida (Fases 1 → 3 → 5) ──
    registros_brutos_iniciales: int = 0       # Total leído del CSV original (ej. 47,739).
    registros_excluidos_temporal: int = 0     # Excluidos por año > 2024 o año NaN (ej. 9,171).
    registros_excluidos_insular: int = 0      # Excluidos por pertenecer a Galápagos (ej. 2).
    registros_universo_filtrado: int = 0      # Universo continental 2010-2024 (ej. 38,566).
    registros_finales_etiquetados: int = 0    # Dataset definitivo exportado en Fase 5 (ej. 38,565).

    # ── 3. Desglose de validación y rescate geoespacial (Fase 4) ──
    geo_correctos_primera_auditoria: int = 0         # Caen dentro de su cantón al primer intento.
    candidatos_fuera_poligono: int = 0               # Caen fuera del cantón en la 1ra auditoría.
    limbo_formato_correcto_retenidos: int = 0        # Tienen punto decimal y coords válidas (retenidos).
    candidatos_corruptos_sin_decimal: int = 0        # Sin punto decimal → enviados al reparador.
    coordenadas_rescatadas_algoritmo: int = 0        # Recuperadas exitosamente por los 4 escenarios.
    coordenadas_descartadas_irreversibles: int = 0   # Irrecuperables (ej. (0, 0) en el océano).
    detalle_rescate_por_escenario: dict[str, int] = field(default_factory=dict)

    # ── 4. Indicadores porcentuales de calidad y efectividad ──
    tasa_retencion_post_filtro_pct: float = 0.0           # Universo filtrado / Brutos iniciales (%).
    precision_topologica_inicial_pct: float = 0.0         # Geo correctos 1ra aud. / Universo (%).
    tasa_rescate_sobre_corruptos_pct: float = 0.0         # Rescatados / Corruptos sin decimal (%).
    efectividad_georreferenciacion_pct: float = 0.0       # Finales / Universo filtrado (%) [métrica R].
    retencion_global_bruto_a_final_pct: float = 0.0       # Finales / Brutos iniciales (%).
    integridad_contable_ok: bool = False                  # True si todas las sumas cuadran sin fugas.

    # ── 5. Perfil estructural del dataset final (Fase 5) ──
    columnas_finales: int = 0
    nombres_columnas: list[str] = field(default_factory=list)
    esquema_tipos: dict[str, str] = field(default_factory=dict)
    anio_min: int | None = None
    anio_max: int | None = None
    fecha_min: str | None = None
    fecha_max: str | None = None
    provincias_unicas: int = 0
    cantones_unicos: int = 0

    def to_dict(self) -> dict:
        """Convierte la instancia del reporte en un diccionario serializable a JSON."""
        # `asdict(self)` transforma recursivamente todos los campos del dataclass en un `dict`.
        return asdict(self)


# =========================================================================
# FUNCIÓN AUXILIAR INTERNA — Inferencia desde artefactos Parquet en disco
# =========================================================================
def _inferir_limbo_desde_artefactos(
    ruta_filtrado: Path,
    ruta_geo_correctos: Path,
) -> int | None:
    """
    Reconstruye cuántos registros del universo filtrado quedaron en `limbo_formato_correcto`
    cuando el módulo se ejecuta de forma autónoma sin pasar conteos en memoria.

    Lógica:
        En la Fase 4 (`geometrias.py`), a los registros con coordenadas numéricas válidas se
        les asigna `ID_temp = 1..N`. Los que pasan la 1ra auditoría se guardan en
        `geo_correctos.parquet` conservando su `ID_temp`. Los que NO están en `geo_correctos`
        pero sí tienen punto decimal `.` en `latitud` conforman exactamente `limbo_formato_correcto`.
    """
    if not (ruta_filtrado.exists() and ruta_geo_correctos.exists()):
        return None

    df_filt = pd.read_parquet(ruta_filtrado)
    df_corr = pd.read_parquet(ruta_geo_correctos)

    if "ID_temp" not in df_corr.columns or "latitud" not in df_filt.columns:
        return None

    # Reproducimos el filtrado de coordenadas convertibles a número de `crear_geodataframe_puntos`.
    lat_num = pd.to_numeric(df_filt["latitud"], errors="coerce")
    lon_num = pd.to_numeric(df_filt["longitud"], errors="coerce")
    df_validos = df_filt.loc[lat_num.notna() & lon_num.notna()].copy()
    df_validos["ID_temp"] = range(1, len(df_validos) + 1)

    # Filtramos los que NO aprobaron la primera auditoría espacial (`~` = negación).
    ids_correctos = set(df_corr["ID_temp"].tolist())
    fuera_poligono = df_validos[~df_validos["ID_temp"].isin(ids_correctos)]

    # De esos, contamos cuántos sí tenían punto decimal literal `"."` (`regex=False`).
    tiene_punto = fuera_poligono["latitud"].astype(str).str.contains(".", regex=False, na=False)
    return int(tiene_punto.sum())


# =========================================================================
# PASO 5.5a — Cálculo integral de métricas del pipeline
# =========================================================================
def calcular_metricas_pipeline(
    df_final: pd.DataFrame | None = None,
    n_brutos_iniciales: int | None = None,
    n_excluidos_temporal: int | None = None,
    n_excluidos_insular: int | None = None,
    n_universo_filtrado: int | None = None,
    n_geo_correctos: int | None = None,
    n_rescatados_algoritmo: int | None = None,
    n_limbo_retenidos: int | None = None,
    n_descartados_irreversibles: int | None = None,
    detalle_escenarios: dict[str, int] | None = None,
) -> ResumenAuditoriaPipeline:
    r"""
    Calcula todas las métricas de auditoría del ciclo de vida (Fases 1 a 5).

    Puede invocarse de dos maneras complementarias:
      1. **En memoria desde `main.py`**: recibiendo directamente los conteos exactos de
         cada fase y el `df_final` recién estandarizado.
      2. **De forma autónoma desde disco**: si algún conteo es `None`, lee automáticamente
         los artefactos Parquet de `data/interim/` y `data/processed/`.

    Parameters
    ----------
    df_final : pd.DataFrame or None, optional
        Dataset final de 21 columnas. Si es `None`, se carga de `SALIDA_PARQUET_FINAL`
        (o `PROCESSED_GEORREFERENCIADO`).
    n_brutos_iniciales : int or None, optional
        Total de registros crudos al iniciar el pipeline (Fase 1).
    n_excluidos_temporal : int or None, optional
        Registros descartados por filtro temporal (`anio_hecho > 2024` o nulo).
    n_excluidos_insular : int or None, optional
        Registros insulares de Galápagos separados en la Fase 3.
    n_universo_filtrado : int or None, optional
        Universo continental válido 2010–2024 que entra a la validación geoespacial.
    n_geo_correctos : int or None, optional
        Registros validados en la primera auditoría punto-en-polígono (Fase 4.4).
    n_rescatados_algoritmo : int or None, optional
        Coordenadas recuperadas por los 4 escenarios decimales (Fase 4.6).
    n_limbo_retenidos : int or None, optional
        Registros con formato decimal válido retenidos pese a discrepancia cantonal (Fase 4.5).
    n_descartados_irreversibles : int or None, optional
        Registros corruptos irrecuperables excluidos del dataset final.
    detalle_escenarios : dict[str, int] or None, optional
        Desglose opcional `{escenario_1..4: cantidad}` del algoritmo reparador.

    Returns
    -------
    ResumenAuditoriaPipeline
        Objeto con conteos, tasas de rescate, efectividad e integridad contable.
    """
    # ── 1. Cargar `df_final` desde disco si no fue pasado en memoria ──
    if df_final is None:
        if SALIDA_PARQUET_FINAL.exists():
            df_final = pd.read_parquet(SALIDA_PARQUET_FINAL)
        elif PROCESSED_GEORREFERENCIADO.exists():
            df_final = pd.read_parquet(PROCESSED_GEORREFERENCIADO)
        else:
            raise FileNotFoundError(
                "No se proporcionó `df_final` ni existen artefactos Parquet en `data/processed/`."
            )

    n_finales = len(df_final)

    # ── 2. Resolver conteos globales del ciclo de vida (Fases 1 y 3) ──
    if n_universo_filtrado is None:
        if INTERIM_FILTRADO.exists():
            n_universo_filtrado = len(pd.read_parquet(INTERIM_FILTRADO))
        else:
            n_universo_filtrado = n_finales

    if n_brutos_iniciales is None:
        if INTERIM_RENOMBRADO.exists():
            n_brutos_iniciales = len(pd.read_parquet(INTERIM_RENOMBRADO))
        else:
            n_brutos_iniciales = n_universo_filtrado

    if n_excluidos_insular is None:
        if INTERIM_INSULAR_EXCLUIDO.exists():
            n_excluidos_insular = len(pd.read_parquet(INTERIM_INSULAR_EXCLUIDO))
        else:
            n_excluidos_insular = 0

    if n_excluidos_temporal is None:
        # Por conservación de masa en Fase 3: brutos = temporal + insular + universo_filtrado.
        n_excluidos_temporal = max(
            0, n_brutos_iniciales - n_universo_filtrado - n_excluidos_insular
        )

    # ── 3. Resolver desglose geoespacial (Fase 4) ──
    if n_geo_correctos is None:
        if INTERIM_GEO_CORRECTOS.exists():
            n_geo_correctos = len(pd.read_parquet(INTERIM_GEO_CORRECTOS))
        else:
            n_geo_correctos = n_finales

    # Puntos que no cayeron dentro de su cantón declarado en la primera pasada.
    n_fuera_poligono = max(0, n_universo_filtrado - n_geo_correctos)

    if n_descartados_irreversibles is None:
        n_descartados_irreversibles = max(0, n_universo_filtrado - n_finales)

    # Resolver `n_limbo_retenidos` y `n_rescatados_algoritmo` de forma consistente.
    if n_limbo_retenidos is None and n_rescatados_algoritmo is None:
        inferido_limbo = _inferir_limbo_desde_artefactos(
            INTERIM_FILTRADO, INTERIM_GEO_CORRECTOS
        )
        if inferido_limbo is not None:
            n_limbo_retenidos = inferido_limbo
            n_rescatados_algoritmo = max(
                0, (n_finales - n_geo_correctos) - n_limbo_retenidos
            )
        else:
            n_rescatados_algoritmo = 0
            n_limbo_retenidos = max(0, n_finales - n_geo_correctos)
    elif n_limbo_retenidos is None:
        n_limbo_retenidos = max(
            0, (n_finales - n_geo_correctos) - int(n_rescatados_algoritmo or 0)
        )
    elif n_rescatados_algoritmo is None:
        n_rescatados_algoritmo = max(
            0, (n_finales - n_geo_correctos) - n_limbo_retenidos
        )

    # Candidatos sin punto decimal evaluados por el algoritmo reparador:
    # son exactamente la suma de los que logró rescatar + los descartados irreversibles.
    n_corruptos_sin_decimal = n_rescatados_algoritmo + n_descartados_irreversibles

    # ── 4. Calcular tasas e indicadores porcentuales (evitando división para cero) ──
    tasa_retencion_filtro = (
        round((n_universo_filtrado / n_brutos_iniciales) * 100, 4)
        if n_brutos_iniciales > 0
        else 0.0
    )
    precision_topologica_inicial = (
        round((n_geo_correctos / n_universo_filtrado) * 100, 4)
        if n_universo_filtrado > 0
        else 0.0
    )
    tasa_rescate_corruptos = (
        round((n_rescatados_algoritmo / n_corruptos_sin_decimal) * 100, 4)
        if n_corruptos_sin_decimal > 0
        else 0.0
    )
    # Métrica oficial de efectividad equivalente a la línea 518 del script R:
    # `(nrow(homi_Nueva) / nrow(homi_2010_2024)) * 100`
    efectividad_geo = (
        round((n_finales / n_universo_filtrado) * 100, 4)
        if n_universo_filtrado > 0
        else 0.0
    )
    retencion_global = (
        round((n_finales / n_brutos_iniciales) * 100, 4)
        if n_brutos_iniciales > 0
        else 0.0
    )

    # ── 5. Verificación matemática de integridad contable de extremo a extremo ──
    # Ecuación 1 (Fase 1 → 3): brutos == excluidos_temporal + excluidos_insular + universo_filtrado
    cuadra_fase3 = (
        n_excluidos_temporal + n_excluidos_insular + n_universo_filtrado
    ) == n_brutos_iniciales

    # Ecuación 2 (Fase 4 → 5): universo_filtrado == correctos + rescatados + limbo + descartados
    cuadra_fase4 = (
        n_geo_correctos
        + n_rescatados_algoritmo
        + n_limbo_retenidos
        + n_descartados_irreversibles
    ) == n_universo_filtrado

    # Ecuación 3 (Ensamble final): finales == correctos + rescatados + limbo
    cuadra_ensamble = (
        n_geo_correctos + n_rescatados_algoritmo + n_limbo_retenidos
    ) == n_finales

    integridad_ok = bool(cuadra_fase3 and cuadra_fase4 and cuadra_ensamble)

    # ── 6. Extraer perfil estructural y cobertura del dataset final ──
    nombres_cols = list(df_final.columns)
    esquema_tipos = {col: str(dtype) for col, dtype in df_final.dtypes.items()}

    anio_min: int | None = None
    anio_max: int | None = None
    if "anio_hecho" in df_final.columns and df_final["anio_hecho"].notna().any():
        anio_min = int(df_final["anio_hecho"].min())
        anio_max = int(df_final["anio_hecho"].max())

    fecha_min: str | None = None
    fecha_max: str | None = None
    if "fecha_hecho" in df_final.columns and df_final["fecha_hecho"].notna().any():
        fechas_dt = pd.to_datetime(df_final["fecha_hecho"], errors="coerce").dropna()
        if len(fechas_dt) > 0:
            fecha_min = fechas_dt.min().strftime("%Y-%m-%d")
            fecha_max = fechas_dt.max().strftime("%Y-%m-%d")

    n_provincias = (
        int(df_final["provincia"].nunique(dropna=True))
        if "provincia" in df_final.columns
        else 0
    )
    n_cantones = (
        int(df_final["canton"].nunique(dropna=True))
        if "canton" in df_final.columns
        else 0
    )

    marca_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    return ResumenAuditoriaPipeline(
        fecha_generacion_utc=marca_utc,
        registros_brutos_iniciales=n_brutos_iniciales,
        registros_excluidos_temporal=n_excluidos_temporal,
        registros_excluidos_insular=n_excluidos_insular,
        registros_universo_filtrado=n_universo_filtrado,
        registros_finales_etiquetados=n_finales,
        geo_correctos_primera_auditoria=n_geo_correctos,
        candidatos_fuera_poligono=n_fuera_poligono,
        limbo_formato_correcto_retenidos=n_limbo_retenidos,
        candidatos_corruptos_sin_decimal=n_corruptos_sin_decimal,
        coordenadas_rescatadas_algoritmo=n_rescatados_algoritmo,
        coordenadas_descartadas_irreversibles=n_descartados_irreversibles,
        detalle_rescate_por_escenario=detalle_escenarios or {},
        tasa_retencion_post_filtro_pct=tasa_retencion_filtro,
        precision_topologica_inicial_pct=precision_topologica_inicial,
        tasa_rescate_sobre_corruptos_pct=tasa_rescate_corruptos,
        efectividad_georreferenciacion_pct=efectividad_geo,
        retencion_global_bruto_a_final_pct=retencion_global,
        integridad_contable_ok=integridad_ok,
        columnas_finales=len(nombres_cols),
        nombres_columnas=nombres_cols,
        esquema_tipos=esquema_tipos,
        anio_min=anio_min,
        anio_max=anio_max,
        fecha_min=fecha_min,
        fecha_max=fecha_max,
        provincias_unicas=n_provincias,
        cantones_unicos=n_cantones,
    )


# =========================================================================
# PASO 5.5b — Persistencia estructurada en JSON y Markdown + consola
# =========================================================================
def exportar_reporte_json(
    resumen: ResumenAuditoriaPipeline,
    ruta_salida: Path = SALIDA_AUDITORIA_JSON,
) -> Path:
    """
    Guarda el resumen estadístico completo en un archivo JSON estructurado UTF-8.

    Parameters
    ----------
    resumen : ResumenAuditoriaPipeline
        Objeto con todas las métricas calculadas.
    ruta_salida : Path, optional
        Ruta destino del JSON (`reports/auditoria_pipeline.json` por defecto).

    Returns
    -------
    Path
        Ruta absoluta del archivo JSON escrito.
    """
    ruta_salida = Path(ruta_salida)
    ruta_salida.parent.mkdir(parents=True, exist_ok=True)

    # `with open(...) as f:` abre el archivo y garantiza cerrarlo automáticamente al salir
    # del bloque, incluso si ocurriera un error intermedio (context manager de Python).
    # `ensure_ascii=False` conserva tildes y eñes reales en vez de códigos `\u00f3`.
    # `indent=2` formatea el JSON con sangría de 2 espacios para lectura humana.
    with open(ruta_salida, mode="w", encoding="utf-8") as archivo_json:
        json.dump(resumen.to_dict(), archivo_json, ensure_ascii=False, indent=2)

    print(f"        Reporte JSON guardado: {ruta_salida}")
    return ruta_salida


def exportar_reporte_markdown(
    resumen: ResumenAuditoriaPipeline,
    ruta_salida: Path = SALIDA_AUDITORIA_MD,
) -> Path:
    """
    Exporta una ficha técnica en formato Markdown lista para anexar al documento de tesis.

    Parameters
    ----------
    resumen : ResumenAuditoriaPipeline
        Objeto con todas las métricas calculadas.
    ruta_salida : Path, optional
        Ruta destino del archivo Markdown (`reports/auditoria_pipeline.md` por defecto).

    Returns
    -------
    Path
        Ruta absoluta del archivo Markdown escrito.
    """
    ruta_salida = Path(ruta_salida)
    ruta_salida.parent.mkdir(parents=True, exist_ok=True)

    estado_txt = "VERIFICADA (100% cuadre contable)" if resumen.integridad_contable_ok else "OBSERVADA"
    rango_fechas = (
        f"{resumen.fecha_min} a {resumen.fecha_max}"
        if resumen.fecha_min and resumen.fecha_max
        else f"{resumen.anio_min}–{resumen.anio_max}"
    )

    lineas_md = [
        "# Auditoría Estadística Integral del Pipeline (Fases 1 a 5)",
        "",
        f"- **Fecha de generación (UTC):** `{resumen.fecha_generacion_utc}`",
        f"- **Integridad contable extremo a extremo:** **{estado_txt}**",
        f"- **Cobertura temporal validada:** `{rango_fechas}`",
        f"- **Cobertura territorial continental:** `{resumen.provincias_unicas}` provincias | `{resumen.cantones_unicos}` cantones",
        f"- **Esquema consolidado:** `{resumen.columnas_finales}` columnas limpias",
        "",
        "## 1. Trazabilidad del Ciclo de Vida de los Registros",
        "",
        "| Etapa del Pipeline | Registros | Porcentaje |",
        "|---|---:|---:|",
        f"| Registros brutos iniciales (CSV 2010–2025) | {resumen.registros_brutos_iniciales:,} | 100.00% |",
        f"| (-) Excluidos por filtro temporal (`anio_hecho > 2024`) | {resumen.registros_excluidos_temporal:,} | — |",
        f"| (-) Excluidos por filtro insular (Galápagos) | {resumen.registros_excluidos_insular:,} | — |",
        f"| **(=) Universo continental de análisis (2010–2024)** | **{resumen.registros_universo_filtrado:,}** | **{resumen.tasa_retencion_post_filtro_pct:.2f}%** |",
        f"| (+) Validados en 1ra auditoría punto-en-polígono | {resumen.geo_correctos_primera_auditoria:,} | {resumen.precision_topologica_inicial_pct:.2f}% |",
        f"| (+) Rescatados por algoritmo reparador decimal (4 escenarios) | {resumen.coordenadas_rescatadas_algoritmo:,} | {resumen.tasa_rescate_sobre_corruptos_pct:.2f}% (sobre corruptos) |",
        f"| (+) Retenidos en limbo con formato decimal válido | {resumen.limbo_formato_correcto_retenidos:,} | — |",
        f"| (-) Coordenadas descartadas irreversibles | {resumen.coordenadas_descartadas_irreversibles:,} | — |",
        f"| **(=) REGISTROS FINALES ETIQUETADOS Y GEORREFERENCIADOS** | **{resumen.registros_finales_etiquetados:,}** | **{resumen.efectividad_georreferenciacion_pct:.4f}%** |",
        "",
        "## 2. Indicadores Clave de Efectividad",
        "",
        f"- **Efectividad general de georreferenciación (sobre universo 2010–2024):** `{resumen.efectividad_georreferenciacion_pct:.4f}%`",
        f"- **Tasa de retención global (bruto inicial → entregable final):** `{resumen.retencion_global_bruto_a_final_pct:.2f}%`",
        f"- **Candidatos sin punto decimal evaluados por algoritmo reparador:** `{resumen.candidatos_corruptos_sin_decimal:,}` "
        f"(rescatados: `{resumen.coordenadas_rescatadas_algoritmo:,}`, descartados irreversibles: `{resumen.coordenadas_descartadas_irreversibles:,}`)",
        "",
    ]

    ruta_salida.write_text("\n".join(lineas_md), encoding="utf-8")
    print(f"        Reporte Markdown guardado: {ruta_salida}")
    return ruta_salida


def imprimir_resumen_pipeline(resumen: ResumenAuditoriaPipeline) -> None:
    """
    Muestra en consola el cuadro ejecutivo de control integral (equivalente a R Fases 11 y 13).
    """
    print("=" * 68)
    print("  AUDITORÍA ESTADÍSTICA INTEGRAL DEL PIPELINE (FASES 1 A 5)")
    print("=" * 68)
    print(f"  {'1. CICLO DE VIDA DE REGISTROS':<48} {'Conteo':>14}")
    print(f"  {'-' * 48} {'-' * 14}")
    print(f"  {'Registros brutos iniciales (Fase 1)':<48} {resumen.registros_brutos_iniciales:>14,}")
    print(f"  {'(-) Excluidos filtro temporal (> 2024)':<48} {resumen.registros_excluidos_temporal:>14,}")
    print(f"  {'(-) Excluidos filtro insular (Galápagos)':<48} {resumen.registros_excluidos_insular:>14,}")
    print(f"  {'(=) Universo continental 2010-2024 (Fase 3)':<48} {resumen.registros_universo_filtrado:>14,}")
    print(f"  {'-' * 48} {'-' * 14}")
    print(f"  {'2. AUDITORÍA Y RESCATE GEOESPACIAL (Fase 4)':<48}")
    print(f"  {'(+) Correctos en 1ra auditoría topológica':<48} {resumen.geo_correctos_primera_auditoria:>14,}")
    print(f"  {'(+) Rescatados por algoritmo decimal (4 esc.)':<48} {resumen.coordenadas_rescatadas_algoritmo:>14,}")
    print(f"  {'(+) Limbo con formato decimal retenidos':<48} {resumen.limbo_formato_correcto_retenidos:>14,}")
    print(f"  {'(-) Coordenadas descartadas irreversibles':<48} {resumen.coordenadas_descartadas_irreversibles:>14,}")
    print(f"  {'-' * 48} {'-' * 14}")
    print(f"  {'(=) REGISTROS FINALES ETIQUETADOS (Fase 5)':<48} {resumen.registros_finales_etiquetados:>14,}")
    print(f"  {'Columnas limpias seleccionadas':<48} {resumen.columnas_finales:>14}")
    print(f"  {'Provincias / Cantones representados':<48} {f'{resumen.provincias_unicas} / {resumen.cantones_unicos}':>14}")
    print(f"  {'-' * 63}")
    print(f"  • Efectividad de georreferenciación (sobre universo): {resumen.efectividad_georreferenciacion_pct:.4f}%")
    print(f"  • Precisión topológica inicial (1ra pasada):          {resumen.precision_topologica_inicial_pct:.2f}%")
    print(f"  • Tasa de rescate sobre corruptos sin decimal:        {resumen.tasa_rescate_sobre_corruptos_pct:.2f}%")
    print(f"  • Retención global (bruto → final):                   {resumen.retencion_global_bruto_a_final_pct:.2f}%")
    estado = "[OK] CUADRE EXACTO" if resumen.integridad_contable_ok else "[ALERTA] REVISAR CONTEOS"
    print(f"  • Integridad contable del ciclo de vida:              {estado}")
    print("=" * 68)


def generar_auditoria_pipeline(
    df_final: pd.DataFrame | None = None,
    n_brutos_iniciales: int | None = None,
    n_excluidos_temporal: int | None = None,
    n_excluidos_insular: int | None = None,
    n_universo_filtrado: int | None = None,
    n_geo_correctos: int | None = None,
    n_rescatados_algoritmo: int | None = None,
    n_limbo_retenidos: int | None = None,
    n_descartados_irreversibles: int | None = None,
    detalle_escenarios: dict[str, int] | None = None,
    ruta_json: Path = SALIDA_AUDITORIA_JSON,
    ruta_md: Path = SALIDA_AUDITORIA_MD,
) -> ResumenAuditoriaPipeline:
    """
    Función fachada del Paso 5.5: calcula métricas, imprime el resumen y exporta JSON + Markdown.
    """
    print("  [5.5] Generando reporte estadístico de control y efectividad del pipeline")
    resumen = calcular_metricas_pipeline(
        df_final=df_final,
        n_brutos_iniciales=n_brutos_iniciales,
        n_excluidos_temporal=n_excluidos_temporal,
        n_excluidos_insular=n_excluidos_insular,
        n_universo_filtrado=n_universo_filtrado,
        n_geo_correctos=n_geo_correctos,
        n_rescatados_algoritmo=n_rescatados_algoritmo,
        n_limbo_retenidos=n_limbo_retenidos,
        n_descartados_irreversibles=n_descartados_irreversibles,
        detalle_escenarios=detalle_escenarios,
    )
    exportar_reporte_json(resumen, ruta_salida=ruta_json)
    exportar_reporte_markdown(resumen, ruta_salida=ruta_md)
    imprimir_resumen_pipeline(resumen)
    return resumen


# Permite ejecutar la auditoría de forma independiente desde terminal:
#     python -m src.reportes.metricas_pipeline
if __name__ == "__main__":
    generar_auditoria_pipeline()

