from playwright.sync_api import sync_playwright, TimeoutError
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from dotenv import load_dotenv
import os
import json


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


# Abrir y leer el archivo
with open('departamentos.txt', 'r', encoding='utf-8') as f:
    departamentos = json.load(f)


with sync_playwright() as p:
    for depto in departamentos:

        navegador = p.chromium.launch(headless=False)
        contexto = navegador.new_context(ignore_https_errors=True)
        pagina = contexto.new_page()
        intentosDepto = depto['intentos'];

        try:
            try:
                pagina.goto(depto["url"])
            except Exception as e:
                
                    depto["intentos"] = intentosDepto + 1
                    with open('departamentos.txt', 'w', encoding='utf-8') as f:
                        json.dump(departamentos, f, indent=4, ensure_ascii=False)

                    if intentosDepto < 5:    
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

