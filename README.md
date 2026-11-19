# Arteta entre los grandes

¿Dónde está Mikel Arteta frente a los grandes entrenadores de la Premier League, y qué tendría que pasar para alcanzarlos? Arsenal ganó la liga 2025-26 con él, su primer título en 22 años. Este repositorio compara su proceso con el de Ferguson, Wenger, Mourinho, Guardiola y Klopp, partido a partido, desde 1993-94.

- **App interactiva** (Shiny for Python): `app.py`, publicada en [Posit Connect Cloud](https://01a1f297-a04e-16bc-6933-c0d05dc9ade0.share.connect.posit.cloud/).
- **Artículo:** [nicolasforero.pages.dev/escritos/arteta](https://nicolasforero.pages.dev/escritos/arteta/)
- **Método explicado y glosario:** [METODO.md](METODO.md)

## Arquitectura

```
football-data.co.uk ─┐                       ┌─ sql/ (vistas: equipo por partido, tablas, etapas, carreras)
Wikipedia ───────────┼─> src/descargar.py ─> src/base.py ─> DuckDB ─> src/analisis.py ─> resultados/*.json
                     │   (data/raw, release    (Elo, asignación de               (mercado, clústeres,     publicado/*.csv
                     │    "crudos")             entrenadores)                     simulación)              └─> app.py
premier-pronostico ──┘ (entradas/: probabilidad de título de la temporada en curso)
```

- **Docker:** el `Dockerfile` fija el entorno; GitHub Actions construye la imagen y corre el pipeline y las pruebas dentro del contenedor cada martes (`.github/workflows/analisis.yml`).
- **SQL:** todas las métricas por entrenador, temporada y etapa salen de consultas DuckDB en `sql/`.
- **Pruebas** (`tests/`): el parser de Wikipedia, la asignación de entrenadores por fecha, la lectura de CSV con filas irregulares, las probabilidades de las cuotas, la conservación del Elo, que los campeones calculados coincidan con la historia y que el mercado prediga mejor que el Elo.

## Análisis

1. **Validación de datos:** 12.804 partidos; los 33 campeones con temporada completa y sus puntos coinciden con la historia.
2. **Comparación de modelos:** en 2013-2026 (fuera de la calibración), las cuotas predicen mejor que el Elo propio, y el Elo mejor que una constante.
3. **El proceso de Arteta:** Elo partido a partido, puntos, goles, tiros y rendimiento sobre el mercado por temporada.
4. **Comparación por temporada de gestión** con los grandes.
5. **Mérito frente al mercado** con intervalos de confianza por remuestreo (bootstrap).
6. **Clústeres** (k-means contrastado con Ward) y vecinos más cercanos de Arteta.
7. **Simulación** de su carrera, con validación hacia adelante de las probabilidades de título.

## Lo que este proyecto no hace

- **No mide la calidad del plantel ni el gasto.** Las cuotas resumen lo que el mercado esperaba del equipo, que incluye al plantel y también la reputación del entrenador; no son una medida pura del "mérito del técnico".
- **No cubre 1992-93** (no está en la fuente) ni lo anterior: a Ferguson le faltan sus primeras seis temporadas y un título.
- **No incluye copas ni Champions.** Solo la Premier League.
- **La simulación no modela el desgaste ni la salida del entrenador.** Supone que el Arsenal mantiene su nivel con la persistencia histórica de los equipos; por eso se presenta por número de temporadas adicionales.
- **No usa goles esperados (xG)** salvo como referencia: la fuente solo los trae para 2026-27.

## Reproducir

```
docker build -t arsenal-arteta .
docker run --rm -v "$PWD/data:/app/data" -v "$PWD/resultados:/app/resultados" -v "$PWD/publicado:/app/publicado" arsenal-arteta
shiny run app.py
```

## Fuentes y licencias

- Resultados, tiros y cuotas: [football-data.co.uk](https://www.football-data.co.uk).
- Entrenadores: [Wikipedia, List of Premier League managers](https://en.wikipedia.org/wiki/List_of_Premier_League_managers) (CC BY-SA 4.0).
- Probabilidad de la temporada en curso: [premier-pronostico](https://nicolasforero.pages.dev/escritos/premier-pronostico/).

Código bajo licencia MIT. José Nicolás Forero Urrego.
