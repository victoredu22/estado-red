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
    """Obtiene la lista de todos los apartamentos desde el API"""
    try:
        url = f"{api_url}/apartment/all"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error al obtener apartamentos: {e}")
        return []

def actualizar_apartamento(api_mongo_id, data):
    """Actualiza un apartamento en el API usando su ID de MongoDB (_id)"""
    try:
        url = f"{api_url}/apartment/{api_mongo_id}"
        print(f"   Actualizando API ({api_mongo_id}): {data}")
        response = requests.patch(url, json=data)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"   Error al actualizar API: {e}")
        return None

def actualizar_password_local(api_mongo_id, password_local):
    """Actualiza la passwordLocal de un apartamento en el API"""
    try:
        url = f"{api_url}/apartment/{api_mongo_id}/password-local"
        print(f"   Actualizando passwordLocal API ({api_mongo_id}): {password_local}")
        response = requests.post(url, json={"passwordLocal": password_local})
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"   Error al actualizar passwordLocal API: {e}")
        return None

# =====================
# MAIN
# =====================
def main():
    print("Iniciando script de navegacion a seccion Inalambrico...")
    
    try:
        # 1. Obtener todos los apartamentos
        todos_apartamentos = obtener_apartamentos()
        if not todos_apartamentos:
            print("Error: No se pudieron obtener los apartamentos de la API.")
            return

        # 2. Determinar cuáles procesar
        target_apartamentos = []
        if len(sys.argv) >= 2:
            param_buscado = sys.argv[1]
            try:
                # Intentar buscar por ID numérico exacto
                id_num = int(param_buscado)
                target_apartamentos = [d for d in todos_apartamentos if d.get("id") == id_num]
            except ValueError:
                pass
            
            # Si no se encontró por ID o el parámetro no era un número, buscar por nombre
            if not target_apartamentos:
                # Buscamos departamentos cuyo nombre contenga el número o sea el número exacto
                target_apartamentos = [
                    d for d in todos_apartamentos 
                    if param_buscado.lower() in d.get("name", "").lower() or 
                       (str(d.get("id")) == param_buscado)
                ]
            
            if not target_apartamentos:
                print(f"Error: No se encontró el departamento relacionado con: '{param_buscado}'")
                return
            
            # Match más preciso
            if len(target_apartamentos) > 1:
                match_exacto = [d for d in target_apartamentos if d.get("name", "").lower() == param_buscado.lower()]
                if match_exacto:
                    target_apartamentos = match_exacto
                else:
                    match_espacio = [d for d in target_apartamentos if f" {param_buscado}" in d.get("name", "")]
                    if match_espacio:
                        target_apartamentos = [match_espacio[0]]
                    else:
                        target_apartamentos = [target_apartamentos[0]]
            
            print(f"Objetivo: {target_apartamentos[0]['name']} (ID: {target_apartamentos[0]['id']})")
        else:
            print("No se especificó un departamento.")
            return

        # 3. Iniciar Playwright
        with sync_playwright() as p:
            for depto in target_apartamentos:
                print(f"Procesando: {depto['name']} (ID: {depto['id']})")
                num_depto = "".join(filter(str.isdigit, depto["name"]))
                if not num_depto:
                    num_depto = str(depto["id"])
                
                actualizar_apartamento(depto["_id"], {
                    "steps": f"Iniciando configuracion de {depto['name']}",
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
                            
                            # Guardar en base de datos mongo
                            actualizar_password_local(depto["_id"], nueva_pass)
                        
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
