from playwright.sync_api import sync_playwright, TimeoutError
import requests
import os
import sys
from dotenv import load_dotenv

# =====================
# CONFIGURACIONES
# =====================
load_dotenv()
api_url = os.getenv("API_APARTMENTS_URL")

# =====================
# FUNCIONES API
# =====================
def obtener_apartamentos():
    try:
        url = f"{api_url}/apartment/all"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
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
    # Verificar que se recibió el parámetro
    if len(sys.argv) < 2:
        print("❌ Error: Debes proporcionar el número de departamento")
        print("Uso: python resetApartment.py <numero_departamento>")
        return

    numero_depto = sys.argv[1]
    print(f"🔍 Buscando departamento #{numero_depto}...")

    try:
        apartamentos = obtener_apartamentos()

        # Buscar el departamento específico por su número
        depto_encontrado = None
        for depto in apartamentos:
            if str(depto.get("number")) == str(numero_depto):
                depto_encontrado = depto
                break

        if not depto_encontrado:
            print(f"❌ No se encontró el departamento #{numero_depto}")
            return

        if not depto_encontrado.get("active"):
            print(f"⚠️ El departamento #{numero_depto} ({depto_encontrado['name']}) no está activo")
            return

        print(f"✅ Departamento encontrado: {depto_encontrado['name']}")

        with sync_playwright() as p:
            navegador = p.chromium.launch(headless=False)
            contexto = navegador.new_context(ignore_https_errors=True)
            pagina = contexto.new_page()

            # Resetear intentos
            actualizar_apartamento(depto_encontrado["_id"], {
                "attempts": 0,
                "status": True,
                "steps": "iniciando reset manual"
            })

            try:
                try:
                    pagina.goto(depto_encontrado["url"])
                except Exception as e:
                    intentosDepto = depto_encontrado["attempts"]
                    actualizar_apartamento(depto_encontrado["_id"], {
                        "attempts": intentosDepto + 1,
                        "status": False,
                        "steps": "fallo la url del depto"
                    })
                    print(f"❌ No se pudo conectar a {depto_encontrado['name']} ({depto_encontrado['url']}): {e}")
                    navegador.close()
                    return

                pagina.locator("input[type='text']").nth(0).fill(depto_encontrado["user"])
                pagina.locator("input[type='password']").nth(0).fill(depto_encontrado["password"])

                try:
                    pagina.locator("text=Acceder").nth(1).click()
                except Exception as e:
                    print(f"❌ No se pudo hacer clic en Acceder en {depto_encontrado['name']}: {e}")
                    intentosDepto = depto_encontrado["attempts"]
                    actualizar_apartamento(depto_encontrado["_id"], {
                        "attempts": intentosDepto + 1,
                        "status": False,
                        "steps": "fallo credenciales"
                    })
                    navegador.close()
                    return

                try:
                    pagina.wait_for_selector("#lan-info-ip", timeout=5000)
                    if pagina.locator("#lan-info-ip").is_visible():
                        ip_texto = pagina.locator("#lan-info-ip pre").inner_text()
                        print(f"✅ IP encontrada en {depto_encontrado['name']}: {ip_texto}")
                        intentosDepto = depto_encontrado["attempts"]
                        actualizar_apartamento(depto_encontrado["_id"], {
                            "attempts": intentosDepto + 1,
                            "status": False,
                            "steps": "ningun error en el checkeo"
                        })
                    else:
                        print(f"❌ Se ingresó, pero no se encontró la IP en {depto_encontrado['name']}.")
                except TimeoutError:
                    if pagina.url.endswith("/login") or "login" in pagina.title().lower():
                        print(f"⚠️ Credenciales incorrectas para {depto_encontrado['name']}.")
                        intentosDepto = depto_encontrado["attempts"]
                        actualizar_apartamento(depto_encontrado["_id"], {
                            "attempts": intentosDepto + 1,
                            "status": False,
                            "steps": "credenciales incorrectas login"
                        })
                    else:
                        print(f"❌ No se encontró la IP. Timeout en {depto_encontrado['name']}.")
                pagina.wait_for_timeout(3000)

            finally:
                navegador.close()

    except Exception as e:
        print(f"❌ Error general: {e}")


# =====================
# RUN
# =====================
if __name__ == "__main__":
    main()
