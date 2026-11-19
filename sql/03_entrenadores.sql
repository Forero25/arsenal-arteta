-- Etapas: un entrenador en un club, con sus temporadas numeradas desde la primera (1 = primera temporada).
CREATE OR REPLACE VIEW etapa_partido AS
WITH con_etapa AS (
  SELECT ep.*, e.desde,
    -- temporada (año de inicio) en que empezó la etapa; julio o después cuenta para esa temporada
    CASE WHEN month(e.desde) >= 7 THEN year(e.desde) ELSE year(e.desde) - 1 END AS temporada_inicio_etapa
  FROM ep JOIN entrenadores e
    ON e.entrenador = ep.entrenador AND e.club = ep.club AND ep.fecha BETWEEN e.desde AND e.hasta
  WHERE ep.entrenador IS NOT NULL AND NOT ep.interino
  QUALIFY row_number() OVER (PARTITION BY ep.id, ep.club ORDER BY e.desde DESC) = 1
)
SELECT *,
  -- temporada de gestión contada desde que llegó al club (Ferguson llegó en 1986: 1993-94 es su 8.ª)
  temporada - CASE WHEN desde < DATE '1993-07-01' THEN temporada_inicio_etapa
                   ELSE min(temporada) OVER (PARTITION BY entrenador, club, desde) END + 1 AS temporada_gestion,
  row_number() OVER (PARTITION BY entrenador, club, desde ORDER BY fecha) AS partido_gestion,
  desde < DATE '1993-07-01' AS etapa_previa_a_los_datos
FROM con_etapa;

-- Temporadas en curso: no cuentan como completas.
CREATE OR REPLACE VIEW temporadas_completas AS
SELECT temporada FROM tabla GROUP BY temporada HAVING min(pj) >= 38;

-- Resumen por entrenador y temporada de gestión.
CREATE OR REPLACE VIEW gestion_temporada AS
SELECT entrenador, club, desde, temporada, temporada_gestion, count(*) AS pj,
  avg(pts) AS ppp, avg(gf - gc) AS dg_pp, avg(gf) AS gf_pp, avg(gc) AS gc_pp,
  avg(pts - pts_esperados_mercado) AS sobre_mercado_pp, count(pts_esperados_mercado) AS pj_con_cuotas,
  avg(tiros / nullif(tiros + tiros_rival, 0)) AS cuota_tiros,
  avg(arco / nullif(arco + arco_rival, 0)) AS cuota_tiros_arco,
  first(elo ORDER BY fecha) AS elo_inicio, last(elo ORDER BY fecha) AS elo_fin, avg(elo) AS elo_medio,
  temporada IN (SELECT temporada FROM temporadas_completas) AS completa
FROM etapa_partido GROUP BY ALL;

-- Resumen de carrera en la Premier (todas sus etapas).
CREATE OR REPLACE VIEW carrera AS
SELECT entrenador, count(*) AS pj, count(DISTINCT club) AS clubes,
  avg(pts) AS ppp, avg(gf - gc) AS dg_pp, avg(gc) AS gc_pp,
  avg(pts - pts_esperados_mercado) AS sobre_mercado_pp, count(pts_esperados_mercado) AS pj_con_cuotas,
  sum(pts - pts_esperados_mercado) AS sobre_mercado_total,
  avg(tiros / nullif(tiros + tiros_rival, 0)) AS cuota_tiros, avg(elo) AS elo_medio, max(elo) AS elo_max,
  min(fecha) AS primer_partido, max(fecha) AS ultimo_partido,
  (SELECT count(*) FROM campeones c WHERE c.entrenador = etapa_partido.entrenador
     AND c.temporada IN (SELECT temporada FROM temporadas_completas)) AS titulos
FROM etapa_partido GROUP BY entrenador;
