import os

import requests
from dotenv import load_dotenv


load_dotenv()

API_URL = os.getenv("API_APARTMENTS_URL", "").rstrip("/")
API_KEY = os.getenv("ESTADO_RED_API_KEY", "")


def obtener_departamentos_libres() -> list:
    if not API_URL:
        raise RuntimeError("API_APARTMENTS_URL no está configurada")
    if not API_KEY:
        raise RuntimeError("ESTADO_RED_API_KEY no está configurada")

    response = requests.get(
        f"{API_URL}/calendar/free-apartments",
        headers={"X-API-Key": API_KEY},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def main() -> None:
    try:
        apartments = obtener_departamentos_libres()
    except requests.RequestException as error:
        print(f"Error consultando departamentos libres: {error}")
        raise SystemExit(1)
    except RuntimeError as error:
        print(error)
        raise SystemExit(1)

    if not apartments:
        print("No hay departamentos libres según los iCal consultados.")
        return

    print("Departamentos libres:")
    for apartment in apartments:
        print(
            f"- Departamento {apartment['apartmentId']}: "
            f"{apartment['apartmentName']} "
            f"({apartment['freeDate']})"
        )


if __name__ == "__main__":
    main()
