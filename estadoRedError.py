from playwright.sync_api import sync_playwright, TimeoutError
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import requests
from dotenv import load_dotenv
import os
import json
import socketio

load_dotenv()  # Carga las variables del archivo .env
api_url = os.getenv('API_APARTMENTS_URL') 

def obtener_apartamentos():
    try:
        url = f"{api_url}/room-routers"
        response = requests.get(url)
        print("API URL:", url)
        print("Código de estado:", response.status_code)
        response.raise_for_status()
        data = response.json()
        return data
    except requests.RequestException as e:
        print(f"Error al obtener routers: {e}")
        return []


def actualizar_apartamento(apartamento_id, data):
    try:
        url = f"{api_url}/room-routers/{apartamento_id}"
        print(f"Enviando PATCH a {url} con data: {data}")
        response = requests.patch(url, json=data)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error al actualizar router {apartamento_id}: {e}")
        return None


def main():
    routers = obtener_apartamentos()

    with sync_playwright() as p:
        for depto in routers:
            if depto["active"]:
                navegador = p.chromium.launch(headless=False)
                contexto = navegador.new_context(ignore_https_errors=True)
                pagina = contexto.new_page()
                intentosDepto = depto["attempts"]

                apt_info = depto.get("apartmentId") or {}
                apt_name = apt_info.get("name", "Desconocido")

                actualizar_apartamento(depto["_id"], {"status": True})

                try:
                    try:
                        pagina.goto(depto["url"] + "")
                    except Exception as e:
                        # Actualiza intentos + 1
                        actualizar_apartamento(depto["_id"], {"attempts": intentosDepto + 1, "status": False})

                        if intentosDepto < 5:    
                            mensaje = f"❌ No se pudo conectar a {apt_name} ({depto['url']}): {e}"
                            print(mensaje)
                        navegador.close()
                        continue  # Pasar al siguiente departamento
            
                    # Llenar usuario y contraseña dinámicamente
                    pagina.locator("input[type='text']").nth(0).fill(depto["user"])
                    pagina.locator("input[type='password']").nth(0).fill(depto["password"])

                    # Intentar login
                    try:
                        pagina.locator("text=Acceder").nth(1).click()
                    except Exception as e:
                        mensaje = f"❌ No se pudo hacer clic en Acceder en {apt_name}: {e}"
                        print(mensaje)
                        navegador.close()
                        continue

                    pagina.wait_for_timeout(3000)

                finally:
                    navegador.close()


if __name__ == "__main__":
    main()
