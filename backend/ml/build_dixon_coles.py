"""
ml/build_dixon_coles.py — Ajusta y guarda los parametros Dixon-Coles por liga.

Salida: ml/data/dixon_coles.json

Uso:  python -m ml.build_dixon_coles
"""
import json

from ml import dixon_coles


if __name__ == "__main__":
    summary = dixon_coles.build()
    print("Dixon-Coles ajustado por liga (equipos):")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
