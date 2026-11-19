# Entorno reproducible del análisis: mismas versiones en cualquier máquina.
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ src/
COPY sql/ sql/
COPY tests/ tests/
COPY entradas/ entradas/
# Los datos y los resultados se montan como volumen para que queden en la máquina anfitriona.
CMD ["sh", "-c", "python src/correr.py && pytest -q"]
