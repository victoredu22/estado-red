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
                # Ej: "Depto 1" contiene "1"
                # O si el usuario puso "Depto 1" completo
                target_apartamentos = [
                    d for d in todos_apartamentos 
                    if param_buscado.lower() in d.get("name", "").lower() or 
                       (str(d.get("id")) == param_buscado)
                ]
            
            if not target_apartamentos:
                print(f"Error: No se encontró el departamento relacionado con: '{param_buscado}'")
                return
            
            # Si hay más de uno (ej: "1" en "Depto 1" y "Depto 11"), intentamos el match más corto o exacto
            if len(target_apartamentos) > 1:
                # Filtramos por el nombre exacto si existe
                match_exacto = [d for d in target_apartamentos if d.get("name", "").lower() == param_buscado.lower()]
                if match_exacto:
                    target_apartamentos = match_exacto
                else:
                    # O el que contenga el número con un espacio, ej: "Depto 1"
                    match_espacio = [d for d in target_apartamentos if f" {param_buscado}" in d.get("name", "")]
                    if match_espacio:
                        target_apartamentos = [match_espacio[0]]
                    else:
                        target_apartamentos = [target_apartamentos[0]] # Tomamos el primero
            
            print(f"Objetivo: {target_apartamentos[0]['name']} (ID: {target_apartamentos[0]['id']})")
        else:
            # Procesar todos los activos si no se especifica uno (opcional, el usuario dijo que ahora seria especifico)
            print("No se especificó un departamento. Listando opciones disponibles (IDs):")
            activos = [d for d in todos_apartamentos if d.get("active")]
            for a in activos:
                print(f" - {a['id']}: {a['name']}")
            print("\nUso: py configurarInalambrico.py <numero_depto>")
            return

        # 3. Iniciar Playwright
        with sync_playwright() as p:
            for depto in target_apartamentos:
                print(f"Procesando: {depto['name']} (ID: {depto['id']})")
                
                # Reseteamos status/steps al iniciar
                actualizar_apartamento(depto["_id"], {
                    "steps": "Iniciando navegacion a Inalambrico",
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
                    pagina.locator("input[type='password']").nth(0).fill(depto["password"])
                    
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
                        
                        # Probamos varios selectores comunes
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
                                # Algunos equipos Pharos requieren marcar este checkbox para editar el canal
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
                                
                                # Rotación circular: 1 -> 6 -> 11 -> 1
                                nuevo_canal = "1 /" # Valor por defecto seguro
                                if "11 /" in valor_actual:
                                    nuevo_canal = "1 /"
                                elif "1 /" in valor_actual:
                                    nuevo_canal = "6 /"
                                elif "6 /" in valor_actual:
                                    nuevo_canal = "11 /"
                                else:
                                    nuevo_canal = "1 /" # Fallback a 1 si el canal actual es Auto u otro
                                
                                print(f"   Objetivo: Seleccionar '{nuevo_canal}'")
                                
                                # Abrir el menu: Clic en el switch (.combobox-switch)
                                switch = container.locator(".combobox-switch")
                                switch.click()
                                pagina.wait_for_timeout(2000)
                                
                                # Intentamos varios selectores para la opcion
                                selector_li = f"li:has-text('{nuevo_canal}')"
                                if not pagina.locator(selector_li).last.is_visible():
                                    selector_li = f"li.combobox-list-item:has-text('{nuevo_canal}')"
                                
                                opcion = pagina.locator(selector_li).last
                                if opcion.is_visible():
                                    print(f"   Haciendo clic en la opcion: '{opcion.inner_text().strip()}'")
                                    # Intentamos Metodo 1: Clic estandar
                                    opcion.click(force=True)
                                    pagina.wait_for_timeout(2000)
                                    
                                    # Verificacion
                                    valor_ahora = (input_text.get_attribute("value") or input_text.input_value() or "").strip()
                                    if nuevo_canal not in valor_ahora:
                                        print("   No cambio el valor con click estandar. Intentando Metodo 2: Evaluate JS Click...")
                                        opcion.evaluate("node => node.click()")
                                        pagina.wait_for_timeout(2000)
                                    
                                    # Verificacion Final
                                    valor_final = (input_text.get_attribute("value") or input_text.input_value() or "").strip()
                                    if nuevo_canal in valor_final:
                                        print(f"   Exito: Canal cambiado a {valor_final}")
                                    else:
                                        print(f"   Fallo final: No se pudo cambiar el canal. Valor actual: '{valor_final}'")
                                else:
                                    print(f"   Error: No se visualiza la opcion '{nuevo_canal}' en el menu desplegable.")

                            except Exception as e:
                                print(f"   Error critico al rotar canal: {e}")

                            # 2. Cambio de Contraseña (PSK)
                            try:
                                print("   Buscando campo de contraseña (PSK)...")
                                # Buscamos el input que contiene 'pablo' o el que sigue al label 'Contraseña de PSK'
                                input_pass = pagina.locator("input[value*='pablo']").first
                                if not input_pass.is_visible():
                                    # Fallback por label si el valor no esta cargado aun
                                    input_pass = pagina.locator("label:has-text('Contraseña de PSK')").locator("xpath=../../..//input[@type='text']").first
                                
                                if input_pass.is_visible():
                                    pass_actual = input_pass.input_value() or input_pass.get_attribute("value") or ""
                                    print(f"   Contraseña actual detectada: '{pass_actual}'")
                                    
                                    # Lógica de cambio: [numero]pablo -> pablo[numero] y viceversa
                                    nueva_pass = pass_actual
                                    if pass_actual.endswith("pablo"):
                                        numero = pass_actual.replace("pablo", "")
                                        nueva_pass = f"pablo{numero}"
                                    elif pass_actual.startswith("pablo"):
                                        numero = pass_actual.replace("pablo", "")
                                        nueva_pass = f"{numero}pablo"
                                    
                                    if nueva_pass != pass_actual:
                                        print(f"   Cambiando contraseña a: '{nueva_pass}'")
                                        input_pass.fill("")
                                        input_pass.fill(nueva_pass)
                                        print("   Contraseña rellenada.")
                                    else:
                                        print("   No se pudo determinar el formato de la contraseña para cambiarla.")
                                else:
                                    print("   No se encontro el campo de contraseña PSK.")

                            except Exception as e:
                                print(f"   Error al cambiar contraseña: {e}")

                            # 3. Guardar cambios / Aplicar
                            try:
                                print("   Buscando boton Guardar o Aplicar...")
                                # Probamos con el ID especifico del screenshot: #wireless-submit-button
                                # O con el texto 'Guardar' / 'Aplicar'
                                boton_aplicar = pagina.locator("#wireless-submit-button")
                                if not boton_aplicar.is_visible():
                                    boton_aplicar = pagina.locator("text=Aplicar").first
                                    
                                if not boton_aplicar.is_visible():
                                    boton_aplicar = pagina.locator("text=Guardar").first
                                    
                                if boton_aplicar.is_visible():
                                    print(f"   Haciendo clic en {boton_aplicar.inner_text().strip() or 'el boton de envio'}...")
                                    boton_aplicar.click()
                                    pagina.wait_for_timeout(5000) # Esperar mas tiempo para el reinicio de red si aplica
                                    print("   Cambios aplicados correctamente.")
                                else:
                                    print("   Boton Guardar/Aplicar no encontrado.")
                            except Exception as e:
                                print(f"   Error al guardar/aplicar: {e}")

                            actualizar_apartamento(depto["_id"], {
                                "steps": "Rotacion de canal y cambio de clave finalizados",
                                "status": True
                            })
                            pagina.wait_for_timeout(2000)
                        else:
                            print("   No se pudo encontrar el link a INALAMBRICO")
                            actualizar_apartamento(depto["_id"], {"steps": "No se encontró sección Inalambrico", "status": False})

                    except Exception as e:
                        print(f"   Error al navegar: {e}")
                        actualizar_apartamento(depto["_id"], {"steps": "Error navegando a Inalambrico", "status": False})

                finally:
                    navegador.close()

    except Exception as e:
        print(f"Error general en el proceso: {e}")

if __name__ == "__main__":
    main()
