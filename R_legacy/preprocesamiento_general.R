# =========================================================================
# LIMPIEZA DEL ENTORNO DE TRABAJO
# =========================================================================
# rm() elimina objetos de la memoria RAM. ls() lista todo lo que está guardado en el entorno.
# Juntos, garantizan que el código corra desde cero sin arrastrar datos basura de análisis previos.
rm(list = ls()) #Ctrl + Shift + F10 es mas completo

# =========================================================================
# FASE 1: ENTORNO Y LIBRERÍAS
# =========================================================================
## Cargando paquetes necesarios
# library() carga extensiones de R que contienen funciones prefabricadas.
library(tidyverse) # tidyverse es una colección de paquetes diseñados bajo una misma filosofía llamada tidy data (datos limpios/ordenados)
                    # 1. Cada variable está en una columna. 2. Cada observación está en una fila. 3. Cada valor está en su propia celda.
library(lubridate) # Especializado en manipular fechas (años, meses, días). Entendiedolos como textos ej. "2026-05-05"
library(sf)        # (Simple Features) La librería geoespacial estándar; para representar datos con coordenadas o mapas.
library(sp)        # (Spatial) Librería geoespacial clásica; se mantiene por compatibilidad con formatos de coordenadas antiguos.



# =========================================================================
# FASE 2: CONFIGURACIÓN PARÁMETROS INICIALES
# =========================================================================
## Rutas de directorios
# Creamos variables de texto que almacenan las rutas de las carpetas en tu disco duro (D:) 
# para no tener que escribir toda la ruta cada vez que abramos un archivo.
repositorio <- "D:/R/preprocesamiento_datos_limpio/preprocesamiento_datos/datos_homicidios/HOMICIDIOS-2025" 
repositorio_carto <- "D:/R/preprocesamiento_datos_limpio/preprocesamiento_datos/datos_homicidios/HOMICIDIOS-2025/Provincias_Cantones_Parroquias" 


## Fijar directorio principal
# setwd() le dice a R cuál es tu carpeta de trabajo por defecto. Toda lectura o guardado de archivos 
# se hará en esta ruta a menos que se especifique lo contrario.
setwd(repositorio) 

## Nombres de archivos
nombre_archibo_original_rds <- "base_homi_2010_2025_original.rds"




# =========================================================================
# FASE 3: CARGA, REETIQUETADO Y PREPROCESAMIENTO DE LOS DATOS DE HOMICIDIOS
# =========================================================================
## Lectura del archivo maestro de datos
dir() #Verifico que se listen los archibos en la ruta WD
# readRDS() lee un archivo binario nativo de R. Es extremadamente veloz y mantiene los formatos originales 
# de las columnas (números, fechas, textos) sin alterarlos.
homi_2010_2025_raw <- readRDS(nombre_archibo_original_rds)

# Usamos rename() para darle un nombre descriptivo a cada columna según la guía.
# Sintaxis: nuevo_nombre = nombre_original
homi_2010_2025 <- homi_2010_2025_raw %>% 
  rename(
    codigo_caso          = X2,          # Identificador policial codificado
    tipo_delito          = X4,          # Tipificación legal (ej: Homicidio, Asesinato)
    fecha_hecho          = X33,         # Fecha exacta en formato Año-Mes-Día
    anio_hecho           = anio,        # Año de ocurrencia
    mes_hecho            = mes,         # Mes del suceso
    dia_semana           = dia,         # Día cronológico de la semana
    hora_aproximada      = rangoh,      # Hora promedio del evento
    provincia            = DPA_DESPRO,  # Nombre oficial de la provincia
    canton               = X133,        # Nombre oficial del cantón
    zona_tipo            = X23,         # Clasificación territorial (Urbano o Rural)
    lugar_especifico     = X28,         # Espacio público o privado de la agresión
    tipo_arma            = X35,         # Instrumento del deceso
    motivacion_detalle   = X39,         # Causa hipotética de la agresión
    causa_especifica     = X40,         # Detalle fáctico del móvil
    edad_victima         = X45,         # Edad en años de la víctima
    sexo_victima         = X47,         # Género biológico
    nacionalidad_victima = X53,         # País de origen
    latitud              = X21,         # Coordenada decimal Y corregida
    longitud             = X22,         # Coordenada decimal X corregida
    #id_auditoria         = ID.temp,     # ID de control de auditoría
    AUX_HORA_SISTEMA     = X208,        # Auditoría horaria interna
    AUX_MINUTO_SISTEMA   = X209         # Auditoría de minutos interna
  )



