import os
import sys
import requests
from pathlib import Path
from dotenv import load_dotenv

# Forzar salida en UTF-8 en consola de Windows
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()

def enviar_mensaje_telegram(texto: str):
    if not BOT_TOKEN or not CHAT_ID:
        print("❌ Error: Faltan credenciales en el archivo .env")
        return
    
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": texto,
        "parse_mode": "HTML"
    }
    try:
        response = requests.post(url, json=payload, timeout=8)
        if response.status_code == 200:
            print("✅ Notificación enviada a Telegram.")
        else:
            print(f"❌ Error en Telegram: {response.text}")
    except Exception as e:
        print(f"❌ Error de red al enviar a Telegram: {e}")

if __name__ == "__main__":
    # Si se pasa como argumento 'encendido' o 'apagado'
    modo = sys.argv[1] if len(sys.argv) > 1 else "encendido"
    
    if modo == "encendido":
        mensaje = "🟢 <b>PC Encendido</b>\n\nEl equipo se ha iniciado y está en línea."
    elif modo == "apagado":
        mensaje = "🔴 <b>PC Apagado</b>\n\nEl equipo se está desconectando / apagando."
    else:
        mensaje = f"ℹ️ <b>Notificación PC:</b> {modo}"
        
    enviar_mensaje_telegram(mensaje)
