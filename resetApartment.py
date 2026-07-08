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
    """Obtiene la lista de todos los routers desde el API"""
    try:
        url = f"{api_url}/room-routers"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error al obtener routers: {e}")
        return []

def actualizar_apartamento(api_mongo_id, data):
    """Actualiza un router en el API usando su ID de MongoDB (_id)"""
    try:
        url = f"{api_url}/room-routers/{api_mongo_id}"
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
    # Verificar que se recibió el parámetro
    if len(sys.argv) < 2:
        print("❌ Error: Debes proporcionar el número de departamento")
        print("Uso: python resetApartment.py <numero_departamento>")
        return

    id_depto = int(sys.argv[1])
    print(f"🔍 Buscando router del departamento con id: {id_depto}...")

    try:
        routers = obtener_apartamentos()

        # Buscar el router específico por el id de su apartamento
        depto_encontrado = None
        for depto in routers:
            if depto.get("apartmentId", {}).get("id") == id_depto:
                depto_encontrado = depto
                break

        if not depto_encontrado:
            print(f"❌ No se encontró el router para el departamento con id: {id_depto}")
            return

        apt_info = depto_encontrado.get("apartmentId") or {}
        apt_name = apt_info.get("name", "Desconocido")

        if not depto_encontrado.get("active"):
            print(f"⚠️ El router del departamento {apt_name} (id: {id_depto}) no está activo")
            return

        print(f"✅ Router encontrado para el departamento: {apt_name}")

        with sync_playwright() as p:
            navegador = p.chromium.launch(headless=False)
            contexto = navegador.new_context(ignore_https_errors=True)
            pagina = contexto.new_page()

            try:
                try:
                    pagina.goto(depto_encontrado["url"])
                except Exception as e:
                    print(f"❌ No se pudo conectar a {apt_name} ({depto_encontrado['url']}): {e}")
                    navegador.close()
                    return

                pagina.locator("input[type='text']").nth(0).fill(depto_encontrado["user"])
                pagina.locator("input[type='password']").nth(0).fill(depto_encontrado["password"])

                try:
                    pagina.locator("text=Acceder").nth(1).click()
                except Exception as e:
                    print(f"❌ No se pudo hacer clic en Acceder en {apt_name}: {e}")
                    navegador.close()
                    return

                # Esperar a que cargue la página después del login
                pagina.wait_for_timeout(2000)

                # Verificar si el login fue exitoso
                if pagina.url.endswith("/login") or "login" in pagina.title().lower():
                    print(f"⚠️ Credenciales incorrectas para {apt_name}.")
                    navegador.close()
                    return

                print(f"✅ Login exitoso en {apt_name}")

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
                    botones = pagina.locator("a.button-button").all()
                    print(f"   Total de botones encontrados: {len(botones)}")

                    botones_reiniciar = []
                    for i, boton in enumerate(botones):
                        texto = boton.inner_text()
                        print(f"   Botón {i}: '{texto}'")
                        if "Reiniciar" in texto:
                            botones_reiniciar.append((i, boton))

                    print(f"   Botones con 'Reiniciar': {len(botones_reiniciar)}")

                    # Hacer clic en el segundo botón "Reiniciar" (Reinicializar Dispositivo)
                    if len(botones_reiniciar) >= 2:
                        print(f"\n🔄 Haciendo clic en botón Reinicializar Dispositivo (índice {botones_reiniciar[1][0]})...")
                        botones_reiniciar[1][1].click()
                        pagina.wait_for_timeout(2000)
                        print("✅ Clic en Reinicializar Dispositivo exitoso")

                        # Buscar el modal de confirmación
                        try:
                            print("\n🔍 Buscando modal de confirmación...")
                            tiene_configuracion = False
                            tiene_reinicializar = False

                            try:
                                configuracion = pagina.locator("text=Configuración").first
                                if configuracion.is_visible():
                                    tiene_configuracion = True
                                    print("✅ Se encontró 'Configuración' en el modal")
                            except:
                                print("❌ NO se encontró 'Configuración' en el modal")

                            try:
                                reinicializar = pagina.locator("text=/reinicializar/i").first
                                if reinicializar.is_visible():
                                    tiene_reinicializar = True
                                    texto_completo = reinicializar.inner_text()
                                    print(f"✅ Se encontró 'reinicializar': '{texto_completo}'")
                            except:
                                print("❌ NO se encontró 'reinicializar' en el modal")

                            # Resumen
                            print(f"\n📊 Resumen del modal:")
                            print(f"   - Contiene 'Configuración': {tiene_configuracion}")
                            print(f"   - Contiene 'reinicializar': {tiene_reinicializar}")

                            if tiene_reinicializar:
                                print("✅ ¡Modal correcto! Contiene 'reinicializar'")
                                print("🔄 Haciendo clic en 'Sí' para confirmar...")

                                try:
                                    # Usar el ID específico del botón "Sí"
                                    print("   Buscando botón 'Sí' por ID...")
                                    boton_si = pagina.locator("#configuration-reboot-confirm-btn-ok a.button-button")

                                    if boton_si.is_visible():
                                        print("   ✅ Encontrado botón 'Sí' por ID")
                                        boton_si.click()
                                        pagina.wait_for_timeout(2000)
                                        print("✅ Confirmación exitosa - Dispositivo reiniciándose")

                                        # Esperar 2 minutos mientras el dispositivo se reinicia
                                        try:
                                            print("\n⏳ Esperando 2 minutos para el reinicio del dispositivo...")
                                            pagina.wait_for_timeout(120000)
                                            print("\n✅ Tiempo de espera completado (2 minutos)")
                                            print("🎉 Proceso de reinicio completado exitosamente")
                                            return
                                        except Exception as e:
                                            print(f"   ⚠️ Error durante la espera: {e}")
                                            print("\n🎉 Proceso completado")
                                            return
                                    else:
                                        print("❌ El botón 'Sí' no está visible")
                                except Exception as e:
                                    print(f"❌ Error al hacer clic en 'Sí': {e}")
                            else:
                                print("⚠️ Modal NO contiene 'reinicializar' - NO se hará clic en 'Sí'")
                                print("⏸️ Esperando 30 segundos para que veas el modal...")
                                pagina.wait_for_timeout(30000)

                        except Exception as e:
                            print(f"❌ Error al buscar modal: {e}")
                    else:
                        print("❌ No se encontraron suficientes botones 'Reiniciar'")

                except Exception as e:
                    print(f"❌ Error al identificar botones: {e}")
                    navegador.close()
                    return

                pagina.wait_for_timeout(60000)

            finally:
                navegador.close()

    except Exception as e:
        print(f"❌ Error general: {e}")

if __name__ == "__main__":
    main()