## Normalización del texto e indexación del Cantón
# Tomamos la base original y usamos el operador pipe ( %>% ) para pasar los datos secuencialmente por varios pasos.
homi_2010_2025 <- homi_2010_2025 %>% 
  mutate(
    # mutate() modifica columnas.
    # str_trim() remueve espacios fantasmas al inicio o final (ej: " QUITO  " -> "QUITO").
    # str_to_upper() pasa todo a MAYÚSCULAS homogéneas.
    
    # iconv() con "ASCII//TRANSLIT" convierte caracteres especiales. Remueve tildes y eñes (ej: "Guayaquíl" -> "GUAYAQUIL").
    # Gráficamente: Esto es vital para que al cruzar los datos de texto con el mapa, coincidan letra por letra.
    
    # Limpieza de Código de Caso
    codigo_caso          = iconv(str_to_upper(str_trim(codigo_caso)), to = "ASCII//TRANSLIT"),
    
    # Limpieza de Tipo de Delito
    tipo_delito          = iconv(str_to_upper(str_trim(tipo_delito)), to = "ASCII//TRANSLIT"),
    
    # Limpieza de Zona Tipo
    zona_tipo            = iconv(str_to_upper(str_trim(zona_tipo)), to = "ASCII//TRANSLIT"),
    
    # Limpieza de Lugar Específico
    lugar_especifico     = iconv(str_to_upper(str_trim(lugar_especifico)), to = "ASCII//TRANSLIT"),
    
    # Limpieza de Tipo de Arma
    tipo_arma            = iconv(str_to_upper(str_trim(tipo_arma)), to = "ASCII//TRANSLIT"),
    
    # Limpieza de Motivación Detalle
    motivacion_detalle   = iconv(str_to_upper(str_trim(motivacion_detalle)), to = "ASCII//TRANSLIT"),
    
    # Limpieza de Causa Específica
    causa_especifica     = iconv(str_to_upper(str_trim(causa_especifica)), to = "ASCII//TRANSLIT"),
    
    # Limpieza de Sexo de la Víctima
    sexo_victima         = iconv(str_to_upper(str_trim(sexo_victima)), to = "ASCII//TRANSLIT"),
    
    # Limpieza de Nacionalidad de la Víctima
    nacionalidad_victima = iconv(str_to_upper(str_trim(nacionalidad_victima)), to = "ASCII//TRANSLIT"),
    
    # Limpieza de Cantón
    canton               = iconv(str_to_upper(str_trim(canton)), to = "ASCII//TRANSLIT"),
    
    # Limpieza de Mes del Hecho
    mes_hecho            = iconv(str_to_upper(str_trim(mes_hecho)), to = "ASCII//TRANSLIT"),
    
    # Limpieza de Día de la Semana
    dia_semana           = iconv(str_to_upper(str_trim(dia_semana)), to = "ASCII//TRANSLIT"),
    
    # Limpieza de Provincia
    provincia            = iconv(str_to_upper(str_trim(provincia)), to = "ASCII//TRANSLIT")
  )

## Exclusión estricta de registros temporales (Filtro Año <= 2024)
homi_2010_2024 <- homi_2010_2025 %>% 
  # as.numeric() transforma el año a formato numérico puro para poder hacer comparaciones matemáticas.
  mutate(anio_hecho = as.numeric(anio_hecho)) %>% 
  # filter() conserva únicamente las filas con años menores o iguales a 2024 (descarta 2025).
  filter(anio_hecho <= 2024) %>% 
  # drop_na() elimina registros en caso de que existan valores vacíos (NA) en el año.
  drop_na(anio_hecho)


## FILTRO CRÍTICO: Exclusión simétrica de la Región Insular (Galápagos)
# El operador ! junto con %in% significa: "Fíltra y quédate con todo lo que NO pertenezca a este listado".
# Gráficamente: El mapa de Ecuador continental es compacto, pero Galápagos está muy alejado en el Pacífico.
# Si dejas puntos en Galápagos, al hacer el mapa final, la escala se estirará tanto que el continente se verá diminuto.
homi_2010_2024_continental <- homi_2010_2024 %>%
  filter(!canton %in% c("GALAPAGOS", "ISABELA", "SANTA CRUZ", "SAN CRISTOBAL"))

homi_2010_2024_insular <- homi_2010_2024 %>%
  filter(canton %in% c("GALAPAGOS", "ISABELA", "SANTA CRUZ", "SAN CRISTOBAL"))

# =========================================================================
# AUDITORÍA DE CARACTERES ESPECIALES (TILDES Y EÑES OCULTAS)
# =========================================================================
print("--- BUSCANDO TILDES, EÑES O CARACTERES ESPECIALES ---")

# Patrón Regex para capturar eñes (mayúsculas/minúsculas) y cualquier letra con tilde o diéresis
patron_especial <- "[áéíóúÁÉÍÓÚñÑüÜ]"

# Identificar cuáles columnas son de tipo texto (character)
columnas_texto <- names(homi_2010_2024)[sapply(homi_2010_2024, is.character)]
hallazgos <- FALSE

# Bucle para revisar columna por columna
for (col in columnas_texto) {
  # Buscamos las filas que cumplan con el patrón especial
  filas_con_problemas <- which(grepl(patron_especial, homi_2010_2024[[col]]))
  
  if (length(filas_con_problemas) > 0) {
    hallazgos <- TRUE
    print(paste0("⚠️ Columna encontrada: '", col, "'"))
    
    # Mostramos los primeros 5 registros con problemas en esa columna
    for (fila in head(filas_con_problemas, 5)) {
      print(paste0("   - Fila [", fila, "]: '", homi_2010_2024[[col]][fila], "'"))
    }
    if (length(filas_con_problemas) > 5) {
      print(paste0("   ... y ", length(filas_con_problemas) - 5, " registros más en esta columna."))
    }
    print("------------------------------------------------")
  }
}

