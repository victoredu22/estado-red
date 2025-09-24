from playwright.sync_api import sync_playwright, TimeoutError
import socketio
import os
import ssl
import certifi
from dotenv import load_dotenv

load_dotenv()  # Carga las variables del archivo .env

api_url = os.getenv("API_APARTMENTS_URL")
sio_url = os.getenv("SERVER_SOCKET")

sio = socketio.Client()

# Crear contexto SSL seguro usando certifi
ssl_context = ssl.create_default_context(cafile=certifi.where())

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


def main():
    try:
        sio.connect(
            sio_url,
            transports=["websocket"],
            socketio_path="/socket.io",
            ssl=ssl_context
        )
        sio.wait()
    except Exception as e:
        print("❌ Error al conectar:", e)


if __name__ == "__main__":
    main()
