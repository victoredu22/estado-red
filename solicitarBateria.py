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
HEADERS = {"X-API-Key": API_KEY}


def main() -> None:
    if not API_URL:
        print("[ERROR] API_APARTMENTS_URL no está configurada")
        sys.exit(1)
    if not API_KEY:
        print("[ERROR] ESTADO_RED_API_KEY no está configurada")
        sys.exit(1)

    try:
        response = requests.post(
            f"{API_URL}/fcm/battery/request",
            headers=HEADERS,
            json={},
            timeout=15,
        )
        response.raise_for_status()
        data = response.json()

        print("📲 Solicitud de batería enviada con éxito:")
        print(f"• Request ID: {data.get('requestId', 'N/A')}")
        if data.get("messageId"):
            print(f"• Message ID: {data.get('messageId')}")
        print("Esperando que el dispositivo reporte su estado...")
    except requests.RequestException as err:
        print(f"[ERROR] Error al solicitar batería: {err}")
        sys.exit(1)


if __name__ == "__main__":
    main()
