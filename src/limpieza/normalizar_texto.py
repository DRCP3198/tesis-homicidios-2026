"""
normalizar_texto.py — Módulo de limpieza y normalización textual.

Corresponde a la Fase 2 de la migración R → Python (líneas 81-130 del R):
    homi_2010_2025 <- homi_2010_2025 %>%
        mutate(
            columna = iconv(str_to_upper(str_trim(columna)),
                            to = "ASCII//TRANSLIT"),
            ...
        )

Funciones principales:
    - normalizar_todas_columnas(): Aplica strip + upper + unidecode
      a las 13 columnas de texto definidas en config.py.
    - guardar_intermedio_normalizado(): Guarda el resultado en Parquet.
    - cargar_intermedio_normalizado(): Vuelve a leer ese Parquet.

¿Por qué normalizar el texto?
    Para que "Guayaquíl", " GUAYAQUIL " y "guayaquil" se conviertan todos en
    "GUAYAQUIL". Así, al comparar el cantón de la base de datos con el cantón
    del mapa (Fase 4), coinciden letra por letra.
"""
# pandas: librería principal de manejo de tablas de datos (DataFrames).
import pandas as pd

from src.ingesta.config import (
    COLUMNAS_TEXTO_NORMALIZAR,     # Lista de las 13 columnas de texto
    INTERIM_NORMALIZADO,           # Ruta de salida: data/interim/homi_normalizado.parquet
    INTERIM_RENOMBRADO,            # Ruta de entrada: data/interim/homi_renombrado.parquet
    MAPEO_HOMOLOGACION_CANTONES,   # Diccionario {(provincia, canton_variante): canton_oficial}
)
# Reutilizamos la función que limpia una columna completa (ver src/utils/texto.py).
from src.utils.texto import normalizar_columna


