# Diccionario de Datos — Homicidios Ecuador (2010-2024)

## Columnas del Dataset Final

| # | Variable | Tipo | Descripción | Columna Original (R) |
|---|----------|------|-------------|----------------------|
| 1 | `codigo_caso` | `str` | Identificador policial codificado del crimen | `X2` |
| 2 | `tipo_delito` | `str` | Tipificación legal: Homicidio, Asesinato, etc. | `X4` |
| 3 | `fecha_hecho` | `datetime` | Fecha exacta del incidente (YYYY-MM-DD) | `X33` |
| 4 | `anio_hecho` | `int` | Año de ocurrencia (2010-2024) | `anio` |
| 5 | `mes_hecho` | `str` | Mes del suceso en palabras | `mes` |
| 6 | `dia_semana` | `str` | Día de la semana del evento | `dia` |
| 7 | `hora_aproximada` | `str` | Franja horaria del evento | `rangoh` |
| 8 | `provincia` | `str` | Nombre oficial de la provincia | `DPA_DESPRO` |
| 9 | `canton` | `str` | Nombre oficial del cantón | `X133` |
| 10 | `zona_tipo` | `str` | Urbano o Rural | `X23` |
| 11 | `lugar_especifico` | `str` | Espacio de la agresión (Vía Pública, etc.) | `X28` |
| 12 | `tipo_arma` | `str` | Arma de Fuego, Arma Blanca, etc. | `X35` |
| 13 | `motivacion_detalle` | `str` | Causa hipotética de la agresión | `X39` |
| 14 | `causa_especifica` | `str` | Detalle del móvil: Riñas, Robo, etc. | `X40` |
| 15 | `edad_victima` | `float` | Edad en años de la víctima | `X45` |
| 16 | `sexo_victima` | `str` | Género biológico registrado | `X47` |
| 17 | `nacionalidad_victima` | `str` | País de origen documentado | `X53` |
| 18 | `latitud` | `float64` | Coordenada Y (validada/reparada) | `X21` → `lat.new` |
| 19 | `longitud` | `float64` | Coordenada X (validada/reparada) | `X22` → `lon.new` |
| 20 | `AUX_HORA_SISTEMA` | `str` | Campo de auditoría horaria | `X208` |
| 21 | `AUX_MINUTO_SISTEMA` | `str` | Campo de auditoría de minutos | `X209` |

## Transformaciones Aplicadas

1. **Normalización textual**: `strip()` + `upper()` + eliminación de tildes
2. **Filtro temporal**: Solo registros con `anio_hecho ≤ 2024`
3. **Filtro geográfico**: Ecuador continental (sin Galápagos)
4. **Validación geoespacial**: Point-in-polygon contra shapefile cantonal
5. **Reparación de coordenadas**: Reconstrucción decimal para datos corruptos

## Valores Categóricos Esperados

- **zona_tipo**: URBANO, RURAL
- **sexo_victima**: MASCULINO, FEMENINO
- **tipo_delito**: HOMICIDIO, ASESINATO, SICARIATO, FEMICIDIO, etc.

