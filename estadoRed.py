from playwright.sync_api import sync_playwright, TimeoutError
import requests
import socketio
import os
from dotenv import load_dotenv

# =====================
# CONFIGURACIONES
# =====================
load_dotenv()  # carga variables desde .env
api_url = os.getenv("API_APARTMENTS_URL")
sio_url = os.getenv("SERVER_SOCKET")

# =====================
# CLIENTE SOCKET.IO
# =====================
sio = socketio.Client()

@sio.event
def connect():
    print(f"✅ Conectado al servidor: {sio_url}")

@sio.event
def connect_error(data):
    print("❌ Error de conexión:", data)

@sio.event
def disconnect():
    print("⚠️ Desconectado")


# =====================
# FUNCIONES API
# =====================
def obtener_apartamentos():
    try:
        url = f"{api_url}/apartment/all"
        response = requests.get(url)
        print("API URL:", url)
        print("Código de estado:", response.status_code)
        print("Texto crudo de la respuesta:", response.text)

        response.raise_for_status()
        data = response.json()
        print("JSON decodificado:", data)
        return data
    except requests.RequestException as e:
        print(f"Error al obtener apartamentos: {e}")
        return []


def actualizar_apartamento(apartamento_id, data):
    try:
        url = f"{api_url}/apartment/{apartamento_id}"
        print(f"Enviando PATCH a {url} con data: {data}")
        response = requests.patch(url, json=data)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error al actualizar apartamento: {e}")
        return None


# =====================
# MAIN
# =====================
def main():
    try:
        # Conexión inicial al socket
        sio.connect(sio_url, transports=["polling", "websocket"], socketio_path="/socket.io")

        apartamentos = obtener_apartamentos()

        with sync_playwright() as p:
            for depto in apartamentos:
                if depto["active"]:
                    navegador = p.chromium.launch(headless=False)
                    contexto = navegador.new_context(ignore_https_errors=True)
                    pagina = contexto.new_page()

                    # Resetear intentos
                    actualizar_apartamento(depto["_id"], {"attempts": 0, "status": "true"})
                    sio.emit("canalFrontend", f"Ejecutando script departamento número: {depto['id']}")

                    try:
                        try:
                            pagina.goto(depto["url"])
                        except Exception as e:
                            intentosDepto = depto["attempts"]
                            actualizar_apartamento(depto["_id"], {"attempts": intentosDepto + 1, "status": "false"})
                            print(f"❌ No se pudo conectar a {depto['name']} ({depto['url']}): {e}")
                            sio.emit("canalFrontend", f"Error {depto['id']}")
                            navegador.close()
                            continue

                        pagina.locator("input[type='text']").nth(0).fill(depto["user"])
                        pagina.locator("input[type='password']").nth(0).fill(depto["password"])

                        try:
                            pagina.locator("text=Acceder").nth(1).click()
                        except Exception as e:
                            print(f"⚠️ No se pudo hacer clic en Acceder en {depto['name']}: {e}")
                            sio.emit("canalFrontend", f"Error {depto['id']}")
                            navegador.close()
                            continue

                        try:
                            pagina.wait_for_selector("#lan-info-ip", timeout=5000)
                            if pagina.locator("#lan-info-ip").is_visible():
                                ip_texto = pagina.locator("#lan-info-ip pre").inner_text()
                                print(f"✅ IP encontrada en {depto['name']}: {ip_texto}")
                            else:
                                print(f"⚠️ Se ingresó, pero no se encontró la IP en {depto['name']}.")
                        except TimeoutError:
                            if pagina.url.endswith("/login") or "login" in pagina.title().lower():
                                print(f"⚠️ Credenciales incorrectas para {depto['name']}.")
                            else:
                                sio.emit("canalFrontend", f"Error {depto['id']}")
                                print(f"⚠️ No se encontró la IP. Timeout en {depto['name']}.")
                        pagina.wait_for_timeout(3000)

                    finally:
                        sio.emit("canalFrontend", f"Finalizado script departamento número: {depto['id']}")
                        navegador.close()

    except Exception as e:
        print("❌ No se pudo conectar:", e)
    finally:
        sio.disconnect()


# =====================
# RUN
# =====================
if __name__ == "__main__":
    main()
