import ssl
import socketio
import os
from dotenv import load_dotenv

# ⚠️ Ignorar validación SSL globalmente
ssl._create_default_https_context = ssl._create_unverified_context

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

def main():
    try:
        sio.connect(sio_url, transports=["websocket"], socketio_path="socket.io")
    except Exception as e:
        print("❌ Error de conexión:", e)

    sio.wait()

if __name__ == "__main__":
    main()
