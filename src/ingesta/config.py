"""
config.py — Configuración centralizada del proyecto.

Define todas las rutas, constantes y parámetros globales
que los demás módulos importan. Usar pathlib.Path para
garantizar compatibilidad cross-platform.

¿Por qué existe este archivo?
    En lugar de escribir rutas como "D:/Tesis/data/raw/..." repetidas en
    cada archivo, las definimos UNA sola vez aquí. Si mañana movemos la
    carpeta del proyecto, solo cambiamos este archivo y todo sigue funcionando.
    Es el equivalente a las variables `repositorio` y `repositorio_carto`
    del script R original (líneas 27-28).

Convención: en Python, las variables escritas TODO EN MAYÚSCULAS se
consideran "constantes" (valores que no deberían cambiar mientras el
programa corre). Python no lo obliga, pero es un acuerdo entre programadores.
"""
# `from ... import ...` trae solo la herramienta que necesitamos de una librería.
# `pathlib` es una librería estándar de Python (viene incluida, no se instala).
# `Path` es una clase que representa una ruta de archivo o carpeta como un
# OBJETO (no como un simple texto). Ventajas:
#   - Funciona igual en Windows (D:\Tesis) y en Linux/Mac (/home/tesis).
#   - Permite unir rutas con el operador "/" de forma limpia.
#   - Tiene métodos útiles como .exists(), .mkdir(), .parent, .stat(), etc.
from pathlib import Path

# =========================================================================
# RUTAS DEL PROYECTO
# =========================================================================
# Raíz del proyecto (D:\Tesis)
# Define la ruta raíz del proyecto, partiendo de la ubicación del archivo actual 
# y subiendo tres niveles de directorios usando el parent.
#
# Desglose paso a paso:
#   __file__        → variable especial de Python que contiene la ruta de ESTE
#                     archivo: "D:\Tesis\src\ingesta\config.py"
#   Path(__file__)  → convierte ese texto en un objeto Path.
#   .resolve()      → lo transforma en ruta absoluta y completa (sin atajos
#                     como "..", y con la letra de unidad incluida).
#   .parent         → sube UN nivel (la carpeta que contiene al archivo):
#                     1er .parent → D:\Tesis\src\ingesta
#                     2do .parent → D:\Tesis\src
#                     3er .parent → D:\Tesis   ← ¡la raíz del proyecto!
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


# Directorios de datos

# Directorio principal donde se almacenarán los datos del proyecto.
# El operador "/" entre un Path y un texto UNE las rutas:
#   D:\Tesis  /  "data"   →   D:\Tesis\data
DATA_DIR = PROJECT_ROOT / "data"

# Directorio que contiene los datos originales sin modificaciones.
# REGLA DE ORO: lo que está en raw/ NUNCA se modifica, solo se lee.
RAW_DIR = DATA_DIR / "raw"

# Directorio para almacenar datos intermedios durante el procesamiento.
#interim	Almacena datos en etapas intermedias de limpieza y transformación.
# Aquí guardamos un archivo .parquet por cada fase terminada, así podemos
# retomar el trabajo desde cualquier fase sin repetir todo desde cero.
INTERIM_DIR = DATA_DIR / "interim"

# Directorio donde se guardarán los datos limpios y preparados para el análisis.
PROCESSED_DIR = DATA_DIR / "processed"

# Directorio destinado al almacenamiento de archivos cartográficos originales.
# (Los shapefiles del mapa de cantones del Ecuador).
CARTOGRAFIA_DIR = RAW_DIR / "cartografia"

# Directorios para reportes de auditoría y figuras cartográficas (Fase 5).
# Aquí se guardan los resúmenes estadísticos (.json / .md) y los mapas (.png)
# listos para incluir en el documento de tesis.
REPORTS_DIR = PROJECT_ROOT / "reports"
FIGURAS_DIR = REPORTS_DIR / "figuras"

# =========================================================================
# ARCHIVOS FUENTE
# =========================================================================
# Ruta completa al CSV original de homicidios (21 columnas, años 2010-2025).
ARCHIVO_HOMICIDIOS_CSV = RAW_DIR / "base_homi_2010_2025.csv"

