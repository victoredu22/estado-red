from playwright.sync_api import sync_playwright, TimeoutError
import requests
import os
import sys
import time
import re
from dotenv import load_dotenv

# Forzar salida en UTF-8 para Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()
api_url = os.getenv("API_APARTMENTS_URL", "https://huellasaraucania.cl/api")

def obtener_apartamentos():
    """Obtiene la lista de todos los routers desde la API"""
    try:
        url = f"{api_url}/room-routers"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error al obtener routers desde la API: {e}")
        return []

def main():
    target_param = sys.argv[1] if len(sys.argv) >= 2 else None
    todos_routers = obtener_apartamentos()

    if not todos_routers:
        print("❌ No se pudieron obtener los routers de la API.")
        return

    # Filtrar según parámetro si se especificó un departamento
    target_routers = []
    if target_param and str(target_param).strip():
        target_str = str(target_param).strip().lower()
        target_routers = [
            r for r in todos_routers 
            if r.get("apartmentId") and (
                str(r.get("apartmentId", {}).get("id")) == target_str or
                target_str in r.get("apartmentId", {}).get("name", "").lower()
            )
        ]
        if not target_routers:
            print(f"❌ No se encontró el departamento relacionado con: '{target_param}'")
            return
    else:
        target_routers = [r for r in todos_routers if r.get("active") and r.get("apartmentId")]
        target_routers = sorted(target_routers, key=lambda x: x.get("apartmentId", {}).get("id", 0))

    print(f"🔍 Procesando {len(target_routers)} departamento(s)...")

    with sync_playwright() as p:
        for depto in target_routers:
            apt_info = depto.get("apartmentId") or {}
            apt_name = apt_info.get("name", "Desconocido")
            apt_id = apt_info.get("id", "N/A")
            url_router = depto.get("url", "N/A")
            user_router = depto.get("user", "N/A")
            pass_a_usar = depto.get("password") or depto.get("passwordLocal") or ""

            print("==================================================")
            print(f"📌 {apt_name} (ID: {apt_id})")
            print(f"   • URL Router: {url_router}")
            print(f"   • Usuario: {user_router}")
            link_url = url_router if url_router.startswith("http") else f"http://{url_router}"
            print(f"   • Password Mongo: <a href=\"{link_url}\">{pass_a_usar}</a>")
            print("--------------------------------------------------")

            navegador = p.chromium.launch(headless=False, args=["--start-maximized"])
            try:
                contexto = navegador.new_context(ignore_https_errors=True, no_viewport=True)
                pagina = contexto.new_page()

                print(f"   🌐 Conectando a {url_router}...")
                pagina.goto(url_router, timeout=30000)
                pagina.wait_for_timeout(2000)

                print(f"   🔑 Iniciando sesión...")
                pagina.locator("input[type='text']").nth(0).fill(user_router)
                pass_input = pagina.locator("input[type='password']").first
                pass_input.fill(pass_a_usar)
                pagina.wait_for_timeout(500)

                # Hacer clic en el botón Acceder
                btn = pagina.locator("a.button-button, button, input[type='submit'], input[type='button']").filter(has_text=re.compile(r"Acceder|Login|Iniciar", re.I)).first
                if btn.is_visible():
                    try:
                        btn.evaluate("node => node.click()")
                    except Exception:
                        try:
                            btn.click(force=True)
                        except Exception:
                            pass
                else:
                    try:
                        pass_input.press("Enter")
                    except Exception:
                        pass

                pagina.wait_for_timeout(4000)

                # Navegar a la sección INALÁMBRICO para extraer la contraseña del Wi-Fi
                wifi_pass_detectada = None
                print("   📡 Navegando a la sección INALÁMBRICO...")

                selectores_inalambrico = [
                    "span.sub-navigator-text:has-text('INALAMBRICO')",
                    "span.sub-navigator-text:has-text('INALÁMBRICO')",
                    "span.sub-navigator-text:has-text('WIRELESS')",
                    "a:has-text('INALAMBRICO')",
                    "a:has-text('INALÁMBRICO')"
                ]

                found_inalambrico = False
                for s in selectores_inalambrico:
                    link = pagina.locator(s)
                    if link.is_visible():
                        link.click()
                        pagina.wait_for_timeout(3000)
                        found_inalambrico = True
                        break

                if found_inalambrico:
                    try:
                        psk_container = pagina.locator("#wl-ap-wpa-pwd")
                        input_pass = psk_container.locator("input.password-visible").first
                        if not input_pass.is_visible():
                            input_pass = psk_container.locator("input:visible").first
                            if not input_pass.is_visible():
                                input_pass = psk_container.locator("input").first

                        if input_pass and input_pass.is_visible():
                            wifi_pass_detectada = (input_pass.input_value() or input_pass.get_attribute("value") or "").strip()
                            if not wifi_pass_detectada:
                                wifi_pass_detectada = psk_container.inner_text().strip().split('\n')[0]
                    except Exception as e_pass:
                        print(f"   Aviso al leer campo PSK: {e_pass}")

                if wifi_pass_detectada:
                    print(f"   ✅ CONTRASEÑA WI-FI LEÍDA DE LA PÁGINA: <a href=\"{link_url}\">{wifi_pass_detectada}</a>")
                else:
                    print(f"   ⚠️ No se pudo leer el campo PSK directamente de la página. (Mongo: <a href=\"{link_url}\">{pass_a_usar}</a>)")

                print("   [INFO] Manteniendo ventana abierta durante 20 segundos...")
                pagina.wait_for_timeout(20000)

            except Exception as e:
                print(f"   ❌ Error conectando a la página del router: {e}")
            finally:
                try:
                    navegador.close()
                except Exception:
                    pass

if __name__ == "__main__":
    main()
