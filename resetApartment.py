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

    id_depto = int(sys.argv[1])
    print(f"🔍 Buscando departamento con id: {id_depto}...")

    try:
        apartamentos = obtener_apartamentos()

        # Buscar el departamento específico por su id
        depto_encontrado = None
        for depto in apartamentos:
            if depto.get("id") == id_depto:
                depto_encontrado = depto
                break

        if not depto_encontrado:
            print(f"❌ No se encontró el departamento con id: {id_depto}")
            return

        if not depto_encontrado.get("active"):
            print(f"⚠️ El departamento {depto_encontrado['name']} (id: {id_depto}) no está activo")
            return

        print(f"✅ Departamento encontrado: {depto_encontrado['name']}")

        with sync_playwright() as p:
            navegador = p.chromium.launch(headless=False)
            contexto = navegador.new_context(ignore_https_errors=True)
            pagina = contexto.new_page()

            try:
                try:
                    pagina.goto(depto_encontrado["url"])
                except Exception as e:
                    print(f"❌ No se pudo conectar a {depto_encontrado['name']} ({depto_encontrado['url']}): {e}")
                    navegador.close()
                    return

                pagina.locator("input[type='text']").nth(0).fill(depto_encontrado["user"])
                pagina.locator("input[type='password']").nth(0).fill(depto_encontrado["password"])

                try:
                    pagina.locator("text=Acceder").nth(1).click()
                except Exception as e:
                    print(f"❌ No se pudo hacer clic en Acceder en {depto_encontrado['name']}: {e}")
                    navegador.close()
                    return

                # Esperar a que cargue la página después del login
                pagina.wait_for_timeout(2000)

                # Verificar si el login fue exitoso
                if pagina.url.endswith("/login") or "login" in pagina.title().lower():
                    print(f"⚠️ Credenciales incorrectas para {depto_encontrado['name']}.")
                    navegador.close()
                    return

                print(f"✅ Login exitoso en {depto_encontrado['name']}")

                # Navegar a la sección SISTEMA
                try:
                    print("🔧 Navegando a SISTEMA...")
                    pagina.locator("span.sub-navigator-text:has-text('SISTEMA')").click()
                    pagina.wait_for_timeout(3000)
                    print("✅ Navegación a SISTEMA completada")
                except Exception as e:
                    print(f"❌ Error al navegar a SISTEMA: {e}")
                    navegador.close()
                    return

                # Hacer scroll hacia abajo para encontrar el botón
                try:
                    print("📜 Haciendo scroll hacia el botón Reinicializar...")
                    pagina.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    pagina.wait_for_timeout(1000)
                except Exception as e:
                    print(f"⚠️ No se pudo hacer scroll: {e}")

                # Identificar y marcar los botones Reiniciar
                try:
                    print("🔄 Buscando botones tipo enlace con clase 'button-button'...")
                    # Los botones son enlaces <a> con clase button-button
                    botones = pagina.locator("a.button-button").all()
                    print(f"   Total de botones encontrados: {len(botones)}")

                    # Buscar específicamente botones que contengan "Reiniciar"
                    botones_reiniciar = []
                    for i, boton in enumerate(botones):
                        texto = boton.inner_text()
                        print(f"   Botón {i}: '{texto}'")
                        if "Reiniciar" in texto:
                            botones_reiniciar.append((i, boton))

                    print(f"   Botones con 'Reiniciar': {len(botones_reiniciar)}")

                    # Cambiar el texto de los botones para identificarlos
                    if len(botones_reiniciar) >= 1:
                        print("📝 Cambiando texto de botones para identificación...")
                        botones_reiniciar[0][1].evaluate("el => el.textContent = 'Reinicio Fabrica'")
                        print("   ✅ Primer botón cambiado a 'Reinicio Fabrica'")

                    if len(botones_reiniciar) >= 2:
                        botones_reiniciar[1][1].evaluate("el => el.textContent = 'Reinicio Dispositivo'")
                        print("   ✅ Segundo botón cambiado a 'Reinicio Dispositivo'")

                    print("\n⏸️  Revisa visualmente los botones en el navegador")
                    print("   BOTON 1 = Restablecer a los Ajustes Predeterminados de Fábrica")
                    print("   BOTON 2 = Reinicializar Dispositivo")

                    # Esperar para que puedas verlos
                    pagina.wait_for_timeout(30000)

                except Exception as e:
                    print(f"❌ Error al identificar botones: {e}")
                    navegador.close()
                    return

                pagina.wait_for_timeout(15000)

            finally:
                navegador.close()

    except Exception as e:
        print(f"❌ Error general: {e}")


# =====================
# RUN
# =====================
if __name__ == "__main__":
    main()
