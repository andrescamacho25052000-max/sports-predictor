"""
ml/build_dixon_coles_national.py — Ajusta y guarda Dixon-Coles de SELECCIONES.

Salida: ml/data/dixon_coles_national.json

Uso:  python -m ml.build_dixon_coles_national
"""
import json

from ml import dixon_coles


if __name__ == "__main__":
    print("Ajustando Dixon-Coles nacional (puede tardar)...")
    summary = dixon_coles.build_national()
    print(json.dumps(summary, indent=2, ensure_ascii=False))
