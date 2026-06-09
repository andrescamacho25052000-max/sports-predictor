"""
ml/elo.py — Sistema de Elo Rating para fútbol.

Cada equipo arranca con 1500 puntos. Después de cada partido:
  - El ganador sube, el perdedor baja
  - Cuanto más inesperado el resultado, mayor el cambio
  - El margen de goles amplifica el cambio (ganar 4-0 ≠ ganar 1-0)
  - Ventaja de localía: +100 pts en el cálculo esperado

Los ratings finales se guardan en ml/data/elo_ratings.json
para usarse en predicciones en tiempo real.
"""
import json, os

DATA_DIR  = os.path.join(os.path.dirname(__file__), "data")
ELO_PATH  = os.path.join(DATA_DIR, "elo_ratings.json")

BASE_ELO  = 1500    # rating de un equipo nuevo / desconocido
K_FACTOR  = 32      # sensibilidad (más alto = cambia más rápido)
HOME_ADV  = 100     # puntos extra al local en el cálculo esperado


def _expected_score(elo_a: float, elo_b: float) -> float:
    """Probabilidad esperada de victoria para el equipo A."""
    return 1 / (1 + 10 ** ((elo_b - elo_a) / 400))


def _margin_multiplier(goal_diff: int) -> float:
    """Amplifica el cambio de Elo según la diferencia de goles."""
    if goal_diff <= 1: return 1.00
    if goal_diff == 2: return 1.50
    return 1.75


class EloSystem:
    """Mantiene y actualiza los ratings Elo de todos los equipos."""

    def __init__(self):
        self.ratings: dict[int, float] = {}

    # ── Consulta ──────────────────────────────────────────────────

    def get(self, team_id: int) -> float:
        return self.ratings.get(team_id, BASE_ELO)

    def diff(self, home_id: int, away_id: int) -> float:
        """Diferencia de Elo (local − visitante)."""
        return self.get(home_id) - self.get(away_id)

    def expected_home_win(self, home_id: int, away_id: int) -> float:
        """Prob. de victoria local incluyendo ventaja de localía."""
        return _expected_score(self.get(home_id) + HOME_ADV, self.get(away_id))

    # ── Actualización ────────────────────────────────────────────

    def update(self, home_id: int, away_id: int,
               home_goals: int, away_goals: int) -> tuple[float, float]:
        """
        Registra un partido y actualiza ambos ratings.
        Devuelve (elo_home_antes, elo_away_antes).
        """
        h_before = self.get(home_id)
        a_before = self.get(away_id)

        exp_h = _expected_score(h_before + HOME_ADV, a_before)
        exp_a = 1 - exp_h

        if home_goals > away_goals:
            act_h, act_a = 1.0, 0.0
        elif home_goals < away_goals:
            act_h, act_a = 0.0, 1.0
        else:
            act_h, act_a = 0.5, 0.5

        mult = _margin_multiplier(abs(home_goals - away_goals))

        self.ratings[home_id] = h_before + K_FACTOR * mult * (act_h - exp_h)
        self.ratings[away_id] = a_before + K_FACTOR * mult * (act_a - exp_a)

        return h_before, a_before

    # ── Persistencia ─────────────────────────────────────────────

    def save(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        data = {str(k): round(v, 2) for k, v in self.ratings.items()}
        with open(ELO_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"  Elo guardado: {len(data)} equipos -> {ELO_PATH}")

    def load(self) -> "EloSystem":
        if os.path.exists(ELO_PATH):
            with open(ELO_PATH, encoding="utf-8") as f:
                data = json.load(f)
            self.ratings = {int(k): float(v) for k, v in data.items()}
        return self

    def top(self, n: int = 10) -> list[tuple[int, float]]:
        """Devuelve los N equipos con mayor Elo."""
        return sorted(self.ratings.items(), key=lambda x: -x[1])[:n]