if (!hallazgos) {
  print("¡Felicidades! 🎉 No se encontraron eñes ni tildes ocultas en las columnas de texto.")
}


# =========================================================================
# FASE 4: AUDITORÍA DE CONTROL - CONTEOS INICIALES
# =========================================================================
## Diagnóstico por consola del volumen de registros
# print() escribe mensajes en la consola. paste() une textos y cálculos en una sola línea legible.
# nrow() cuenta la cantidad de filas (registros de homicidios) que tiene el dataframe en ese instante.
print("--- CONTEO TOTAL DE REGISTROS ---")
print(paste("Datos originales cargados (con 2025):", nrow(homi_2010_2025)))
print(paste("Datos procesados actuales (SOLO Continental hasta 2024):", nrow(homi_2010_2024)))
print(paste("Registros excluidos (2025 + Galápagos):", nrow(homi_2010_2025) - nrow(homi_2010_2024)))

print("--- VALORES ÚNICOS PROCESADOS (CANTONES) ---")
# unique() analiza la columna y extrae una lista sin repetidos de los cantones presentes.
# head(..., 20) nos muestra los primeros 20 cantones en la consola para revisar visualmente que no tengan tildes ni errores.
print(head(unique(homi_2010_2024$CANTON_HECHO), 150))

# =========================================================================
# FASE 5: PREPARACIÓN CARTOGRÁFICA DEL MAPA BASE
# =========================================================================
## Cambio temporal al repositorio de mapas
# Cambiamos de carpeta de trabajo temporalmente para leer los archivos de cartografía.
setwd(repositorio_carto)

## Carga del archivo Shapefile cantonal
# read_sf() lee el archivo "nxcantones.shp" (el mapa) y lo carga como un objeto espacial con geometrías de polígonos.
Provincia <- read_sf("nxcantones.shp")
# st_transform() proyecta las coordenadas del mapa. El CRS 4326 corresponde a WGS84 (coordenadas geográficas estándar 
# basadas en Latitud y Longitud, usadas por los GPS mundiales).
Provincia <- st_transform(Provincia, crs = 4326) 

## Reparar geometrías inválidas (vértices duplicados, auto-intersecciones)
# st_make_valid() corrige internamente los polígonos del mapa que tengan líneas cruzadas o nodos duplicados.
# Gráficamente: "Sana" los bordes de los cantones en el mapa digital para que los algoritmos de colisión geométrica no fallen.
Provincia <- st_make_valid(Provincia)

## Homologación del texto en la cartografía del mapa
Provincia <- Provincia %>% 
  # Creamos una columna estandarizada en el mapa (CANTON_MAPA) limpiando la columna original del mapa (DPA_DESCAN).
  mutate(CANTON_MAPA = iconv(str_to_upper(str_trim(DPA_DESCAN)), to = "ASCII//TRANSLIT")) %>% 
  # Removemos Galápagos y zonas no delimitadas del mapa base para alinearlo perfectamente con nuestra base de datos.
  filter(DPA_DESPRO != "GALAPAGOS", DPA_DESPRO != "ZONA NO DELIMITADA")

# =========================================================================
# FASE 6: CONVERSIÓN ESPACIAL DE PUNTOS ORIGINALES
# =========================================================================
## Depuración primaria de registros sin coordenadas numéricas
homi_2010_2024_fin <- homi_2010_2024 %>%
  # Forzamos las columnas crudas de texto "X21" y "X22" a convertirse en números decimales puros (Latitud y Longitud).
  mutate(
    lat.new = as.numeric(X21),
    lon.new = as.numeric(X22)
  ) %>% 
  # !is.na() significa "que NO sea un valor nulo/vacío". Eliminamos registros sin coordenadas porque es imposible mapearlos.
  filter(!is.na(lat.new) & !is.na(lon.new))

## Creación de un Identificador Único Temporal de Control
# Generamos una secuencia numérica del 1 hasta el total de filas. Esto le da una "cédula de identidad" única 
# e irrepetible a cada fila de homicidio para rastrearla a lo largo de los algoritmos de validación espacial.
homi_2010_2024_fin$ID.temp <- 1:nrow(homi_2010_2024_fin)

## Estructuración geométrica vectorial del dataset de homicidios
# data.frame() crea una tabla simple únicamente con los componentes del eje Y (Latitud) y eje X (Longitud).
point_analisis <- data.frame(
  y = homi_2010_2024_fin$lat.new,
  x = homi_2010_2024_fin$lon.new
)
# st_as_sf() transforma la tabla simple de coordenadas en un objeto puramente geográfico (SF).
# coords = c("x", "y") define los ejes, y crs = st_crs(Provincia) le hereda el mismo sistema de proyección del mapa de cantones.
# Gráficamente: Transforma números planos en "puntos flotantes espaciales" listos para interactuar con los polígonos del mapa.
point_analisis <- st_as_sf(point_analisis, coords = c("x", "y"), crs = st_crs(Provincia)) 
# Le inyectamos el ID de control al objeto geográfico para saber a qué delito le pertenece cada punto en el espacio.
point_analisis$ID.temp <- homi_2010_2024_fin$ID.temp

