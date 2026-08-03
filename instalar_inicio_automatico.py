# instalar_inicio_automatico.py
# -----------------------------------------------------------------------------
# Hace que "Incidencias RFID" se abra SOLA al encender el ordenador (queda en la
# bandeja leyendo correos). Crea un acceso directo en la carpeta de Inicio.
#
#   Activar:    python instalar_inicio_automatico.py
#   Desactivar: python instalar_inicio_automatico.py --quitar
# -----------------------------------------------------------------------------
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

PROYECTO = os.path.dirname(os.path.abspath(__file__))
PYTHONW = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
SCRIPT = os.path.join(PROYECTO, "app_escritorio.py")
STARTUP = os.path.join(os.environ["APPDATA"],
                       r"Microsoft\Windows\Start Menu\Programs\Startup")
ACCESO = os.path.join(STARTUP, "Incidencias RFID.lnk")


def instalar():
    import win32com.client  # viene con pywin32
    shell = win32com.client.Dispatch("WScript.Shell")
    s = shell.CreateShortcut(ACCESO)
    s.TargetPath = PYTHONW
    s.Arguments = f'"{SCRIPT}"'
    s.WorkingDirectory = PROYECTO
    s.WindowStyle = 7  # minimizado
    s.Description = "Gestor de Incidencias RFID"
    s.IconLocation = PYTHONW
    s.Save()
    print("[OK] Arranque automatico ACTIVADO.")
    print("    Se abrira sola al encender el PC. Acceso creado en:")
    print("   ", ACCESO)


def quitar():
    if os.path.exists(ACCESO):
        os.remove(ACCESO)
        print("[OK] Arranque automatico DESACTIVADO.")
    else:
        print("No estaba activado (no habia nada que quitar).")


if __name__ == "__main__":
    if "--quitar" in sys.argv:
        quitar()
    else:
        instalar()