# Ruta completa al shapefile (mapa digital) de cantones del Ecuador.
# Un "shapefile" es un formato de mapa que en realidad son varios archivos
# con el mismo nombre (.shp = formas, .dbf = tabla de datos, .prj = proyección,
# .shx = índice). Basta con apuntar al .shp y la librería encuentra los demás.
ARCHIVO_SHAPEFILE_CANTONES = CARTOGRAFIA_DIR / "nxcantones.shp"

# =========================================================================
# PARÁMETROS DEL PIPELINE
# =========================================================================
# Año máximo a incluir en el análisis (excluye 2025 en adelante)
# Se usa en la Fase 3 (filtros.py). Equivale a `filter(anio_hecho <= 2024)` en R.
ANIO_MAXIMO = 2024

# Cantones insulares a excluir del análisis continental
# Es una LISTA (se escribe con corchetes [ ]): una colección ordenada de valores.
# Equivale a c("GALAPAGOS", "ISABELA", "SANTA CRUZ", "SAN CRISTOBAL") en R.
CANTONES_GALAPAGOS = ["GALAPAGOS", "ISABELA", "SANTA CRUZ", "SAN CRISTOBAL"]

# Provincias a excluir del mapa base
# Se usa en la Fase 4 (cartografia.py) para quitar del mapa las zonas que
# no forman parte del análisis continental.
PROVINCIAS_EXCLUIR_MAPA = ["GALAPAGOS", "ZONA NO DELIMITADA"]

# Sistema de referencia de coordenadas objetivo (WGS84)
# Define el sistema de referencia de coordenadas WGS84 (EPSG:4326) 
# para representar ubicaciones geográficas mediante latitud y longitud.
# En palabras simples: es el "idioma" en que se expresan las coordenadas.
# 4326 es el código del sistema que usan los GPS y Google Maps
# (latitud entre -90 y 90, longitud entre -180 y 180).
CRS_OBJETIVO = 4326

# =========================================================================
# MAPEO DE COLUMNAS: nombre_original → nombre_descriptivo
# =========================================================================
# Correspondencia directa con el rename() de la Fase 3 del código R (líneas 53-77)
# Clave valor ***
# Es un DICCIONARIO (se escribe con llaves { }): una colección de pares
# "clave": "valor". Funciona como un traductor:
#   - La CLAVE (izquierda) es el nombre críptico original del CSV ("X2").
#   - El VALOR (derecha) es el nombre descriptivo que queremos ("codigo_caso").
# Para consultar un valor se usa: MAPEO_COLUMNAS["X2"]  →  "codigo_caso"
MAPEO_COLUMNAS = {
    "X2":         "codigo_caso",           # Identificador policial codificado
    "X4":         "tipo_delito",           # Tipificación legal (Homicidio, Asesinato)
    "X33":        "fecha_hecho",           # Fecha exacta (Año-Mes-Día)
    "anio":       "anio_hecho",            # Año de ocurrencia
    "mes":        "mes_hecho",             # Mes del suceso
    "dia":        "dia_semana",            # Día cronológico de la semana
    "rangoh":     "hora_aproximada",       # Hora promedio del evento
    "DPA_DESPRO": "provincia",             # Nombre oficial de la provincia
    "X133":       "canton",                # Nombre oficial del cantón
    "X23":        "zona_tipo",             # Clasificación territorial (Urbano/Rural)
    "X28":        "lugar_especifico",      # Espacio público o privado de la agresión
    "X35":        "tipo_arma",             # Instrumento del deceso
    "X39":        "motivacion_detalle",    # Causa hipotética de la agresión
    "X40":        "causa_especifica",      # Detalle fáctico del móvil
    "X45":        "edad_victima",          # Edad en años de la víctima
    "X47":        "sexo_victima",          # Género biológico
    "X53":        "nacionalidad_victima",  # País de origen
    "X21":        "latitud",               # Coordenada decimal Y (potencialmente corrupta)
    "X22":        "longitud",              # Coordenada decimal X (potencialmente corrupta)
    "X208":       "AUX_HORA_SISTEMA",      # Auditoría horaria interna
    "X209":       "AUX_MINUTO_SISTEMA",    # Auditoría de minutos interna
} 

