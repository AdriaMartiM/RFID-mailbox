# autenticar_outlook.py
# -----------------------------------------------------------------------------
# Login de Outlook (modo delegado) de USO ÚNICO. Versión AUTOMÁTICA:
#   1) Abre el navegador con la pantalla de Microsoft.
#   2) Tú inicias sesión y aceptas.
#   3) Microsoft redirige a http://localhost:8400/... y este script CAPTURA el
#      código él solo (no hay que copiar ni pegar nada).
#   4) Guarda la sesión en 'o365_token.txt'. A partir de ahí, run.py lee solo.
#
# Ejecútalo así, una sola vez:
#     python autenticar_outlook.py
# -----------------------------------------------------------------------------
import sys
import webbrowser
import http.server
from urllib.parse import urlparse, parse_qs

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

from app.services.outlook_service import construir_account, SCOPES, REDIRECT_URI

# Puerto donde escuchamos el redirect (debe coincidir con REDIRECT_URI).
_PUERTO = urlparse(REDIRECT_URI).port or 80
_captura = {}


class _Handler(http.server.BaseHTTPRequestHandler):
    """Recoge la redirección de Microsoft (con el 'code') en localhost:8400."""
    def do_GET(self):
        qs = parse_qs(urlparse(self.path).query)
        if "code" in qs or "error" in qs:
            _captura["url"] = f"{REDIRECT_URI}{self.path}"
            cuerpo = ("<html><body style='font-family:sans-serif;text-align:center;margin-top:80px'>"
                      "<h2>Conexion completada</h2>"
                      "<p>Ya puedes cerrar esta pestana y volver al programa.</p>"
                      "</body></html>")
        else:
            cuerpo = "<html><body>Esperando…</body></html>"
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(cuerpo.encode("utf-8"))

    def log_message(self, *args):
        pass  # sin ruido en consola


def main():
    account = construir_account()

    if account.is_authenticated:
        print("Ya habia una sesion valida guardada. No hace falta volver a entrar.")
        return

    # 1) Generamos la URL de login
    url, flow = account.con.get_authorization_url(requested_scopes=SCOPES)

    # 2) Levantamos el servidor local que recogerá el redirect
    try:
        servidor = http.server.HTTPServer(("localhost", _PUERTO), _Handler)
    except OSError as e:
        print(f"[ERROR] No se pudo abrir el puerto {_PUERTO} en localhost: {e}")
        print("  ¿Hay otro programa usándolo? Cierra y reintenta.")
        return

    print("Se va a abrir el navegador para iniciar sesion en Outlook.")
    print("   1) Inicia sesion con tu cuenta (la que accede al buzon rfid@).")
    print("   2) Acepta los permisos.")
    print("   3) Cuando veas 'Conexion completada', vuelve aqui. (Automatico)\n")
    print("Si el navegador no se abre solo, abre esta URL a mano:\n")
    print(url + "\n")

    try:
        webbrowser.open(url)
    except Exception:
        pass

    # 3) Esperamos a recibir el redirect con el código (una sola petición útil)
    print("Esperando a que completes el inicio de sesion en el navegador…")
    while "url" not in _captura:
        servidor.handle_request()
    servidor.server_close()

    # 4) Intercambiamos el código por el token y lo guardamos
    redirect_url = _captura["url"]
    if "error" in parse_qs(urlparse(redirect_url).query):
        print("\n[ERROR] Microsoft devolvio un error en el login. Revisa los permisos e intentalo de nuevo.")
        return

    ok = account.con.request_token(redirect_url, flow=flow)
    if ok:
        print("\n[OK] Sesion guardada en 'o365_token.txt'.")
        print("Ya puedes arrancar el programa con:  python run.py")
    else:
        print("\n[ERROR] No se pudo obtener el token. Intentalo de nuevo.")


if __name__ == "__main__":
    main()
