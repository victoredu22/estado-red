from playwright.sync_api import sync_playwright, TimeoutError
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from connection import get_apartment, update_apartment
import requests
from dotenv import load_dotenv
import os
import socketio

load_dotenv()  # Carga las variables del archivo .env
slack_token = os.getenv("SLACK_TOKEN")
api_url = os.getenv('API_APARTMENTS_URL') 
client = WebClient(token=slack_token)

sio = socketio.Client()
sio_url = os.getenv('SERVER_SOCKET')
def enviar_mensaje_a_slack(mensaje):
    try:
        response = client.chat_postMessage(
            channel="#estado-red",
            text=f"Estado de red:\n{mensaje}"
        )
        print("Mensaje enviado:", response["ts"])
    except SlackApiError as e:
        print("Error al enviar mensaje:", e.response["error"])


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
        print(f"Enviando Patch a {url} con data: {data}")
        response = requests.patch(url, json=data)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        enviar_mensaje_a_slack_error(f"❌ Error al actualizar apartamento {apartamento_id}: {e}")

def main():

    apartamentos = obtener_apartamentos()

    sio.connect(sio_url)
    with sync_playwright() as p:
        for depto in apartamentos:
            navegador = p.chromium.launch(headless=False)
            contexto = navegador.new_context(ignore_https_errors=True)
            pagina = contexto.new_page()

            # Actualiza intentos a 0 (por ejemplo)
            actualizar_apartamento(depto["_id"], {"status": 'true'})
            sio.emit("canalFrontend", "ejecutando script departamento numero: " + str(depto["id"]))

            try:
                try:
                    pagina.goto(depto["url"])
                except Exception as e:
                    intentosDepto = depto["attempts"]
                    # Actualiza intentos + 1
                    actualizar_apartamento(depto["_id"], {"attempts": intentosDepto + 1, "status":'false'})
                    mensaje = f"❌ No se pudo conectar a {depto['name']} ({depto['url']}): {e}"
                    enviar_mensaje_a_slack_error(mensaje)
                    navegador.close()
                    continue
   
                pagina.locator("input[type='text']").nth(0).fill(depto["user"])
                pagina.locator("input[type='password']").nth(0).fill(depto["password"])

                try:
                    pagina.locator("text=Acceder").nth(1).click()
                except Exception as e:
                    mensaje = f"No se pudo hacer clic en Acceder en {depto['name']}: {e}"
                    enviar_mensaje_a_slack(mensaje)
                    navegador.close()
                    continue

                try:
                    pagina.wait_for_selector("#lan-info-ip", timeout=5000)
                    if pagina.locator("#lan-info-ip").is_visible():
                        ip_texto = pagina.locator("#lan-info-ip pre").inner_text()
                        mensaje = f"IP encontrada en {depto['name']}: `{ip_texto}`"
                    else:
                        mensaje = f"Se ingresó, pero no se encontró la IP en {depto['name']}."
                except TimeoutError:
                    if pagina.url.endswith("/login") or "login" in pagina.title().lower():
                        mensaje = f"Credenciales incorrectas para {depto['name']}."
                    else:
                        mensaje = f"No se encontró la IP. Timeout en {depto['name']}."

                enviar_mensaje_a_slack(mensaje)
                pagina.wait_for_timeout(3000)

            finally:
                sio.emit("canalFrontend", "finalizado script departamento numero: " + str(depto["id"]))
                navegador.close()

    sio.disconnect()
if __name__ == "__main__":
    main()
