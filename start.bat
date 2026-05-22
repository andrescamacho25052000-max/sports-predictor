@echo off
echo Iniciando Sports Predictor...

echo.
echo [1/2] Instalando dependencias del backend...
cd backend
pip install -r requirements.txt -q

echo.
echo [2/2] Iniciando backend en puerto 8000...
start "Backend FastAPI" cmd /k "uvicorn main:app --reload --port 8000"

timeout /t 2 /nobreak > nul

echo.
echo [3/3] Iniciando frontend en puerto 3000...
cd ..\frontend
start "Frontend Next.js" cmd /k "npm run dev"

echo.
echo Listo! Abre http://localhost:3000 en tu navegador.
pause
