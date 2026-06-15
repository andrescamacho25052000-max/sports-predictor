"""
bet_slip_analyzer.py
====================
Analiza la imagen de un cupón de apuestas (combinada de Betplay) usando el
modelo de visión de Claude, y la evalúa contra las predicciones del modelo.

Flujo:
  1. Claude lee la imagen y extrae las patas (equipos, mercado, selección, cuota).
  2. main.run_full_prediction() corre la predicción de cada partido.
  3. Claude mapea cada pata a la probabilidad del modelo y emite el veredicto.

Requiere ANTHROPIC_API_KEY en el entorno. Si falta, devuelve un error claro.
"""
import os
import json
import re
from dotenv import load_dotenv

load_dotenv()

MODEL = "claude-opus-4-8"
_client = None


def _get_client():
    """Cliente Anthropic perezoso. Lanza RuntimeError si no hay API key."""
    global _client
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise RuntimeError(
            "Falta ANTHROPIC_API_KEY. Agrega tu clave de Anthropic en backend/.env "
            "para activar el análisis de cupones por imagen."
        )
    if _client is None:
        import anthropic
        _client = anthropic.Anthropic()
    return _client


def _json_from_text(text: str) -> dict:
    """Extrae el primer bloque JSON de la respuesta de Claude."""
    text = text.strip()
    # quitar fences ```json ... ```
    fence = re.search(r"```(?:json)?\s*(.+?)```", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1:
        text = text[start:end + 1]
    return json.loads(text)


def _text_block(resp) -> str:
    for b in resp.content:
        if b.type == "text":
            return b.text
    return ""


# ── Paso 1: extracción de la imagen ───────────────────────────────────────────

def extract_legs(image_b64: str, media_type: str = "image/png") -> dict:
    """
    Lee el cupón y devuelve:
      {"legs": [{"home","away","market","selection","odds"}],
       "total_odds": float|None, "stake": float|None}
    Los nombres de equipos se normalizan a la lista canónica de selecciones.
    """
    import football_api as fapi
    canonical = fapi.national_team_names()
    canon_str = ", ".join(n for n in canonical if n)

    prompt = (
        "Eres un lector de cupones de apuestas deportivas. Extrae del cupón de la "
        "imagen TODAS las selecciones (patas) de la combinada.\n\n"
        "Para cada pata devuelve: el partido (equipo local y visitante), el mercado "
        "(p.ej. 'Total de goles', 'Doble Oportunidad', 'Hándicap', 'Total de tarjetas', "
        "'Total de tiros de esquina', 'Total de faltas'), la selección exacta tal como "
        "aparece (p.ej. 'Más de 2.5', 'Canadá o Empate', 'Turquía -2.5') y la cuota si "
        "se ve.\n\n"
        f"Normaliza los nombres de equipos a uno de esta lista exacta (en inglés): {canon_str}. "
        "Usa el nombre de la lista que corresponda a cada equipo del cupón "
        "(p.ej. 'Países Bajos'->'Netherlands', 'Brasil'->'Brazil', 'Marruecos'->'Morocco', "
        "'EUA'/'Estados Unidos'->'United States', 'Turquía'->'Turkey'). Si no hay match, usa el nombre tal cual.\n\n"
        "Devuelve SOLO un objeto JSON con esta forma, sin texto extra:\n"
        '{"legs": [{"home": "Netherlands", "away": "Japan", "market": "Total de goles", '
        '"selection": "Menos de 4.5", "odds": 1.2}], "total_odds": 2.5, "stake": 3000}\n'
        "Si la cuota total o el monto no se ven, usa null."
    )

    resp = _get_client().messages.create(
        model=MODEL,
        max_tokens=2000,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {
                    "type": "base64", "media_type": media_type, "data": image_b64}},
                {"type": "text", "text": prompt},
            ],
        }],
    )
    return _json_from_text(_text_block(resp))


# ── Paso 3: mapeo + veredicto ──────────────────────────────────────────────────

def map_and_analyze(legs: list[dict], predictions: dict, total_odds, stake) -> dict:
    """
    legs: patas extraídas.
    predictions: {"Home vs Away": <dict de /predict con poisson, corners_cards...>}
    Devuelve el análisis estructurado para el frontend.
    """
    # Compactar las predicciones a lo esencial para no inflar el prompt
    compact = {}
    for key, p in predictions.items():
        po = p.get("poisson", {}) or {}
        cc = p.get("corners_cards", {}) or {}
        compact[key] = {
            "probabilities": p.get("probabilities"),
            "expected_goals": po.get("expected_goals"),
            "over_under": po.get("over_under"),
            "btts": po.get("btts"),
            "handicap": po.get("handicap"),
            "half_time": po.get("half_time"),
            "home_goals": po.get("home_goals"),
            "away_goals": po.get("away_goals"),
            "corners": {
                "expected_total": cc.get("corners", {}).get("expected_total"),
                "over_under": cc.get("corners", {}).get("over_under"),
            },
            "yellow_cards": {
                "expected_total": cc.get("yellow_cards", {}).get("expected_total"),
                "over_under": cc.get("yellow_cards", {}).get("over_under"),
            },
            "fouls_expected_total": cc.get("fouls", {}).get("expected_total"),
        }

    prompt = (
        "Eres un analista de apuestas. Tienes las patas de una combinada y las "
        "predicciones del modelo para cada partido. Para CADA pata, estima la "
        "probabilidad del modelo (0-100) que corresponde a esa selección, mapeándola "
        "al mercado correcto de las predicciones.\n\n"
        "Notas de mapeo:\n"
        "- 1X2 viene en 'probabilities' (home_win/draw/away_win).\n"
        "- Doble oportunidad = suma de dos resultados (p.ej. local o empate = home_win+draw).\n"
        "- Over/Under de goles: 'over_under' (over_2.5, under_2.5...). under = 100-over.\n"
        "- Hándicap: 'handicap' (home_-1.5, away_+1.5...). Las claves -2.5/-1.5/+1.5/+2.5 ya son %.\n"
        "- Córners/tarjetas: 'over_under' viene como fracción 0-1; conviértela a % (×100). "
        "'Menos de X' = (1 - over)×100.\n"
        "- Faltas: usa una Poisson con media 'fouls_expected_total' para la línea pedida.\n"
        "- 'Marca' un equipo = home_goals.home_over_0_5 / away_goals.away_over_0_5.\n\n"
        "Calcula la probabilidad combinada como el PRODUCTO de las patas. La cuota justa = "
        "100/combinada. Una combinada tiene valor si la cuota ofrecida supera la cuota justa.\n\n"
        f"PATAS:\n{json.dumps(legs, ensure_ascii=False)}\n\n"
        f"PREDICCIONES:\n{json.dumps(compact, ensure_ascii=False)}\n\n"
        f"CUOTA TOTAL OFRECIDA: {total_odds}\n\n"
        "Devuelve SOLO JSON con esta forma:\n"
        '{"legs":[{"match":"Netherlands vs Japan","market":"Menos de 4.5 goles",'
        '"prob":92.3,"min_odds":1.08,"note":"breve"}],'
        '"combined_prob":27.3,"fair_odds":3.66,"offered_odds":2.5,'
        '"value":"negativo|justo|positivo",'
        '"verdict":"2-3 frases en español sobre qué tan factible es y si tiene valor",'
        '"weakest_leg":"la pata menos probable"}'
    )

    resp = _get_client().messages.create(
        model=MODEL,
        max_tokens=3000,
        messages=[{"role": "user", "content": prompt}],
    )
    result = _json_from_text(_text_block(resp))
    result["stake"] = stake
    return result
