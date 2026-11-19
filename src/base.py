"""Construye la base DuckDB (data/premier.duckdb) con partidos, entrenadores, Elo y una vista por equipo y partido.

Todas las métricas posteriores salen de consultas SQL sobre esta base (sql/*.sql).
"""
import os, sys
import duckdb
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from entrenadores import cargar as cargar_entrenadores
from partidos import cargar as cargar_partidos, asignar
from elo import correr

K, H, REG = 10, 70, 0.15   # calibrados en 1995-2012 (ver src/calibrar_elo.py)
BASE = "data/premier.duckdb"
SQL = os.path.join(os.path.dirname(__file__), "..", "sql")


def construir(ruta=BASE):
    e = cargar_entrenadores()
    p = asignar(cargar_partidos(), e)
    elo = correr(p, K, H, REG).reset_index()
    if os.path.exists(ruta):
        os.remove(ruta)
    con = duckdb.connect(ruta)
    con.register("p_df", p); con.register("e_df", e); con.register("elo_df", elo)
    con.execute("CREATE TABLE partidos AS SELECT * FROM p_df")
    con.execute("CREATE TABLE entrenadores AS SELECT * FROM e_df")
    con.execute("CREATE TABLE elo AS SELECT * FROM elo_df")
    for v in ("p_df", "e_df", "elo_df"):
        con.unregister(v)
    for f in sorted(os.listdir(SQL)):
        con.execute(open(os.path.join(SQL, f)).read())
    return con


if __name__ == "__main__":
    con = construir()
    for t in con.execute("SELECT table_name, table_type FROM information_schema.tables ORDER BY 1").fetchall():
        print(t, con.execute(f'SELECT count(*) FROM "{t[0]}"').fetchone()[0])
