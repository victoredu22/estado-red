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
        response = requests.get(
            f"{API_URL}/fcm/battery",
            headers=HEADERS,
            timeout=15,
        )
        response.raise_for_status()
        data = response.json()

        bateria = data.get("battery", "N/A")
        cargando = "Sí ⚡" if data.get("charging") else "No"
        dispositivo = data.get("deviceId", "Desconocido")
        actualizado = data.get("updatedAt", "Sin fecha")

        print("🔋 Estado actual de batería:")
        print(f"• Nivel de batería: {bateria}%")
        print(f"• Cargando: {cargando}")
        print(f"• Dispositivo: {dispositivo}")
        print(f"• Última actualización: {actualizado}")
    except requests.RequestException as err:
        print(f"[ERROR] Error al obtener batería: {err}")
        sys.exit(1)


if __name__ == "__main__":
    main()
