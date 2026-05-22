# ⚽ Predictor Deportivo

App web de predicción estadística de partidos de fútbol. No adivina — calcula.

## Stack

- **Frontend:** Next.js 16 + Tailwind CSS + Axios + Recharts
- **Backend:** Python FastAPI + Uvicorn
- **Modelo:** Reglas ponderadas (Fase 1) → Machine Learning (Fase 2)
- **API deportiva:** Football-Data.org (pendiente — actualmente usa datos mock)

## Cómo ejecutar

### Opción 1 — Script automático
```
Doble clic en start.bat
```

### Opción 2 — Manual

**Backend (Terminal 1):**
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

**Frontend (Terminal 2):**
```bash
cd frontend
npm install
npm run dev
```

Abrir: http://localhost:3000

## API Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/leagues` | Lista de ligas |
| GET | `/leagues/{liga}/matches` | Partidos de una liga |
| GET | `/teams` | Lista de equipos |
| POST | `/predict` | Predicción para un partido |

## Modelo de predicción

| Factor | Peso |
|--------|------|
| Forma reciente | 30% |
| Calidad del plantel | 25% |
| Localía | 15% |
| Lesiones | 15% |
| Historial directo | 10% |
| Clima y condiciones | 5% |

## Roadmap

- [x] Fase 1 — MVP con modelo por reglas
- [ ] Fase 2 — Machine Learning (scikit-learn / XGBoost)
- [ ] Fase 3 — Gráficos, comparación de jugadores
- [ ] Fase 4 — Lanzamiento y monetización
