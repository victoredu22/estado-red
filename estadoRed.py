from playwright.sync_api import sync_playwright, TimeoutError
from connection import get_apartment, update_apartment
import requests
import socketio
import os
from dotenv import load_dotenv

load_dotenv()  # Carga las variables del archivo .env

api_url = os.getenv("API_APARTMENTS_URL")
sio_url = os.getenv("SERVER_SOCKET")

sio = socketio.Client()

# ========================
# Eventos socket.io
# ========================
@sio.event
def connect():
    print("✅ Conectado al servidor:", sio_url)
    sio.emit("test", "Hola desde Python")

@sio.event
def connect_error(data):
    print("❌ Error de conexión:", data)

@sio.event
def disconnect():
    print("⚠️ Desconectado")

# ========================
# MAIN
# ========================
def main():
    try:
        # Intento normal
        sio.connect(sio_url, transports=["websocket"])
    except Exception as e:
        print("⚠️ Error SSL, reintentando sin verificación:", e)
        # Intento ignorando verificación SSL
        sio.connect(sio_url, transports=["websocket"], ssl_verify=False)

    sio.wait()  # Mantener la conexión abierta
    sio.disconnect()

if __name__ == "__main__":
    main()
