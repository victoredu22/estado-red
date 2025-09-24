import os
import socketio
import ssl
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

def main():
    try:
        # Intento normal
        sio.connect(sio_url, transports=["websocket"], socketio_path="socket.io")
    except Exception as e:
        print("⚠️ Error SSL, reintentando sin verificación:", e)
        # Intento ignorando certificados
        sio.connect(
            sio_url,
            transports=["websocket"],
            socketio_path="socket.io",
            sslopt={"cert_reqs": ssl.CERT_NONE}
        )

    sio.wait()

if __name__ == "__main__":
    main()
