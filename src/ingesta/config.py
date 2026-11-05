"""
config.py — Configuración centralizada del proyecto.

Define todas las rutas, constantes y parámetros globales
que los demás módulos importan. Usar pathlib.Path para
garantizar compatibilidad cross-platform.
"""
from pathlib import Path

# =========================================================================
# RUTAS DEL PROYECTO
# =========================================================================
# Raíz del proyecto (D:\Tesis)
# Define la ruta raíz del proyecto, partiendo de la ubicación del archivo actual 
# y subiendo tres niveles de directorios usando el parent.
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


# Directorios de datos

# Directorio principal donde se almacenarán los datos del proyecto.
DATA_DIR = PROJECT_ROOT / "data"

# Directorio que contiene los datos originales sin modificaciones.
RAW_DIR = DATA_DIR / "raw"

# Directorio para almacenar datos intermedios durante el procesamiento.
#interim	Almacena datos en etapas intermedias de limpieza y transformación.
INTERIM_DIR = DATA_DIR / "interim"

# Directorio donde se guardarán los datos limpios y preparados para el análisis.
PROCESSED_DIR = DATA_DIR / "processed"

# Directorio destinado al almacenamiento de archivos cartográficos originales.
CARTOGRAFIA_DIR = RAW_DIR / "cartografia"

# =========================================================================
# ARCHIVOS FUENTE
# =========================================================================
ARCHIVO_HOMICIDIOS_CSV = RAW_DIR / "base_homi_2010_2025.csv"
ARCHIVO_SHAPEFILE_CANTONES = CARTOGRAFIA_DIR / "nxcantones.shp"

# =========================================================================
# PARÁMETROS DEL PIPELINE
# =========================================================================
# Año máximo a incluir en el análisis (excluye 2025 en adelante)
ANIO_MAXIMO = 2024

# Cantones insulares a excluir del análisis continental
CANTONES_GALAPAGOS = ["GALAPAGOS", "ISABELA", "SANTA CRUZ", "SAN CRISTOBAL"]

# Provincias a excluir del mapa base
PROVINCIAS_EXCLUIR_MAPA = ["GALAPAGOS", "ZONA NO DELIMITADA"]

# Sistema de referencia de coordenadas objetivo (WGS84)
# Define el sistema de referencia de coordenadas WGS84 (EPSG:4326) 
# para representar ubicaciones geográficas mediante latitud y longitud.
CRS_OBJETIVO = 4326

# =========================================================================
# MAPEO DE COLUMNAS: nombre_original → nombre_descriptivo
# =========================================================================
# Correspondencia directa con el rename() de la Fase 3 del código R (líneas 53-77)
# Clave valor ***
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

# =========================================================================
# ARCHIVOS DE SALIDA INTERMEDIA
# =========================================================================
INTERIM_RENOMBRADO = INTERIM_DIR / "homi_renombrado.parquet"
INTERIM_NORMALIZADO = INTERIM_DIR / "homi_normalizado.parquet"
INTERIM_FILTRADO = INTERIM_DIR / "homi_filtrado_2024.parquet"
INTERIM_GEO_CORRECTOS = INTERIM_DIR / "geo_correctos.parquet"

# =========================================================================
# ARCHIVOS DE SALIDA FINAL
# =========================================================================
SALIDA_CSV_FINAL = PROCESSED_DIR / "homi_Final_Continental_Etiquetado.csv"
SALIDA_PARQUET_FINAL = PROCESSED_DIR / "homi_Final_Continental_Etiquetado.parquet"
SALIDA_GPKG_FINAL = PROCESSED_DIR / "homi_final.gpkg"

