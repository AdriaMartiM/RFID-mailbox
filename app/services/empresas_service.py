# app/services/empresas_service.py
# -----------------------------------------------------------------------------
# Lista de empresas/marcas del desplegable "Empresa".
#
# Sale de 'empresas.json' (en la raíz del proyecto), que se edita a mano. El
# archivo se relee solo cuando cambia: basta con guardar y recargar la página,
# no hace falta reiniciar el programa.
# -----------------------------------------------------------------------------
import json
import os

ARCHIVO = os.getenv("EMPRESAS_JSON", "empresas.json")

# Caché: nos quedamos con lo leído y la fecha del archivo, para no abrirlo en
# cada petición pero enterarnos igualmente si lo editas.
_cache = {"mtime": None, "empresas": []}


def _normalizar(datos) -> list:
    """Admite las dos formas razonables del archivo:
         {"empresas": ["A", "B"]}   ó   ["A", "B"]
    Quita vacíos y repetidos, respetando el orden en que están escritos."""
    if isinstance(datos, dict):
        datos = datos.get("empresas", [])
    if not isinstance(datos, list):
        return []
    vistos, limpias = set(), []
    for e in datos:
        if not isinstance(e, str):
            continue
        nombre = e.strip()
        clave = nombre.lower()
        if not nombre or clave in vistos:
            continue
        vistos.add(clave)
        limpias.append(nombre)
    return limpias


def cargar_empresas() -> list:
    """Devuelve la lista de empresas del JSON. Si el archivo no existe o está
    mal escrito, devuelve una lista vacía (quien llame decide qué hacer) y avisa
    por consola, para que un JSON con una coma de más no tumbe la web."""
    try:
        mtime = os.path.getmtime(ARCHIVO)
    except OSError:
        return []

    if _cache["mtime"] == mtime:
        return _cache["empresas"]

    try:
        with open(ARCHIVO, "r", encoding="utf-8") as f:
            empresas = _normalizar(json.load(f))
    except (OSError, json.JSONDecodeError) as e:
        print(f"[AVISO] No se pudo leer '{ARCHIVO}': {e}")
        print("        Revisa que sea JSON válido (comillas dobles, sin coma final).")
        return _cache["empresas"]   # nos quedamos con lo último que sí funcionó

    _cache["mtime"] = mtime
    _cache["empresas"] = empresas
    return empresas