# =========================================================================
# FASE 7: PRIMERA AUDITORÍA TOPOLÓGICA (PERTENENCIA POLIGONAL)
# =========================================================================
## Indexación de cantones únicos para optimizar el bucle iterativo
cantones.puntos <- unique(homi_2010_2024_fin$CANTON_HECHO) 
correctos <- c() # Inicializamos un vector vacío que actuará como una "canasta" para guardar los ID de los casos que pasen la prueba.

## Bucle de intersección espacial Cantón por Cantón
# for() ejecutará un ciclo repetitivo desde el primer cantón hasta el último (longitud del vector).
for(j in 1:length(cantones.puntos)) {
  # Filtramos los homicidios que de forma escrita dicen pertenecer al cantón actual de la iteración.
  base.canton <- homi_2010_2024_fin %>% filter(CANTON_HECHO == cantones.puntos[j])
  # Filtramos el polígono geométrico (el dibujo en el mapa) que corresponde al mismo cantón.
  poligono.canton <- Provincia %>% filter(CANTON_MAPA == cantones.puntos[j])
  
  # Si existen tanto el polígono en el mapa como registros en la base de datos de texto, entramos a evaluar:
  if(nrow(poligono.canton) > 0 & nrow(base.canton) > 0) {
    # Extraemos los puntos geográficos de esos casos específicos usando sus IDs de control.
    puntos.evaluar <- point_analisis %>% filter(ID.temp %in% base.canton$ID.temp)
    # st_intersects() evalúa colisiones espaciales. Retorna una matriz lógica (TRUE/FALSE) indicando si el punto cae dentro del polígono.
    aux.dentro.polig <- st_intersects(puntos.evaluar, poligono.canton, sparse = FALSE)
    # apply(..., 1, any) revisa fila por fila de la matriz y detecta los puntos que dieron TRUE (que están dentro del polígono).
    dentro.polig <- puntos.evaluar[apply(aux.dentro.polig, 1, any), ]
    # c() concatena (acumula) los IDs de los registros correctos dentro de nuestra canasta de control.
    correctos <- c(correctos, dentro.polig$ID.temp)
  }
}

## Subdivisión: Dataset de Coordenadas Perfectas de Origen
# Filtramos la base original quedándonos solo con los casos cuyos IDs demostraron caer dentro de su cantón real.
geo_correctos <- homi_2010_2024_fin %>% filter(ID.temp %in% correctos)
# Calculamos el porcentaje de efectividad de digitación inicial de la base de datos dividiendo los correctos para el total.
print(paste0("Calidad de data inicial perfecta: ", round(nrow(geo_correctos)/nrow(homi_2010_2024_fin), 4)*100, "%"))

## Subdivisión: Dataset del Limbo de Revisión Extrema
# Filtramos la base original con el operador !, obteniendo los registros con coordenadas corruptas o inconsistentes.
geo.corregir.master <- homi_2010_2024_fin %>% filter(!(ID.temp %in% correctos))

# =========================================================================
# FASE 8: ALGORITMO TEXTUAL REPARADOR DE DÍGITOS DECIMALES
# =========================================================================
## Desactivación de S2 para mitigar conflictos geométricos de topología esférica
# sf_use_s2(FALSE) le ordena a R apagar el motor geométrico global de Google (S2) que asume que la Tierra es una esfera perfecta.
# Al apagarlo, R calcula las intersecciones sobre un plano cartesiano plano bidimensional regular, evitando errores matemáticos severos.
sf_use_s2(FALSE) 

## PROTECCIÓN ESPACIAL: Separación de registros según formato de cadena
# grepl() busca patrones de texto. Buscamos un punto decimal "\\." en la columna de latitud.
# Si tiene punto, es un registro con formato digital normal (pero que cayó fuera del cantón por desborde de fronteras políticas).
limbo_formato_correcto <- geo.corregir.master %>% filter(grepl("\\.", as.character(lat.new)))
# Si NO tiene punto decimal, es un registro corrupto grave (ej: un número entero continuo como "-214589" en lugar de "-2.14589").
geo.corregir.1 <- geo.corregir.master %>% filter(!grepl("\\.", as.character(lat.new)))

## Limpieza e inicialización de cadenas numéricas corruptas
if(nrow(geo.corregir.1) > 0) {
  geo.corregir.1 <- geo.corregir.1 %>% 
    mutate(
      # gsub() busca un carácter y lo destruye o reemplaza. Aquí eliminamos todos los puntos viejos y signos menos de la cadena de texto
      # para dejar una tira limpia de números puros sobre la cual operar matemáticamente mediante reconstrucción posicional.
      limpia.lat = gsub("\\.", "", as.character(lat.new)),
      limpia.lat = gsub("-", "", limpia.lat),
      limpia.lat = as.numeric(limpia.lat)
    )
}

## Definición de contenedores para la reclasificación por iteración
# Creamos variables vacías para almacenar los homicidios que vayamos rescatando según el tipo de reparación decimal que requieran.
correctos3 <- c()
geo.corregir.1a <- data.frame()
geo.corregir.1b <- data.frame()
geo.corregir.1f <- data.frame()
geo.corregir.1g <- data.frame()

