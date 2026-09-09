import os
import sys

import requests
from dotenv import load_dotenv


load_dotenv()

API_URL = os.getenv("API_APARTMENTS_URL", "").rstrip("/")
API_KEY = os.getenv("ESTADO_RED_API_KEY", "")


def obtener_proximas_llegadas(apartment_id: str | None = None) -> list:
    if not API_URL:
        raise RuntimeError("API_APARTMENTS_URL no está configurada")
    if not API_KEY:
        raise RuntimeError("ESTADO_RED_API_KEY no está configurada")

    params = {"apartmentId": apartment_id} if apartment_id else None
    response = requests.get(
        f"{API_URL}/calendar/next-arrivals",
        headers={"X-API-Key": API_KEY},
        params=params,
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def main() -> None:
    apartment_id = sys.argv[1] if len(sys.argv) > 1 else None

    try:
        arrivals = obtener_proximas_llegadas(apartment_id)
    except requests.RequestException as error:
        print(f"Error consultando próximas llegadas: {error}")
        raise SystemExit(1)
    except RuntimeError as error:
        print(error)
        raise SystemExit(1)

    if not arrivals:
        print("No se encontraron departamentos con iCal configurado.")
        return

    for apartment in arrivals:
        reservation = apartment.get("nextArrival")
        title = f"Departamento {apartment.get('apartmentId')}: {apartment.get('apartmentName')}"

        if apartment.get("error"):
            print(f"{title} - {apartment['error']}")
        elif reservation:
            print(
                f"{title}\n"
                f"  Check-in: {reservation['checkIn']}\n"
                f"  Check-out: {reservation['checkOut']}\n"
                f"  Estado: {reservation.get('summary', 'Sin detalle')}"
            )
        else:
            print(f"{title} - Sin eventos en el iCal.")


if __name__ == "__main__":
    main()
