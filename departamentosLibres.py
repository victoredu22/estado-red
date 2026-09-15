import datetime
import os
import re
import sys

import requests
from dotenv import load_dotenv

# Forzar salida en UTF-8 para evitar errores de codificación en Windows
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


load_dotenv()

API_URL = os.getenv("API_APARTMENTS_URL", "").rstrip("/")
API_KEY = os.getenv("ESTADO_RED_API_KEY", "")

MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
}


def es_hoy(fecha_str: str) -> bool:
    if not fecha_str:
        return False

    texto = fecha_str.lower().strip()
    if "hoy" in texto:
        return True

    # Fechas de referencia para 'hoy': hora local del sistema y zona de Chile (UTC-3 / UTC-4)
    hoy_fechas = {datetime.date.today()}
    for offset in (-3, -4):
        tz = datetime.timezone(datetime.timedelta(hours=offset))
        hoy_fechas.add(datetime.datetime.now(tz).date())

    # Formato común en español: "domingo, 13 de septiembre de 2026"
    match = re.search(r"(\d{1,2})\s+de\s+([a-zA-Záéíóúñ]+)(?:\s+de\s+(\d{4}))?", texto)
    if match:
        dia = int(match.group(1))
        mes = MESES.get(match.group(2))
        if mes:
            año = int(match.group(3)) if match.group(3) else datetime.date.today().year
            try:
                if datetime.date(año, mes, dia) in hoy_fechas:
                    return True
            except ValueError:
                pass

    # Formato ISO: YYYY-MM-DD
    match_iso = re.search(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b", texto)
    if match_iso:
        try:
            if datetime.date(int(match_iso.group(1)), int(match_iso.group(2)), int(match_iso.group(3))) in hoy_fechas:
                return True
        except ValueError:
            pass

    # Formato DD/MM/YYYY
    match_slash = re.search(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b", texto)
    if match_slash:
        try:
            if datetime.date(int(match_slash.group(3)), int(match_slash.group(2)), int(match_slash.group(1))) in hoy_fechas:
                return True
        except ValueError:
            pass

    return False


def formatear_fecha(fecha_str: str) -> str:
    if not fecha_str:
        return ""
    texto = fecha_str.strip()
    if "hoy" in texto.lower():
        return texto
    if es_hoy(texto):
        return f"hoy - {texto}"
    return texto


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

    libres_actuales = [
        apt for apt in apartments
        if not apt.get("freeDate") or es_hoy(apt.get("freeDate", ""))
    ]

    if not libres_actuales:
        print("No hay departamentos libres actualmente según los iCal consultados.")
        return

    print("Departamentos libres:\n")
    bloques = []
    for apartment in libres_actuales:
        fecha = formatear_fecha(apartment.get("freeDate", ""))
        fecha_texto = f" ({fecha})" if fecha else ""
        bloques.append(
            f"- Departamento {apartment['apartmentId']}: "
            f"{apartment['apartmentName']}"
            f"{fecha_texto}"
        )
    print("\n---\n".join(bloques))


if __name__ == "__main__":
    main()
