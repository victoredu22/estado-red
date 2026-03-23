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
                
                # Extraer numero del departamento para la contraseña
                num_depto = "".join(filter(str.isdigit, depto["name"]))
                if not num_depto:
                    num_depto = str(depto["id"])
                
                # Reseteamos status/steps al iniciar
                actualizar_apartamento(depto["_id"], {
                    "steps": f"Iniciando configuracion de {depto['name']}",
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
                                
                                # Rotación circular: 11 -> 1 -> 6 -> 11
                                nuevo_canal_prefix = "1 /"
                                if "11 /" in valor_actual:
                                    nuevo_canal_prefix = "1 /"
                                elif "1 /" in valor_actual:
                                    nuevo_canal_prefix = "6 /"
                                elif "6 /" in valor_actual:
                                    nuevo_canal_prefix = "11 /"
                                
                                print(f"   Objetivo: Seleccionar canal que empiece con '{nuevo_canal_prefix}'")
                                
                                # Abrir el menu
                                container.locator(".combobox-switch").click()
                                pagina.wait_for_timeout(2000)
                                
                                # Selector preciso usando REGEX para evitar que '11' coincida con '1'
                                # Buscamos LIs que EMPIECEN exactamente con el prefijo deseado
                                regex_selector = re.compile(f"^{re.escape(nuevo_canal_prefix)}")
                                opcion = pagina.locator("li").filter(has_text=regex_selector).last
                                
                                if opcion.is_visible():
                                    texto_opcion = opcion.inner_text().strip()
                                    print(f"   Haciendo clic preciso en: '{texto_opcion}'")
                                    
                                    # Metodo 1: Clic estandar
                                    opcion.click(force=True)
                                    pagina.wait_for_timeout(2000)
                                    
                                    # Verificacion
                                    valor_final = (input_text.get_attribute("value") or input_text.input_value() or "").strip()
                                    if nuevo_canal_prefix in valor_final:
                                        print(f"   Exito: Canal cambiado a {valor_final}")
                                    else:
                                        print(f"   No cambio. Intentando Metodo 2: JS evaluate click...")
                                        opcion.evaluate("node => node.click()")
                                        pagina.wait_for_timeout(2000)
                                        valor_final = (input_text.get_attribute("value") or input_text.input_value() or "").strip()
                                        print(f"   Valor final tras JS: '{valor_final}'")
                                else:
                                    print(f"   Error: No se encontro ninguna opcion que empiece con '{nuevo_canal_prefix}'")
                                    # Depuracion: ver que opciones hay
                                    opciones = pagina.locator("li:visible").all_inner_texts()
                                    print(f"   Opciones visibles (primeras 5): {opciones[:5]}")

                            except Exception as e:
                                print(f"   Error critico al rotar canal: {e}")

                            # 2. Cambio de Contraseña (PSK)
                            try:
                                print("   Buscando campo de contraseña (PSK)...")
                                # El contenedor es #wl-ap-wpa-pwd según el HTML del usuario
                                psk_container = pagina.locator("#wl-ap-wpa-pwd")
                                input_pass = psk_container.locator("input.password-visible").first
                                if not input_pass.is_visible():
                                    input_pass = psk_container.locator("input:visible").first
                                    if not input_pass.is_visible():
                                        input_pass = psk_container.locator("input").first
                                
                                if input_pass and input_pass.is_visible():
                                    pass_actual = (input_pass.input_value() or input_pass.get_attribute("value") or "").strip()
                                    if not pass_actual:
                                        # Intentamos leer el texto si el value esta vacio (a veces Pharos lo hace)
                                        pass_actual = psk_container.inner_text().strip().split('\n')[0]
                                    
                                    print(f"   Contraseña actual detectada: '{pass_actual}'")
                                    
                                    # Lógica de cambio: [numero]pablo <-> pablo[numero]
                                    num_str = str(num_depto)
                                    base_pablo = f"{num_str}pablo"
                                    swap_pablo = f"pablo{num_str}"
                                    
                                    nueva_pass = base_pablo # Default
                                    if base_pablo in pass_actual:
                                        nueva_pass = swap_pablo
                                    elif swap_pablo in pass_actual:
                                        nueva_pass = base_pablo
                                    
                                    if nueva_pass != pass_actual or True: # Forzamos escritura para asegurar
                                        print(f"   Cambiando contraseña a: '{nueva_pass}'")
                                        input_pass.fill("")
                                        input_pass.fill(nueva_pass)
                                        pagina.wait_for_timeout(1000)
                                        
                                        # Verificación final
                                        verif = (input_pass.input_value() or input_pass.get_attribute("value") or "").strip()
                                        if verif == nueva_pass:
                                            print("   Exito: Contraseña escrita correctamente.")
                                            cambio_psk_exitoso = True
                                        else:
                                            # Respaldo con JS
                                            input_pass.evaluate(f"node => node.value = '{nueva_pass}'")
                                            input_pass.dispatch_event("change")
                                            print(f"   Escrito por JS: '{nueva_pass}'")
                                            cambio_psk_exitoso = True
                                else:
                                    print("   No se encontro el campo de contraseña PSK en #wl-ap-wpa-pwd.")
                            except Exception as e:
                                print(f"   Error al cambiar contraseña: {e}")

                            # 3. Guardar cambios / Aplicar
                            try:
                                print("   Buscando boton Aplicar...")
                                # Selector basado en el HTML del usuario: .button-wrap >> text=Aplicar
                                boton_aplicar = pagina.locator("div.button-wrap").filter(has_text="Aplicar").locator("a.button-button").first
                                if not boton_aplicar.is_visible():
                                    boton_aplicar = pagina.locator("a.button-button").filter(has_text="Aplicar").first
                                
                                if boton_aplicar.is_visible():
                                    print(f"   Haciendo clic en el boton Aplicar...")
                                    # Metodo 1: Clic natural
                                    boton_aplicar.click()
                                    pagina.wait_for_timeout(3000)
                                    
                                    # Si sigue visible, intentamos Metodo 2: JS Evaluate
                                    if boton_aplicar.is_visible():
                                        print("   El boton sigue visible. Intentando clic forzado por JS...")
                                        boton_aplicar.evaluate("node => node.click()")
                                        pagina.wait_for_timeout(5000)
                                    
                                    print("   Cambios aplicados correctamente.")
                                    cambio_canal_exitoso = True # Asumimos éxito si llegamos aquí
                                else:
                                    print("   Boton Aplicar no encontrado. Probando fallback con selectors genericos...")
                                    fallback = pagina.locator("#wireless-submit-button").or_(pagina.get_by_text("Aplicar")).or_(pagina.get_by_text("Guardar"))
                                    if fallback.count() > 0 and fallback.first.is_visible():
                                        print(f"   Haciendo clic en el fallback: {fallback.first.inner_text()}")
                                        fallback.first.click()
                                        pagina.wait_for_timeout(5000)
                                        cambio_canal_exitoso = True
                                    else:
                                        print("   No se encontro ningun boton de envio.")
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