## Bucle de reestructuración matemática de posiciones de caracteres
if(nrow(geo.corregir.1) > 0) {
  # Este bucle simula escenarios de errores comunes de digitación (falta de puntos o signos en zonas específicas del Ecuador)
  for(i in 1:10) {
    
    ### Escenario de reconstrucción decimal 1: Formato "X.XXXXXX" (Positivo)
    # Reconstruye el número asumiendo coordenadas al norte de la Línea Equinoccial (Ecuador Septentrional positivo).
    if(i == 1) {
      geo.corregir.1 <- geo.corregir.1 %>% mutate(
        lat.1 = str_sub(limpia.lat, 1, 1), # Extrae el primer dígito numérico.
        lat.leng = str_length(limpia.lat),  # Mide cuántos caracteres de longitud tiene la cadena limpia.
        lat.2 = str_sub(limpia.lat, 2, lat.leng), # Extrae todo el bloque numérico restante desde la posición 2.
        lat.final = paste0(lat.1, ".", lat.2) # Inserta artificialmente un punto decimal en medio de ambos bloques de texto.
      )
      # Reconstruimos la tabla espacial efímera con el nuevo eje Y reparado textualmente y el eje X original.
      point_analisis_c1 <- data.frame(y = as.numeric(geo.corregir.1$lat.final), x = geo.corregir.1$lon.new)   
      if(nrow(point_analisis_c1) > 0) {
        point_analisis_c1 <- st_as_sf(point_analisis_c1, coords = c("x", "y"), crs = st_crs(Provincia))  
        point_analisis_c1$ID.temp <- geo.corregir.1$ID.temp
        cantones.c1 <- unique(geo.corregir.1$CANTON_HECHO)
        
        # Volvemos a probar con st_intersects si esta reparación matemática hizo que el punto aterrice dentro de su cantón.
        for(j in 1:length(cantones.c1)) {
          base.c1 <- geo.corregir.1 %>% filter(CANTON_HECHO == cantones.c1[j])
          poly.c1 <- Provincia %>% filter(CANTON_MAPA == cantones.c1[j])
          if(nrow(poly.c1) > 0 & nrow(base.c1) > 0) {
            pts.eval <- point_analisis_c1 %>% filter(ID.temp %in% base.c1$ID.temp)
            dentro <- pts.eval[apply(st_intersects(pts.eval, poly.c1, sparse = FALSE), 1, any), ]
            correctos3 <- c(correctos3, dentro$ID.temp)
          }
        }
        # Los casos rescatados por este escenario se guardan en "geo.corregir.1a".
        geo.corregir.1a <- geo.corregir.1 %>% filter(ID.temp %in% correctos3)
        # Los casos que siguen fallando se quedan en "geo.corregir.1" para ser evaluados en el siguiente escenario.
        geo.corregir.1 <- geo.corregir.1 %>% filter(!(ID.temp %in% correctos3))
      }
    }
    
    ### Escenario de reconstrucción decimal 2: Formato "0.XXXXXX" (Positivo)
    # Diseñado para coordenadas extremadamente pegadas al norte de la Línea Equinoccial que inician con cero absoluto.
    if(i == 2) {
      geo.corregir.1 <- geo.corregir.1 %>% mutate(
        lat.1 = str_sub(limpia.lat, 1, 1),
        lat.leng = str_length(limpia.lat),
        lat.2 = str_sub(limpia.lat, 2, lat.leng),
        lat.final = paste0(0, ".", lat.1, lat.2) # Fuerza la inserción de un prefijo estricto "0."
      )
      point_analisis_c2 <- data.frame(y = as.numeric(geo.corregir.1$lat.final), x = geo.corregir.1$lon.new)   
      if(nrow(point_analisis_c2) > 0) {
        point_analisis_c2 <- st_as_sf(point_analisis_c2, coords = c("x", "y"), crs = st_crs(Provincia))  
        point_analisis_c2$ID.temp <- geo.corregir.1$ID.temp
        cantones.c2 <- unique(geo.corregir.1$CANTON_HECHO)
        for(j in 1:length(cantones.c2)) {
          base.c2 <- geo.corregir.1 %>% filter(CANTON_HECHO == cantones.c2[j])
          poly.c2 <- Provincia %>% filter(CANTON_MAPA == cantones.c2[j])
          if(nrow(poly.c2) > 0 & nrow(base.c2) > 0) {
            pts.eval <- point_analisis_c2 %>% filter(ID.temp %in% base.c2$ID.temp)
            dentro <- pts.eval[apply(st_intersects(pts.eval, poly.c2, sparse = FALSE), 1, any), ]
            correctos3 <- c(correctos3, dentro$ID.temp)
          }
        }
        geo.corregir.1b <- geo.corregir.1 %>% filter(ID.temp %in% correctos3)
        geo.corregir.1 <- geo.corregir.1 %>% filter(!(ID.temp %in% correctos3))
      }
    }
    
    ### Escenario de reconstrucción decimal 6: Formato "-X.XXXXXX" (Negativo - Hemisferio Sur)
    # ESCENARIO HISTÓRICAMENTE CRÍTICO PARA ECUADOR: La inmensa mayoría del territorio continental ecuatoriano 
    # (Guayaquil, Cuenca, Amazonía) está en el Hemisferio Sur, por ende, su latitud DEBE comenzar obligatoriamente con un signo MENOS.
    if(i == 6) {
      geo.corregir.1 <- geo.corregir.1 %>% mutate(
        lat.1 = str_sub(limpia.lat, 1, 1),
        lat.leng = str_length(limpia.lat),
        lat.2 = str_sub(limpia.lat, 2, lat.leng),
        lat.final = paste0("-", lat.1, ".", lat.2) # Inserta el signo negativo y el punto decimal correspondiente.
      )
      point_analisis_c6 <- data.frame(y = as.numeric(geo.corregir.1$lat.final), x = geo.corregir.1$lon.new)   
      if(nrow(point_analisis_c6) > 0) {
        point_analisis_c6 <- st_as_sf(point_analisis_c6, coords = c("x", "y"), crs = st_crs(Provincia))  
        point_analisis_c6$ID.temp <- geo.corregir.1$ID.temp
        cantones.c6 <- unique(geo.corregir.1$CANTON_HECHO)
        for(j in 1:length(cantones.c6)) {
          base.c6 <- geo.corregir.1 %>% filter(CANTON_HECHO == cantones.c6[j])
          poly.c6 <- Provincia %>% filter(CANTON_MAPA == cantones.c6[j])
          if(nrow(poly.c6) > 0 & nrow(base.c6) > 0) {
            pts.eval <- point_analisis_c6 %>% filter(ID.temp %in% base.c6$ID.temp)
            dentro <- pts.eval[apply(st_intersects(pts.eval, poly.c6, sparse = FALSE), 1, any), ]
            correctos3 <- c(correctos3, dentro$ID.temp)
          }
        }
        geo.corregir.1f <- geo.corregir.1 %>% filter(ID.temp %in% correctos3)
        geo.corregir.1 <- geo.corregir.1 %>% filter(!(ID.temp %in% correctos3))
      }
    }
    
    ### Escenario de reconstrucción decimal 7: Formato "-0.XXXXXX" (Negativo - Proximidad Línea Equinoccial)
    # Orientado para las provincias y cantones inmediatamente ubicados al sur de la línea del Ecuador que inician con "-0."
    if(i == 7) {
      geo.corregir.1 <- geo.corregir.1 %>% mutate(
        lat.1 = str_sub(limpia.lat, 1, 1),
        lat.leng = str_length(limpia.lat),
        lat.2 = str_sub(limpia.lat, 2, lat.leng),
        lat.final = paste0("-0.", lat.1, lat.2) # Reconstruye inyectando la estructura de texto "-0."
      )
      point_analisis_c7 <- data.frame(y = as.numeric(geo.corregir.1$lat.final), x = geo.corregir.1$lon.new)   
      if(nrow(point_analisis_c7) > 0) {
        point_analisis_c7 <- st_as_sf(point_analisis_c7, coords = c("x", "y"), crs = st_crs(Provincia))  
        point_analisis_c7$ID.temp <- geo.corregir.1$ID.temp
        cantones.c7 <- unique(geo.corregir.1$CANTON_HECHO)
        for(j in 1:length(cantones.c7)) {
          base.c7 <- geo.corregir.1 %>% filter(CANTON_HECHO == cantones.c7[j])
          poly.c7 <- Provincia %>% filter(CANTON_MAPA == cantones.c7[j])
          if(nrow(poly.c7) > 0 & nrow(base.c7) > 0) {
            pts.eval <- point_analisis_c7 %>% filter(ID.temp %in% base.c7$ID.temp)
            dentro <- pts.eval[apply(st_intersects(pts.eval, poly.c7, sparse = FALSE), 1, any), ]
            correctos3 <- c(correctos3, dentro$ID.temp)
          }
        }
        geo.corregir.1g <- geo.corregir.1 %>% filter(ID.temp %in% correctos3)
        geo.corregir.1 <- geo.corregir.1 %>% filter(!(ID.temp %in% correctos3))
      }
    }
  }
}

