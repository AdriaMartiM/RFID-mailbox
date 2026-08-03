@echo off
rem Lanza la app de escritorio SIN ventana de consola.
cd /d "%~dp0"
where pythonw >nul 2>nul && (
    start "" pythonw "app_escritorio.py"
) || (
    start "" "%LocalAppData%\Programs\Python\Python314\pythonw.exe" "app_escritorio.py"
)