# =========================================================================
# FUNCIÓN AUXILIAR: Homologación de variantes y errores de tipeo en cantones
# =========================================================================
def homologar_cantones_por_provincia(df: pd.DataFrame) -> pd.DataFrame:
    """
    Homologa las variantes de escritura de cantones en el DataFrame de
    homicidios desambiguando por la tupla `(provincia, canton)`, e imprime
    en consola el resumen estadístico y una muestra explícita de las filas
    corregidas.

    ¿Por qué desambiguar usando `(provincia, canton)` en lugar de solo `canton`?
        El caso crítico es `"SAN MIGUEL DE SALCEDO"`, que aparece registrado en
        dos provincias distintas:
          1. En `"COTOPAXI"`, corresponde al cantón cuyo nombre oficial en la
             cartografía INEC (`DPA_DESCAN`) es `"SALCEDO"` (3 registros).
          2. En `"BOLIVAR"`, corresponde a un error de tipeo policial para un
             hecho ocurrido físicamente en el cantón `"SAN MIGUEL"` de Bolívar
             (1 registro, `codigo_caso=92067`, coords `-1.7061, -79.11753`).
        Asimismo, unifica variantes de espacio o nombre histórico largo:
          • `("LOS RIOS", "PUEBLO VIEJO")` → `"PUEBLOVIEJO"`
          • `("ORELLANA", "PUERTO FRANCISCO DE ORELLANA")` → `"ORELLANA"`

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame con las columnas `"provincia"` y `"canton"` ya pasadas por
        `normalizar_columna()` (en MAYÚSCULAS y sin tildes).

    Returns
    -------
    pd.DataFrame
        DataFrame con la columna `"canton"` homologada al estándar del INEC.
    """
    # Si por alguna razón el DataFrame de prueba no tiene ambas columnas, salimos sin cambios.
    if "provincia" not in df.columns or "canton" not in df.columns:
        return df

    total_homologados = 0
    muestras_consola: list[dict[str, str]] = []
    resumen_pares: list[tuple[str, str, str, int]] = []

    # Recorremos cada regla del diccionario:
    #   • `(prov_objetivo, canton_erroneo)` es la tupla clave.
    #   • `canton_oficial` es el nombre estandarizado según el shapefile del INEC.
    for (prov_objetivo, canton_erroneo), canton_oficial in MAPEO_HOMOLOGACION_CANTONES.items():
        # Creamos una máscara booleana (Serie de True/False) que exige que AMBAS
        # condiciones se cumplan en la misma fila: misma provincia Y mismo cantón variante.
        mascara = (df["provincia"] == prov_objetivo) & (df["canton"] == canton_erroneo)
        n_afectados = int(mascara.sum())

        if n_afectados > 0:
            resumen_pares.append((prov_objetivo, canton_erroneo, canton_oficial, n_afectados))
            total_homologados += n_afectados

            # Extraemos hasta 2 filas de muestra por cada caso para enseñarlas en consola
            # ANTES de sobrescribir el valor de la columna `"canton"`.
            filas_muestra = df.loc[mascara].head(2)
            for _, fila in filas_muestra.iterrows():
                muestras_consola.append({
                    "codigo_caso": str(fila.get("codigo_caso", "N/A")),
                    "fecha_hecho": str(fila.get("fecha_hecho", "N/A"))[:10],
                    "provincia": prov_objetivo,
                    "canton_antes": canton_erroneo,
                    "canton_despues": canton_oficial,
                    "coords": f"({fila.get('latitud', '?')}, {fila.get('longitud', '?')})",
                })

            # `.loc[mascara, "canton"] = canton_oficial` actualiza únicamente las filas
            # donde `mascara` es True en la columna `"canton"`.
            df.loc[mascara, "canton"] = canton_oficial

    # Si hubo registros corregidos, imprimimos la tabla resumen y las filas de ejemplo en consola.
    if total_homologados > 0:
        print("-" * 60)
        print("  [2.1] HOMOLOGACIÓN DE VARIANTES Y ERRORES DE TIPEO EN CANTONES")
        print("-" * 60)
        print(
            f"  {'Provincia':<12} | {'Cantón original (variante)':<30} | "
            f"{'Cantón oficial INEC':<14} | {'Filas':>6}"
        )
        print("  " + "-" * 70)
        for prov, c_ant, c_nue, conteo in resumen_pares:
            print(f"  {prov:<12} | {c_ant:<30} | {c_nue:<14} | {conteo:>6,}")
        print("  " + "-" * 70)
        print(f"  Total de registros homologados por (provincia, cantón): {total_homologados:,}")

        print("\n  Muestra de registros corregidos (incluye desambiguación Cotopaxi vs. Bolívar):")
        print(
            f"  {'Caso':<8} | {'Fecha':<10} | {'Provincia':<10} | "
            f"{'Antes → Después':<42} | {'Coordenadas (lat, lon)'}"
        )
        print("  " + "-" * 98)
        for m in muestras_consola:
            transicion = f"{m['canton_antes']} -> {m['canton_despues']}"
            print(
                f"  {m['codigo_caso']:<8} | {m['fecha_hecho']:<10} | {m['provincia']:<10} | "
                f"{transicion:<42} | {m['coords']}"
            )

    # También mostramos una muestra informativa de cantones con "Ñ" (RUMINAHUI y LOGRONO)
    # que en el CSV se normalizan con "N" y que ahora empatarán con el shapefile reparado.
    mascara_ene = df["canton"].isin(["RUMINAHUI", "LOGRONO"])
    if mascara_ene.any():
        conteo_ene = df.loc[mascara_ene, "canton"].value_counts().to_dict()
        resumen_ene = ", ".join(f"{k}: {v:,} filas" for k, v in conteo_ene.items())
        print(f"\n  [INFO Ñ→N] Cantones normalizados que empatan con SHP reparado: {resumen_ene}")
        muestra_ene = (
            df.loc[mascara_ene]
            .groupby("canton", as_index=False)
            .first()
        )
        for _, fila in muestra_ene.iterrows():
            print(
                f"             • Ejemplo {fila.get('provincia', '')} - {fila['canton']}: "
                f"codigo_caso={fila.get('codigo_caso', 'N/A')}, "
                f"fecha={str(fila.get('fecha_hecho', 'N/A'))[:10]}, "
                f"coords=({fila.get('latitud', '?')}, {fila.get('longitud', '?')})"
            )

    return df