# Columnas de texto que requieren normalización (Fase 2)
# LISTA **
# Son las 13 columnas a las que se les aplicará: quitar espacios extremos,
# pasar a MAYÚSCULAS y eliminar tildes/eñes (ver src/utils/texto.py).
COLUMNAS_TEXTO_NORMALIZAR = [
    "codigo_caso",
    "tipo_delito",
    "zona_tipo",
    "lugar_especifico",
    "tipo_arma",
    "motivacion_detalle",
    "causa_especifica",
    "sexo_victima",
    "nacionalidad_victima",
    "canton",
    "mes_hecho",
    "dia_semana",
    "provincia",
]
# Los otros datos como fecha_hecho, anio_hecho, hora_aproximada, edad_victima, 
# latitud, longitud, AUX_HORA_SISTEMA y AUX_MINUTO_SISTEMA no se tratan por el momento



# =========================================================================
# ESQUEMA CONSOLIDADO DE 21 COLUMNAS FINALES (Fase 5)
# =========================================================================
# Orden oficial de las 21 columnas limpias según docs/diccionario_datos.md
# y la arquitectura del proyecto (equivale al dplyr::select() de R Fase 13).
#
# Breve guía técnica de los tipos de datos (dtypes) de Pandas usados aquí:
#   • string        → Texto nativo de Pandas (admite valores faltantes `pd.NA` sin mezclarse con números).
#   • category      → Equivalente al `factor` de R. En vez de guardar 38,000 veces el texto
#                     "ECUATORIANA" en memoria, Pandas guarda una tabla pequeña de categorías únicas
#                     y un código numérico interno por fila (reduce drásticamente el peso en RAM y Parquet).
#   • datetime64[ns]→ Tipo temporal nativo con precisión de nanosegundos (permite extraer mes, trimestre,
#                     ordenar cronológicamente e indexar series temporales en la Fase 6).
#   • Int64         → Entero de 64 bits "nulable" (con "I" mayúscula). A diferencia del `int64` clásico,
#                     sí soporta celdas vacías (`pd.NA`) sin forzar toda la columna a decimal.
#   • float64       → Número real de doble precisión (admite decimales en coordenadas, horas y edades).
COLUMNAS_FINALES_21 = [
    "codigo_caso",           # 1.  str/string — Identificador policial codificado
    "tipo_delito",           # 2.  category   — Tipificación legal
    "fecha_hecho",           # 3.  datetime64 — Fecha exacta (YYYY-MM-DD)
    "anio_hecho",            # 4.  Int64      — Año de ocurrencia (2010-2024)
    "mes_hecho",             # 5.  category   — Mes del suceso
    "dia_semana",            # 6.  category   — Día de la semana
    "hora_aproximada",       # 7.  float64    — Hora decimal aproximada del evento
    "provincia",             # 8.  category   — Nombre oficial de la provincia
    "canton",                # 9.  category   — Nombre oficial del cantón
    "zona_tipo",             # 10. category   — Urbano / Rural / SD
    "lugar_especifico",      # 11. category   — Espacio de la agresión
    "tipo_arma",             # 12. category   — Instrumento del deceso
    "motivacion_detalle",    # 13. category   — Causa hipotética
    "causa_especifica",      # 14. category   — Detalle fáctico del móvil
    "edad_victima",          # 15. float64    — Edad en años (admite decimales en lactantes)
    "sexo_victima",          # 16. category   — Género biológico
    "nacionalidad_victima",  # 17. category   — País de origen
    "latitud",               # 18. float64    — Coordenada Y validada/reparada (desde lat_num)
    "longitud",              # 19. float64    — Coordenada X validada/reparada (desde lon_num)
    "AUX_HORA_SISTEMA",      # 20. Int64      — Auditoría horaria interna (0-23)
    "AUX_MINUTO_SISTEMA",    # 21. Int64      — Auditoría de minutos interna (0-59)
]

