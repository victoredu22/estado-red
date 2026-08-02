from playwright.sync_api import sync_playwright, TimeoutError
import requests
import os
import sys
import re
from dotenv import load_dotenv

# Forzar salida en UTF-8 para evitar errores en terminales Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

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
        print(f"   Actualizando API ({api_mongo_id}): {data}")
        response = requests.patch(url, json=data)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"   Error al actualizar API: {e}")
        return None

# =====================
# MAIN
# =====================
def main():
    print("Iniciando script de navegacion a seccion Inalambrico...")
    
    try:
        if len(sys.argv) < 3 or not re.fullmatch(r"\d{6}", sys.argv[2]):
            print("Error: debes indicar el departamento y una contraseña de exactamente 6 dígitos.")
            return

        nueva_password_solicitada = sys.argv[2]

        # 1. Obtener todos los routers
        todos_routers = obtener_apartamentos()
        if not todos_routers:
            print("Error: No se pudieron obtener los routers de la API.")
            return

        # 2. Determinar cuáles procesar
        target_routers = []
        if len(sys.argv) >= 2:
            param_buscado = sys.argv[1]
            try:
                # Intentar buscar por ID numérico exacto
                id_num = int(param_buscado)
                target_routers = [d for d in todos_routers if d.get("apartmentId", {}).get("id") == id_num]
            except ValueError:
                pass
            
            # Si no se encontró por ID o el parámetro no era un número, buscar por nombre
            if not target_routers:
                target_routers = [
                    d for d in todos_routers 
                    if param_buscado.lower() in d.get("apartmentId", {}).get("name", "").lower() or 
                       (str(d.get("apartmentId", {}).get("id")) == param_buscado)
                ]
            
            if not target_routers:
                print(f"Error: No se encontró el departamento relacionado con: '{param_buscado}'")
                return
            
            # Match más preciso
            if len(target_routers) > 1:
                match_exacto = [d for d in target_routers if d.get("apartmentId", {}).get("name", "").lower() == param_buscado.lower()]
                if match_exacto:
                    target_routers = match_exacto
                else:
                    match_espacio = [d for d in target_routers if f" {param_buscado}" in d.get("apartmentId", {}).get("name", "")]
                    if match_espacio:
                        target_routers = [match_espacio[0]]
                    else:
                        target_routers = [target_routers[0]]
            
            apt_info = target_routers[0].get("apartmentId") or {}
            print(f"Objetivo: {apt_info.get('name')} (ID: {apt_info.get('id')})")
        else:
            print("No se especificó un departamento. Listando opciones disponibles (IDs):")
            activos = [d for d in todos_routers if d.get("active")]
            for a in activos:
                a_apt = a.get("apartmentId") or {}
                print(f" - {a_apt.get('id')}: {a_apt.get('name')}")
            print("\nUso: py configurarInalambrico.py <numero_depto>")
            return

        # 3. Iniciar Playwright
        with sync_playwright() as p:
            for depto in target_routers:
                apt_info = depto.get("apartmentId") or {}
                apt_name = apt_info.get("name", "Desconocido")
                apt_id = apt_info.get("id", "N/A")
                
                print(f"Procesando: {apt_name} (ID: {apt_id})")
                
                # Extraer numero del departamento para la contraseña
                num_depto = "".join(filter(str.isdigit, apt_name))
                if not num_depto:
                    num_depto = str(apt_id)
                
                # Reseteamos status/steps al iniciar
                actualizar_apartamento(depto["_id"], {
                    "steps": f"Iniciando configuracion de {apt_name}",
                    "status": True
                })

                navegador = p.chromium.launch(headless=False)
                contexto = navegador.new_context(ignore_https_errors=True)
                pagina = contexto.new_page()

                try:
                    # Conexión
                    print(f"   Conectando a {depto['url']}...")
                    try:
                        pagina.goto(depto["url"], timeout=30000)
                    except Exception as e:
                        print(f"   Error de conexión: {e}")
                        actualizar_apartamento(depto["_id"], {"steps": "Error de conexión", "status": False})
                        continue

                    # Login
                    print("   Iniciando sesión...")
                    pagina.locator("input[type='text']").nth(0).fill(depto["user"])
                    pagina.locator("input[type='password']").nth(0).fill(depto["passwordLocal"])
                    
                    try:
                        # Intentar clic en Acceder
                        pagina.locator("text=Acceder").nth(1).click()
                        pagina.wait_for_timeout(3000)
                    except Exception as e:
                        print(f"   Error al hacer clic en Acceder: {e}")
                        actualizar_apartamento(depto["_id"], {"steps": "Error en botón login", "status": False})
                        continue

                    # Verificar si el login fue exitoso
                    if pagina.url.endswith("/login") or "login" in pagina.title().lower():
                        print("   Credenciales incorrectas.")
                        actualizar_apartamento(depto["_id"], {"steps": "Credenciales incorrectas", "status": False})
                        continue

                    print("   Login exitoso")

                    # Navegar a INALAMBRICO
                    try:
                        print("   Buscando sección INALAMBRICO...")
                        selectores = [
                            "span.sub-navigator-text:has-text('INALAMBRICO')",
                            "span.sub-navigator-text:has-text('INALÁMBRICO')",
                            "span.sub-navigator-text:has-text('WIRELESS')",
                            "a:has-text('INALAMBRICO')",
                            "a:has-text('INALÁMBRICO')"
                        ]
                        
                        found = False
                        for s in selectores:
                            link = pagina.locator(s)
                            if link.is_visible():
                                print(f"   Sección encontrada con selector: {s}")
                                link.click()
                                pagina.wait_for_timeout(3000)
                                found = True
                                break
                        
                        if found:
                            print("   Sección INALAMBRICO cargada correctamente")
                            
                            # 1. Rotación de Canal
                            try:
                                print("   Verificando si es necesario habilitar 'Cambio de Canal'...")
                                checkbox_canal = pagina.locator("label:has-text('Cambio de Canal')").locator("xpath=../..//input[@type='checkbox']").first
                                if checkbox_canal.is_visible() and not checkbox_canal.is_checked():
                                    print("   Marcando el checkbox 'Cambio de Canal'...")
                                    checkbox_canal.click()
                                    pagina.wait_for_timeout(1000)
                                
                                print("   Detectando canal actual...")
                                container = pagina.locator("#wl-basic-ap-channel")
                                input_text = container.locator("input.combobox-text")
                                valor_actual = (input_text.get_attribute("value") or input_text.input_value() or "").strip()
                                if not valor_actual:
                                    valor_actual = container.inner_text().strip()
                                
                                print(f"   Canal actual: '{valor_actual}'")
                                
                                # Rotación circular: 11 -> 1 -> 6 -> 11
                                nuevo_canal_prefix = "1 /"
                                if "11 /" in valor_actual: nuevo_canal_prefix = "1 /"
                                elif "1 /" in valor_actual: nuevo_canal_prefix = "6 /"
                                elif "6 /" in valor_actual: nuevo_canal_prefix = "11 /"
                                
                                print(f"   Objetivo: Seleccionar canal que empiece con '{nuevo_canal_prefix}'")
                                
                                container.locator(".combobox-switch").click()
                                pagina.wait_for_timeout(2000)
                                regex_selector = re.compile(f"^{re.escape(nuevo_canal_prefix)}")
                                opcion = pagina.locator("li").filter(has_text=regex_selector).last
                                
                                if opcion.is_visible():
                                    texto_opcion = opcion.inner_text().strip()
                                    print(f"   Haciendo clic preciso en: '{texto_opcion}'")
                                    opcion.click(force=True)
                                    pagina.wait_for_timeout(2000)
                                    
                                    valor_final = (input_text.get_attribute("value") or input_text.input_value() or "").strip()
                                    if nuevo_canal_prefix in valor_final:
                                        print(f"   Exito: Canal cambiado a {valor_final}")
                                    else:
                                        print(f"   No cambio. Intentando Metodo JS evaluate click...")
                                        opcion.evaluate("node => node.click()")
                                        pagina.wait_for_timeout(2000)
                                else:
                                    print(f"   Error: No se encontro ninguna opcion que empiece con '{nuevo_canal_prefix}'")
                            except Exception as e:
                                print(f"   Error critico al rotar canal: {e}")

                            # 2. Cambio de Contraseña (PSK)
                            try:
                                print("   Buscando campo de contraseña (PSK)...")
                                psk_container = pagina.locator("#wl-ap-wpa-pwd")
                                input_pass = psk_container.locator("input.password-visible").first
                                if not input_pass.is_visible():
                                    input_pass = psk_container.locator("input:visible").first
                                    if not input_pass.is_visible():
                                        input_pass = psk_container.locator("input").first
                                
                                if input_pass and input_pass.is_visible():
                                    pass_actual = (input_pass.input_value() or input_pass.get_attribute("value") or "").strip()
                                    if not pass_actual:
                                        pass_actual = psk_container.inner_text().strip().split('\n')[0]
                                    
                                    print(f"   Contraseña actual detectada: '{pass_actual}'")
                                    
                                    nueva_pass = nueva_password_solicitada
                                    
                                    print(f"   Cambiando contraseña a: '{nueva_pass}'")
                                    inputs = psk_container.locator("input").all()
                                    for inp in inputs:
                                        try:
                                            inp.fill("")
                                            inp.type(nueva_pass, delay=100)
                                            inp.dispatch_event("input")
                                            inp.dispatch_event("change")
                                            inp.dispatch_event("blur")
                                        except:
                                            pass
                                        
                                    print(f"   Escritura robusta finalizada: '{nueva_pass}'")
                                else:
                                    print("   No se encontro el campo de contraseña PSK.")
                            except Exception as e:
                                print(f"   Error al cambiar contraseña: {e}")

                            # 3. Guardar cambios
                            try:
                                print("   Buscando boton Aplicar...")
                                boton_aplicar = pagina.locator("div.button-wrap a.button-button:has-text('Aplicar')")
                                if not boton_aplicar.is_visible():
                                    boton_aplicar = pagina.locator("#wireless-submit-button")
                                    if not boton_aplicar.is_visible():
                                        boton_aplicar = pagina.locator("text=Aplicar").first
                                    
                                if boton_aplicar.is_visible():
                                    boton_aplicar.scroll_into_view_if_needed()
                                    boton_aplicar.click()
                                    pagina.wait_for_timeout(5000)
                                    print("   Cambios aplicados correctamente.")
                                else:
                                    print("   Boton Aplicar no encontrado.")
                            except Exception as e:
                                print(f"   Error al guardar/aplicar: {e}")

                            actualizar_apartamento(depto["_id"], {
                                "steps": "Rotacion de canal y cambio de clave finalizados",
                                "status": True,
                                "passwordLocal": nueva_pass
                            })
                            pagina.wait_for_timeout(2000)
                        else:
                            print("   No se pudo encontrar el link a INALAMBRICO")
                            actualizar_apartamento(depto["_id"], {"steps": "No se encontró sección Inalambrico", "status": False})

                    except Exception as e:
                        print(f" Error al navegar: {e}")
                        actualizar_apartamento(depto["_id"], {"steps": "Error navegando a Inalambrico", "status": False})

                finally:
                    navegador.close()

    except Exception as e:
        print(f"Error general en el proceso: {e}")

if __name__ == "__main__":
    main()
