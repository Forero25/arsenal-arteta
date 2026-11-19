"""Análisis principal: proceso de Arteta, comparación con los grandes, mérito frente al mercado,
comparación de modelos, clústeres y simulación. Lee data/premier.duckdb y escribe resultados/*.json."""
import json, os, sys
import duckdb
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
RES = "resultados"
GRANDES_MIN_PJ, GRANDES_MIN_PPP = 300, 1.9   # regla de datos para "los grandes" (ver README)
SEMILLA = 2026  # cada función crea su propio generador: resultados idénticos en cualquier máquina


def con():
    return duckdb.connect("data/premier.duckdb", read_only=True)


def guardar(nombre, obj):
    os.makedirs(RES, exist_ok=True)
    json.dump(obj, open(f"{RES}/{nombre}.json", "w"), ensure_ascii=False, indent=1, default=float)


def grandes(c):
    df = c.sql(f"SELECT * FROM carrera WHERE pj >= {GRANDES_MIN_PJ} AND ppp >= {GRANDES_MIN_PPP} ORDER BY ppp DESC").df()
    return df.entrenador.tolist()


def bootstrap_media(x, n=4000):
    x = np.asarray(x, float)
    x = x[~np.isnan(x)]
    if len(x) < 5:
        return [np.nan, np.nan]
    idx = np.random.default_rng(SEMILLA).integers(0, len(x), (n, len(x)))
    m = x[idx].mean(axis=1)
    return [float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))]


# 1. Validación: campeones y puntos calculados contra la historia conocida
def validacion(c):
    camp = c.sql("SELECT temporada, club, pts, entrenador FROM campeones WHERE temporada IN (SELECT temporada FROM temporadas_completas) ORDER BY temporada").df()
    return {"campeones": camp.to_dict("records"),
            "n_partidos": c.sql("SELECT count(*) FROM partidos").fetchall()[0][0],
            "temporadas": c.sql("SELECT min(temporada), max(temporada) FROM partidos").fetchall()[0],
            "sin_entrenador": c.sql("SELECT count(*) FROM ep WHERE entrenador IS NULL").fetchall()[0][0]}