# =========================================================================
# FASE 9: ENSAMBLAJE DE BASE GEORREFERENCIADA
# =========================================================================
## Concatenación de registros reparados exitosamente por bucles
# rbind() (Row Bind) une tablas verticalmente, pegando filas debajo de otras filas. 
# Consolidamos los cuatro grupos que rescatamos con éxito gracias al formateo de texto del paso anterior.
listo.corrcion.casos.posibles <- rbind(geo.corregir.1a, geo.corregir.1b, geo.corregir.1f, geo.corregir.1g) 

## Limpieza de campos estructurales auxiliares
if(nrow(listo.corrcion.casos.posibles) > 0) {
  # Sobreescribimos la columna "lat.new" convirtiendo la cadena de texto reparada "lat.final" en un número decimal válido.
  listo.corrcion.casos.posibles$lat.new <- as.numeric(listo.corrcion.casos.posibles$lat.final)
  listo.corrcion.casos.posibles <- listo.corrcion.casos.posibles %>% 
    # any_of() identifica si existen las columnas de texto internas que usamos para trocear el número y las destruye 
    # para dejar el dataframe perfectamente limpio y homólogo a las demás bases de datos.
    dplyr::select(-any_of(c("limpia.lat", "lat.1", "lat.leng", "lat.2", "lat.final")))
}

