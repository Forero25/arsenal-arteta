-- Una fila por equipo y partido: el punto de vista de cada club.
CREATE OR REPLACE VIEW equipo_partido AS
WITH base AS (
  SELECT p.*, e.elo_l, e.elo_v, e.esperado_l FROM partidos p JOIN elo e USING (id)
)
SELECT id, temporada, fecha, local AS club, visita AS rival, TRUE AS en_casa,
       entrenador_l AS entrenador, interino_l AS interino,
       gl AS gf, gv AS gc, tiros_l AS tiros, tiros_v AS tiros_rival, arco_l AS arco, arco_v AS arco_rival,
       xg_l AS xg, xg_v AS xg_rival, elo_l AS elo, elo_v AS elo_rival,
       p_l AS p_gana, p_e AS p_empata, p_v AS p_pierde
FROM base
UNION ALL
SELECT id, temporada, fecha, visita, local, FALSE, entrenador_v, interino_v,
       gv, gl, tiros_v, tiros_l, arco_v, arco_l, xg_v, xg_l, elo_v, elo_l, p_v, p_e, p_l
FROM base;

CREATE OR REPLACE VIEW ep AS
SELECT *,
  CASE WHEN gf > gc THEN 3 WHEN gf = gc THEN 1 ELSE 0 END AS pts,
  3 * p_gana + p_empata AS pts_esperados_mercado
FROM equipo_partido;
