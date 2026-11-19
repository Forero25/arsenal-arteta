"""Arteta entre los grandes: app en Shiny for Python.

Compara a Mikel Arteta con los entrenadores de la Premier League desde 1993-94: trayectoria Elo, puntos por
temporada de gestión, rendimiento frente a lo que esperaban las casas de apuestas, perfiles (clústeres) y una
simulación de cuántos títulos podría sumar. Los datos los produce el pipeline de este repositorio.
José Nicolás Forero Urrego · https://nicolasforero.pages.dev
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, render_plotly

AQUI = Path(__file__).parent
R = {f.stem: json.load(open(f)) for f in (AQUI / "resultados").glob("*.json")}
TEMP = pd.read_csv(AQUI / "publicado" / "temporadas_gestion.csv")
ELO = pd.read_csv(AQUI / "publicado" / "elo_por_partido.csv")
CARRERA = pd.DataFrame(R["grandes"]["carrera"])
ENTRENADORES = sorted(CARRERA.entrenador)
AZUL, ROSA, MENTA, AMBAR, LAVANDA, TINTA, GRIS = "#4F6BD8", "#EBA3B0", "#8CCFB8", "#F5B482", "#B9A7E8", "#1F2430", "#C9CED6"


def num(x, d=0):
    if x is None or x != x:
        return "–"
    s = f"{x:,.{d}f}"
    return s.replace(",", "§").replace(".", ",").replace("§", ".")


def pct(x, d=0):
    return "–" if x is None or x != x else num(100 * x, d) + " %"


def signo(x, d=2):
    return "–" if x is None or x != x else ("+" if x > 0 else "") + num(x, d)


def figura(fig, alto=380):
    fig.update_layout(height=alto, margin=dict(l=10, r=10, t=10, b=10), paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", font=dict(family="Inter, system-ui", color=TINTA, size=12),
                      legend=dict(orientation="h", y=-0.18), hoverlabel=dict(bgcolor="white"),
                      modebar=dict(bgcolor="rgba(0,0,0,0)", color="#9CA3AF", activecolor=TINTA))
    fig.update_xaxes(gridcolor="#ECE8E0", zeroline=False)
    fig.update_yaxes(gridcolor="#ECE8E0", zeroline=False)
    return fig


CSS = """
:root { --bs-body-bg: #F6F4EF; --bs-body-color: #1F2430; --bs-primary: #4F6BD8; --bs-border-color: #ECE8E0;
        --bs-body-font-family: Inter, system-ui, -apple-system, 'Segoe UI', sans-serif; }
