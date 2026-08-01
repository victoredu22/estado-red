from playwright.sync_api import sync_playwright, TimeoutError
import requests
import os
import sys
import time
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
    """Obtiene la lista de todos los routers de la API"""
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
    print("Iniciando script de verificación de conexión...")
    
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
                id_num = int(param_buscado)
                target_routers = [d for d in todos_routers if d.get("apartmentId", {}).get("id") == id_num]
            except ValueError:
                pass
            
            if not target_routers:
                target_routers = [
                    d for d in todos_routers 
                    if param_buscado.lower() in d.get("apartmentId", {}).get("name", "").lower() or 
                       (str(d.get("apartmentId", {}).get("id")) == param_buscado)
                ]
            
            if not target_routers:
                print(f"Error: No se encontró el apartamento relacionado con: '{param_buscado}'")
                return
            
            apt_info = target_routers[0].get("apartmentId") or {}
            print(f"Objetivo único: {apt_info.get('name')} (ID: {apt_info.get('id')})")
        else:
            # Si no se pasan argumentos, procesamos todos los activos
            target_routers = [d for d in todos_routers if d.get("active")]
            print(f"No se especificó un departamento. Se procesarán {len(target_routers)} routers activos.")

        # 3. Iniciar Playwright
        if target_routers:
            p = sync_playwright().start()
            navegadores = []
            for depto in target_routers:
                apt_info = depto.get("apartmentId") or {}
                apt_name = apt_info.get("name", "Desconocido")
                apt_id = apt_info.get("id", "N/A")
                
                print(f"\nProcesando: {apt_name} (ID: {apt_id})")
                
                actualizar_apartamento(depto["_id"], {
                    "steps": f"Verificando conexión...",
                    "status": False
                })

                navegador = p.chromium.launch(headless=False)
                navegadores.append(navegador)
                try:
                    contexto = navegador.new_context(ignore_https_errors=True)
                    pagina = contexto.new_page()

                    print(f"   Intentando conectar a {depto['url']} ...")
                    pagina.goto(depto["url"], timeout=30000)
                    
                    print("   Iniciando sesión...")
                    pagina.locator("input[type='text']").nth(0).fill(depto["user"])
                    pagina.locator("input[type='password']").nth(0).fill(depto["passwordLocal"])
                    
                    try:
                        # Intentar clic en Acceder
                        pagina.locator("text=Acceder").nth(1).click()
                        pagina.wait_for_timeout(3000)
                    except Exception as e:
                        raise Exception("Fallo en el botón de inicio de sesión o timeout")

                    # Verificar si el login fue exitoso comprobando si sigue en la pantalla de login
                    if pagina.url.endswith("/login") or "login" in pagina.title().lower():
                        print("   [ERROR] Credenciales incorrectas.")
                        actualizar_apartamento(depto["_id"], {
                            "steps": "Fallo: Credenciales incorrectas",
                            "status": False
                        })
                    else:
                        print(f"   [ÉXITO] Conexión y login exitosos.")
                        actualizar_apartamento(depto["_id"], {
                            "steps": "Conexión y login exitosos",
                            "status": True
                        })
                        navegadores.remove(navegador)
                        navegador.close()
                except Exception as e:
                    print(f"   [ERROR] No se pudo conectar a la URL: {e}")
                    actualizar_apartamento(depto["_id"], {
                        "steps": f"Fallo de conexión: {str(e)[:60]}",
                        "status": False
                    })
                finally:
                    pass

            time.sleep(120)
            for navegador in navegadores:
                navegador.close()
            p.stop()
    except Exception as e:
        print(f"Error general: {e}")

if __name__ == "__main__":
    main()
