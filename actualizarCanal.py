from playwright.sync_api import sync_playwright, TimeoutError
import requests
import os
import sys
import re
from dotenv import load_dotenv

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
        print(f"   📡 Actualizando API ({api_mongo_id}): {data}")
        response = requests.patch(url, json=data)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"   ❌ Error al actualizar API: {e}")
        return None

# =====================
# MAIN
# =====================
def main():
    print("🚀 Iniciando script de actualización de canales...")
    
    try:
        # 1. Obtener todos los apartamentos
        todos_apartamentos = obtener_apartamentos()
        if not todos_apartamentos:
            print("❌ No se pudieron obtener los apartamentos de la API.")
            return

        # 2. Determinar cuáles procesar
        target_apartamentos = []
        if len(sys.argv) >= 2:
            id_buscado = int(sys.argv[1])
            target_apartamentos = [d for d in todos_apartamentos if d.get("id") == id_buscado]
            if not target_apartamentos:
                print(f"❌ No se encontró el departamento con ID numérico: {id_buscado}")
                return
        else:
            # Procesar todos los activos si no se especifica uno
            target_apartamentos = [d for d in todos_apartamentos if d.get("active")]
            print(f"📋 Se procesarán {len(target_apartamentos)} departamentos activos.")

        # 3. Iniciar Playwright
        with sync_playwright() as p:
            for depto in target_apartamentos:
                print(f"\n🏠 Procesando: {depto['name']} (ID: {depto['id']})")
                
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
                    print(f"   🔗 Conectando a {depto['url']}...")
                    try:
                        pagina.goto(depto["url"], timeout=30000)
                    except Exception as e:
                        print(f"   ❌ Error de conexión: {e}")
                        actualizar_apartamento(depto["_id"], {"steps": "Error de conexión", "status": False})
                        continue

                    # Login
                    print("   🔐 Iniciando sesión...")
                    pagina.locator("input[type='text']").nth(0).fill(depto["user"])
                    pagina.locator("input[type='password']").nth(0).fill(depto["password"])
                    
                    try:
                        # Intentar clic en Acceder
                        pagina.locator("text=Acceder").nth(1).click()
                        pagina.wait_for_timeout(3000)
                    except Exception as e:
                        print(f"   ❌ Error al hacer clic en Acceder: {e}")
                        actualizar_apartamento(depto["_id"], {"steps": "Error en botón login", "status": False})
                        continue

                    # Verificar si el login fue exitoso
                    if pagina.url.endswith("/login") or "login" in pagina.title().lower():
                        print("   ⚠️ Credenciales incorrectas.")
                        actualizar_apartamento(depto["_id"], {"steps": "Credenciales incorrectas", "status": False})
                        continue

                    print("   ✅ Login exitoso")

                    # Navegar a ESTADO (usualmente es la principal o tiene un link)
                    try:
                        print("   📋 Buscando sección ESTADO...")
                        # Intentar buscar el link o span que diga ESTADO
                        estado_link = pagina.locator("span.sub-navigator-text:has-text('ESTADO')")
                        if estado_link.is_visible():
                            estado_link.click()
                            pagina.wait_for_timeout(2000)
                        
                        # Extraer Canal/Frecuencia
                        # Buscamos por texto "Canal/Frecuencia"
                        print("   🔍 Extrayendo Canal/Frecuencia...")
                        
                        # Estrategia: Buscar el elemento que contiene el texto y obtener el siguiente o el valor en la misma fila
                        # Según el usuario: "dice canal/fecuencia y despues el valor"
                        texto_completo = pagina.content()
                        
                        # Usar regex o locators para encontrar el valor
                        # Ejemplo: Canal/Frecuencia : 1 (2412 MHz)
                        match = re.search(r"Canal/Frecuencia\s*[:]\s*([\w\s\(\)]+)", texto_completo)
                        
                        canal_valor = "No encontrado"
                        if match:
                            canal_valor = match.group(1).strip()
                            # Limpiar un poco si hay saltos de línea o muchos espacios
                            canal_valor = " ".join(canal_valor.split())
                        else:
                            # Intentar buscar en la tabla si existe
                            try:
                                # Buscar el TD que contiene el texto y obtener el siguiente TD
                                canal_label = pagina.locator("td:has-text('Canal/Frecuencia')")
                                if canal_label.is_visible():
                                    canal_valor = pagina.locator("td:has-text('Canal/Frecuencia') + td").inner_text()
                            except:
                                pass

                        print(f"   📡 Canal detectado: {canal_valor}")
                        
                        # Actualizar en el API
                        actualizar_apartamento(depto["_id"], {
                            "channel": canal_valor,
                            "steps": "Canal actualizado correctamente",
                            "status": True
                        })

                    except Exception as e:
                        print(f"   ❌ Error al extraer canal: {e}")
                        actualizar_apartamento(depto["_id"], {"steps": "Error extrayendo canal", "status": False})

                finally:
                    navegador.close()

    except Exception as e:
        print(f"❌ Error general en el proceso: {e}")

if __name__ == "__main__":
    main()
