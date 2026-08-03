# app_escritorio.py
# -----------------------------------------------------------------------------
# Lanza la aplicación como PROGRAMA DE ESCRITORIO (ventana propia), con:
#   - El servidor web por dentro (mismo código de siempre).
#   - Icono en la BANDEJA del sistema: al cerrar la ventana, NO se apaga; sigue
#     leyendo correos en segundo plano. Desde el icono puedes volver a abrirla
#     o salir del todo.
#
# Arráncalo con (sin ventana de consola):
#     pythonw app_escritorio.py
# o con consola (para ver mensajes):
#     python app_escritorio.py
# -----------------------------------------------------------------------------
import os
import sys
import time
import socket
import subprocess
import threading

PROYECTO = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(PROYECTO, "app_escritorio.py")

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

import uvicorn
import webview

HOST = "127.0.0.1"
PORT = 8000
URL = f"http://{HOST}:{PORT}"

_estado = {"tray_ok": False, "icon": None, "window": None}


def _aviso(msg, titulo="Incidencias RFID"):
    """Muestra un mensaje en una ventanita de Windows (funciona sin consola)."""
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, msg, titulo, 0x10)  # icono de error
    except Exception:
        print(msg)


def _servidor_responde():
    """¿Ya hay un servidor escuchando en el puerto?"""
    try:
        with socket.create_connection((HOST, PORT), 0.3):
            return True
    except OSError:
        return False


def _arrancar_servidor():
    """Arranca el servidor FastAPI (sin reload) en este proceso."""
    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=False, log_level="warning")


def _esperar_servidor(timeout=40):
    """Espera a que el puerto esté escuchando antes de abrir la ventana."""
    for _ in range(timeout * 10):
        try:
            with socket.create_connection((HOST, PORT), 0.3):
                return True
        except OSError:
            time.sleep(0.1)
    return False


def _esperar_puerto_libre(timeout=15):
    """Espera a que NADIE escuche en el puerto (la instancia anterior ya murió),
    para reiniciar sin chocar."""
    for _ in range(timeout * 10):
        try:
            with socket.create_connection((HOST, PORT), 0.2):
                pass  # todavía hay alguien escuchando
            time.sleep(0.1)
        except OSError:
            return True  # conexión rechazada => puerto libre
    return False


def _icono():
    """Dibuja un icono sencillo para la bandeja."""
    from PIL import Image, ImageDraw
    img = Image.new("RGBA", (64, 64), (15, 108, 189, 255))  # azul Outlook
    d = ImageDraw.Draw(img)
    d.rectangle([10, 10, 54, 54], outline=(255, 255, 255, 255), width=3)
    d.text((18, 22), "RF", fill=(255, 255, 255, 255))
    return img


def _arrancar_bandeja():
    """Icono en la bandeja: Abrir ventana / Salir."""
    try:
        import pystray
    except Exception:
        return  # sin bandeja: la ventana funcionará igual (cerrar = salir)

    def mostrar(icon, item):
        if _estado["window"]:
            _estado["window"].show()

    def recargar_pagina(icon, item):
        # Para cambios de pantalla/CSS/plantillas: recarga la web sin reiniciar.
        if _estado["window"]:
            try:
                _estado["window"].load_url(URL)
            except Exception:
                pass

    def reiniciar(icon, item):
        # Para cambios de Python: relanza la app entera (nueva instancia).
        subprocess.Popen([sys.executable, SCRIPT, "--reiniciar"], cwd=PROYECTO,
                         close_fds=True)
        try:
            icon.stop()
        except Exception:
            pass
        os._exit(0)

    def salir(icon, item):
        try:
            icon.stop()
        except Exception:
            pass
        os._exit(0)

    menu = pystray.Menu(
        pystray.MenuItem("Abrir Incidencias RFID", mostrar, default=True),
        pystray.MenuItem("Recargar página (cambios de pantalla)", recargar_pagina),
        pystray.MenuItem("Reiniciar app (cambios de programa)", reiniciar),
        pystray.MenuItem("Salir", salir),
    )
    icon = pystray.Icon("incidencias_rfid", _icono(), "Incidencias RFID", menu)
    _estado["icon"] = icon
    _estado["tray_ok"] = True
    icon.run()


def _al_cerrar():
    """Al cerrar la ventana: si hay bandeja, la ocultamos (sigue activo en
    segundo plano). Si no hay bandeja, dejamos que se cierre del todo."""
    if _estado["tray_ok"] and _estado["window"]:
        _estado["window"].hide()
        return False  # cancela el cierre real
    return True       # sin bandeja: cierre normal


def main():
    # Si venimos de un "Reiniciar", esperamos a que la instancia anterior suelte el puerto
    if "--reiniciar" in sys.argv:
        _esperar_puerto_libre()

    # 1) Servidor por dentro. Si YA hay uno escuchando (otra instancia / run.py),
    #    lo reutilizamos en vez de chocar y morir en silencio.
    if not _servidor_responde():
        threading.Thread(target=_arrancar_servidor, daemon=True, name="servidor-web").start()
        if not _esperar_servidor():
            _aviso(
                "No se pudo arrancar el programa en el puerto 8000.\n\n"
                "Suele ser porque ya hay otra ventana abierta usando ese puerto.\n"
                "Cierra las otras (o desde el icono de la bandeja: Salir) y vuelve a intentarlo."
            )
            return

    # 2) Bandeja del sistema (en hilo aparte)
    threading.Thread(target=_arrancar_bandeja, daemon=True, name="bandeja").start()
    time.sleep(0.4)  # damos un instante a que se cree el icono

    # 3) Ventana de escritorio
    try:
        ventana = webview.create_window(
            "Incidencias RFID", URL, width=1280, height=820, min_size=(900, 600),
        )
        _estado["window"] = ventana
        ventana.events.closing += _al_cerrar
        webview.start()
    except Exception as e:
        _aviso(
            "No se pudo abrir la ventana de la aplicación.\n\n"
            f"Detalle: {e}\n\n"
            "Mientras tanto puedes usarla en el navegador: " + URL
        )


if __name__ == "__main__":
    main()
