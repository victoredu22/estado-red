import os
import sys

import requests
from dotenv import load_dotenv

# Forzar salida en UTF-8 para evitar errores de codificación en Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

load_dotenv()

API_URL = os.getenv("API_APARTMENTS_URL", "").rstrip("/")
API_KEY = os.getenv("ESTADO_RED_API_KEY", "")


def activar_llamada() -> dict:
    if not API_URL:
        raise RuntimeError("API_APARTMENTS_URL no está configurada")
    if not API_KEY:
        raise RuntimeError("ESTADO_RED_API_KEY no está configurada")

    response = requests.post(
        f"{API_URL}/fcm/call",
        headers={"X-API-Key": API_KEY},
        json={},
        timeout=15,
    )
    response.raise_for_status()
    return response.json()


def main() -> None:
    try:
        result = activar_llamada()
        print("📞 Señal de llamada enviada con éxito:")
        if result.get("messageId"):
            print(f"• Message ID: {result.get('messageId')}")
        print("El dispositivo móvil debería comenzar a sonar.")
    except (requests.RequestException, RuntimeError) as error:
        print(f"[ERROR] Error activando llamada: {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
