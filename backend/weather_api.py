import requests

GEO_URL     = "https://geocoding-api.open-meteo.com/v1/search"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"

# Weathercode → descripción + emoji (WMO standard)
WEATHER_DESC = {
    0:  ("Despejado",          "☀️"),
    1:  ("Mayormente despejado","🌤️"),
    2:  ("Parcialmente nublado","⛅"),
    3:  ("Nublado",            "☁️"),
    45: ("Niebla",             "🌫️"),
    48: ("Niebla con escarcha", "🌫️"),
    51: ("Llovizna leve",      "🌦️"),
    53: ("Llovizna moderada",  "🌦️"),
    55: ("Llovizna intensa",   "🌧️"),
    61: ("Lluvia leve",        "🌧️"),
    63: ("Lluvia moderada",    "🌧️"),
    65: ("Lluvia intensa",     "🌧️"),
    71: ("Nevada leve",        "🌨️"),
    73: ("Nevada moderada",    "🌨️"),
    75: ("Nevada intensa",     "❄️"),
    80: ("Chubascos leves",    "🌦️"),
    81: ("Chubascos moderados","🌧️"),
    82: ("Chubascos intensos", "⛈️"),
    95: ("Tormenta",           "⛈️"),
    99: ("Tormenta con granizo","⛈️"),
}

SURFACE_LABELS = {
    "grass":          "Césped natural",
    "artificial turf":"Césped artificial",
    "hybrid grass":   "Césped híbrido",
    "dirt":           "Tierra",
}


def get_coordinates(city: str) -> tuple[float, float] | None:
    """Geocodifica el nombre de una ciudad usando Open-Meteo."""
    try:
        r = requests.get(GEO_URL, params={"name": city, "count": 1, "language": "es"}, timeout=8)
        if r.status_code == 200:
            results = r.json().get("results", [])
            if results:
                return results[0]["latitude"], results[0]["longitude"]
    except Exception as e:
        print(f"[Weather] Geocoding error: {e}")
    return None


def get_weather(city: str, date: str) -> dict | None:
    """
    Retorna el pronóstico del clima para una ciudad y fecha dada.
    date formato: 'YYYY-MM-DD'
    """
    coords = get_coordinates(city)
    if not coords:
        return None

    lat, lon = coords
    try:
        r = requests.get(WEATHER_URL, params={
            "latitude":  lat,
            "longitude": lon,
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,windspeed_10m_max,weathercode",
            "timezone":  "auto",
            "forecast_days": 16,
        }, timeout=8)

        if r.status_code != 200:
            return None

        data  = r.json()
        dates = data["daily"]["time"]

        if date not in dates:
            # Si la fecha no está en el pronóstico, tomamos el más cercano disponible
            idx = 0
        else:
            idx = dates.index(date)

        code = data["daily"]["weathercode"][idx]
        desc, emoji = WEATHER_DESC.get(code, ("Desconocido", "🌡️"))

        temp_max  = data["daily"]["temperature_2m_max"][idx]
        temp_min  = data["daily"]["temperature_2m_min"][idx]
        precip    = data["daily"]["precipitation_sum"][idx]
        wind      = data["daily"]["windspeed_10m_max"][idx]

        # Impacto en el juego
        impact = _weather_impact(code, precip, wind)

        return {
            "city":        city,
            "date":        dates[idx],
            "temp_max":    temp_max,
            "temp_min":    temp_min,
            "precipitation": precip,
            "windspeed":   wind,
            "description": desc,
            "emoji":       emoji,
            "impact":      impact,
        }
    except Exception as e:
        print(f"[Weather] Forecast error: {e}")
        return None


def _weather_impact(code: int, precip: float, wind: float) -> str:
    """Describe el impacto del clima en el partido."""
    if code in (95, 99):
        return "Tormenta — condiciones muy adversas para el juego"
    if code in (61, 63, 65, 80, 81, 82):
        return "Lluvia — puede afectar el pase y la velocidad del balón"
    if code in (71, 73, 75):
        return "Nevada — condiciones muy difíciles, terreno resbaladizo"
    if wind > 50:
        return "Viento fuerte — afecta tiros libres y centros"
    if wind > 30:
        return "Viento moderado — puede influir en el juego aéreo"
    if precip > 5:
        return "Lluvia considerable — terreno pesado"
    if code in (0, 1):
        return "Condiciones ideales para el juego"
    return "Condiciones normales"
