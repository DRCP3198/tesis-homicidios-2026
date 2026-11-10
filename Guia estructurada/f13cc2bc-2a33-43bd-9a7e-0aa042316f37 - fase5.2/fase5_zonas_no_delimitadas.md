# 🏛️ Fase 5 — Homologación Jurídica, Normativa y Cartográfica de Zonas No Delimitadas y Variantes Cantonales

> [!IMPORTANT]
> **Propósito para el Informe de Tesis:** Este documento consolida el sustento **100% legal, normativo, cartográfico y estadístico** (Leyes de Fijación de Límites Territoriales Internos 2013–2017, Consultas Populares del CNE, Suplementos del Registro Oficial, CONALI, SENPLADES e INEC) utilizado para homologar las antiguas **Zonas No Delimitadas (Código DPA `90`)** y las variantes de escritura cantonal antes del modelado de **Series Temporales Multivariantes**.

---

## 1. Planteamiento del Problema Cartográfico y Estadístico

En el shapefile histórico de la División Político-Administrativa del INEC ([`nxcantones.shp`](file:///D:/Tesis/data/raw/cartografia/nxcantones.shp)) y en los registros administrativos de homicidios intencionales del Ministerio del Interior / Policía Nacional (`2010–2024`), coexistían tres desfaces estructurales que afectaban la primera auditoría espacial punto-en-polígono (`gpd.sjoin`):

1. **Tres territorios bajo el código transitorio `DPA_PROVIN = "90"` (`"ZONA NO DELIMITADA"`):**
   - `9001` — **Las Golondrinas** ($147\text{ km}^2$, límite Imbabura–Esmeraldas).
   - `9003` — **Manga del Cura** ($487\text{ km}^2$, límite Manabí–Guayas).
   - `9004` — **El Piedrero / Colonia Agrícola Amazonas** ($167.2\text{ km}^2$, límite Cañar–Guayas).
   En el script original en R, al ejecutar `filter(DPA_DESPRO != "ZONA NO DELIMITADA")`, estos tres polígonos se eliminaban del mapa continental, dejando **tres vacíos geográficos internos** y enviando artificialmente al `limbo` los **117 homicidios** ocurridos dentro de sus límites.
2. **Dualidad temporal en las etiquetas del parte policial (`2010–2024`):**
   - Como la serie histórica abarca 15 años (`2010–2024`) y las leyes definitivas de fijación de límites se promulgaron entre **2015 y 2017**, una parte de los homicidios ocurridos en esos tres polígonos fue registrada con el nombre antiguo de la zona (`"EL PIEDRERO"`: 51 casos; `"MANGA DEL CURA"`: 15 casos; `"LAS GOLONDRINAS"`: 1 caso) y otra parte ya fue registrada con el cantón oficial (`"LA TRONCAL"`: 17 casos; `"EL CARMEN"`: 24 casos).
3. **Corrupción de codificación en el Shapefile (`Ð` por `Ñ`) y variantes de tipeo cantonal:**
   - En `nxcantones.shp`, la letra `Ñ` quedó codificada con el byte `Ð` (`U+00D0`, letra islandesa *Eth*) en `"RUMIÐAHUI"` y `"LOGROÐO"`, que al pasar por `unidecode()` se convertía erróneamente en `"RUMIDAHUI"` y `"LOGRODO"` (71 casos afectados).
   - En el CSV policial existían variantes de escritura y un caso de ambigüedad interprovincial crítica en `"SAN MIGUEL DE SALCEDO"` entre **Cotopaxi** y **Bolívar** (159 casos afectados).

---

## 2. Sustento Jurídico y Normativo Oficial (Resoluciones 2015–2017)

El marco rector que extinguió las Zonas No Delimitadas en el Ecuador continental es la **Ley para la Fijación de Límites Territoriales Internos**, publicada en el **Registro Oficial Suplemento N.° 934 del 16 de abril de 2013**, y su Reglamento General publicado en el **Registro Oficial Suplemento N.° 408 del 5 de enero de 2015**, ejecutados técnicamente por el **Comité Nacional de Límites Internos (CONALI)** y actualizados en el *Clasificador Geográfico Estadístico (DPA)* del **INEC**.

### 2.1. Caso 1: Manga del Cura (`Código INEC 9003` → `MANABI / EL CARMEN`)

| Atributo Normativo | Detalle Oficial para Cita en Tesis |
|---|---|
| **Diferendo histórico** | Zona de $487\text{ km}^2$ disputada entre las provincias de **Manabí** y **Guayas**. |
| **Convocatoria y Dictamen** | **Corte Constitucional del Ecuador**, Dictamen Favorable N.° `001-15-DCP-CC` y **Decreto Ejecutivo N.° 737** (agosto de 2015). |
| **Consulta Popular CNE** | Realizada el **27 de septiembre de 2015** por el Consejo Nacional Electoral (CNE) sobre un padrón de 15,342 electores. Ganó la opción de pertenecer a la provincia de **Manabí** con el **64.2% de los votos válidos** (8,525 votos frente a 4,380 de Guayas). Resultados proclamados en el **Registro Oficial N.° 611 del 20 de octubre de 2015**. |
| **Ley Definitiva (Registro Oficial)** | **Ley que Fija el Límite Territorial Definitivo entre las Provincias de Guayas y Manabí en la Zona denominada Manga del Cura**, aprobada por la Asamblea Nacional y promulgada en el **Registro Oficial Suplemento N.° 994 del 28 de abril de 2017**. |
| **Jurisdicción asignada** | Provincia de **Manabí**, Cantón **El Carmen** (integrada mediante las parroquias rurales Santa María y El Paraíso–La 14). |
| **Impacto en la base (`2010–2024`)** | De los 38 registros con coordenadas válidas dentro del polígono (`+1` registro descartado en `0, 0`), **24** ya traían `MANABI - EL CARMEN` y **14** traían `MANABI - MANGA DEL CURA`. Al homologar `("MANABI", "MANGA DEL CURA") → "EL CARMEN"`, **los 38 registros (100%) validan en `geo_correctos`**. |

---

### 2.2. Caso 2: Las Golondrinas (`Código INEC 9001` → `IMBABURA / COTACACHI`)

| Atributo Normativo | Detalle Oficial para Cita en Tesis |
|---|---|
| **Diferendo histórico** | Zona de $147\text{ km}^2$ en la cuenca baja del río Guayllabamba, disputada entre las provincias de **Imbabura** y **Esmeraldas**. |
| **Convocatoria y Dictamen** | **Corte Constitucional del Ecuador**, Dictamen N.° `006-15-DCP-CC` y **Decreto Ejecutivo N.° 878** (enero de 2016). |
| **Consulta Popular CNE** | Realizada el **3 de abril de 2016** por el CNE. Ganó la opción de pertenecer a la provincia de **Imbabura** con el **58.30% de los votos válidos**. |
| **Ley Definitiva (Registro Oficial)** | **Ley que Fija el Límite Territorial entre las Provincias de Esmeraldas e Imbabura en la Zona denominada Las Golondrinas**, aprobada por la Asamblea Nacional y promulgada en el **Registro Oficial Suplemento N.° 999 del 8 de mayo de 2017** (Artículos 1 y 2). |
| **Jurisdicción asignada** | Provincia de **Imbabura**, Cantón **Cotacachi** (adscrita a la parroquia rural García Moreno). |
| **Impacto en la base y hallazgo de lindero** | Dentro del polígono caen **10 registros** (todos con `provincia = "IMBABURA"`): **1 registro** (`codigo_caso = 93752`, `2024-06-16`) venía como `LAS GOLONDRINAS` y al homologarse a `COTACACHI` pasa a `geo_correctos`. Los otros **9 registros** fueron digitados por la Subzona Policial Imbabura con el nombre de la capital provincial (`IBARRA`); en estricto apego a la Ley (que adjudicó el territorio al cantón **Cotacachi** y no a Ibarra), esos 9 casos permanecen legítimamente identificados en el **`limbo_formato_correcto`** como discrepancia administrativa intercantonal. |

---

### 2.3. Caso 3: El Piedrero / Colonia Agrícola Amazonas (`Código INEC 9004` → `CAÑAR / LA TRONCAL`)

| Atributo Normativo | Detalle Oficial para Cita en Tesis |
|---|---|
| **Antecedente territorial** | Sector de $167.2\text{ km}^2$ entre los ríos Bulubulu y Cañar, limítrofe entre **Cañar (cantón La Troncal)** y **Guayas (cantón El Triunfo)**. |
| **Normativa de Planificación y Registro Policial (SENPLADES / MDG)** | Conforme al **Acuerdo Ministerial SENPLADES N.° 557-2012** (*Conformación de Distritos y Circuitos Administrativos de Planificación*) y al clasificador operativo del **Ministerio del Interior / Policía Nacional (Subzona Cañar N.° 3, Distrito 03D03 La Troncal, Circuito 03D03C03 El Piedrero)**, la totalidad de la gestión de seguridad ciudadana y levantamiento de actas en la serie `2010–2024` operó bajo la jurisdicción de **Cañar — La Troncal**. *(Nota jurídica adicional: si bien el Decreto Ejecutivo N.° 1395 del 16 de mayo de 2017, R.O. Suplemento N.° 2 del 29 de mayo de 2017, planteó la delimitación hacia Guayas y fue objeto de acción de inconstitucionalidad en el Caso N.° 31-17-IN ante la Corte Constitucional, en la fuente estadística oficial del Ministerio del Interior el **98.55%** de los eventos del polígono están codificados en la provincia de **`CAÑAR`**)*. |
| **Jurisdicción asignada por coherencia provincial de la fuente** | Provincia de **Cañar**, Cantón **La Troncal** (`("CANAR", "EL PIEDRERO") → "LA TRONCAL"`). Esto preserva al 100% la provincia original declarada en la base de datos sin alterar la serie provincial de Cañar ni de Guayas. |
| **Impacto en la base y hallazgo de lindero** | De los **69 registros** ubicados dentro del polígono `EL PIEDRERO`: **68 registros** pertenecen a `CANAR` (**17** ya venían como `LA TRONCAL` y **51** venían como `EL PIEDRERO`), los cuales pasan directamente a **`geo_correctos`**. El **1 registro restante** (`codigo_caso = 34252`, `2017-10-16`), que fue reportado con `provincia = "GUAYAS", canton = "GUAYAQUIL"`, queda retenido en el **`limbo_formato_correcto`** como caso real de lindero interprovincial. |

---

## 3. Desambiguación Toponímica Adicional y Corrección del Shapefile

Además de las tres antiguas Zonas No Delimitadas, el módulo [`normalizar_texto.py`](file:///D:/Tesis/src/limpieza/normalizar_texto.py) ([`homologar_cantones_por_provincia()`](file:///D:/Tesis/src/limpieza/normalizar_texto.py#L41-L152)) y el módulo [`cartografia.py`](file:///D:/Tesis/src/validacion_geo/cartografia.py) ([`reparar_codificacion_shapefile()`](file:///D:/Tesis/src/validacion_geo/cartografia.py#L42-L108)) ejecutan las siguientes reglas deterministas:

| Tipo de Corrección | Provincia | Valor Original (Crudo) | Valor Oficial Homologado | Registros Beneficiados | Justificación Técnica |
|---|---|---|---|---:|---|
| **Desambiguación interprovincial** | `COTOPAXI` | `SAN MIGUEL DE SALCEDO` | `SALCEDO` | **3** | En Cotopaxi, el cantón con cabecera San Miguel de Salcedo se denomina oficialmente `SALCEDO` en la DPA del INEC (coords `-1.07, -78.59`). |
| **Desambiguación interprovincial** | `BOLIVAR` | `SAN MIGUEL DE SALCEDO` | `SAN MIGUEL` | **1** | El caso `92067` (`2024-05-20`, coords `-1.7061, -79.11753`) ocurrió en la provincia de Bolívar, dentro del polígono del cantón **`SAN MIGUEL`** (San Miguel de Bolívar). |
| **Unificación ortográfica** | `LOS RIOS` | `PUEBLO VIEJO` | `PUEBLOVIEJO` | **94** | El nombre oficial del cantón en el INEC se escribe en una sola palabra (`PUEBLOVIEJO`, uniéndose a los 276 registros ya existentes). |
| **Nombre corto oficial INEC** | `ORELLANA` | `PUERTO FRANCISCO DE ORELLANA` | `ORELLANA` | **61** | En el CSV se usó el nombre de la cabecera cantonal en lugar del nombre oficial del cantón (`ORELLANA`, uniéndose a los 131 registros ya existentes). |
| **Reparación byte `Ð` en SHP** | `PICHINCHA` | `RUMIÐAHUI` (SHP) | `RUMINAHUI` | **64** | Evita que `unidecode("Ð")` genere `"RUMIDAHUI"` y permite el cruce exacto con `"RUMINAHUI"` del CSV. |
| **Reparación byte `Ð` en SHP** | `MORONA SANTIAGO` | `LOGROÐO` (SHP) | `LOGRONO` | **7** | Evita que `unidecode("Ð")` genere `"LOGRODO"` y permite el cruce exacto con `"LOGRONO"` del CSV. |

---

## 4. Radiografía Exacta del Antes vs. Después (¿Qué queda realmente en el Limbo?)

Con la aplicación conjunta de las correcciones anteriores (Opción A), el resultado empírico sobre los **38,566 registros continentales (`2010–2024`)** es el siguiente:

| Indicador de Auditoría Geoespacial | Antes de Homologar | Después de Homologar (Opción A) | Variación |
|---|---:|---:|---:|
| **Validados en 1ra auditoría (`geo_correctos`)** | `38,166` (`98.96%`) | **`38,503` (`99.84%`)** | **`+337` registros validados** |
| **Retenidos en `limbo_formato_correcto`** | `399` (`1.04%`) | **`62` (`0.16%`)** | **`-337` registros (reducción del 84.5%)** |
| **Coordenadas descartadas irreversibles (`0, 0`)** | `1` (`0.0026%`) | **`1` (`0.0026%`)** | Sin cambio (`codigo_caso = 96547`) |
| **Total georreferenciado final (`homi_final`)** | `38,565` (`99.9974%`) | **`38,565` (`99.9974%`)** | **100% cuadre contable** |
| **Cantones únicos en el dataset final** | `220` (con duplicados y ZND sueltas) | **`214` cantones oficiales limpios** | Sin cantones partidos ni categorías artificiales |

### ¿Cuáles son exactamente los únicos 62 registros (`0.16%`) que quedan en el `limbo_formato_correcto`?

Tal como anticipaste, una vez resueltas las Zonas No Delimitadas por la vía legal, **los únicos 62 casos que permanecen en el limbo son casos reales de linderos físicos, borde costero o digitación provincial**:

1. **26 casos de Linderos Intercantonales / Interprovinciales (`41.9%` del limbo):**
   - **9 casos** en el polígono de **Las Golondrinas (Cotacachi)** que fueron registrados policialmente bajo el cantón vecino **`IBARRA`**.
   - **6 casos** en la frontera urbana conurbada entre **`HUAQUILLAS`** y **`ARENILLAS`** (El Oro).
   - **4 casos** en el límite entre **`ORELLANA`** y **`LA JOYA DE LOS SACHAS`** (Orellana).
   - **3 casos** en el límite entre **`TULCAN`** y **`SAN PEDRO DE HUACA`** (Carchi).
   - **1 caso** en el polígono de **El Piedrero (La Troncal, Cañar)** registrado bajo **`GUAYAS - GUAYAQUIL`**.
   - **3 casos** aislados en calles limítrofes de **`ALFREDO BAQUERIZO MORENO / YAGUACHI`**, **`BALZAR / MOCACHE`** y **`TISALEO / MOCHA`**.
2. **18 casos de Borde Costero, Esteros y Muelles Portuarios (`29.0%` del limbo):**
   - Ubicados en **`MACHALA`** (13 casos en muelles de Puerto Bolívar / Jambelí), **`GUAYAQUIL`** (2 casos en el Estero Salado / Río Guayas), **`ESMERALDAS`** (1), **`SAMBORONDON`** (1) y **`PORTOVIEJO`** (1), donde la coordenada GPS del levantamiento en muelle o manglar cae unos metros fuera del polígono continental simplificado del shapefile.
3. **18 casos con Nombre de Provincia repetido en la columna `canton` (`29.0%` del limbo):**
   - Registros donde el digitador policial escribió el nombre de la provincia en el campo del cantón (`GUAYAS - GUAYAS`: 11 casos; `EL ORO - EL ORO`: 3 casos; `MANABI - MANABI`: 2 casos; `PICHINCHA - PICHINCHA`: 2 casos), pero cuyas coordenadas GPS sí caen correctamente dentro de su provincia.

---

## 5. Archivos del Proyecto Actualizados

- [`src/ingesta/config.py`](file:///D:/Tesis/src/ingesta/config.py): Diccionarios [`MAPEO_CARACTERES_CORRUPTOS_SHP`](file:///D:/Tesis/src/ingesta/config.py#L185-L188), [`MAPEO_HOMOLOGACION_CANTONES`](file:///D:/Tesis/src/ingesta/config.py#L205-L222) y [`MAPEO_ZONAS_NO_DELIMITADAS_SHP`](file:///D:/Tesis/src/ingesta/config.py#L229-L245).
- [`src/limpieza/normalizar_texto.py`](file:///D:/Tesis/src/limpieza/normalizar_texto.py): Función [`homologar_cantones_por_provincia()`](file:///D:/Tesis/src/limpieza/normalizar_texto.py#L41-L152) con tabla resumen y muestra en consola.
- [`src/validacion_geo/cartografia.py`](file:///D:/Tesis/src/validacion_geo/cartografia.py): Funciones [`reparar_codificacion_shapefile()`](file:///D:/Tesis/src/validacion_geo/cartografia.py#L42-L108) y [`homologar_zonas_no_delimitadas_shp()`](file:///D:/Tesis/src/validacion_geo/cartografia.py#L121-L179).
- [`src/validacion_geo/reparacion.py`](file:///D:/Tesis/src/validacion_geo/reparacion.py): Función [`imprimir_detalle_no_reparados()`](file:///D:/Tesis/src/validacion_geo/reparacion.py#L492-L534) para visualizar en consola los registros descartados.
- [`reports/auditoria_pipeline.md`](file:///D:/Tesis/reports/auditoria_pipeline.md) y [`reports/auditoria_pipeline.json`](file:///D:/Tesis/reports/auditoria_pipeline.json): Reportes regenerados con los nuevos conteos (`38,503` correctos en 1ra auditoría, `62` en limbo, `1` descartado, `214` cantones únicos).
