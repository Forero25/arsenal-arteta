"""Descarga los datos crudos a data/raw/ (no se versionan).

- football-data.co.uk: un CSV por temporada de la Premier League (E0) desde 1993-94, con resultados,
  tiros (desde 2000-01) y cuotas de casas de apuestas.
- Wikipedia: la lista de entrenadores de la Premier League, con sus fechas en cada club.
"""
import os, sys, time, urllib.request

UA = {"User-Agent": "arsenal-arteta portfolio project (github.com/Forero25/arsenal-arteta)"}
RAW = "data/raw"


def bajar(url, destino, intentos=3):
    for i in range(intentos):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=60) as r:
                datos = r.read()
            open(destino, "wb").write(datos)
            return len(datos)
        except Exception as e:  # noqa: BLE001
            print("reintento", url, e, file=sys.stderr)
            time.sleep(3 * (i + 1))
    raise SystemExit(f"No se pudo bajar {url}")


def temporadas(hasta=2026):
    for a in range(1993, hasta + 1):
        yield f"{a % 100:02d}{(a + 1) % 100:02d}", a


def main():
    os.makedirs(f"{RAW}/football-data", exist_ok=True)
    for cod, a in temporadas():
        n = bajar(f"https://www.football-data.co.uk/mmz4281/{cod}/E0.csv", f"{RAW}/football-data/E0_{a}.csv")
        print(cod, n)
        time.sleep(0.5)
    os.makedirs(f"{RAW}/wikipedia", exist_ok=True)
    for pag in ["List_of_Premier_League_managers"]:
        api = f"https://en.wikipedia.org/w/api.php?action=parse&page={pag}&format=json&prop=text|wikitext&formatversion=2"
        print(pag, bajar(api, f"{RAW}/wikipedia/{pag}.json"))


if __name__ == "__main__":
    main()
