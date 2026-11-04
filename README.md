# Preprocesamiento de Datos de Homicidios — Ecuador (2010-2024)

## Descripción

Pipeline de preprocesamiento de datos de homicidios para Ecuador continental,
migrado desde R (En colavoración con los docentes) a Python 3.13. Incluye limpieza textual, numerica, validación geoespacial,
reparación de coordenadas corruptas y exportación de datos limpios para modelos
de series temporales.

## Requisitos

- Python 3.13 (usar `py -3.13` en Windows)
- Entorno virtual (`.venv`)
- Dependencias: ver `requirements.txt`

## Instalación

```powershell
# Crear entorno virtual
py -3.13 -m venv .venv

# Activar
.\.venv\Scripts\Activate.ps1

# Instalar dependencias
python -m pip install -r requirements.txt
```

## Uso

```powershell
# Activar el entorno virtual (si no está activo)
.\.venv\Scripts\Activate.ps1

# Ejecutar el pipeline completo
python main.py
```

## Estructura del Proyecto

```
D:\Tesis\
├── data/
│   ├── raw/                  # Datos BRUTOS originales (inmutables)
│   │   ├── base_homi_2010_2025.csv
│   │   └── cartografia/      # Shapefiles cantonales
│   ├── interim/              # Datos intermedios (Parquet)
│   └── processed/            # Datos FINALES listos para análisis
├── src/
│   ├── ingesta/              # Carga y configuración
│   ├── limpieza/             # Normalización textual y filtros
│   ├── validacion_geo/       # Pipeline geoespacial completo
│   ├── exportacion/          # Salida CSV, Parquet, GeoPackage
│   ├── reportes/             # Auditorías y visualización
│   └── utils/                # Funciones reutilizables
├── notebooks/                # Jupyter para exploración
├── tests/                    # Pruebas automatizadas
├── R_legacy/                 # Código R original (referencia)
├── main.py                   # Orquestador del pipeline
├── requirements.txt          # Dependencias Python
└── README.md                 # Este archivo
```

## Fases del Pipeline

| Fase | Descripción | Estado |
|------|-------------|--------|
| 1. Revicion de datos y Renombrado | Lectura CSV + renombrado 21 columnas | ✅ |
| 2. Limpieza Textual | Mayúsculas, tildes, espacios | ⬜ |
| 3. Filtrado | Año ≤2024, sin Galápagos | ⬜ |
| 4. Validación Geoespacial | Point-in-polygon + reparación coords | ⬜ |
| 5. Exportación Final | CSV, Parquet, GeoPackage | ⬜ |
| 6. Series Temporales | Agregación, modelado (futuro) | ⬜ |

## Origen de Datos

- **Fuente**: Base de datos proporcinadas por el docente de homicidios en Ecuador
- **Periodo**: 2010-2025 (filtrado a 2024 para análisis)
- **Formato original**: RDS/CSV con 21 columnas codificadas
- **Registros**: ~40,000 casos de homicidios en Ecuador

