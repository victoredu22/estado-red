from playwright.sync_api import sync_playwright, TimeoutError
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from dotenv import load_dotenv
import os
import json

load_dotenv()  # Carga las variables del archivo .env

slack_token = os.getenv('SLACK_TOKEN')
client = WebClient(token=slack_token)

def enviar_mensaje_a_slack(mensaje):
    try:
        response = client.chat_postMessage(
            channel="#estado-red",
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

        depto["intentos"] = 0
        with open('departamentos.txt', 'w', encoding='utf-8') as f:
            json.dump(departamentos, f, indent=4, ensure_ascii=False)

        try:
            try:
                pagina.goto(depto["url"])

            except Exception as e:
                mensaje = f"❌ No se pudo conectar a {depto['nombre']} ({depto['url']}): {e}"
                enviar_mensaje_a_slack(mensaje)
                navegador.close()
                continue  # Pasar al siguiente departamento

            # Llenar usuario y contraseña dinámicamente
            pagina.locator("input[type='text']").nth(0).fill(depto["usuario"])
            pagina.locator("input[type='password']").nth(0).fill(depto["contrasena"])

            # Intentar login
            try:
                pagina.locator("text=Acceder").nth(1).click()
            except Exception as e:
                mensaje = f"No se pudo hacer clic en Acceder en {depto['nombre']}: {e}"
                enviar_mensaje_a_slack(mensaje)
                navegador.close()
                continue  # ✅ Ahora sí dentro del for

            # Esperar IP
            try:
                pagina.wait_for_selector("#lan-info-ip", timeout=5000)
                if pagina.locator("#lan-info-ip").is_visible():
                    ip_texto = pagina.locator("#lan-info-ip pre").inner_text()
                    mensaje = f"IP encontrada en {depto['nombre']}: `{ip_texto}`"
                else:
                    mensaje = f"Se ingresó, pero no se encontró la IP en {depto['nombre']}."
            except TimeoutError:
                if pagina.url.endswith("/login") or "login" in pagina.title().lower():
                    mensaje = f"Credenciales incorrectas para {depto['nombre']}."
                else:
                    mensaje = f"No se encontró la IP. Timeout en {depto['nombre']}."

            enviar_mensaje_a_slack(mensaje)
            pagina.wait_for_timeout(3000)
        finally:
            navegador.close()


