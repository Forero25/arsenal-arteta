"""Partidos de la Premier League desde 1993-94 (football-data.co.uk) y quién dirigió a cada equipo."""
import glob, os, re
import numpy as np
import pandas as pd

NOMBRES = {  # football-data -> Wikipedia
    "Birmingham": "Birmingham City", "Blackburn": "Blackburn Rovers", "Bolton": "Bolton Wanderers",
    "Bradford": "Bradford City", "Brighton": "Brighton & Hove Albion", "Cardiff": "Cardiff City",
    "Charlton": "Charlton Athletic", "Coventry": "Coventry City", "Derby": "Derby County",
    "Huddersfield": "Huddersfield Town", "Hull": "Hull City", "Ipswich": "Ipswich Town", "Leeds": "Leeds United",
    "Leicester": "Leicester City", "Luton": "Luton Town", "Man City": "Manchester City",
    "Man United": "Manchester United", "Newcastle": "Newcastle United", "Norwich": "Norwich City",
    "Nott'm Forest": "Nottingham Forest", "Oldham": "Oldham Athletic", "QPR": "Queens Park Rangers",
    "Sheffield Weds": "Sheffield Wednesday", "Stoke": "Stoke City", "Swansea": "Swansea City",
    "Swindon": "Swindon Town", "Tottenham": "Tottenham Hotspur", "West Brom": "West Bromwich Albion",
    "West Ham": "West Ham United", "Wigan": "Wigan Athletic", "Wolves": "Wolverhampton Wanderers",
}
CASAS = ["B365", "BW", "GB", "IW", "LB", "SB", "WH", "SJ", "VC", "BS", "PS", "BF", "BV", "SK", "PP"]


def probabilidades(df):
    """Probabilidad implícita promedio entre casas de apuestas, quitando el margen de cada una."""
    ps = []
    for c in CASAS:
        cols = [f"{c}H", f"{c}D", f"{c}A"]
        if all(x in df for x in cols):
            o = df[cols].apply(pd.to_numeric, errors="coerce")
            inv = 1 / o
            ps.append(inv.div(inv.sum(axis=1), axis=0).to_numpy())
    if not ps:
        return np.full((len(df), 3), np.nan), np.zeros(len(df), int)
    arr = np.stack(ps)                       # casas x partidos x 3
    n = np.sum(~np.isnan(arr[:, :, 0]), axis=0)
    with np.errstate(all="ignore"):
        prom = np.nanmean(arr, axis=0)
    return prom, n


def leer_csv(f):
    """Algunas temporadas traen filas con más columnas que el encabezado (cuotas extra al final):
    se conservan las columnas del encabezado y se descarta lo que sobra, sin perder partidos."""
    import csv, io
    filas = list(csv.reader(io.open(f, encoding="latin1")))
    cab = [c.strip().lstrip("\ufeff").lstrip("ï»¿") for c in filas[0]]
    cuerpo = [r[:len(cab)] + [""] * (len(cab) - len(r)) for r in filas[1:] if any(x.strip() for x in r)]
    return pd.DataFrame(cuerpo, columns=cab).replace("", np.nan)


def cargar(raw="data/raw/football-data"):
    out = []
    for f in sorted(glob.glob(f"{raw}/E0_*.csv")):
        anio = int(re.search(r"E0_(\d{4})", f).group(1))
        d = leer_csv(f)
        d = d.dropna(subset=["HomeTeam", "AwayTeam", "FTHG", "FTAG"])
        fecha = pd.to_datetime(d["Date"], dayfirst=True, format="mixed")
        p, n = probabilidades(d)
        x = pd.DataFrame({
            "temporada": anio, "fecha": fecha.dt.date,
            "local": d["HomeTeam"].map(lambda t: NOMBRES.get(t, t)),
            "visita": d["AwayTeam"].map(lambda t: NOMBRES.get(t, t)),
            "gl": pd.to_numeric(d["FTHG"]).astype(int), "gv": pd.to_numeric(d["FTAG"]).astype(int),
            "tiros_l": pd.to_numeric(d.get("HS"), errors="coerce"), "tiros_v": pd.to_numeric(d.get("AS"), errors="coerce"),
            "arco_l": pd.to_numeric(d.get("HST"), errors="coerce"), "arco_v": pd.to_numeric(d.get("AST"), errors="coerce"),
            "xg_l": pd.to_numeric(d.get("HxG"), errors="coerce"), "xg_v": pd.to_numeric(d.get("AxG"), errors="coerce"),
            "p_l": p[:, 0], "p_e": p[:, 1], "p_v": p[:, 2], "n_casas": n,
        })
        out.append(x)
    df = pd.concat(out, ignore_index=True).sort_values(["fecha", "local"]).reset_index(drop=True)
    df["fecha"] = pd.to_datetime(df["fecha"])
    df["id"] = np.arange(len(df))
    return df


def asignar(partidos, entrenadores):
    """Entrenador de cada equipo en cada partido: el que estaba a cargo ese día (si hay solapamiento, el más reciente)."""
    e = entrenadores.copy()
    e["desde"], e["hasta"] = pd.to_datetime(e["desde"]), pd.to_datetime(e["hasta"])
    filas = []
    for lado, eq in (("l", "local"), ("v", "visita")):
        m = partidos[["id", "fecha", eq]].rename(columns={eq: "club"}).merge(e, on="club", how="left")
        m = m[(m.fecha >= m.desde) & (m.fecha <= m.hasta)].sort_values("desde").drop_duplicates("id", keep="last")
        filas.append(m.set_index("id")[["entrenador", "interino"]].add_suffix(f"_{lado}"))
    return partidos.join(filas[0], on="id").join(filas[1], on="id")


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(__file__))
    from entrenadores import cargar as cargar_e
    p = asignar(cargar(), cargar_e())
    print(p.shape, p.temporada.min(), p.temporada.max())
    print(p.groupby("temporada").size().to_string())
    print("sin entrenador local/visita:", p.entrenador_l.isna().sum(), p.entrenador_v.isna().sum())
    print(p[p.entrenador_l.isna() | p.entrenador_v.isna()][["fecha", "local", "visita", "entrenador_l", "entrenador_v"]].head(30).to_string())
    print("con cuotas:", p.p_l.notna().groupby(p.temporada).mean().round(2).to_dict())
