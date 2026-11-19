"""Fechas de cada entrenador en cada club, desde el wikitext de "List of Premier League managers" (Wikipedia, CC BY-SA 4.0)."""
import json, re
from datetime import date
import pandas as pd

DTS = re.compile(r"\{\{dts\|(?:format=dmy\|)?(\d{4})\|(\d{1,2})\|(\d{1,2})\}\}")


def nombre(fila):
    m = re.search(r"\{\{sortname\|([^|}]+)\|([^|}]+)", fila)
    if m:
        return f"{m.group(1).strip()} {m.group(2).strip()}"
    m = re.search(r"\[\[(?:[^\]|]+\|)?([^\]]+)\]\]", fila.split("\n")[0])
    return m.group(1).strip() if m else None


def parsear(wikitext, hoy=None):
    hoy = hoy or date.today()
    ini = wikitext.find('|+Managers')
    fin = wikitext.find("\n|}", ini)
    filas = wikitext[ini:fin].split("\n|-")[1:]
    out = []
    for f in filas:
        lineas = [l for l in f.strip().split("\n") if l.strip()]
        if not lineas or "scope=\"row\"" not in lineas[0] and "scope=row" not in lineas[0].replace('"', ''):
            continue
        club = re.search(r"\n\|\[\[(?:[^\]|]+\|)?([^\]]+)\]\]", f)
        fechas = DTS.findall(f)
        if not club or not fechas:
            continue
        desde = date(*map(int, fechas[0]))
        hasta = date(*map(int, fechas[1])) if len(fechas) > 1 else hoy
        out.append({"entrenador": nombre(lineas[0]), "club": club.group(1).strip(), "desde": desde, "hasta": hasta,
                    "interino": "double dagger" in lineas[0], "vigente": len(fechas) == 1})
    return pd.DataFrame(out)


def cargar(ruta="data/raw/wikipedia/List_of_Premier_League_managers.json"):
    w = json.load(open(ruta))["parse"]["wikitext"]
    return parsear(w)


if __name__ == "__main__":
    e = cargar()
    print(len(e), e.interino.sum(), e.vigente.sum())
    print(e[e.club == "Arsenal"].to_string())
    print(e[e.vigente].to_string())
