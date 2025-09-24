from playwright.sync_api import sync_playwright, TimeoutError
from connection import get_apartment, update_apartment
import requests
import socketio
import os
from dotenv import load_dotenv

load_dotenv()  # Carga las variables del archivo .env

api_url = os.getenv('API_APARTMENTS_URL') 


sio = socketio.Client()
sio_url = os.getenv('SERVER_SOCKET')

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


sio.connect(sio_url, transports=["websocket"])
sio.wait()

def main():


    sio.connect(sio_url, transports=["websocket"], ssl_verify=False)


    sio.disconnect()
if __name__ == "__main__":
    main()
