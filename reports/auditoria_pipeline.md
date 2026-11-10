# Auditoría Estadística Integral del Pipeline (Fases 1 a 5)

- **Fecha de generación (UTC):** `2026-11-10T16:18:09Z`
- **Integridad contable extremo a extremo:** **VERIFICADA (100% cuadre contable)**
- **Cobertura temporal validada:** `2010-01-01 a 2024-12-31`
- **Cobertura territorial continental:** `23` provincias | `214` cantones
- **Esquema consolidado:** `21` columnas limpias

## 1. Trazabilidad del Ciclo de Vida de los Registros

| Etapa del Pipeline | Registros | Porcentaje |
|---|---:|---:|
| Registros brutos iniciales (CSV 2010–2025) | 47,739 | 100.00% |
| (-) Excluidos por filtro temporal (`anio_hecho > 2024`) | 9,171 | — |
| (-) Excluidos por filtro insular (Galápagos) | 2 | — |
| **(=) Universo continental de análisis (2010–2024)** | **38,566** | **80.79%** |
| (+) Validados en 1ra auditoría punto-en-polígono | 38,503 | 99.84% |
| (+) Rescatados por algoritmo reparador decimal (4 escenarios) | 0 | 0.00% (sobre corruptos) |
| (+) Retenidos en limbo con formato decimal válido | 62 | — |
| (-) Coordenadas descartadas irreversibles | 1 | — |
| **(=) REGISTROS FINALES ETIQUETADOS Y GEORREFERENCIADOS** | **38,565** | **99.9974%** |

## 2. Indicadores Clave de Efectividad

- **Efectividad general de georreferenciación (sobre universo 2010–2024):** `99.9974%`
- **Tasa de retención global (bruto inicial → entregable final):** `80.78%`
- **Candidatos sin punto decimal evaluados por algoritmo reparador:** `1` (rescatados: `0`, descartados irreversibles: `1`)
