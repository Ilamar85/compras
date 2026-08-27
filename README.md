# monitor-precio-cama

Revisa cada 3 días el precio de la **Cama Europea CIC New Ortopedic 2 Plazas Base Dividida** (sin respaldo ni muebles) en Hites, Paris, Ripley, Lider y Mercado Libre Chile. Corre gratis en GitHub Actions, sin tokens de Claude.

## Setup

1. Crear repo en GitHub (público o privado) y subir estos archivos.
2. En **Settings → Actions → General → Workflow permissions**, activar "Read and write permissions" (para que el workflow pueda hacer commit y crear issues).
3. Listo. El workflow corre solo cada 3 días (`cron: 0 12 */3 * *`).

## Ejecutar manualmente

En GitHub: pestaña **Actions → Monitor precio cama CIC New Ortopedic → Run workflow**.

O local:
```bash
pip install -r requirements.txt
python scripts/check_precio.py
```

## Resultados

- `data/precios_historial.csv` — historial completo, una fila por tienda por corrida.
- `data/precios_latest.json` — snapshot de la última revisión.
- Si el mejor precio encontrado es ≤ $300.000, se crea automáticamente un **GitHub Issue** de alerta.

## Limitaciones conocidas

- **Lider.cl** renderiza el precio con JavaScript; el fetch simple puede fallar. Si pasa, queda registrado como `verificado=False` con el motivo, no se omite silenciosamente.
- Si Hites/Paris/Ripley cambian su HTML, el parser de precios ($xxx.xxx) puede requerir ajuste.
- Mercado Libre usa la API pública oficial (`api.mercadolibre.com`), más estable que scraping directo.

## Pedirle a Claude que analice los datos

Cuando quieras, puedes pegarle a Claude el contenido de `data/precios_latest.json` o el CSV y pedir un análisis — ahí sí se usan tokens, pero solo cuando tú lo decides, no en cada corrida automática.
