## La pregunta

¿Dónde está Mikel Arteta frente a los grandes entrenadores de la Premier League, y qué tendría que pasar para alcanzarlos? Arsenal ganó la liga 2025-26 con Arteta, su primer título en 22 años. Con un título, ¿ya es comparable con Ferguson, Wenger, Mourinho, Guardiola y Klopp?

## Quiénes son "los grandes"

No los elegí a dedo. La regla es: **al menos 300 partidos de Premier y al menos 1,9 puntos por partido**. La cumplen cinco: Guardiola, Ferguson, Klopp, Mourinho y Wenger. Arteta tiene el promedio (2,02) pero todavía no los partidos (258): con su ritmo actual, entraría al grupo en la temporada 2027-28.

## Los datos

- **Partidos:** todos los de la Premier desde 1993-94, de football-data.co.uk: resultado, tiros (desde 2000-01) y cuotas de varias casas de apuestas (desde 2000-01). La temporada 1992-93 no está en la fuente.
- **Entrenadores:** la lista de Wikipedia con la fecha de llegada y salida de cada entrenador en cada club, incluidos los interinos. Cada partido se asigna al entrenador que estaba a cargo ese día. Los interinos no cuentan en las comparaciones.
- **Base de datos:** todo queda en DuckDB y las métricas salen de consultas SQL (carpeta `sql/`). El pipeline corre dentro de un contenedor Docker, así que se reproduce igual en cualquier máquina.
- **Validación:** los campeones y sus puntos, calculados desde los partidos, coinciden con la historia (Arsenal 90 en 2003-04, City 100 en 2017-18, Liverpool 99 en 2019-20, Arsenal 85 en 2025-26).

## Las cuatro herramientas

**1. Elo: la fuerza del equipo en un número.** Cada club empieza en 1.500. Después de cada partido, el que ganó le quita puntos al que perdió, y le quita más si la victoria era menos esperada o fue por goleada. Ejemplo: si el Arsenal (1.600) visita a un equipo de 1.500, la ventaja de local del rival (70 puntos) deja el partido casi parejo; si el Arsenal gana 2-0, sube unos 7 puntos. Los parámetros se eligieron con 1995-2012 y se probaron en 2013-2026.

**2. Puntos sobre lo esperado por el mercado.** Las cuotas de las casas de apuestas dicen qué probabilidad tenía cada equipo de ganar, empatar o perder. Con eso calculo cuántos puntos "se esperaban" de cada partido. Ejemplo: si un equipo tenía 60 % de ganar y 25 % de empatar, se esperaban 3 × 0,60 + 1 × 0,25 = 2,05 puntos; si ganó, sacó 0,95 por encima. Sumado en una carrera, mide cuánto superó un entrenador lo que el mercado esperaba de su plantel.

**3. Clústeres: perfiles de entrenador.** Agrupo a los entrenadores con al menos 100 partidos desde 2000-01 según siete rasgos (puntos, goles a favor y en contra, dominio de tiros, puntos sobre el mercado, cuánto subió el Elo del club y cuánto varió de una temporada a otra). Uso k-means y lo contrasto con un método jerárquico.

**4. Simulación del futuro.** Con todas las temporadas desde 1995-96 estimo cuánto se mantiene el nivel de un equipo de un año a otro (los puntos de una temporada predicen los de la siguiente) y cuántos puntos suele tener el mejor rival. Con eso simulo 20.000 futuros posibles. Para la temporada en curso uso el pronóstico de mi otro proyecto (premier-pronostico).

## Glosario

<dl class="glosario">
<dt>Elo</dt><dd>Rating de fuerza que sube al ganar y baja al perder, más cuanto más inesperado el resultado. 1.500 es un equipo promedio.</dd>
<dt>Temporada de gestión</dt><dd>Número de temporada desde que el entrenador llegó al club. Permite comparar la 3.ª de Arteta con la 3.ª de Klopp.</dd>
<dt>Puntos sobre el mercado</dt><dd>Puntos obtenidos menos los que implicaban las cuotas de apuestas antes del partido.</dd>
<dt>Intervalo de confianza del 95 %</dt><dd>Rango donde estaría el valor real con alta probabilidad, dado el número de partidos. Si incluye el cero, no se puede descartar que el mérito sea suerte.</dd>
<dt>Clúster</dt><dd>Grupo de entrenadores con rasgos parecidos, encontrado por el algoritmo sin decirle cuántos ni cuáles.</dd>
<dt>Silueta</dt><dd>Medida de qué tan separados quedan los grupos: cerca de 1, muy nítidos; cerca de 0, se mezclan.</dd>
<dt>Error cuadrático</dt><dd>Promedio del cuadrado de la diferencia entre lo que predijo un modelo y lo que pasó. Más bajo es mejor.</dd>
</dl>
