import os
import sys
import time

import requests
from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv("API_APARTMENTS_URL", "").rstrip("/")
API_KEY = os.getenv("ESTADO_RED_API_KEY", "")
HEADERS = {"X-API-Key": API_KEY}


def validar_configuracion() -> None:
    if not API_URL:
        raise RuntimeError("API_APARTMENTS_URL no está configurada")
    if not API_KEY:
        raise RuntimeError("ESTADO_RED_API_KEY no está configurada")


def solicitar_bateria() -> dict:
    response = requests.post(
        f"{API_URL}/fcm/battery/request",
        headers=HEADERS,
        json={},
        timeout=15,
    )
    response.raise_for_status()
    return response.json()


def obtener_bateria() -> dict | None:
    response = requests.get(
        f"{API_URL}/fcm/battery",
        headers=HEADERS,
        timeout=15,
    )
    response.raise_for_status()
    return response.json()


def consultar_bateria() -> dict:
    request = solicitar_bateria()
    request_id = request.get("requestId")

    # FCM es asíncrono: esperamos a que Android responda y actualice MongoDB.
    for _ in range(15):
        status = obtener_bateria()
        if status and status.get("requestId") == request_id:
            return status
        time.sleep(1)

    raise TimeoutError("El teléfono no respondió con el estado de batería")


def main() -> None:
    try:
        validar_configuracion()
        status = consultar_bateria()
        print("Estado de batería:")
        print(f"  Batería: {status.get('battery')}%")
        print(f"  Cargando: {'sí' if status.get('charging') else 'no'}")
        print(f"  Dispositivo: {status.get('deviceId', 'sin identificar')}")
        print(f"  Actualizado: {status.get('updatedAt', 'sin fecha')}")
    except (requests.RequestException, RuntimeError, TimeoutError) as error:
        print(f"Error consultando batería: {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