# =========================================================================
# FUNCIÓN PRINCIPAL: Normaliza todas las columnas de texto
# =========================================================================
def normalizar_todas_columnas(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aplica la normalización textual a las 13 columnas de texto del dataset.

    Equivalencia R (líneas 83-130):
        homi_2010_2025 <- homi_2010_2025 %>%
            mutate(
                codigo_caso = iconv(str_to_upper(str_trim(codigo_caso)),
                                    to = "ASCII//TRANSLIT"),
                tipo_delito = iconv(str_to_upper(str_trim(tipo_delito)),
                                    to = "ASCII//TRANSLIT"),
                ...  # 13 columnas en total
            )

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame con columnas ya renombradas (salida de Fase 1).

    Returns
    -------
    pd.DataFrame
        DataFrame con las 13 columnas de texto normalizadas:
        mayúsculas, sin tildes/eñes/diéresis, sin espacios extremos.

    Raises
    ------
    KeyError
        Si alguna de las 13 columnas esperadas no existe en el DataFrame.
    """
    print("=" * 60)  # "=" * 60 repite el carácter 60 veces → línea decorativa.
    print("  FASE 2: LIMPIEZA Y NORMALIZACIÓN TEXTUAL")
    print("=" * 60)

    # ── Verificar que todas las columnas de texto existen ──
    columnas_faltantes = set(COLUMNAS_TEXTO_NORMALIZAR) - set(df.columns) #set me coje una lista y me transofrma a una estructura de datos comparable/operable con el operador -
    # Resultado: columnas que deberían existir pero NO están en la tabla.
    # Un conjunto vacío equivale a False → solo entra al if si falta alguna.
    if columnas_faltantes:
        raise KeyError( #quivalente a throw new Exception(...) en Java
            # KeyError = tipo de error para "no encontré esa clave/columna".
            f"Columnas de texto no encontradas (a normalizar) en el DataFrame: {columnas_faltantes}. "
            f"Columnas disponibles: {list(df.columns)}"
        )

    # ── Aplicar normalización columna por columna ──
    # Equivalente a cada línea del mutate() de R:
    #   columna = iconv(str_to_upper(str_trim(columna)), to = "ASCII//TRANSLIT")
    #
    # `for columna in LISTA:` → repite el bloque de código una vez por cada
    # elemento de la lista. En cada vuelta, la variable `columna` toma el
    # siguiente nombre ("codigo_caso", luego "tipo_delito", etc.).
    for columna in COLUMNAS_TEXTO_NORMALIZAR:
        valores_antes = df[columna].dropna().unique()[:3]  # Muestra para el log
        # df[columna]: Selecciona toda esa columna del DataFrame.
        # .dropna(): Borra temporalmente los valores nulos (NaN o vacíos) para que no molesten
        #.unique(): Saca solo los valores únicos (quita repetidos, ideal para ver patrones rápido).
        # [:3]: Recorta y se queda solo con los primeros 3 ejemplos.
        df[columna] = normalizar_columna(df[columna]) #Internamente hace un map de la columna (tipo serie) aplicando a su vez la funcion individual de normalizacion para cada dato
        # Al asignar con df[columna] = ..., REEMPLAZAMOS la columna vieja por la limpia.
        valores_despues = df[columna].dropna().unique()[:3] #Unicamente para ver el resultado

        # {columna:<25} → escribe el nombre alineado a la izquierda ocupando 25
        #                 espacios, para que la impresión quede en columnas ordenadas.
        print(f"  [OK] {columna:<25} | Antes: {list(valores_antes)}")
        # {'':25} → imprime un texto vacío de 25 espacios (solo para alinear).
        print(f"       {'':25} | Después: {list(valores_despues)}")

    # ── Paso 2.1: Homologar variantes y errores de tipeo en cantones por provincia ──
    # Desambigua casos como ("COTOPAXI", "SAN MIGUEL DE SALCEDO") -> "SALCEDO" vs.
    # ("BOLIVAR", "SAN MIGUEL DE SALCEDO") -> "SAN MIGUEL", y unifica "PUEBLO VIEJO" -> "PUEBLOVIEJO"
    # y "PUERTO FRANCISCO DE ORELLANA" -> "ORELLANA".
    df = homologar_cantones_por_provincia(df)

    print("-" * 60)
    print(f"  Columnas normalizadas: {len(COLUMNAS_TEXTO_NORMALIZAR)}")
    print(f"  Total registros: {len(df):,}")  # {:,} = separador de miles
    print("=" * 60)

    return df  # Devolvemos la tabla con las 13 columnas ya limpias y cantones homologados.


# =========================================================================
# FUNCIONES DE PERSISTENCIA: guardar y cargar el intermedio normalizado
# =========================================================================
# "Persistencia" = guardar los datos en disco para que no se pierdan al
# cerrar el programa, y poder volver a leerlos después.
def guardar_intermedio_normalizado(df: pd.DataFrame) -> None:
    """
    Guarda el DataFrame normalizado en formato Parquet.

    Salida: data/interim/homi_normalizado.parquet

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame con columnas de texto ya normalizadas.
    """
    INTERIM_NORMALIZADO.parent.mkdir(parents=True, exist_ok=True)
    # INTERIM_NORMALIZADO: Es una variable de tipo pathlib.Path, usado para amnejar rutas
    # .parent: Agarra la ruta, es decir, ignora el nombre del archivo final
    # .mkdir(parents=True, exist_ok=True) Crea la ruta en caso de no exisitir

    df.to_parquet(INTERIM_NORMALIZADO, index=False, engine="pyarrow")
    # Coje los datos df y guarda el DataFrame en formato Parquet
    # index=False: Le dice a Pandas que no guarde el índice numérico de las filas
    # engine="pyarrow": Especifica el "motor" o biblioteca que se encargará de traducir y comprimir
    tamanio_kb = INTERIM_NORMALIZADO.stat().st_size / 1024
    # .stat().st_size → tamaño del archivo en bytes; / 1024 → lo pasa a kilobytes.
    print(f"  Guardado intermedio: {INTERIM_NORMALIZADO}")
    print(f"  Tamaño: {tamanio_kb:.1f} KB")  # :.1f → número con 1 decimal


def cargar_intermedio_normalizado() -> pd.DataFrame:
    """
    Carga el archivo Parquet intermedio de datos normalizados.

    Returns
    -------
    pd.DataFrame
        DataFrame previamente normalizado y guardado.

    Raises
    ------
    FileNotFoundError
        Si el archivo intermedio no existe.
    """
    # Si el archivo todavía no existe (no se ha corrido la Fase 2), avisamos con un error claro.
    if not INTERIM_NORMALIZADO.exists():
        raise FileNotFoundError(
            f"No existe el archivo intermedio: {INTERIM_NORMALIZADO}. "
            "Ejecuta primero la Fase 2 (normalizar_todas_columnas + guardar)."
        )
    return pd.read_parquet(INTERIM_NORMALIZADO, engine="pyarrow") #Saco y devuelvo mis datos guardados, en tipo dataframe


# =========================================================================
# EJECUCIÓN DIRECTA (para pruebas rápidas desde terminal)
# =========================================================================
# `__name__` es una variable especial que Python crea automáticamente:
#   - Si ejecutas ESTE archivo directamente (python -m src.limpieza.normalizar_texto),
#     __name__ vale "__main__" → el bloque de abajo SÍ se ejecuta.
#   - Si este archivo es IMPORTADO desde otro (ej. desde main.py),
#     __name__ vale "src.limpieza.normalizar_texto" → el bloque NO se ejecuta.
# Así podemos probar la fase por separado sin afectar al pipeline completo.
if __name__ == "__main__":
    # Permite ejecutar: python -m src.limpieza.normalizar_texto
    print("Cargando datos de Fase 1 (homi_renombrado.parquet)...")

    if not INTERIM_RENOMBRADO.exists():
        raise FileNotFoundError(
            f"No existe {INTERIM_RENOMBRADO}. Ejecuta primero la Fase 1."
        )

    df = pd.read_parquet(INTERIM_RENOMBRADO, engine="pyarrow")  # Lee la salida de la Fase 1
    df = normalizar_todas_columnas(df)                          # Aplica la Fase 2
    guardar_intermedio_normalizado(df)                          # Guarda el resultado
    print("\n[OK] Fase 2 completada exitosamente.")  # "\n" = salto de línea
