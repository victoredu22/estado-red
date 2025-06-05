from playwright.sync_api import sync_playwright, TimeoutError
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import requests
from dotenv import load_dotenv
import os
import json


load_dotenv()  # Carga las variables del archivo .env

slack_token = os.getenv('SLACK_TOKEN')
api_url = os.getenv('API_APARTMENTS_URL') 

client = WebClient(token=slack_token)


def enviar_mensaje_a_slack_error(mensaje):
    try:
        response = client.chat_postMessage(
            channel="#estado-red-error",
            text=f"Estado de red:\n{mensaje}"
        )
        print("Mensaje enviado:", response["ts"])
    except SlackApiError as e:
        print("Error al enviar mensaje:", e.response["error"])


def obtener_apartamentos():
    try:
        response = requests.get(api_url)
        print("API URL:", api_url)
        print("Código de estado:", response.status_code)
        print("Texto crudo de la respuesta:", response.text)

        response.raise_for_status()
        data = response.json()
        print("JSON decodificado:", data)
        return data
    except requests.RequestException as e:
        enviar_mensaje_a_slack_error(f"❌ Error al obtener apartamentos: {e}")
        return []


def actualizar_apartamento(apartamento_id, data):
    try:
        url = f"{api_url}/{apartamento_id}"
        print(f"Enviando PATCH a {url} con data: {data}")
        response = requests.patch(url, json=data)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        enviar_mensaje_a_slack_error(f"❌ Error al actualizar apartamento {apartamento_id}: {e}")

def main():

    apartamentos = obtener_apartamentos()

    with sync_playwright() as p:
        for depto in apartamentos:

            navegador = p.chromium.launch(headless=False)
            contexto = navegador.new_context(ignore_https_errors=True)
            pagina = contexto.new_page()
            intentosDepto = depto["attempts"]

            print(intentosDepto)
            try:
                try:
                    pagina.goto(depto["url"]+"")
                except Exception as e:
                    
                        # Actualiza intentos + 1
                        actualizar_apartamento(depto["_id"], {"attempts": intentosDepto + 1, "status":'false'})

                        if intentosDepto < 5:    
                            mensaje = f"❌ No se pudo conectar a {depto['name']} ({depto['url']}): {e}"
                            enviar_mensaje_a_slack_error(mensaje)
                        navegador.close()
                        continue  # Pasar al siguiente departamento
            
                # Llenar usuario y contraseña dinámicamente
                pagina.locator("input[type='text']").nth(0).fill(depto["user"])
                pagina.locator("input[type='password']").nth(0).fill(depto["password"])

                # Intentar login
                try:
                    pagina.locator("text=Acceder").nth(1).click()
                except Exception as e:
                    mensaje = f"❌ No se pudo hacer clic en Acceder en {depto['name']}: {e}"
                    enviar_mensaje_a_slack_error(mensaje)
                    navegador.close()
                    continue

                pagina.wait_for_timeout(3000)

            finally:
                navegador.close()


if __name__ == "__main__":
    main()
