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
    """Obtiene la lista de todos los routers de habitaciones desde el API"""
    try:
        url = f"{api_url}/room-routers"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error al obtener routers de la API: {e}")
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
    print("Iniciando script de actualización de canales...")
    
    try:
        # 1. Obtener todos los routers de la API
        todos_routers = obtener_apartamentos()
        if not todos_routers:
            print("Error: No se pudieron obtener los routers de la API.")
            return

        # 2. Determinar cuáles procesar
        target_routers = []
        if len(sys.argv) >= 2:
            id_buscado = int(sys.argv[1])
            target_routers = [d for d in todos_routers if d.get("apartmentId", {}).get("id") == id_buscado]
            if not target_routers:
                print(f"Error: No se encontró el apartamento con ID numérico: {id_buscado}")
                return
        else:
            # Procesar todos los activos si no se especifica uno
            target_routers = [d for d in todos_routers if d.get("active")]
            print(f"Se procesarán {len(target_routers)} routers activos.")

        # 3. Iniciar Playwright
        with sync_playwright() as p:
            for depto in target_routers:
                apt_info = depto.get("apartmentId") or {}
                apt_name = apt_info.get("name", "Desconocido")
                apt_id = apt_info.get("id", "N/A")
                
                print(f"Procesando: {apt_name} (ID: {apt_id})")
                
                # Reseteamos status/steps al iniciar
                actualizar_apartamento(depto["_id"], {
                    "steps": "Iniciando actualización de canal",
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

                    # Navegar a ESTADO (usualmente es la principal o tiene un link)
                    try:
                        print("   Buscando sección ESTADO...")
                        # Intentar buscar el link o span que diga ESTADO
                        estado_link = pagina.locator("span.sub-navigator-text:has-text('ESTADO')")
                        if estado_link.is_visible():
                            estado_link.click()
                            pagina.wait_for_timeout(2000)
                        
                        # Extraer Canal/Frecuencia
                        print("   Extrayendo Canal/Frecuencia...")
                        
                        # Usar el selector específico indicado por el usuario
                        canal_valor = "No encontrado"
                        try:
                            # Según el DOM proporcionado: #wireless-info-channel
                            # El valor real suele estar dentro de .text-wrap-outer dentro del widget
                            selector_canal = "#wireless-info-channel .text-wrap-outer"
                            if pagina.locator(selector_canal).is_visible():
                                canal_valor = pagina.locator(selector_canal).inner_text().strip()
                            else:
                                # Fallback al widget completo o búsqueda por texto
                                canal_label = pagina.locator("#wireless-info-channel")
                                if canal_label.is_visible():
                                    canal_valor = canal_label.inner_text().replace("Canal/Frecuencia", "").replace(":", "").strip()
                        except Exception as e:
                            print(f"   Fallo selector específico: {e}")

                        # Fallback a Regex si no se encontró por selectores CSS
                        if canal_valor == "No encontrado":
                            try:
                                print("   No se encontró mediante selectores CSS. Probando Regex...")
                                texto_completo = pagina.content()
                                match = re.search(r"Canal/Frecuencia\s*[:]\s*([\w\s\(\)]+)", texto_completo)
                                if match:
                                    canal_valor = match.group(1).strip()
                                    canal_valor = " ".join(canal_valor.split())
                            except Exception as e:
                                print(f"   Fallo en la extracción por Regex: {e}")

                        print(f"   Canal detectado: {canal_valor}")
                        
                        # Actualizar en el API
                        actualizar_apartamento(depto["_id"], {
                            "channel": canal_valor,
                            "steps": "Canal actualizado correctamente",
                            "status": True
                        })

                    except Exception as e:
                        print(f"   Error al extraer canal: {e}")
                        actualizar_apartamento(depto["_id"], {"steps": "Error extrayendo canal", "status": False})

                finally:
                    navegador.close()

    except Exception as e:
        print(f"Error general en el proceso: {e}")

if __name__ == "__main__":
    main()
