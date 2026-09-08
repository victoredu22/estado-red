from playwright.sync_api import sync_playwright, TimeoutError
import requests
import os
import sys
import time
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
api_key = os.getenv("ESTADO_RED_API_KEY")
if not api_key:
    raise RuntimeError("ESTADO_RED_API_KEY no está configurada")
api_headers = {"X-API-Key": api_key}

# =====================
# FUNCIONES API
# =====================
def obtener_apartamentos():
    """Obtiene la lista de todos los routers de la API"""
    try:
        url = f"{api_url}/room-routers"
        response = requests.get(url, headers=api_headers)
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
        response = requests.patch(url, json=data, headers=api_headers)
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
            target_routers = [d for d in todos_routers if d.get("active")]
            print(f"No se especificó un departamento. Se procesarán {len(target_routers)} routers activos.")

        # 3. Iniciar Playwright
        if target_routers:
            with sync_playwright() as p:
                for depto in target_routers:
                    apt_info = depto.get("apartmentId") or {}
                    apt_name = apt_info.get("name", "Desconocido")
                    apt_id = apt_info.get("id", "N/A")
                    
                    print(f"\nProcesando: {apt_name} (ID: {apt_id})")
                    
                    actualizar_apartamento(depto["_id"], {
                        "steps": "Verificando conexión...",
                        "status": False
                    })

                    navegador = p.chromium.launch(headless=False, args=["--start-maximized"])
                    try:
                        contexto = navegador.new_context(ignore_https_errors=True, no_viewport=True)
                        pagina = contexto.new_page()

                        print(f"   Intentando conectar a {depto['url']} ...")
                        pagina.goto(depto["url"], timeout=30000)
                        pagina.wait_for_timeout(2000)
                        
                        # Usar el parámetro 'password' de Mongo
                        pass_a_usar = depto.get("password") or ""
                        print(f"   Iniciando sesión con usuario '{depto['user']}' y contraseña (password): '{pass_a_usar}'...")
                        
                        # Llenar usuario y contraseña
                        pagina.locator("input[type='text']").nth(0).fill(depto["user"])
                        pass_input = pagina.locator("input[type='password']").first
                        pass_input.fill(pass_a_usar)
                        pagina.wait_for_timeout(500)
                        
                        # Estrategia de clic robusta para el botón Acceder
                        btn = pagina.locator("a.button-button, button, input[type='submit'], input[type='button']").filter(has_text=re.compile(r"Acceder|Login|Iniciar", re.I)).first
                        
                        if btn.is_visible():
                            print("   Ejecutando clic directo (JS evaluate) en el botón Acceder...")
                            try:
                                btn.evaluate("node => node.click()")
                            except Exception:
                                try:
                                    btn.click(force=True)
                                except Exception:
                                    pass
                        else:
                            print("   Enviando tecla Enter en el campo de contraseña...")
                            try:
                                pass_input.press("Enter")
                            except Exception:
                                pass

                        pagina.wait_for_timeout(5000)

                        # Detectar éxito comprobando si hay elementos del panel de control
                        es_exitoso = False
                        try:
                            if (pagina.locator("text=INALAMBRICO").count() > 0 or 
                                pagina.locator("text=INALÁMBRICO").count() > 0 or 
                                pagina.locator("text=WIRELESS").count() > 0 or 
                                pagina.locator("text=ESTADO").count() > 0 or
                                "cpe" in pagina.title().lower()):
                                es_exitoso = True
                        except Exception:
                            es_exitoso = False

                        if es_exitoso:
                            # Extraer tiempo de conexión / activación de la página
                            tiempos_encontrados = []
                            try:
                                body_text = pagina.locator("body").inner_text()
                                lineas = [l.strip() for l in body_text.split("\n") if l.strip()]
                                for i in range(len(lineas) - 1):
                                    if re.search(r"tiempo\s*de|uptime|tiempo\s*transcurrido", lineas[i], re.I):
                                        label = lineas[i].rstrip(":")
                                        val = lineas[i+1]
                                        tiempos_encontrados.append(f"{label}: {val}")
                            except Exception as err_t:
                                print(f"   Aviso al extraer tiempo: {err_t}")

                            info_tiempo = " | ".join(dict.fromkeys(tiempos_encontrados)) if tiempos_encontrados else "Tiempo no especificado"
                            print(f"   [ÉXITO] Conexión y login exitosos.")
                            print(f"   ⏱️ {info_tiempo}")
                            actualizar_apartamento(depto["_id"], {
                                "steps": f"Conexión exitosa ({info_tiempo})",
                                "status": True
                            })
                        else:
                            print(f"   [ERROR] Credenciales incorrectas o el inicio de sesión falló.")
                            actualizar_apartamento(depto["_id"], {
                                "steps": "Fallo: Credenciales incorrectas",
                                "status": False
                            })
                    except Exception as e:
                        print(f"   [ERROR] No se pudo conectar a la URL o timeout: {e}")
                        actualizar_apartamento(depto["_id"], {
                            "steps": f"Fallo de conexión: {str(e)[:60]}",
                            "status": False
                        })
                    finally:
                        print("   [INFO] Manteniendo ventana del navegador abierta durante 20 segundos...")
                        time.sleep(20)
                        try:
                            navegador.close()
                        except Exception:
                            pass

    except Exception as e:
        print(f"Error general: {e}")

if __name__ == "__main__":
    main()