# Las 12 columnas de texto de "baja cardinalidad" (pocos valores distintos repetidos en miles de filas,
# ej. 24 provincias, 7 días, 12 meses) que se convierten a tipo `category` en la Fase 5.
# NOTA: `codigo_caso` NO se incluye aquí porque casi cada fila tiene un código único (alta cardinalidad).
COLUMNAS_CATEGORICAS_FINALES = [
    "tipo_delito",
    "mes_hecho",
    "dia_semana",
    "provincia",
    "canton",
    "zona_tipo",
    "lugar_especifico",
    "tipo_arma",
    "motivacion_detalle",
    "causa_especifica",
    "sexo_victima",
    "nacionalidad_victima",
]

# Mapeo que homologa las coordenadas numéricas validadas en la Fase 4
# (lat_num / lon_num) hacia los nombres definitivos del diccionario de datos.
# Se pasa a `df.rename(columns=MAPEO_COORDENADAS_FINALES)` en el Paso 5.1.
MAPEO_COORDENADAS_FINALES = {
    "lat_num": "latitud",
    "lon_num": "longitud",
}

# =========================================================================
# ARCHIVOS DE SALIDA INTERMEDIA
# =========================================================================
# Cada fase guarda su resultado en un archivo .parquet dentro de data/interim/.
# Parquet es un formato binario, comprimido y que respeta los tipos de datos
# (reemplaza al .rds de R). Es mucho más rápido de leer que un CSV.
INTERIM_RENOMBRADO = INTERIM_DIR / "homi_renombrado.parquet"                  # Salida Fase 1 (ingesta)
INTERIM_NORMALIZADO = INTERIM_DIR / "homi_normalizado.parquet"                # Salida Fase 2 (texto limpio)
INTERIM_FILTRADO = INTERIM_DIR / "homi_filtrado_2024.parquet"                 # Salida Fase 3 (continental <=2024)
INTERIM_INSULAR_EXCLUIDO = INTERIM_DIR / "homi_insular_excluido.parquet"      # Trazabilidad Fase 3 (Galápagos)
INTERIM_GEO_CORRECTOS = INTERIM_DIR / "geo_correctos.parquet"                 # Salida Fase 4 (1ra auditoría sjoin)
PROCESSED_GEORREFERENCIADO = PROCESSED_DIR / "homi_georreferenciado.parquet"  # Salida Fase 4 (ensamble completo)

# =========================================================================
# ARCHIVOS DE SALIDA FINAL (Fase 5)
# =========================================================================
# Archivos definitivos que se generarán en la Fase 5 (exportación final):
#   1. CSV UTF-8    → texto plano separado por comas para Excel, R o cualquier software externo.
#   2. Parquet      → formato columnar binario con tipos preservados para Python (Fase 6).
#   3. GeoPackage   → contenedor espacial SQLite estándar OGC en un solo archivo `.gpkg`
#                     (reemplaza al `.shp` antiguo evitando truncar nombres de columnas a 10 letras).
SALIDA_CSV_FINAL = PROCESSED_DIR / "homi_Final_Continental_Etiquetado.csv"
SALIDA_PARQUET_FINAL = PROCESSED_DIR / "homi_final.parquet"
SALIDA_GPKG_FINAL = PROCESSED_DIR / "homi_final.gpkg"

# Reportes estructurados y visualizaciones diagnósticas (Pasos 5.5 y 5.6):
#   • .json → datos estructurados clave-valor legibles por código o dashboards.
#   • .md   → tabla ejecutiva en formato Markdown lista para copiar/anexar a la tesis.
#   • .png  → mapa diagnóstico renderizado a 300 DPI (calidad de impresión editorial).
SALIDA_AUDITORIA_JSON = REPORTS_DIR / "auditoria_pipeline.json"
SALIDA_AUDITORIA_MD = REPORTS_DIR / "auditoria_pipeline.md"
SALIDA_MAPA_DIAGNOSTICO = FIGURAS_DIR / "mapa_diagnostico_continental.png"
