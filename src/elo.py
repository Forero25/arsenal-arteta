"""Rating Elo propio para todos los equipos de la Premier League, partido a partido.

Elo resume la fuerza de un equipo en un número: gana puntos cuando le va mejor de lo esperado y los pierde
cuando le va peor. La expectativa del local es E = 1 / (1 + 10^(-(R_l + H - R_v) / 400)), donde H es la
ventaja de jugar en casa. Tras el partido, cada equipo suma K · M · (resultado − E), con resultado 1, 0,5 o 0
y M un multiplicador que crece con la diferencia de goles (una goleada dice más que un 1-0).
Entre temporadas cada rating se acerca un poco a la media (los planteles cambian), y un recién ascendido
entra con el promedio de los que descendieron.
"""
import numpy as np
import pandas as pd

INICIO = 1500.0


def multiplicador(dg):
    dg = abs(dg)
    return np.where(dg <= 1, 1.0, np.where(dg == 2, 1.5, (11 + dg) / 8))


def correr(p: pd.DataFrame, K=20.0, H=60.0, regresion=0.2):
    r = {}
    filas = []
    temporada_ant = None
    for t, grupo in p.groupby("temporada", sort=True):
        equipos = set(grupo.local) | set(grupo.visita)
        if temporada_ant is not None:
            media = np.mean(list(r.values()))
            salieron = [e for e in r if e not in equipos]
            base_ascendido = np.mean([r[e] for e in salieron]) if salieron else media
            r = {e: v + regresion * (media - v) for e, v in r.items() if e in equipos}
            for e in equipos - set(r):
                r[e] = base_ascendido
        else:
            r = {e: INICIO for e in equipos}
        for row in grupo.itertuples():
            rl, rv = r[row.local], r[row.visita]
            e = 1 / (1 + 10 ** (-(rl + H - rv) / 400))
            res = 1.0 if row.gl > row.gv else 0.5 if row.gl == row.gv else 0.0
            d = K * float(multiplicador(row.gl - row.gv)) * (res - e)
            filas.append((row.id, rl, rv, e))
            r[row.local], r[row.visita] = rl + d, rv - d
        temporada_ant = t
    out = pd.DataFrame(filas, columns=["id", "elo_l", "elo_v", "esperado_l"]).set_index("id")
    return out


def puntaje(p, elo, desde=1995):
    """Error cuadrático entre la expectativa Elo y el resultado (1/0,5/0), fuera de las dos primeras temporadas."""
    m = p.join(elo, on="id")
    m = m[m.temporada >= desde]
    res = np.where(m.gl > m.gv, 1.0, np.where(m.gl == m.gv, 0.5, 0.0))
    return float(np.mean((m.esperado_l - res) ** 2))


def calibrar(p):
    mejor = None
    filas = []
    for K in (15, 20, 25, 30, 35):
        for H in (40, 60, 80, 100):
            for reg in (0.0, 0.1, 0.2, 0.3):
                s = puntaje(p, correr(p, K, H, reg))
                filas.append((K, H, reg, s))
                if mejor is None or s < mejor[3]:
                    mejor = (K, H, reg, s)
    return mejor, pd.DataFrame(filas, columns=["K", "H", "regresion", "error"])
