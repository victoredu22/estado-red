import socketio
import os
from dotenv import load_dotenv

load_dotenv()
sio_url = os.getenv("SERVER_SOCKET")

sio = socketio.Client()

@sio.event
def connect():
    print("✅ Conectado al servidor:", sio_url)

@sio.event
def connect_error(data):
    print("❌ Error de conexión:", data)

@sio.event
def disconnect():
    print("⚠️ Desconectado")


sio.connect(
    "https://cumbresanramon.cl",
    transports=["websocket"],
    socketio_path="/socket.io",
    ssl=ssl_context
)
sio.wait()
