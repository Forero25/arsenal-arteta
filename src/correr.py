"""Pipeline completo: descarga -> base DuckDB -> análisis. Es lo que corre el contenedor."""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
import descargar, base, analisis

if __name__ == "__main__":
    if "--sin-descarga" not in sys.argv:
        descargar.main()
    base.construir()
    analisis.main()
