import sys
import uvicorn

# Permite imprimir emojis en la consola de Windows (evita UnicodeEncodeError)
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

print("Arrancando servidor...")

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True
    )

    