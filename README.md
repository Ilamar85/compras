# compras
# Revisión de Costos

Herramienta en Python para consolidar, clasificar y auditar el gasto doméstico a partir de boletas electrónicas chilenas, y comparar precios entre las tiendas donde efectivamente se compra.

Datos base: `data/Listado_de_Compras.xlsx` — 157 documentos entre **2019-11** y **2026-08**, 91 compras válidas por **$6.300.887** en 28 comercios.

---

## Qué resuelve

| Necesidad | Comando |
|---|---|
| Saber en qué se va la plata (categoría, local, mes, año) | `resumen` |
| Informe Excel con KPIs, tablas y gráficos | `reporte` |
| Detectar boletas duplicadas y documentos que no son gasto | automático |
| Ver qué productos se repiten y cuánto varió su precio | `recurrentes`, `historial` |
| Comparar el mismo producto entre tiendas, con despacho y precio por unidad | `buscar`, `cotizar`, `comparar` |
| Controlar gasto real contra presupuesto por categoría | `presupuesto` |

---

## Instalación

```bash
git clone <url-del-repo>
cd revision-costos
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -e .                                       # opcional: habilita el comando revision-costos
```

Requiere Python 3.10 o superior.

---

## Uso

Sin instalar el paquete, anteponer `PYTHONPATH=src python -m revision_costos`. Con `pip install -e .`, usar directamente `revision-costos`.

```bash
# KPIs y resúmenes en consola
revision-costos --hoja "Listado Completo" resumen

# Informe Excel completo en reportes/
revision-costos --hoja "Listado Completo" reporte

# Control presupuestario de un mes específico
revision-costos --hoja "Listado Completo" presupuesto --periodo 2026-08

# Productos comprados más de una vez, con dispersión de precio
revision-costos --hoja "Listado Completo" recurrentes

# Historial de precio de un producto
revision-costos --hoja "Listado Completo" historial "goodnites"
```

### Comparación de precios

```bash
# 1. URLs de búsqueda en las tiendas aplicables a la categoría
revision-costos buscar "pañales goodnites talla g" --categoria panales

# 2. Planilla de cotización para completar con los precios observados
revision-costos cotizar "Pañales Goodnites G" --categoria panales --salida reportes/cotizacion.csv

# 3. Evaluación: precio por unidad, mejor tienda y ahorro
revision-costos comparar reportes/cotizacion.csv
```

Salida de ejemplo:

```
producto             mejor_tienda  precio_unitario_min  ahorro_unitario  ahorro_%
Pañales Goodnites G  Líder                        1356              143       9.5
```

El comparador normaliza a **precio por unidad incluyendo despacho**, de modo que un pack más barato con envío pagado no gana frente a uno con despacho gratis.

---

## Estructura

```
revision-costos/
├── config/
│   ├── tiendas.yaml         # tiendas priorizadas, URLs de búsqueda y alias de sucursales
│   └── categorias.yaml      # reglas de clasificación y presupuestos mensuales
├── data/
│   ├── Listado_de_Compras.xlsx
│   └── raw/                 # boletas originales (no versionadas)
├── reportes/                # salidas generadas (no versionadas)
├── src/revision_costos/
│   ├── carga.py             # lectura de Excel/CSV y normalización de encabezados
│   ├── normaliza.py         # tienda canónica, categoría, duplicados
│   ├── analisis.py          # KPIs y resúmenes
│   ├── comparador.py        # comparación de precios entre tiendas
│   ├── reporte.py           # exportación a Excel con formato y gráficos
│   └── cli.py               # interfaz de línea de comandos
└── tests/
```

---

## Formato de entrada

El archivo de gastos debe tener al menos estas columnas (los nombres se reconocen con variantes en `carga.MAPA_COLUMNAS`):

| Columna | Obligatoria | Descripción |
|---|---|---|
| `Local` | sí | Comercio emisor de la boleta |
| `Fecha` | sí | Fecha del documento |
| `Producto / Descripción` | sí | Detalle de lo comprado |
| `Monto ($)` | sí | Monto en pesos |
| `Categoría` | no | Tipo de documento origen (Compra, Duplicado, Ticket de cambio…) |
| `Observaciones` | no | Notas libres |
| `Archivo de respaldo` | no | Nombre del archivo de la boleta |

---

## Reglas de negocio

**Qué cuenta como gasto.** Se excluyen del total las filas cuya categoría origen sea `Duplicado`, `Ticket de cambio`, `Nota de crédito`, `Guía de despacho` o `Términos y condiciones`, las filas sin monto y las detectadas como duplicadas.

**Detección de duplicados.** Se marca duplicada una fila que repite local + fecha + monto de una anterior. Solo aplica a filas con fecha y monto: sin ambos datos no hay evidencia suficiente.

**Consolidación de tiendas.** Las sucursales y canales se agrupan bajo un id canónico según `config/tiendas.yaml` → `alias`. Así `Paris` y `Paris.cl` suman juntos, igual que `Falabella`, `Falabella (Internet)` y `Falabella (Concepción)`.

**Clasificación.** Por palabras clave sobre descripción y local, evaluadas en el orden de `config/categorias.yaml`. Lo no reconocido cae en `otros`. Para mejorar la precisión, agregar palabras a la categoría correspondiente en ese archivo.

**Prioridad de tiendas.** Las búsquedas usan el orden de `prioridad` de `config/tiendas.yaml`, construido a partir de los comercios presentes en las boletas históricas. **Mercado Libre Chile se incluye siempre**, en cualquier categoría, vía la marca `incluir_siempre: true`.

---

## Configuración

Agregar una tienda nueva en `config/tiendas.yaml`:

```yaml
  - id: nueva_tienda
    nombre: Nueva Tienda
    url_busqueda: "https://www.nuevatienda.cl/search?q={q}"
    prioridad: 14
    categorias: [hogar, tecnologia]
```

Ajustar un presupuesto en `config/categorias.yaml`:

```yaml
  supermercado:
    palabras: [...]
    presupuesto_mensual: 450000
```

---

## Limitaciones

- No hace scraping automático: varios retailers chilenos renderizan precios con JavaScript y bloquean peticiones automatizadas. Líder en particular debe verificarse en su app o sitio. El flujo `cotizar` → `comparar` está diseñado para captura manual o semiautomática.
- Los montos se toman tal como vienen en la planilla; no se ajustan por inflación ni UF.
- La clasificación por palabras clave requiere mantención a medida que aparecen productos nuevos.

---

## Pruebas

```bash
PYTHONPATH=src python -m pytest tests -q
```

---

## Uso como librería

```python
from revision_costos import cargar_gastos, normalizar
from revision_costos.analisis import resumen_por_categoria, kpis
from revision_costos.reporte import generar_reporte

df = normalizar(cargar_gastos("data/Listado_de_Compras.xlsx", "Listado Completo"))
print(kpis(df))
print(resumen_por_categoria(df))
generar_reporte(df, "reportes/informe.xlsx")
```
