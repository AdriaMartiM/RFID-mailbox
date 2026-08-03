@echo off
rem Igual que el lanzador normal pero CON consola, para ver errores si algo falla.
cd /d "%~dp0"
echo Iniciando Incidencias RFID (modo diagnostico)...
echo.
python "app_escritorio.py"
echo.
echo ---------------------------------------------
echo Si la ventana no abrio, arriba esta el motivo.
pause
