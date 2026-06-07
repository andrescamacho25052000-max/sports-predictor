@echo off
chcp 65001 > nul
echo.
echo ================================================
echo   Sports Predictor - Entrenar modelo XGBoost
echo ================================================
echo.
echo Este proceso descargara ~3 temporadas de datos
echo reales y entrenara el modelo. Puede tardar
echo 3-5 minutos la primera vez (descarga de datos).
echo.
pause

cd /d "%~dp0backend"

echo.
echo [1/3] Descargando datos historicos de la API...
echo       (se guardan en cache, solo la primera vez)
echo.
python -m ml.collect
if %errorlevel% neq 0 (
    echo ERROR en la descarga. Verifica que el backend funcione.
    pause
    exit /b 1
)

echo.
echo [2/3] Construyendo dataset de entrenamiento...
echo.
python -m ml.build_dataset
if %errorlevel% neq 0 (
    echo ERROR construyendo el dataset.
    pause
    exit /b 1
)

echo.
echo [3/3] Entrenando modelo XGBoost...
echo.
python -m ml.train
if %errorlevel% neq 0 (
    echo ERROR en el entrenamiento.
    pause
    exit /b 1
)

echo.
echo ================================================
echo   Modelo entrenado correctamente.
echo   La proxima vez que uses la app, las predicciones
echo   usaran XGBoost automaticamente.
echo ================================================
echo.
pause