## Consolidación final unificada de registros espaciales válidos
# Unimos de forma vertical los 3 pilares del procesamiento: los correctos iniciales + los reparados textualmente + el limbo analítico.
homi_Nueva <- rbind(geo_correctos, listo.corrcion.casos.posibles, limbo_formato_correcto)
homi_Nueva <- homi_Nueva %>% 
  mutate(lat.new = as.numeric(lat.new), lon.new = as.numeric(lon.new)) %>% 
  # Control de calidad estricto de cierre para eliminar físicamente cualquier fila remanente que se haya quedado sin coordenadas válidas.
  filter(!is.na(lat.new) & !is.na(lon.new))

# =========================================================================
# FASE 10: ALMACENAMIENTO Y EXPORTACIÓN DE ENTREGABLES
# =========================================================================
## Retorno al directorio de salida
setwd(repositorio)

## Construcción del objeto geográfico vectorial SF
# st_as_sf() procesa de forma definitiva la tabla unificada final, transformando las coordenadas numéricas 
# en una columna nativa espacial tipo "GEOMETRY" bajo la proyección global standard 4326.
homi_Nueva_espacial <- st_as_sf(homi_Nueva, coords = c("lon.new", "lat.new"), crs = 4326)

## Escritura física de los archivos estructurados
# st_write() guarda físicamente las capas vectoriales en formato Shapefile de ESRI para mapear en softwares como QGIS o ArcGIS.
# delete_layer = TRUE sobreescribe el mapa si ya existía uno previo, evitando errores de bloqueo de archivos en disco.
st_write(homi_Nueva_espacial, "homi_Nueva.shp", delete_layer = TRUE, quiet = TRUE)
# write.csv() exporta la tabla tabular en un archivo CSV plano estándar compatible con Microsoft Excel.
write.csv(homi_Nueva, "homi_Nueva_limpio7.csv", row.names = FALSE)
# saveRDS() almacena la base de datos comprimida en formato nativo de R para futuras cargas instantáneas con máxima fidelidad.
saveRDS(homi_Nueva, file = "homi_2010_2024_2.rds")

# =========================================================================
# FASE 11: REPORTE ESTADÍSTICO DE CONTROL INTEGRAL
# =========================================================================
# Bloque puramente informativo para visualizar en consola los indicadores de rendimiento técnico de nuestro algoritmo informático.
print("========================================================")
print("               REPORTE DE VERIFICACIÓN FINAL              ")
print("========================================================")
print(paste("-> Homicidios procesados (2010-2024):", nrow(homi_2010_2024)))
print(paste("-> Total rescatados perfectos a la primera:", nrow(geo_correctos)))
print(paste("-> Total rescatados por algoritmo de texto:", nrow(listo.corrcion.casos.posibles)))
print(paste("-> Casos en limbo con coordenadas correctas retenidos:", nrow(limbo_formato_correcto)))
print(paste("TOTAL DE REGISTROS GEORREFERENCIADOS:", nrow(homi_Nueva)))
print(paste("Efectividad total de la base:", round((nrow(homi_Nueva) / nrow(homi_2010_2024)) * 100, 2), "%"))
print("========================================================")

# =========================================================================
# FASE 12: VISUALIZACIÓN CARTOGRÁFICA DIAGNÓSTICA
# =========================================================================
## Carga del mapa base referencial para el ploteo estético
Mapa_Completo <- read_sf(file.path(repositorio_carto, "nxcantones.shp"))
Mapa_Completo <- st_transform(Mapa_Completo, crs = 4326)

## Disolución de geometrías cantonales a límites provinciales ecuatorianos
# Gráficamente: Como tu mapa base original divide al Ecuador en pequeños cantones, este bloque usa group_by() y summarize() 
# para fusionar ("disolver") las líneas fronterizas de los cantones pertenecientes a una misma provincia. 
# El resultado es un mapa más limpio que solo muestra los bordes externos de las 24 provincias continentales.
Mapa_Provincias <- Mapa_Completo %>%
  filter(DPA_DESPRO != "GALAPAGOS") %>% 
  group_by(DPA_DESPRO) %>%              
  summarize(.groups = "drop")            

## Lectura espacial de control del producto generado
test_mapa <- st_read("homi_Nueva.shp", quiet = TRUE)

## Generación de la gráfica espacial de puntos sobre polígonos
# ggplot() inicializa un lienzo gráfico vacío.
ggplot() +
  # geom_sf() dibuja objetos geográficos. Aquí grafica el fondo gris claro ("gray96") con líneas negras que representan las provincias.
  geom_sf(data = Mapa_Provincias, fill = "gray96", color = "black", size = 0.4) + 
  # geom_jitter() grafica los homicidios como puntos individuales sobre las provincias. El término jitter añade un mini-desplazamiento 
  # aleatorio imperceptible invisible para que los puntos que tienen exactamente las mismas coordenadas exactas no se encimen por completo, 
  # permitiendo percibir visualmente la densidad de los crímenes (puntos de color rojo oscuro "darkred").
  geom_jitter(data = test_mapa, aes(geometry = geometry), 
              stat = "sf_coordinates", alpha = 0.4, color = "darkred", size = 0.8) +
  theme_minimal() + # Aplica un diseño estético minimalista con fondos blancos muy elegante para reportes ejecutivos.
  labs(
    title = "Distribución Geográfica de Homicidios en Ecuador",
    subtitle = "Límites provinciales unificados (Datos Validados Continentales 2010-2024)",
    x = "Longitud",
    y = "Latitud"
  )

