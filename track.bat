@echo off
chcp 65001 > nul
echo.
echo ╔══════════════════════════════════════════════════╗
echo ║   Sports Predictor — Auto Tracker               ║
echo ║   Predice partidos y registra resultados reales ║
echo ╚══════════════════════════════════════════════════╝
echo.
echo Opciones:
echo   [1] Ejecutar completo (predecir + resultados)
echo   [2] Solo predecir partidos proximos
echo   [3] Solo actualizar resultados
echo   [4] Dry-run (ver que haria sin guardar nada)
echo   [5] Salir
echo.
set /p opcion="Elige una opcion (1-5): "

if "%opcion%"=="1" goto completo
if "%opcion%"=="2" goto solo_pred
if "%opcion%"=="3" goto solo_res
if "%opcion%"=="4" goto dryrun
if "%opcion%"=="5" goto fin
goto fin

:completo
cd /d "%~dp0backend"
python loop_agent.py
goto pausa

:solo_pred
cd /d "%~dp0backend"
python loop_agent.py --solo-pred
goto pausa

:solo_res
cd /d "%~dp0backend"
python loop_agent.py --solo-res
goto pausa

:dryrun
cd /d "%~dp0backend"
python loop_agent.py --dry-run
goto pausa

:pausa
echo.
pause

:fin
