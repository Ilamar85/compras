#!/usr/bin/env python3
"""
Monitor de precio: Cama Europea CIC New Ortopedic 2 Plazas Base Dividida.
Revisa Hites, Paris, Ripley y Mercado Libre Chile, guarda historial en CSV
y JSON del último resultado. Pensado para correr vía GitHub Actions cada 3 días.
"""

import csv
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CSV_PATH = DATA_DIR / "precios_historial.csv"
LATEST_JSON_PATH = DATA_DIR / "precios_latest.json"

UMBRAL_BUENO = 300_000
UMBRAL_ALTO = 350_000

TIENDAS = {
    "Hites": "https://www.hites.com/cama-europea-cic-new-ortopedic-2-plazas-base-dividida-793171001.html",
    "Paris": "https://www.paris.cl/cama-europea-new-ortopedic-2-plazas-base-dividida-377000999.html",
    "Ripley": "https://simple.ripley.cl/cama-europea-cic-new-ortopedic-2-plazas-2000372222275p",
    "Lider": "https://www.lider.cl/ip/combos-dormitorio/cama-europea-europea-new-ortopedic-2-plaza-base-dividida-2-almohadas/00780642760258",
}

PRICE_RE = re.compile(r"\$\s?([\d.]{5,10})")


def parse_price_from_text(text: str) -> list[int]:
    """Extrae todos los precios tipo $319.990 encontrados en un texto."""
    matches = PRICE_RE.findall(text)
    precios = []
    for m in matches:
        limpio = m.replace(".", "")
        if limpio.isdigit():
            valor = int(limpio)
            if 50_000 < valor < 2_000_000:  # rango plausible para esta cama
                precios.append(valor)
    return sorted(set(precios))


def fetch_precio(tienda: str, url: str) -> dict:
    resultado = {
        "tienda": tienda,
        "url": url,
        "precios_encontrados": [],
        "precio_minimo": None,
        "verificado": False,
        "error": None,
    }
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # 1. Intentar meta-tags Open Graph (más confiable si existen)
        og_price = soup.find("meta", {"property": "product:price:amount"}) or soup.find(
            "meta", {"property": "og:price:amount"}
        )
        precios = []
        if og_price and og_price.get("content"):
            try:
                precios.append(int(float(og_price["content"])))
            except ValueError:
                pass

        # 2. Fallback: buscar patrones $xxx.xxx en el texto visible
        if not precios:
            precios = parse_price_from_text(soup.get_text(" "))

        if precios:
            resultado["precios_encontrados"] = precios
            resultado["precio_minimo"] = min(precios)
            resultado["verificado"] = True
        else:
            resultado["error"] = "No se encontró un precio en la página (posible render JS)"

    except requests.RequestException as exc:
        resultado["error"] = str(exc)

    return resultado


def fetch_mercadolibre() -> dict:
    resultado = {
        "tienda": "Mercado Libre Chile",
        "url": None,
        "precios_encontrados": [],
        "precio_minimo": None,
        "verificado": False,
        "error": None,
    }
    query = "cama europea CIC new ortopedic 2 plazas base dividida"
    api_url = f"https://api.mercadolibre.com/sites/MLC/search?q={requests.utils.quote(query)}"
    try:
        resp = requests.get(api_url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        candidatos = []
        for item in data.get("results", [])[:10]:
            titulo = item.get("title", "").lower()
            if "respaldo" in titulo or "velador" in titulo or "closet" in titulo or "comoda" in titulo:
                continue  # excluir versiones con muebles extra
            if "new ortopedic" in titulo or "ortopedic" in titulo:
                candidatos.append(item)

        if candidatos:
            barato = min(candidatos, key=lambda i: i.get("price", float("inf")))
            resultado["precios_encontrados"] = [int(c["price"]) for c in candidatos]
            resultado["precio_minimo"] = int(barato["price"])
            resultado["url"] = barato.get("permalink")
            resultado["verificado"] = True
        else:
            resultado["error"] = "Sin publicaciones exactas del producto (solo colchón suelto o con muebles)"

    except (requests.RequestException, ValueError, KeyError) as exc:
        resultado["error"] = str(exc)

    return resultado


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).isoformat()

    resultados = [fetch_precio(t, u) for t, u in TIENDAS.items()]
    resultados.append(fetch_mercadolibre())

    # Guardar historial CSV (append)
    nuevo_archivo = not CSV_PATH.exists()
    with CSV_PATH.open("a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if nuevo_archivo:
            writer.writerow(["fecha_utc", "tienda", "precio_minimo", "verificado", "url", "error"])
        for r in resultados:
            writer.writerow(
                [timestamp, r["tienda"], r["precio_minimo"], r["verificado"], r["url"], r["error"]]
            )

    # Guardar último snapshot en JSON
    snapshot = {"fecha_utc": timestamp, "resultados": resultados}
    LATEST_JSON_PATH.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False), encoding="utf-8")

    # Resumen en consola / logs de GitHub Actions
    print(f"\n=== Revisión de precios — {timestamp} ===")
    verificados = [r for r in resultados if r["verificado"]]
    for r in resultados:
        estado = f"${r['precio_minimo']:,}".replace(",", ".") if r["verificado"] else f"NO VERIFICADO ({r['error']})"
        print(f"  {r['tienda']:<20} {estado}")

    if verificados:
        mejor = min(verificados, key=lambda r: r["precio_minimo"])
        print(f"\nMejor precio: {mejor['tienda']} — ${mejor['precio_minimo']:,}".replace(",", ".") + f" — {mejor['url']}")

        if mejor["precio_minimo"] <= UMBRAL_BUENO:
            print("=> BAJO EL UMBRAL DE BUEN PRECIO. Considerar comprar.")
            # Señal para el workflow: crea GH issue solo si conviene
            gh_output = os.environ.get("GITHUB_OUTPUT")
            if gh_output:
                with open(gh_output, "a", encoding="utf-8") as f:
                    f.write("buen_precio=true\n")
                    f.write(f"mejor_tienda={mejor['tienda']}\n")
                    f.write(f"mejor_precio={mejor['precio_minimo']}\n")
                    f.write(f"mejor_url={mejor['url']}\n")
        else:
            gh_output = os.environ.get("GITHUB_OUTPUT")
            if gh_output:
                with open(gh_output, "a", encoding="utf-8") as f:
                    f.write("buen_precio=false\n")
    else:
        print("\nNingún precio pudo verificarse en esta corrida.")
        sys.exit(1)


if __name__ == "__main__":
    import os
    main()