# str() inspecciona a fondo la estructura de almacenamiento del objeto: muestra tipos de datos (números, caracteres) y dimensiones.
str(homi_Nueva)

# =========================================================================
# FASE 13: ETIQUETADO FINAL MAESTRO Y DEPURACIÓN ESTRUCTURAL
# =========================================================================

### 1. Renombrado y Selección Definitiva basándonos en str(homi_Nueva)
# dplyr::select() aquí realiza dos tareas críticas al mismo tiempo: 
# Primero, actúa como filtro estructural reteniendo solo las columnas indispensables para los usuarios finales.
# Segundo, renombra las columnas encriptadas del proveedor (ej: "X33", "X35") a nombres descriptivos en español técnico.
# Gráficamente: Transforma una matriz incomprensible en una base de datos gerencial lista para analistas de políticas públicas.
homi_Analisis_Final <- homi_Nueva %>% 
  dplyr::select(
    codigo_caso          = X2,           # Identificador policial codificado del crimen.
    tipo_delito          = X4,           # Tipificación legal del incidente (ej: Homicidio, Asesinato).
    fecha_hecho          = X33,          # Fecha exacta en formato estándar Año-Mes-Día.
    anio_hecho           = anio,         # Desglose del año de ocurrencia.
    mes_hecho            = mes,          # Mes del suceso expresado en palabras en minúsculas.
    dia_semana           = dia,          # Día cronológico de la semana.
    hora_aproximada      = rangoh,       # Hora promedio del evento
    provincia_mapa       = DPA_DESPRO,   # Nombre oficial de la provincia validada geográficamente.
    canton               = X133,         # Nombre oficial del cantón validado geográficamente.
    zona_tipo            = X23,          # Clasificación territorial de la escena (Urbano o Rural).
    lugar_especifico     = X28,          # Espacio público o privado de la agresión (ej: Vía Pública).
    tipo_arma            = X35,          # Instrumento del deceso (ej: Arma de Fuego, Arma Blanca).
    motivacion_detalle   = X39,          # Causa hipotética de la agresión según investigación (ej: Violencia Comunitaria).
    causa_especifica     = X40,          # Detalle fáctico del móvil (ej: Riñas, Robo).
    edad_victima         = X45,          # Edad cronológica en años de la persona fallecida.
    sexo_victima         = X47,          # Género biológico registrado de la víctima.
    nacionalidad_victima = X53,          # País de origen documentado del ciudadano.
    latitud_reparada     = lat.new,      # Coordenada decimal Y final calculada, auditada y corregida.
    longitud_reparada    = lon.new,      # Coordenada decimal X final calculada, auditada y corregida.
    id_auditoria         = ID.temp,      # Nuestro ID de control único: Es vital guardarlo para saber el rastreo de auditoría del caso.
    AUX_HORA_SISTEMA     = X208,         # Campo secundario de auditoría horaria de registros informáticos.
    AUX_MINUTO_SISTEMA   = X209          # Campo secundario de auditoría de minutos de sistemas internos.
  )

### 2. Bloque de escritura seguro y actualización del repositorio
setwd(repositorio)

archivo_csv <- "homi_Final_Continental_Etiquetado.csv"
archivo_rds <- "homi_Final_Continental_Etiquetado.rds"

# Eliminar versiones viejas bloqueadas si existen
# tryCatch() es un escudo contra errores. Si el archivo CSV está abierto por un usuario en Microsoft Excel, 
# Excel bloquea el disco duro e impide que R lo modifique. tryCatch evita que el programa colapse por completo 
# emitiendo una alerta amigable en la consola en lugar de un mensaje de error fatal.
if (file.exists(archivo_csv)) {
  tryCatch(file.remove(archivo_csv), error = function(e) {
    print("Nota: Si el CSV está abierto en Excel, ciérralo para actualizar los cambios.")
  })
}

# Grabado final de la información procesada
# Guardamos los archivos definitivos completamente pulidos, renombrados y limpios para el consumo de los usuarios finales.
write.csv(homi_Analisis_Final, archivo_csv, row.names = FALSE)
saveRDS(homi_Analisis_Final, file = archivo_rds)

print("=========================================================================")
print("   ¡PASO 13 COMPLETADO: BASE DE DATOS MAESTRA GENERADA EXITOSAMENTE!   ")
print("=========================================================================")
print(paste("-> Registros consolidados exportados:", nrow(homi_Analisis_Final)))
print(paste("-> Columnas limpias seleccionadas:", ncol(homi_Analisis_Final)))
print("=========================================================================")

# Comandos de control final para diagnosticar la salud y completitud de la base final limpia.
summary(homi_Analisis_Final)
str(homi_Analisis_Final)

