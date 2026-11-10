# 🏛️ Fase 5 — Homologación Jurídica, Normativa y Geoespacial de Zonas No Delimitadas, Variantes Cantonales y Casos Anómalos de Limbo

> [!IMPORTANT]
> **Propósito para el Informe de Tesis:** Este documento consolida el sustento **100% legal, normativo, cartográfico y estadístico** (Leyes de Fijación de Límites Territoriales Internos 2013–2017, Consultas Populares del CNE, Suplementos del Registro Oficial, CONALI, SENPLADES e INEC) junto con las reglas deterministas de intersección espacial exacta (`Point-in-Polygon`, sin umbrales ni *buffers* arbitrarios) aplicadas antes del modelado de **Series Temporales Multivariantes**.

---

## 1. Planteamiento del Problema Cartográfico y Estadístico

En el shapefile histórico de la División Político-Administrativa del INEC ([`nxcantones.shp`](file:///D:/Tesis/data/raw/cartografia/nxcantones.shp)) y en los registros administrativos de homicidios intencionales del Ministerio del Interior / Policía Nacional (`2010–2024`), coexistían cuatro fuentes de discrepancia que reducían artificialmente la primera auditoría espacial punto-en-polígono (`gpd.sjoin` con predicado estricto `intersects`):

1. **Tres territorios bajo el código transitorio `DPA_PROVIN = "90"` (`"ZONA NO DELIMITADA"`):**
   - `9001` — **Las Golondrinas** ($147\text{ km}^2$, límite Imbabura–Esmeraldas).
   - `9003` — **Manga del Cura** ($487\text{ km}^2$, límite Manabí–Guayas).
   - `9004` — **El Piedrero / Colonia Agrícola Amazonas** ($167.2\text{ km}^2$, límite Cañar–Guayas).
   En el script original en R, al ejecutar `filter(DPA_DESPRO != "ZONA NO DELIMITADA")`, estos tres polígonos se eliminaban del mapa continental, dejando **tres vacíos geográficos internos** y enviando artificialmente al `limbo` los **117 homicidios** ocurridos dentro de sus límites.
2. **Dualidad temporal y administrativa en las etiquetas de esas tres zonas (`2010–2024`):**
   - Como la serie histórica abarca 15 años (`2010–2024`) y las leyes definitivas de fijación de límites se promulgaron entre **2015 y 2017**, una parte de los homicidios fue registrada con el nombre antiguo de la zona (`"EL PIEDRERO"`: 51 casos; `"MANGA DEL CURA"`: 15 casos; `"LAS GOLONDRINAS"`: 1 caso), otra parte con el cantón oficial (`"LA TRONCAL"`: 17 casos; `"EL CARMEN"`: 24 casos), y **10 casos** fueron registrados con la cabecera provincial o zonal lejana (**9 casos** en Las Golondrinas digitados como `IBARRA` a $\sim 97\text{ km}$ de distancia, y **1 caso** en El Piedrero digitado como `GUAYAS - GUAYAQUIL` a $\sim 50.8\text{ km}$ de distancia).
3. **Registros con el nombre de la `provincia` repetido en la columna `canton` (`22 casos` en 2024):**
   - En el año 2024 se registraron **22 eventos** donde el digitador policial repitió el nombre de la provincia en el campo del cantón (`GUAYAS - GUAYAS`: 11; `EL ORO - EL ORO`: 3; `MANABI - MANABI`: 2; `PICHINCHA - PICHINCHA`: 2; `ORELLANA - ORELLANA`: 4), generando cantones inexistentes en la DPA oficial del INEC o asignando erróneamente a la capital cuando las coordenadas caían a $16.5\text{ km}$ en `LA JOYA DE LOS SACHAS`.
4. **Corrupción de codificación en el Shapefile (`Ð` por `Ñ`) y variantes ortográficas cantonales (`230 casos`):**
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
| **Impacto en la base (`2010–2024`)** | Los **38 registros** con coordenadas válidas dentro del polígono (`24` originalmente `EL CARMEN` + `14` homologados desde `MANGA DEL CURA`) pasan al 100% a **`geo_correctos`**. El único caso con coordenada `(0, 0)` (`codigo_caso = 96547`) se descarta en el Paso 4.6. |

---

### 2.2. Caso 2: Las Golondrinas (`Código INEC 9001` → `IMBABURA / COTACACHI`)

| Atributo Normativo | Detalle Oficial para Cita en Tesis |
|---|---|
| **Diferendo histórico** | Zona de $147\text{ km}^2$ en la cuenca baja del río Guayllabamba, disputada entre las provincias de **Imbabura** y **Esmeraldas**. |
| **Convocatoria y Dictamen** | **Corte Constitucional del Ecuador**, Dictamen N.° `006-15-DCP-CC` y **Decreto Ejecutivo N.° 878** (enero de 2016). |
| **Consulta Popular CNE** | Realizada el **3 de abril de 2016** por el CNE. Ganó la opción de pertenecer a la provincia de **Imbabura** con el **58.30% de los votos válidos**. |
| **Ley Definitiva (Registro Oficial)** | **Ley que Fija el Límite Territorial entre las Provincias de Esmeraldas e Imbabura en la Zona denominada Las Golondrinas**, aprobada por la Asamblea Nacional y promulgada en el **Registro Oficial Suplemento N.° 999 del 8 de mayo de 2017** (Artículos 1 y 2). |
| **Jurisdicción asignada** | Provincia de **Imbabura**, Cantón **Cotacachi** (adscrita a la parroquia rural García Moreno). |
| **Impacto en la base (`2010–2024`)** | Los **10 registros** ubicados físicamente dentro del polígono `9001` (`1` registrado como `LAS GOLONDRINAS` y `9` registrados bajo la sede de la Subzona Policial Imbabura como `IBARRA`, ubicada a $\sim 97\text{ km}$ de distancia) quedan homologados en **`IMBABURA - COTACACHI`** conforme a la Ley R.O.S. N.° 999 y validan al 100% en **`geo_correctos`**. |

---

### 2.3. Caso 3: El Piedrero / Colonia Agrícola Amazonas (`Código INEC 9004` → `CAÑAR / LA TRONCAL`)

| Atributo Normativo | Detalle Oficial para Cita en Tesis |
|---|---|
| **Antecedente territorial** | Sector de $167.2\text{ km}^2$ entre los ríos Bulubulu y Cañar, limítrofe entre **Cañar (cantón La Troncal)** y **Guayas (cantón El Triunfo)**. |
| **Normativa de Planificación y Registro Policial (SENPLADES / MDG)** | Conforme al **Acuerdo Ministerial SENPLADES N.° 557-2012** (*Conformación de Distritos y Circuitos Administrativos de Planificación*) y al clasificador operativo del **Ministerio del Interior / Policía Nacional (Subzona Cañar N.° 3, Distrito 03D03 La Troncal, Circuito 03D03C03 El Piedrero)**, la gestión de seguridad ciudadana y levantamiento de actas en la serie `2010–2024` operó bajo la jurisdicción de **Cañar — La Troncal**. *(Nota jurídica: aunque el Decreto Ejecutivo N.° 1395 del 16 de mayo de 2017, R.O. Suplemento N.° 2 del 29 de mayo de 2017, planteó la delimitación hacia Guayas y fue objeto de acción constitucional en el Caso N.° 31-17-IN, en la fuente oficial del Ministerio del Interior 68 de los 69 eventos del polígono están codificados en la provincia de **`CAÑAR`**)*. |
| **Jurisdicción asignada** | Provincia de **Cañar**, Cantón **La Troncal**. |
| **Impacto en la base (`2010–2024`)** | Los **69 registros** cuyas coordenadas caen en el interior del polígono `9004` (`17` ya etiquetados como `LA TRONCAL`, `51` homologados desde `EL PIEDRERO` y `1` caso `97311` de 2024 corregido por `Point-in-Polygon` tras haberse digitado erróneamente como `GUAYAS - GUAYAQUIL` a $50.8\text{ km}$ de Guayaquil) validan al 100% en **`geo_correctos`**. |

---

## 3. Reglas Deterministas de Homologación Textual y `Point-in-Polygon`

| Módulo y Función | Regla Aplicada | Casos Corregidos | Sustento Técnico y Metodológico |
|---|---|---:|---|
| [`cartografia.py`](file:///D:/Tesis/src/validacion_geo/cartografia.py) → [`reparar_codificacion_shapefile()`](file:///D:/Tesis/src/validacion_geo/cartografia.py#L42-L108) | Reparación de byte corrupto `Ð` (`U+00D0`) → `N` en `DPA_DESCAN` (`RUMIÐAHUI` → `RUMINAHUI`, `LOGROÐO` → `LOGRONO`) | **71** | Evita que `unidecode("Ð")` genere `"RUMIDAHUI"` y `"LOGRODO"`. |
| [`normalizar_texto.py`](file:///D:/Tesis/src/limpieza/normalizar_texto.py) → [`homologar_cantones_por_provincia()`](file:///D:/Tesis/src/limpieza/normalizar_texto.py#L41-L152) | Desambiguación por tupla `(provincia, canton)` de variantes ortográficas y ex-ZND (`PUEBLO VIEJO` → `PUEBLOVIEJO`, `PUERTO FRANCISCO DE ORELLANA` → `ORELLANA`, `COTOPAXI/SAN MIGUEL DE SALCEDO` → `SALCEDO`, `BOLIVAR/SAN MIGUEL DE SALCEDO` → `SAN MIGUEL`, `MANGA DEL CURA` → `EL CARMEN`, `LAS GOLONDRINAS` → `COTACACHI`, `EL PIEDRERO` → `LA TRONCAL`) | **226** *(225 con coord. válida + 1 en `0,0`)* | Unifica nombres históricos y evita confundir `SALCEDO` (Cotopaxi) con `SAN MIGUEL` (Bolívar). |
| [`geometrias.py`](file:///D:/Tesis/src/validacion_geo/geometrias.py) → [`corregir_jurisdiccion_por_ubicacion()`](file:///D:/Tesis/src/validacion_geo/geometrias.py#L153-L287) (Regla 1) | Intersección `Point-in-Polygon` cuando `canton == provincia` y el punto cae dentro de otro cantón de la misma provincia (`GUAYAS` → `GUAYAQUIL`/`DURAN`/`NARANJAL`; `EL ORO` → `EL GUABO`/`SANTA ROSA`/`PASAJE`; `MANABI` → `MANTA`; `PICHINCHA` → `QUITO`; `ORELLANA` → `LA JOYA DE LOS SACHAS`) | **22** | Elimina los cantones inexistentes `"GUAYAS"`, `"EL ORO"` y `"MANABI"` (y el falso `"PICHINCHA"` en Quito) asignando el cantón exacto donde cae la coordenada GPS. |
| [`geometrias.py`](file:///D:/Tesis/src/validacion_geo/geometrias.py) → [`corregir_jurisdiccion_por_ubicacion()`](file:///D:/Tesis/src/validacion_geo/geometrias.py#L153-L287) (Regla 2) | Intersección `Point-in-Polygon` dentro de los polígonos `9001` (`LAS GOLONDRINAS`) y `9004` (`EL PIEDRERO`) para registros con cabecera lejana (`9` de `IBARRA` → `COTACACHI`; `1` de `GUAYAS/GUAYAQUIL` → `CANAR/LA TRONCAL`) | **10** | Aplica la jurisdicción legal del polígono donde cayó el punto GPS cuando la distancia al cantón digitado supera los $50\text{ km}$. |

---

## 4. Criterio Metodológico sobre los Únicos 30 Casos Anómalos Retenidos en `limbo_formato_correcto`

> [!NOTE]
> **¿Por qué NO se aplica una tolerancia artificial (como `< 1 km`) sobre los 30 casos restantes?**
> Porque en una investigación científica de tesis no debe introducirse un umbral métrico arbitrario (*ad-hoc*) que no forme parte de un estándar cartográfico o del algoritmo original. En su lugar, la auditoría espacial mantiene el predicado topológico estricto (`intersects` a $0.0\text{ m}$) y **clasifica e imprime explícitamente en consola los 30 casos anómalos (`0.08%` del universo)** dentro de `limbo_formato_correcto`, conservándolos íntegros en la base final sin alterar sus atributos originales.

Al inspeccionar geométricamente esos **30 casos anómalos**, se confirma que se dividen exactamente en dos fenómenos físicos:

### 4.1. Subgrupo A — 18 Casos en Zona Marítima, Estuarina o Fluvial (`CANTON_MAPA = NaN`)
Estos **18 registros SÍ caen en el agua** (zona marítima portuaria, esteros o ríos anchos), fuera de los polígonos de tierra firme del shapefile:
- **`EL ORO / MACHALA` (13 casos):** Ubicados en los muelles marítimos y esteros de Puerto Bolívar.
- **`GUAYAS / GUAYAQUIL` (2 casos):** Ubicados sobre el espejo de agua del Estero Salado.
- **`ESMERALDAS / ESMERALDAS` (1 caso):** Ubicado en la desembocadura del río Esmeraldas.
- **`GUAYAS / SAMBORONDON` (1 caso):** Ubicado sobre el cauce del río Babahoyo.
- **`MANABI / PORTOVIEJO` (1 caso):** Ubicado en la línea de playa de Crucita.

### 4.2. Subgrupo B — 12 Casos en Linderos Terrestres Intercantonales (`CANTON_MAPA != canton`)
Estos **12 registros NO están en el mar**, sino en **tierra firme sobre zonas fronterizas entre dos cantones contiguos**, donde la coordenada GPS cae dentro del polígono del cantón vecino inmediato:
- **Frontera `EL ORO / HUAQUILLAS` vs. `ARENILLAS` (6 casos):** Conurbación terrestre fronteriza entre Huaquillas y Arenillas.
- **Frontera `CARCHI / TULCAN` vs. `SAN PEDRO DE HUACA` (3 casos):** Eje vial terrestre entre Tulcán y Huaca.
- **Frontera `GUAYAS / ALFREDO BAQUERIZO MORENO (JUJAN)` vs. `SAN JACINTO DE YAGUACHI` (1 caso):** Límite rural terrestre ($2.7\text{ m}$).
- **Frontera `GUAYAS / BALZAR` vs. `LOS RIOS / MOCACHE` (1 caso):** Punto exactamente sobre la línea divisoria terrestre ($0.0\text{ m}$).
- **Frontera `TUNGURAHUA / TISALEO` vs. `MOCHA` (1 caso):** Límite terrestre intercantonal sobre la Panamericana Sur.

---

## 5. Cuadro Comparativo Final de Auditoría

| Indicador de Auditoría Geoespacial | Estado Inicial (Sin Homologación) | Estado Final (Con Homologación Legal + `Point-in-Polygon`) | Mejora Neta |
|---|---:|---:|---:|
| **Validados en 1ra auditoría (`geo_correctos`)** | `38,166` (`98.96%`) | **`38,535` (`99.92%`)** | **`+369` registros validados** |
| **Casos anómalos en `limbo_formato_correcto`** | `399` (`1.04%`) | **`30` (`0.08%`)** *(18 marítimos + 12 linderos)* | **`-369` casos (reducción del 92.5%)** |
| **Coordenadas descartadas irreversibles (`0, 0`)** | `1` (`0.0026%`) | **`1` (`0.0026%`)** | Sin cambio (`codigo_caso = 96547`) |
| **Total georreferenciado final (`homi_final`)** | `38,565` (`99.9974%`) | **`38,565` (`99.9974%`)** | **100% cuadre contable** |
| **Cantones únicos representados** | `220` (con nombres falsos y ZND sueltas) | **`211` cantones oficiales INEC** | 100% cantones reales de la DPA |
