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
            print("No se especificó un departamento.")
            return

        # 3. Iniciar Playwright
        with sync_playwright() as p:
            for depto in target_routers:
                apt_info = depto.get("apartmentId") or {}
                apt_name = apt_info.get("name", "Desconocido")
                apt_id = apt_info.get("id", "N/A")
                
                print(f"Procesando: {apt_name} (ID: {apt_id})")
                num_depto = "".join(filter(str.isdigit, apt_name))
                if not num_depto:
                    num_depto = str(apt_id)
                
                actualizar_apartamento(depto["_id"], {
                    "steps": f"Iniciando configuracion de {apt_name}",
                    "status": True
                })

                navegador = p.chromium.launch(headless=False)
                try:
                    contexto = navegador.new_context(ignore_https_errors=True)
                    pagina = contexto.new_page()

                    pagina.goto(depto["url"], timeout=30000)
                    pagina.locator("input[type='text']").nth(0).fill(depto["user"])
                    pagina.locator("input[type='password']").nth(0).fill(depto["password"])
                    pagina.locator("text=Acceder").nth(1).click()
                    pagina.wait_for_timeout(3000)

                    # Navegar a INALAMBRICO
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
                            link.click()
                            pagina.wait_for_timeout(3000)
                            found = True
                            break
                    
                    if found:
                        # 1. Rotación de Canal
                        checkbox_canal = pagina.locator("label:has-text('Cambio de Canal')").locator("xpath=../..//input[@type='checkbox']").first
                        if checkbox_canal.is_visible() and not checkbox_canal.is_checked():
                            checkbox_canal.click()
                            pagina.wait_for_timeout(1000)
                        
                        container = pagina.locator("#wl-basic-ap-channel")
                        input_text = container.locator("input.combobox-text")
                        valor_actual = (input_text.get_attribute("value") or input_text.input_value() or "").strip()
                        
                        nuevo_canal_prefix = "1 /"
                        if "11 /" in valor_actual: nuevo_canal_prefix = "1 /"
                        elif "1 /" in valor_actual: nuevo_canal_prefix = "6 /"
                        elif "6 /" in valor_actual: nuevo_canal_prefix = "11 /"
                        
                        container.locator(".combobox-switch").click()
                        pagina.wait_for_timeout(2000)
                        regex_selector = re.compile(f"^{re.escape(nuevo_canal_prefix)}")
                        opcion = pagina.locator("li").filter(has_text=regex_selector).last
                        
                        if opcion.is_visible():
                            opcion.click(force=True)
                            pagina.wait_for_timeout(2000)

                        # 2. Cambio de Contraseña (PSK)
                        psk_container = pagina.locator("#wl-ap-wpa-pwd")
                        input_pass = psk_container.locator("input.password-visible").first
                        if not input_pass.is_visible():
                            input_pass = psk_container.locator("input:visible").first
                        
                        if input_pass.is_visible():
                            pass_actual = (input_pass.input_value() or "").strip()
                            num_str = str(num_depto)
                            base_pablo = f"319923pablo{num_str}"
                            swap_pablo = f"pablo{num_str}319923"
                            nueva_pass = swap_pablo if base_pablo in pass_actual else base_pablo
                            
                            input_pass.fill("")
                            input_pass.type(nueva_pass, delay=100)
                            
                            # Guardar en base de datos mongo haciendo PATCH al room-router
                            actualizar_apartamento(depto["_id"], {"passwordLocal": nueva_pass})
                        
                        # 3. Guardar cambios
                        boton_aplicar = pagina.locator("div.button-wrap a.button-button:has-text('Aplicar')")
                        if boton_aplicar.is_visible():
                            boton_aplicar.click()
                            pagina.wait_for_timeout(5000)

                        actualizar_apartamento(depto["_id"], {
                            "steps": "Configuracion finalizada",
                            "status": True
                        })
                finally:
                    navegador.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
