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
                            
                            # Seleccionar el Canal 6 (6 / 2437MHz)
                            try:
                                print("   Intentando abrir el menu de Canales...")
                                # En este tipo de widgets, el clic debe ser en el 'switch' (la flechita)
                                # o en el input si el switch no responde bien.
                                
                                switch = pagina.locator("#wl-basic-ap-channel .combobox-switch")
                                input_text = pagina.locator("#wl-basic-ap-channel input.combobox-text")
                                
                                if switch.is_visible():
                                    print("   Click en el switch (.combobox-switch)")
                                    switch.click()
                                else:
                                    print("   Switch no visible, intentando click en el input")
                                    input_text.click()
                                    
                                pagina.wait_for_timeout(2000)
                                
                                # El menú desplegable (la lista de opciones) suele aparecer al final del DOM
                                # o dentro de un contenedor .combobox-list-container
                                print("   Buscando la opcion '6 /' en la lista...")
                                
                                # Usamos un selector mas global para encontrar el LI que contiene el texto
                                opcion_6 = pagina.locator("li:has-text('6 /')").last
                                
                                if opcion_6.is_visible():
                                    print(f"   Opcion encontrada: {opcion_6.inner_text()}")
                                    opcion_6.scroll_into_view_if_needed()
                                    opcion_6.click()
                                    print("   Se hizo clic en la opcion Canal 6.")
                                    
                                    # Esperar a que se procese el cambio
                                    pagina.wait_for_timeout(2000)
                                    
                                    # Verificar si se seleccionó (el input debería tener el valor ahora)
                                    valor_final = input_text.get_attribute("value") or input_text.input_value()
                                    print(f"   Valor actual en el input despues de clic: '{valor_final}'")
                                    
                                else:
                                    # Si no se ve, quizás hay que hacerle focus o scroll
                                    print("   No se visualiza la opcion 6. Listando todas las opciones visibles:")
                                    options = pagina.locator("li.combobox-list-item").all_inner_texts()
                                    print(f"   Opciones encontradas: {options}")

                            except Exception as e:
                                print(f"   Error al intentar seleccionar el canal: {e}")

                            actualizar_apartamento(depto["_id"], {
                                "steps": "Proceso de seleccion de Canal 6 finalizado",
                                "status": True
                            })
                            # Esperar un poco para que el usuario vea la página
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
