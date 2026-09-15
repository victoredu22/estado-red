import datetime
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor

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

DIAS_SEMANA = [
    "lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"
]
MESES_NOMBRES = [
    "", "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
]


def format_date_es(d: datetime.date) -> str:
    return f"{DIAS_SEMANA[d.weekday()]}, {d.day} de {MESES_NOMBRES[d.month]} de {d.year}"


def parse_ics(text: str) -> list[dict]:
    events = []
    current = {}
    for line in text.splitlines():
        line = line.strip()
        if line == "BEGIN:VEVENT":
            current = {}
        elif line == "END:VEVENT":
            if "start" in current and "end" in current:
                events.append(current)
            current = {}
        elif line.startswith("DTSTART"):
            m = re.search(r"(\d{8})", line)
            if m:
                current["start"] = datetime.datetime.strptime(m.group(1), "%Y%m%d").date()
        elif line.startswith("DTEND"):
            m = re.search(r"(\d{8})", line)
            if m:
                current["end"] = datetime.datetime.strptime(m.group(1), "%Y%m%d").date()
        elif line.startswith("SUMMARY:"):
            current["summary"] = line[8:].strip()
    return sorted(events, key=lambda x: x["start"])


def fetch_apartment_ical(apt: dict) -> tuple[dict, list[dict] | None, str | None]:
    ical_url = apt.get("ical")
    if not ical_url:
        return apt, None, "Sin iCal configurado"
    try:
        res = requests.get(ical_url, timeout=10)
        res.raise_for_status()
        events = parse_ics(res.text)
        return apt, events, None
    except Exception as e:
        return apt, None, f"Error al consultar iCal: {e}"


def obtener_departamentos_ocupados(apartment_id: str | None = None) -> list:
    if not API_URL:
        raise RuntimeError("API_APARTMENTS_URL no está configurada")
    if not API_KEY:
        raise RuntimeError("ESTADO_RED_API_KEY no está configurada")

    headers = {"X-API-Key": API_KEY}
    response = requests.get(f"{API_URL}/room-routers", headers=headers, timeout=15)
    response.raise_for_status()
    routers = response.json()

    apartments = {}
    for r in routers:
        apt = r.get("apartmentId")
        if apt and apt.get("id"):
            aid = apt["id"]
            if apartment_id and str(aid) != str(apartment_id):
                continue
            apartments[aid] = {
                "id": aid,
                "name": apt.get("name") or f"Departamento {aid}",
                "ical": apt.get("ical"),
            }

    if not apartments:
        return []

    # Fecha de referencia (zona horaria de Chile UTC-3)
    tz_chile = datetime.timezone(datetime.timedelta(hours=-3))
    hoy = datetime.datetime.now(tz_chile).date()

    sorted_apts = [apartments[k] for k in sorted(apartments.keys())]
    with ThreadPoolExecutor(max_workers=5) as executor:
        ical_results = list(executor.map(fetch_apartment_ical, sorted_apts))

    results = []
    for apt, events, error in ical_results:
        if error or not events:
            continue

        # Reserva en curso / ocupado: empezó hoy o antes, y termina después de hoy
        current_events = [e for e in events if e["start"] <= hoy < e["end"]]
        if current_events:
            curr = current_events[0]
            check_in_str = format_date_es(curr["start"])
            if curr["start"] == hoy:
                check_in_str = f"hoy - {check_in_str}"

            results.append({
                "apartmentId": apt["id"],
                "apartmentName": apt["name"],
                "checkIn": check_in_str,
                "checkOut": format_date_es(curr["end"]),
                "summary": curr.get("summary", "Sin detalle"),
            })

    return results


def main() -> None:
    apartment_id = sys.argv[1] if len(sys.argv) > 1 else None

    try:
        ocupados = obtener_departamentos_ocupados(apartment_id)
    except requests.RequestException as error:
        print(f"Error consultando departamentos ocupados: {error}")
        raise SystemExit(1)
    except RuntimeError as error:
        print(error)
        raise SystemExit(1)

    if not ocupados:
        print("No hay departamentos ocupados actualmente según los iCal consultados.")
        return

    print("Departamentos ocupados:\n")
    bloques = []
    for apt in ocupados:
        bloques.append(
            f"Departamento {apt['apartmentId']}: {apt['apartmentName']}\n"
            f"  Check-in: {apt['checkIn']}\n"
            f"  Check-out: {apt['checkOut']}\n"
            f"  Estado: {apt['summary']}"
        )
    print("\n---\n".join(bloques))


if __name__ == "__main__":
    main()
