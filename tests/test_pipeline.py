import os, sys, json
import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from entrenadores import parsear
from partidos import asignar, leer_csv, probabilidades
from elo import correr

WIKI = """{| class="wikitable"
|+Managers
! scope="col"|Name
|-
!scope="row"|{{sortname|Arsène|Wenger| |Wenger, Arsene}}
|{{flagicon|France}}
|[[Arsenal F.C.|Arsenal]]
|{{dts|format=dmy|1996|10|1}}
|{{dts|format=dmy|2018|5|13}}
|-
! scope="row" style="background:#b7e8b9;"|{{sortname|Freddie|Ljungberg}} {{double dagger}}
|{{flagicon|Sweden}}
|[[Arsenal F.C.|Arsenal]]
|{{dts|format=dmy|2019|11|29}}
|{{dts|format=dmy|2019|12|21}}
|-
!scope="row"|{{sortname|Mikel|Arteta}}
|{{flagicon|Spain}}
|[[Arsenal F.C.|Arsenal]]
|{{dts|format=dmy|2019|12|22}}
|''Present''
|}"""


def test_parser_de_entrenadores():
    e = parsear(WIKI, hoy=pd.Timestamp("2026-11-19").date())
    assert e.entrenador.tolist() == ["Arsène Wenger", "Freddie Ljungberg", "Mikel Arteta"]
    assert e.interino.tolist() == [False, True, False]
    assert e.vigente.tolist() == [False, False, True] and str(e.hasta.iloc[-1]) == "2026-11-19"


def test_asignacion_por_fecha():
    e = parsear(WIKI, hoy=pd.Timestamp("2026-11-19").date())
    p = pd.DataFrame({"id": [0, 1, 2], "fecha": pd.to_datetime(["2010-01-01", "2019-12-01", "2020-01-01"]),
                      "local": ["Arsenal"] * 3, "visita": ["Chelsea"] * 3})
    a = asignar(p, e)
    assert a.entrenador_l.tolist() == ["Arsène Wenger", "Freddie Ljungberg", "Mikel Arteta"]
    assert a.interino_l.tolist() == [False, True, False]


def test_csv_con_filas_mas_largas(tmp_path):
    f = tmp_path / "x.csv"
    f.write_text("Div,Date,HomeTeam,AwayTeam,FTHG,FTAG\nE0,01/01/04,A,B,1,0,9.9,9.9\nE0,02/01/04,C,D,2,2\n", encoding="latin1")
    d = leer_csv(str(f))
    assert len(d) == 2 and list(d.columns) == ["Div", "Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG"]


def test_probabilidades_suman_uno_y_quitan_margen():
    d = pd.DataFrame({"B365H": [2.0], "B365D": [3.4], "B365A": [4.0], "WHH": [2.1], "WHD": [3.3], "WHA": [3.8]})
    p, n = probabilidades(d)
    assert n[0] == 2 and abs(p[0].sum() - 1) < 1e-9 and p[0, 0] > p[0, 2]


def test_elo_suma_cero_y_favorece_al_que_gana():
    p = pd.DataFrame({"id": range(4), "temporada": [2000] * 4, "local": ["A", "B", "A", "B"], "visita": ["B", "A", "B", "A"],
                      "gl": [3, 0, 2, 1], "gv": [0, 1, 0, 1]})
    e = correr(p, K=20, H=60, regresion=0)
    # antes del cuarto partido A ya superó a B, y la suma de ratings se conserva
    ultimo = e.iloc[-1]
    assert ultimo.elo_l < 1500 < ultimo.elo_v and abs(ultimo.elo_l + ultimo.elo_v - 3000) < 1e-9


RES = os.path.join(os.path.dirname(__file__), "..", "resultados")


@pytest.mark.skipif(not os.path.exists(os.path.join(RES, "validacion.json")), reason="sin resultados")
def test_campeones_reproducen_la_historia():
    v = json.load(open(os.path.join(RES, "validacion.json")))
    c = {x["temporada"]: (x["club"], x["pts"]) for x in v["campeones"]}
    assert c[2003] == ("Arsenal", 90) and c[2017] == ("Manchester City", 100)
    assert c[2019] == ("Liverpool", 99) and c[2025] == ("Arsenal", 85) and c[2015][0] == "Leicester City"


@pytest.mark.skipif(not os.path.exists(os.path.join(RES, "modelos.json")), reason="sin resultados")
def test_el_mercado_predice_mejor_que_el_elo_y_el_elo_que_nada():
    e = json.load(open(os.path.join(RES, "modelos.json")))["error_cuadratico"]
    assert e["mercado"] < e["elo"] < e["constante"]
