from playwright.sync_api import sync_playwright, TimeoutError
import requests
import os
import time
from dotenv import load_dotenv

# =====================
# CONFIGURACIONES
# =====================
load_dotenv()  # carga variables desde .env
api_url = os.getenv("API_APARTMENTS_URL")

# =====================
# FUNCIONES API
# =====================
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
        print(f"Error al actualizar router: {e}")
        return None


# =====================
# MAIN
# =====================
def main():
    try:
        routers = obtener_apartamentos()

        p = sync_playwright().start()
        
        try:
            for depto in routers:
                if depto["active"]:
                    navegador = p.chromium.launch(headless=False)
                    contexto = navegador.new_context(ignore_https_errors=True)
                    pagina = contexto.new_page()

                    apt_info = depto.get("apartmentId") or {}
                    apt_name = apt_info.get("name", "Desconocido")

                    # Resetear intentos
                    actualizar_apartamento(depto["_id"], {
                        "attempts": 0,
                        "status": True,
                        "steps": "iniciando intento"
                    })

                    try:
                        try:
                            pagina.goto(depto["url"])
                        except Exception as e:
                            intentosDepto = depto["attempts"]
                            actualizar_apartamento(depto["_id"], {
                                "attempts": intentosDepto + 1,
                                "status": False,
                                "steps": "fallo la url del depto"
                            })
                            print(f"[OK] No se pudo conectar a {apt_name} ({depto['url']}): {e}")
                            continue

                        pagina.locator("input[type='text']").nth(0).fill(depto["user"])
                        pagina.locator("input[type='password']").nth(0).fill(depto["password"])

                        try:
                            pagina.locator("text=Acceder").nth(1).click()
                        except Exception as e:
                            print(f"[ERROR] No se pudo hacer clic en Acceder en {apt_name}: {e}")
                            intentosDepto = depto["attempts"]
                            actualizar_apartamento(depto["_id"], {
                                "attempts": intentosDepto + 1,
                                "status": False,
                                "steps": "fallo credenciales"
                            })
                            continue

                        try:
                            pagina.wait_for_selector("#lan-info-ip", timeout=5000)
                            if pagina.locator("#lan-info-ip").is_visible():
                                ip_texto = pagina.locator("#lan-info-ip pre").inner_text()
                                print(f"[OK] IP encontrada en {apt_name}: {ip_texto}")
                                intentosDepto = depto["attempts"]
                                actualizar_apartamento(depto["_id"], {
                                    "attempts": intentosDepto + 1,
                                    "status": False,
                                    "steps": "ningun error en el checkeo"
                                })
                            else:
                                print(f"[ERROR] Se ingresó, pero no se encontró la IP en {apt_name}.")
                        except TimeoutError:
                            if pagina.url.endswith("/login") or "login" in pagina.title().lower():
                                print(f"[WARN] Credenciales incorrectas para {apt_name}.")
                                intentosDepto = depto["attempts"]
                                actualizar_apartamento(depto["_id"], {
                                    "attempts": intentosDepto + 1,
                                    "status": False,
                                    "steps": "credenciales incorrectas login"
                                })
                            else:
                                print(f"[ERROR] No se encontró la IP. Timeout en {apt_name}.")

                                print(f"[ERROR] No se encontró la IP. Timeout en {depto['name']}.")
                    finally:
                        pass

            while True:
                time.sleep(60)
        finally:
            pass

    except Exception as e:
        print("❌ Error general:", e)


# =====================
# RUN
# =====================
if __name__ == "__main__":
    main()
