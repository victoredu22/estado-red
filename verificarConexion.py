from playwright.sync_api import sync_playwright, TimeoutError
import requests
import os
import sys
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
    print("Iniciando script de verificación de conexión...")
    
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
                id_num = int(param_buscado)
                target_apartamentos = [d for d in todos_apartamentos if d.get("id") == id_num]
            except ValueError:
                pass
            
            if not target_apartamentos:
                target_apartamentos = [
                    d for d in todos_apartamentos 
                    if param_buscado.lower() in d.get("name", "").lower() or 
                       (str(d.get("id")) == param_buscado)
                ]
            
            if not target_apartamentos:
                print(f"Error: No se encontró el departamento relacionado con: '{param_buscado}'")
                return
            
            print(f"Objetivo único: {target_apartamentos[0]['name']} (ID: {target_apartamentos[0]['id']})")
        else:
            # Si no se pasan argumentos, procesamos todos los activos
            target_apartamentos = [d for d in todos_apartamentos if d.get("active")]
            print(f"No se especificó un departamento. Se procesarán {len(target_apartamentos)} departamentos activos.")

        # 3. Iniciar Playwright
        with sync_playwright() as p:
            for depto in target_apartamentos:
                print(f"\nProcesando: {depto['name']} (ID: {depto['id']})")
                
                actualizar_apartamento(depto["_id"], {
                    "steps": f"Verificando conexión...",
                    "status": False
                })

                navegador = p.chromium.launch(headless=False) # Cambia a True si quieres que corra oculto
                try:
                    contexto = navegador.new_context(ignore_https_errors=True)
                    pagina = contexto.new_page()

                    print(f"   Intentando conectar a {depto['url']} ...")
                    # El timeout es de 30 segundos, si el router está caído lanzará TimeoutError o net::ERR_CONNECTION_TIMED_OUT
                    pagina.goto(depto["url"], timeout=30000)
                    
                    print("   Iniciando sesión...")
                    pagina.locator("input[type='text']").nth(0).fill(depto["user"])
                    pagina.locator("input[type='password']").nth(0).fill(depto["password"])
                    
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
                except Exception as e:
                    print(f"   [ERROR] No se pudo conectar a la URL: {e}")
                    actualizar_apartamento(depto["_id"], {
                        "steps": f"Fallo de conexión: {str(e)[:60]}",
                        "status": False
                    })
                finally:
                    navegador.close()
    except Exception as e:
        print(f"Error general: {e}")

if __name__ == "__main__":
    main()