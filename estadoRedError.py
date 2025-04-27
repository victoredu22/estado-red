from playwright.sync_api import sync_playwright, TimeoutError
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from dotenv import load_dotenv
import os

load_dotenv()  # Carga las variables del archivo .env

slack_token = os.getenv('SLACK_TOKEN')
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

# Lista de departamentos con su IP, usuario y contraseña
departamentos = [
    {
        "nombre": "Departamento 6",
        "url": "http://192.168.1.58",
        "usuario": "pablo6",
        "contrasena": "319923pablo6"
    },
    {
        "nombre": "Departamento 5",
        "url": "http://192.168.1.57",
        "usuario": "pablo5",
        "contrasena": "319923pablo5"
    },
    {
        "nombre": "Departamento 4",
        "url": "http://192.168.1.56",
        "usuario": "pablo4",
        "contrasena": "319923pablo4"
    },
    {
        "nombre": "Departamento 1",
        "url": "http://192.168.1.55",
        "usuario": "pablo1",
        "contrasena": "319923pablo"
    },
    # Agrega más si quieres
]

with sync_playwright() as p:
    for depto in departamentos:
        navegador = p.chromium.launch(headless=False)
        contexto = navegador.new_context(ignore_https_errors=True)
        pagina = contexto.new_page()

        try:
            try:
                pagina.goto(depto["url"])
            except Exception as e:
                mensaje = f"❌ No se pudo conectar a {depto['nombre']} ({depto['url']}): {e}"
                enviar_mensaje_a_slack_error(mensaje)
                navegador.close()
                continue  # Pasar al siguiente departamento

            # Llenar usuario y contraseña dinámicamente
            pagina.locator("input[type='text']").nth(0).fill(depto["usuario"])
            pagina.locator("input[type='password']").nth(0).fill(depto["contrasena"])

            # Intentar login
            try:
                pagina.locator("text=Acceder").nth(1).click()
            except Exception as e:
                mensaje = f"❌ No se pudo hacer clic en Acceder en {depto['nombre']}: {e}"
                enviar_mensaje_a_slack_error(mensaje)
                navegador.close()
                continue

            pagina.wait_for_timeout(3000)

        finally:
            navegador.close()

