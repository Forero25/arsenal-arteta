-- Tabla de posiciones por temporada y campeón (calculados con los partidos, no copiados).
CREATE OR REPLACE VIEW tabla AS
SELECT temporada, club, count(*) AS pj, sum(pts) AS pts, sum(gf) - sum(gc) AS dg, sum(gf) AS gf,
       rank() OVER (PARTITION BY temporada ORDER BY sum(pts) DESC, sum(gf) - sum(gc) DESC, sum(gf) DESC) AS puesto
FROM ep GROUP BY temporada, club;

-- Entrenador "de la temporada" en cada club: el que dirigió más partidos ese año.
CREATE OR REPLACE VIEW entrenador_temporada AS
SELECT temporada, club, entrenador, count(*) AS partidos,
       row_number() OVER (PARTITION BY temporada, club ORDER BY count(*) DESC) AS orden
FROM ep WHERE entrenador IS NOT NULL GROUP BY temporada, club, entrenador;

CREATE OR REPLACE VIEW campeones AS
SELECT t.temporada, t.club, t.pts, et.entrenador
FROM tabla t JOIN entrenador_temporada et ON et.temporada = t.temporada AND et.club = t.club AND et.orden = 1
WHERE t.puesto = 1 AND t.pj = (SELECT max(pj) FROM tabla t2 WHERE t2.temporada = t.temporada);
