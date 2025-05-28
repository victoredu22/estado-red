from playwright.sync_api import sync_playwright, TimeoutError
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from connection import get_apartment, update_apartment

from dotenv import load_dotenv
import os


def enviar_mensaje_a_slack(mensaje):
    try:
        response = client.chat_postMessage(
            channel="#estado-red",
            text=f"Estado de red:\n{mensaje}"
        )
        print("Mensaje enviado:", response["ts"])
    except SlackApiError as e:
        print("Error al enviar mensaje:", e.response["error"])


def main():
    load_dotenv()  # Cargar variables del .env

    slack_token = os.getenv("SLACK_TOKEN")
    global client
    client = WebClient(token=slack_token)

    apartamentos = get_apartment()

    with sync_playwright() as p:
        for depto in apartamentos:
            navegador = p.chromium.launch(headless=False)
            contexto = navegador.new_context(ignore_https_errors=True)
            pagina = contexto.new_page()

            # Actualiza intentos a 0 (por ejemplo)
            resultado = update_apartment(depto["id"], {"attemps": 0})
            

            try:
                try:
                    pagina.goto(depto["url"])
                except Exception as e:
                    mensaje = f"❌ No se pudo conectar a {depto['name']} ({depto['url']}): {e}"
                    enviar_mensaje_a_slack(mensaje)
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
                navegador.close()


if __name__ == "__main__":
    main()
