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
            id_buscado = int(sys.argv[1])
            target_apartamentos = [d for d in todos_apartamentos if d.get("id") == id_buscado]
            if not target_apartamentos:
                print(f"Error: No se encontró el departamento con ID numérico: {id_buscado}")
                return
        else:
            # Procesar todos los activos si no se especifica uno
            target_apartamentos = [d for d in todos_apartamentos if d.get("active")]
            print(f"Se procesarán {len(target_apartamentos)} departamentos activos.")

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
                            
                            # 1. Rotación de Canal (ya implementado)
                            try:
                                print("   Detectando canal actual...")
                                input_text = pagina.locator("#wl-basic-ap-channel input.combobox-text")
                                valor_actual = (input_text.get_attribute("value") or input_text.input_value() or "").strip()
                                print(f"   Canal actual: '{valor_actual}'")
                                
                                # Definir el nuevo canal según la rotación
                                nuevo_canal = "6 /" # Valor por defecto
                                if "6 /" in valor_actual:
                                    nuevo_canal = "11 /"
                                elif "11 /" in valor_actual:
                                    nuevo_canal = "1 /"
                                elif "1 /" in valor_actual:
                                    nuevo_canal = "6 /"
                                
                                print(f"   Seleccionando nuevo canal: '{nuevo_canal}'...")
                                switch = pagina.locator("#wl-basic-ap-channel .combobox-switch")
                                if switch.is_visible():
                                    switch.click()
                                else:
                                    input_text.click()
                                    
                                pagina.wait_for_timeout(2000)
                                opcion_nueva = pagina.locator(f"li:has-text('{nuevo_canal}')").last
                                if opcion_nueva.is_visible():
                                    opcion_nueva.click()
                                    print(f"   Canal cambiado a {nuevo_canal}.")
                                else:
                                    print(f"   No se encontro la opcion '{nuevo_canal}'")

                            except Exception as e:
                                print(f"   Error al rotar canal: {e}")

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

                            # 3. Guardar cambios
                            try:
                                print("   Buscando boton Guardar...")
                                boton_guardar = pagina.locator("text=Guardar").first
                                if boton_guardar.is_visible():
                                    print("   Haciendo clic en Guardar...")
                                    boton_guardar.click()
                                    pagina.wait_for_timeout(3000)
                                    print("   Cambios guardados correctamente.")
                                else:
                                    print("   Boton Guardar no encontrado.")
                            except Exception as e:
                                print(f"   Error al guardar: {e}")

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