body { background: #F6F4EF; }
.navbar { background: #F6F4EF !important; border-bottom: 1px solid #ECE8E0; }
.navbar-brand { font-family: Georgia, serif; font-size: 1.35rem; }
.card { border: 1px solid #ECE8E0; box-shadow: none; border-radius: 14px; }
.card-header { background: transparent; font-weight: 600; border-bottom: 1px solid #ECE8E0; }
.bslib-value-box { border: 1px solid #ECE8E0 !important; border-radius: 14px; }
.bslib-value-box .value-box-title { color: #6B7280; font-size: .85rem; }
.bslib-value-box .value-box-value { font-family: Georgia, serif; font-size: 1.9rem; }
.lead { font-size: 1.05rem; max-width: 62rem; color: #374151; }
.nota { color: #6B7280; font-size: .85rem; }
table.tabla { width: 100%; font-size: .9rem; }
table.tabla td, table.tabla th { padding: .38rem .5rem; border-bottom: 1px solid #ECE8E0; }
table.tabla th { color: #6B7280; font-weight: 600; font-size: .8rem; }
table.tabla td.n, table.tabla th.n { text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }
.pos { color: #4F6BD8; font-weight: 600; } .neg { color: #D9667B; font-weight: 600; }
footer.pie { color: #6B7280; font-size: .8rem; margin: 1.5rem 0 1rem; }
dl.glosario dt { font-weight: 600; margin-top: .6rem; } dl.glosario dd { margin-left: 0; color: #374151; }
"""

pie = ui.tags.footer(
    {"class": "pie"},
    "Datos: ", ui.a("football-data.co.uk", href="https://www.football-data.co.uk"), " (resultados, tiros y cuotas) y ",
    ui.a("Wikipedia", href="https://en.wikipedia.org/wiki/List_of_Premier_League_managers"), " (CC BY-SA 4.0). ",
    "Código: ", ui.a("github.com/Forero25/arsenal-arteta", href="https://github.com/Forero25/arsenal-arteta"), " · ",
    ui.a("José Nicolás Forero Urrego", href="https://nicolasforero.pages.dev"),
)


def tarjeta(titulo, *contenido, **kw):
    return ui.card(ui.card_header(titulo), *contenido, **kw)


def tabla_html(df, cols, formatos, clases=None):
    clases = clases or {}
    cab = "".join(f"<th class='{'n' if c in formatos else ''}'>{t}</th>" for c, t in cols)
    filas = []
    for _, r in df.iterrows():
        celdas = []
        for c, _t in cols:
            v = r[c]
            txt = formatos[c](v) if c in formatos else str(v)
            cl = "n" if c in formatos else ""
            if c in clases and v == v:
                cl += " pos" if v > 0 else " neg" if v < 0 else ""
            celdas.append(f"<td class='{cl}'>{txt}</td>")
        filas.append("<tr>" + "".join(celdas) + "</tr>")
    return ui.HTML(f"<table class='tabla'><thead><tr>{cab}</tr></thead><tbody>{''.join(filas)}</tbody></table>")


ar = CARRERA[CARRERA.entrenador == "Mikel Arteta"].iloc[0]
mer = R["mercado"]["Mikel Arteta"]

app_ui = ui.page_navbar(
    ui.nav_panel(
        "Arteta",
        ui.p({"class": "lead"}, "Mikel Arteta llegó al Arsenal en diciembre de 2019, con el equipo en un nivel apenas superior al promedio de la liga. "
             "En su séptima temporada ganó la Premier League. Aquí está su proceso, partido a partido."),
        ui.layout_column_wrap(
            ui.value_box("Partidos en la Premier", num(ar.pj)),
            ui.value_box("Puntos por partido", num(ar.ppp, 2)),
            ui.value_box("Títulos de liga", num(ar.titulos)),
            ui.value_box("Puntos por temporada sobre lo esperado por el mercado", signo(mer["por_38"], 1)),
            width=1 / 4,
        ),
        tarjeta("Nivel del Arsenal (Elo) en cada partido de Arteta", output_widget("g_arteta"),
                ui.p({"class": "nota"}, "Elo propio: 1.500 es un equipo promedio de la Premier. Cada punto es una temporada; la línea, el rating partido a partido.")),
        tarjeta("Temporada por temporada", ui.output_ui("t_arteta")),
    ),
    ui.nav_panel(
        "Comparar",
        ui.layout_sidebar(
            ui.sidebar(
                ui.input_select("a", "Entrenador A", ENTRENADORES, selected="Mikel Arteta"),
                ui.input_select("b", "Entrenador B", ENTRENADORES, selected="Jürgen Klopp"),
                ui.input_radio_buttons("metrica", "Métrica por temporada de gestión",
                                       {"ppp": "Puntos por partido", "sobre_mercado_pp": "Puntos sobre el mercado", "elo_fin": "Elo al final", "cuota_tiros": "Cuota de tiros"}),
                ui.p({"class": "nota"}, "Las temporadas se cuentan desde que el entrenador llegó al club: la 3.ª de Arteta se compara con la 3.ª de Klopp."),
                open="desktop",
            ),
            tarjeta("Trayectoria Elo desde el primer partido en el club", output_widget("g_elo")),
            tarjeta("Por temporada de gestión", output_widget("g_temp")),
            tarjeta("Carrera en la Premier", ui.output_ui("t_comp")),
        ),
    ),
    ui.nav_panel(
        "Perfiles",
        ui.p({"class": "lead"}, "Agrupé a los entrenadores con al menos 100 partidos desde 2000-01 según siete rasgos. "
             "El gráfico los proyecta en dos dimensiones (componentes principales)."),
        tarjeta("Mapa de entrenadores", output_widget("g_pca")),
        ui.layout_column_wrap(
            tarjeta("Promedio de cada grupo", ui.output_ui("t_perfiles")),
            tarjeta("A quién se parece Arteta", ui.output_ui("t_vecinos")),
            width=1 / 2,
        ),
    ),
    ui.nav_panel(
        "Futuro",
        ui.p({"class": "lead"}, "Simulación de 20.000 futuros posibles: ¿cuántos títulos podría sumar Arteta si se queda N temporadas más?"),
        tarjeta("Probabilidad de alcanzar cada cifra de títulos", output_widget("g_sim")),
        tarjeta("Validación: ¿el modelo acierta cuando dice 30 %?", ui.output_ui("t_cal")),
    ),
    ui.nav_panel(
        "Método",
        ui.div({"class": "lead"}, ui.markdown(open(AQUI / "METODO.md", encoding="utf-8").read())),
    ),
    title="Arteta entre los grandes",
    header=ui.tags.style(CSS),
    footer=pie,
    fillable=False,
)


def server(input, output, session):
    @render_plotly
    def g_arteta():
        e = ELO[ELO.entrenador == "Mikel Arteta"]
        t = TEMP[TEMP.entrenador == "Mikel Arteta"]
        fig = go.Figure()
        fig.add_hline(y=1500, line=dict(color=GRIS, dash="dot"))
        fig.add_trace(go.Scatter(x=e.partido_gestion, y=e.elo, mode="lines", line=dict(color=AZUL, width=2), name="Elo",
                                 hovertemplate="Partido %{x}<br>Elo %{y:.0f}<extra></extra>"))
        fin = e.groupby("temporada").partido_gestion.max()
        fig.add_trace(go.Scatter(x=fin.values, y=t.set_index("temporada").loc[fin.index].elo_fin, mode="markers+text",
                                 text=[f"{a}-{(a + 1) % 100:02d}" for a in fin.index], textposition="top center",
                                 marker=dict(color=AMBAR, size=9), name="Fin de temporada"))
        fig.update_xaxes(title="Partido de Arteta en la Premier")
        fig.update_yaxes(title="Elo")
        return figura(fig)

    @render.ui
    def t_arteta():
        t = TEMP[TEMP.entrenador == "Mikel Arteta"].copy()
        t["temp"] = t.temporada.map(lambda a: f"{a}-{(a + 1) % 100:02d}") + t.completa.map(lambda c: "" if c else " (en curso)")
        return tabla_html(t, [("temp", "Temporada"), ("pj", "PJ"), ("ppp", "Pts/partido"), ("gf_pp", "GF/p"), ("gc_pp", "GC/p"),
                              ("cuota_tiros", "Cuota de tiros"), ("sobre_mercado_pp", "Sobre el mercado/p"), ("elo_fin", "Elo final")],
                          {"pj": num, "ppp": lambda v: num(v, 2), "gf_pp": lambda v: num(v, 2), "gc_pp": lambda v: num(v, 2),
                           "cuota_tiros": pct, "sobre_mercado_pp": lambda v: signo(v, 2), "elo_fin": num},
                          {"sobre_mercado_pp": True})

    @reactive.calc
    def pareja():
        return [input.a(), input.b()]

    @render_plotly
    def g_elo():
        fig = go.Figure()
        fig.add_hline(y=1500, line=dict(color=GRIS, dash="dot"))
        for n, col in zip(pareja(), (AZUL, ROSA)):
            e = ELO[ELO.entrenador == n]
            for (club, desde), g in e.groupby(["club", "desde"]):
                fig.add_trace(go.Scatter(x=g.partido_gestion, y=g.elo, mode="lines", line=dict(color=col, width=2),
                                         name=f"{n} · {club} ({desde[:4]})",
                                         hovertemplate=f"{n}<br>Partido %{{x}}<br>Elo %{{y:.0f}}<extra></extra>"))
        fig.update_xaxes(title="Partido desde su llegada al club (desde 1993-94)")
        return figura(fig)

    @render_plotly
    def g_temp():
        m = input.metrica()
        fig = go.Figure()
        for n, col in zip(pareja(), (AZUL, ROSA)):
            t = TEMP[(TEMP.entrenador == n) & (TEMP.pj >= 10)]
            for (club, desde), g in t.groupby(["club", "desde"]):
                fig.add_trace(go.Scatter(x=g.temporada_gestion, y=g[m], mode="lines+markers", line=dict(color=col),
                                         name=f"{n} · {club}", customdata=g.temporada,
                                         hovertemplate="Temporada de gestión %{x} (%{customdata})<br>%{y:.2f}<extra></extra>"))
        fig.update_xaxes(title="Temporada de gestión", dtick=1)
        return figura(fig, 340)

    @render.ui
    def t_comp():
        c = CARRERA[CARRERA.entrenador.isin(pareja())]
        return tabla_html(c, [("entrenador", "Entrenador"), ("pj", "PJ"), ("ppp", "Pts/partido"), ("dg_pp", "Dif. goles/p"),
                              ("sobre_mercado_pp", "Sobre el mercado/p"), ("elo_medio", "Elo medio"), ("titulos", "Títulos")],
                          {"pj": num, "ppp": lambda v: num(v, 2), "dg_pp": lambda v: signo(v, 2),
                           "sobre_mercado_pp": lambda v: signo(v, 2), "elo_medio": num, "titulos": num},
                          {"sobre_mercado_pp": True})

    @render_plotly
    def g_pca():
        c = R["clusteres"]
        e = pd.DataFrame(c["entrenadores"])
        colores = [MENTA, AZUL, AMBAR, LAVANDA, ROSA, GRIS]
        fig = go.Figure()
        for g, d in e.groupby("grupo"):
            fig.add_trace(go.Scatter(x=d.pc1, y=d.pc2, mode="markers", marker=dict(size=9, color=colores[g % 6], line=dict(width=0)),
                                     name=f"Grupo {g + 1}", text=d.entrenador,
                                     hovertemplate="%{text}<br>%{customdata:.2f} pts/partido<extra></extra>", customdata=d.ppp))
        a = e[e.entrenador == "Mikel Arteta"]
        fig.add_trace(go.Scatter(x=a.pc1, y=a.pc2, mode="markers+text", text=["Arteta"], textposition="top center",
                                 marker=dict(size=14, color="rgba(0,0,0,0)", line=dict(color=TINTA, width=2)), name="Arteta"))
        for n in ["Pep Guardiola", "Alex Ferguson", "Jürgen Klopp", "José Mourinho", "Arsène Wenger"]:
            r = e[e.entrenador == n]
            if len(r):
                fig.add_annotation(x=r.pc1.iloc[0], y=r.pc2.iloc[0], text=n.split()[-1], showarrow=False, yshift=12, font=dict(size=11))
        fig.update_xaxes(title=f"Componente 1 ({pct(c['varianza_pca'][0])} de la variación)")
        fig.update_yaxes(title=f"Componente 2 ({pct(c['varianza_pca'][1])})")
        return figura(fig, 460)

    @render.ui
    def t_perfiles():
        p = pd.DataFrame(R["clusteres"]["perfiles"])
        p["g"] = "Grupo " + (p.grupo + 1).astype(str)
        return tabla_html(p, [("g", ""), ("n", "Entrenadores"), ("ppp", "Pts/p"), ("gc_pp", "GC/p"), ("cuota_tiros", "Tiros"),
                              ("sobre_mercado_pp", "Sobre mercado/p"), ("subida_max", "Subida Elo")],
                          {"n": num, "ppp": lambda v: num(v, 2), "gc_pp": lambda v: num(v, 2), "cuota_tiros": pct,
                           "sobre_mercado_pp": lambda v: signo(v, 2), "subida_max": num})

    @render.ui
    def t_vecinos():
        v = pd.DataFrame(R["clusteres"]["vecinos_arteta"])
        return ui.div(tabla_html(v, [("entrenador", "Entrenador"), ("distancia_arteta", "Distancia")], {"distancia_arteta": lambda x: num(x, 2)}),
                      ui.p({"class": "nota"}, "Distancia en las siete variables estandarizadas: 0 sería un perfil idéntico."))

    @render_plotly
    def g_sim():
        s = R["simulacion"]["por_temporadas"]
        h = sorted(s, key=int)
        fig = go.Figure()
        for meta, col in zip(["2", "3", "4", "6"], (MENTA, AZUL, AMBAR, ROSA)):
            fig.add_trace(go.Scatter(x=[int(x) for x in h], y=[s[x]["p_al_menos"][meta] for x in h], mode="lines+markers",
                                     line=dict(color=col, width=2), name=f"{meta} o más títulos",
                                     hovertemplate="%{x} temporadas más<br>%{y:.0%}<extra></extra>"))
        fig.update_yaxes(tickformat=".0%", title="Probabilidad")
        fig.update_xaxes(title="Temporadas adicionales en el Arsenal (contando 2026-27)", dtick=1)
        return figura(fig)

    @render.ui
    def t_cal():
        t = pd.DataFrame(R["simulacion"]["calibracion"]["tabla"])
        cal = R["simulacion"]["calibracion"]
        return ui.div(tabla_html(t, [("tramo", "Probabilidad que dio el modelo"), ("n", "Casos"), ("p_media", "Promedio predicho"), ("frecuencia", "Fueron campeones")],
                                 {"n": num, "p_media": pct, "frecuencia": pct}),
                      ui.p({"class": "nota"}, f"Predicciones hechas solo con el pasado para cada temporada desde 2005-06. Error cuadrático {num(cal['brier'], 3)} "
                           f"contra {num(cal['brier_base'], 3)} de predecir siempre la frecuencia promedio."))


app = App(app_ui, server)