# 2. Comparación de modelos: ¿quién predice mejor los resultados, el Elo propio o las casas de apuestas?
def modelos(c):
    d = c.sql("""SELECT p.temporada, p.gl, p.gv, e.esperado_l, p.p_l, p.p_e, p.p_v
                 FROM partidos p JOIN elo e USING (id) WHERE p.temporada >= 2013 AND p.p_l IS NOT NULL""").df()
    res = np.where(d.gl > d.gv, 1.0, np.where(d.gl == d.gv, 0.5, 0.0))
    mercado = d.p_l + 0.5 * d.p_e
    base = np.full(len(d), np.mean(res[: len(res) // 3]))  # siempre la media histórica de la localía
    def err(x): return float(np.mean((x - res) ** 2))
    return {"periodo": "2013-14 a la fecha (fuera de la calibración del Elo)", "n": int(len(d)),
            "error_cuadratico": {"constante": err(base), "elo": err(d.esperado_l), "mercado": err(mercado)}}


# 3. El proceso de Arteta y la comparación por temporada de gestión
def trayectorias(c, nombres):
    q = """SELECT entrenador, club, desde, temporada, temporada_gestion, pj, ppp, dg_pp, gf_pp, gc_pp,
                  sobre_mercado_pp, pj_con_cuotas, cuota_tiros, cuota_tiros_arco, elo_inicio, elo_fin, elo_medio, completa
           FROM gestion_temporada WHERE entrenador IN ({}) ORDER BY entrenador, desde, temporada""".format(
        ",".join("'" + n.replace("'", "''") + "'" for n in nombres))
    t = c.sql(q).df()
    t["desde"] = t["desde"].astype(str)
    serie = c.sql("""SELECT entrenador, club, cast(desde AS VARCHAR) AS desde, partido_gestion, temporada, temporada_gestion,
                            cast(fecha AS VARCHAR) AS fecha, elo
                     FROM etapa_partido WHERE entrenador IN ({}) ORDER BY entrenador, fecha""".format(
        ",".join("'" + n.replace("'", "''") + "'" for n in nombres))).df()
    return t, serie


def construccion(c):
    """Cuánto subió cada entrenador el nivel del club: Elo al llegar contra su mejor Elo de fin de temporada."""
    return c.sql("""
      WITH s AS (SELECT entrenador, club, desde, temporada_gestion, elo_inicio, elo_fin, pj FROM gestion_temporada
                 WHERE desde >= DATE '1993-07-01')  -- las etapas que empezaron antes de 1993-94 no tienen su punto de partida
      SELECT entrenador, club, cast(desde AS VARCHAR) AS desde,
             first(elo_inicio ORDER BY temporada_gestion) AS elo_llegada,
             max(elo_fin) AS elo_pico, max(elo_fin) - first(elo_inicio ORDER BY temporada_gestion) AS subida,
             arg_max(temporada_gestion, elo_fin) AS temporada_pico, sum(pj) AS pj
      FROM s GROUP BY ALL HAVING sum(pj) >= 100 ORDER BY subida DESC""").df()


# 4. Mérito frente al mercado, con intervalos
def mercado(c, nombres):
    out = {}
    for n in nombres:
        x = c.sql(f"""SELECT pts - pts_esperados_mercado AS s FROM etapa_partido
                      WHERE entrenador = '{n.replace("'", "''")}' AND pts_esperados_mercado IS NOT NULL""").df().s
        out[n] = {"pj": int(len(x)), "sobre_mercado_pp": float(x.mean()), "ic95": bootstrap_media(x),
                  "por_38": float(x.mean() * 38)}
    return out


# 5. Clústeres de perfiles de entrenador
def clusteres(c, min_pj=100):
    """Perfiles de entrenador desde 2000-01 (cuando hay tiros y cuotas para todos).
    Variables: puntos por partido, goles a favor y en contra, dominio de tiros, puntos sobre lo esperado por
    el mercado, subida de Elo del club y variabilidad entre temporadas. k = 2 se descarta de entrada porque solo
    separa "buenos" de "malos"; se elige k entre 3 y 6 por silueta y se contrasta con un método jerárquico."""
    from sklearn.preprocessing import StandardScaler
    from sklearn.cluster import KMeans, AgglomerativeClustering
    from sklearn.metrics import silhouette_score, adjusted_rand_score
    from sklearn.decomposition import PCA
    base = c.sql("""SELECT entrenador, count(*) pj, avg(pts) ppp, avg(gf) gf_pp, avg(gc) gc_pp,
                           avg(tiros / nullif(tiros + tiros_rival, 0)) cuota_tiros,
                           avg(pts - pts_esperados_mercado) sobre_mercado_pp
                    FROM etapa_partido WHERE temporada >= 2000 GROUP BY entrenador""").df()
    var = c.sql("SELECT entrenador, stddev_samp(ppp) variabilidad FROM gestion_temporada WHERE pj >= 19 AND temporada >= 2000 GROUP BY entrenador").df()
    cons = construccion(c).groupby("entrenador").subida.max().rename("subida_max").reset_index()
    tit = c.sql("SELECT entrenador, titulos FROM carrera").df()
    df = base[base.pj >= min_pj].merge(var, on="entrenador", how="left").merge(cons, on="entrenador", how="left").merge(tit, on="entrenador")
    feats = ["ppp", "gf_pp", "gc_pp", "cuota_tiros", "sobre_mercado_pp", "subida_max", "variabilidad"]
    df["subida_max"] = df["subida_max"].fillna(df["subida_max"].median())
    df["variabilidad"] = df["variabilidad"].fillna(df["variabilidad"].median())
    esc = StandardScaler().fit(df[feats])
    Z = esc.transform(df[feats])
    sil = {}
    for k in range(3, 7):
        km = KMeans(k, n_init=100, random_state=0).fit(Z)
        sil[k] = float(silhouette_score(Z, km.labels_))
    k = max(sil, key=sil.get)
    km = KMeans(k, n_init=100, random_state=0).fit(Z)
    ward = AgglomerativeClustering(k, linkage="ward").fit(Z)
    pca = PCA(2).fit(Z)
    P = pca.transform(Z)
    # numerar los grupos de mayor a menor puntos por partido, para que "grupo 0" sea siempre el de más nivel
    orden = pd.Series(km.labels_).groupby(km.labels_).apply(lambda i: df.ppp.iloc[i.index].mean()).sort_values(ascending=False)
    mapa = {g: i for i, g in enumerate(orden.index)}
    df["grupo"], df["pc1"], df["pc2"] = [mapa[x] for x in km.labels_], P[:, 0], P[:, 1]
    perfiles = df.groupby("grupo")[feats + ["pj"]].mean().reset_index()
    perfiles["n"] = df.groupby("grupo").size().values
    # Arteta por tramos de su etapa
    tramos = {}
    fila = df[df.entrenador == "Mikel Arteta"].iloc[0]
    for nombre, cond in {"temporadas_1_3": "temporada_gestion <= 3", "temporadas_4_8": "temporada_gestion >= 4"}.items():
        r = c.sql(f"""SELECT avg(pts) ppp, avg(gf) gf_pp, avg(gc) gc_pp, avg(tiros/nullif(tiros+tiros_rival,0)) cuota_tiros,
                             avg(pts - pts_esperados_mercado) sobre_mercado_pp
                      FROM etapa_partido WHERE entrenador='Mikel Arteta' AND {cond}""").df().iloc[0].to_dict()
        v = pd.DataFrame([{**r, "subida_max": fila.subida_max, "variabilidad": fila.variabilidad}])[feats]
        tramos[nombre] = {"grupo": mapa[int(km.predict(esc.transform(v))[0])], **{f: float(v[f].iloc[0]) for f in feats}}
    # ¿A quién se parece Arteta? Distancia en las variables estandarizadas, solo dentro de su grupo
    za = Z[df.entrenador.values == "Mikel Arteta"][0]
    df["distancia_arteta"] = np.sqrt(((Z - za) ** 2).sum(axis=1))
    ga = int(df.loc[df.entrenador == "Mikel Arteta", "grupo"].iloc[0])
    vecinos = df[(df.grupo == ga) & (df.entrenador != "Mikel Arteta")].nsmallest(5, "distancia_arteta")[["entrenador", "distancia_arteta"]]
    return {"vecinos_arteta": vecinos.to_dict("records"), "k": k, "silueta": sil, "acuerdo_kmeans_ward": float(adjusted_rand_score(km.labels_, ward.labels_)),
            "varianza_pca": pca.explained_variance_ratio_.tolist(), "variables": feats,
            "cargas_pca": {f: pca.components_[:, i].tolist() for i, f in enumerate(feats)},
            "perfiles": perfiles.to_dict("records"),
            "entrenadores": df[["entrenador", "pj", "titulos", "grupo", "pc1", "pc2", "distancia_arteta"] + feats].to_dict("records"),
            "arteta_tramos": tramos}


# 6. Simulación: ¿cuántos títulos podría sumar Arteta?
def _tablas(c):
    return c.sql("""SELECT temporada, club, pts, puesto FROM tabla
                    WHERE temporada BETWEEN 1995 AND (SELECT max(temporada) FROM temporadas_completas)""").df()


def _modelo_puntos(t, hasta=None):
    """Persistencia del nivel: puntos(t+1) = a + b · puntos(t) + ruido, con equipos que siguieron en Primera."""
    x = t.sort_values(["club", "temporada"]).copy()
    x["pts_sig"] = x.groupby("club").pts.shift(-1)
    x["temp_sig"] = x.groupby("club").temporada.shift(-1)
    x = x[(x.temp_sig == x.temporada + 1)]
    if hasta is not None:
        x = x[x.temp_sig <= hasta]
    A = np.column_stack([np.ones(len(x)), x.pts])
    coef, *_ = np.linalg.lstsq(A, x.pts_sig, rcond=None)
    sd = float(np.std(x.pts_sig - A @ coef, ddof=2))
    return coef, sd


def _umbral(t, hasta=None):
    """Máximo de puntos de los demás equipos, visto desde los que terminaron entre los 4 primeros."""
    x = t if hasta is None else t[t.temporada <= hasta]
    out = []
    for temp, g in x.groupby("temporada"):
        for _, f in g[g.puesto <= 4].iterrows():
            out.append(g[g.club != f.club].pts.max())
    return np.array(out, float)


def p_titulo(pts_previos, coef, sd, umbrales, n=20000, rng=None):
    rng = rng or np.random.default_rng(SEMILLA)
    pts = coef[0] + coef[1] * pts_previos + rng.normal(0, sd, n)
    return float((pts > rng.choice(umbrales, n)).mean())


def calibracion_simulacion(c):
    """Validación hacia adelante: para cada temporada desde 2005-06, se estima el modelo solo con el pasado y se
    predice la probabilidad de título de los 6 mejores de la temporada anterior. Se compara con lo que pasó."""
    t = _tablas(c)
    rng = np.random.default_rng(SEMILLA)
    filas = []
    for temp in range(2005, int(t.temporada.max()) + 1):
        coef, sd = _modelo_puntos(t, hasta=temp - 1)
        um = _umbral(t, hasta=temp - 1)
        prev = t[(t.temporada == temp - 1) & (t.puesto <= 6)]
        camp = t[(t.temporada == temp) & (t.puesto == 1)].club.iloc[0]
        for _, f in prev.iterrows():
            filas.append({"temporada": temp, "club": f.club, "p": p_titulo(f.pts, coef, sd, um, 5000, rng), "campeon": f.club == camp})
    d = pd.DataFrame(filas)
    d["tramo"] = pd.cut(d.p, [0, .1, .25, .5, 1], include_lowest=True, labels=["0-10 %", "10-25 %", "25-50 %", "50-100 %"]).astype(str)
    tabla = d.groupby("tramo").agg(n=("p", "size"), p_media=("p", "mean"), frecuencia=("campeon", "mean")).reset_index()
    brier = float(np.mean((d.p - d.campeon) ** 2))
    base = float(np.mean((d.campeon.mean() - d.campeon) ** 2))
    return {"tabla": tabla.to_dict("records"), "brier": brier, "brier_base": base, "n": int(len(d))}


def pronostico_actual():
    """Probabilidad de título de la temporada en curso: copia de la salida del proyecto premier-pronostico
    (modelo Poisson, 20.000 simulaciones), guardada en entradas/ con la fecha de sus datos."""
    pr = json.load(open("entradas/premier_pronostico.json"))
    md = json.load(open("entradas/premier_pronostico_metadata.json"))
    a = next(x for x in pr if x["equipo"].startswith("Arsenal"))
    return {"p_campeon": a["p_campeon"], "puntos": a["puntos"], "pj": a["pj"], "datos_hasta": md["datos_hasta"],
            "fuente": "proyecto premier-pronostico (Poisson, 20.000 simulaciones)"}


def simulacion(c, n=20000, horizonte=8):
    """Monte Carlo de las próximas temporadas de Arteta.
    - Temporada en curso (2026-27): probabilidad del proyecto premier-pronostico.
    - Siguientes: puntos(t+1) = a + b · puntos(t) + ruido; título si supera el máximo de los demás, tomado de la
      distribución histórica. Parte de los 85 puntos de 2025-26 y no supone ni declive ni mejora del entrenador."""
    t = _tablas(c)
    coef, sd = _modelo_puntos(t)
    um = _umbral(t)
    actual = pronostico_actual()
    ultimo = float(t[(t.club == "Arsenal") & (t.temporada == t.temporada.max())].pts.iloc[0])
    p0 = actual.get("p_campeon", np.nan)
    RNG = np.random.default_rng(SEMILLA)
    pts = np.full(n, ultimo)
    titulos = np.zeros((n, horizonte), int)
    for h in range(horizonte):
        nuevos = coef[0] + coef[1] * pts + RNG.normal(0, sd, n)
        if h == 0 and not np.isnan(p0):
            titulos[:, 0] = RNG.random(n) < p0
            # los puntos de 2026-27 siguen la misma persistencia para alimentar las temporadas siguientes
        else:
            titulos[:, h] = nuevos > RNG.choice(um, n)
        pts = nuevos
    acum = titulos.cumsum(axis=1)
    metas = {"Klopp": 1, "Wenger": 3, "Mourinho": 3, "Guardiola": 6, "Ferguson": 13}
    tabla = {}
    for h in range(horizonte):
        total = 1 + acum[:, h]   # ya ganó 2025-26
        tabla[h + 1] = {"titulos_esperados": float(total.mean()),
                        "p_al_menos": {str(v): float((total >= v).mean()) for v in (2, 3, 4, 6)},
                        "percentiles_10_50_90": [float(np.percentile(total, q)) for q in (10, 50, 90)]}
    return {"modelo": {"a": float(coef[0]), "b": float(coef[1]), "sd": sd, "umbral_mediana": float(np.median(um))},
            "puntos_2025_26": ultimo, "temporada_en_curso": actual, "metas": metas, "n_sim": n,
            "por_temporadas": tabla, "calibracion": calibracion_simulacion(c)}


def main():
    c = con()
    g = grandes(c)
    nombres = sorted(set(g) | {"Mikel Arteta"})
    todos = c.sql("SELECT entrenador FROM carrera WHERE pj >= 100").df().entrenador.tolist()
    t, serie = trayectorias(c, todos)
    guardar("validacion", validacion(c))
    guardar("modelos", modelos(c))
    guardar("grandes", {"regla": {"min_pj": GRANDES_MIN_PJ, "min_ppp": GRANDES_MIN_PPP}, "grandes": g,
                        "carrera": c.sql("SELECT * EXCLUDE (primer_partido, ultimo_partido), cast(primer_partido AS VARCHAR) AS primer_partido FROM carrera WHERE pj >= 100 ORDER BY ppp DESC").df().to_dict("records")})
    guardar("trayectorias", {"temporadas": t[t.entrenador.isin(nombres)].to_dict("records")})
    guardar("construccion", construccion(c).to_dict("records"))
    guardar("campeones_elo", c.sql("""
        SELECT ca.temporada, ca.club, ca.pts, ca.entrenador, last(e.elo ORDER BY e.fecha) AS elo_fin,
               avg(e.pts - e.pts_esperados_mercado) AS sobre_mercado_pp,
               (SELECT t2.pts FROM tabla t2 WHERE t2.temporada = ca.temporada AND t2.puesto = 2 LIMIT 1) AS pts_segundo
        FROM campeones ca JOIN ep e ON e.temporada = ca.temporada AND e.club = ca.club
        WHERE ca.temporada IN (SELECT temporada FROM temporadas_completas)
        GROUP BY ALL ORDER BY elo_fin DESC""").df().to_dict("records"))
    guardar("mercado", mercado(c, nombres))
    guardar("clusteres", clusteres(c))
    guardar("simulacion", simulacion(c))
    os.makedirs("publicado", exist_ok=True)
    serie.to_csv("publicado/elo_por_partido.csv", index=False)
    t.to_csv("publicado/temporadas_gestion.csv", index=False)
    print("grandes:", g)


if __name__ == "__main__":
    main()
