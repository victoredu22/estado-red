import ssl
import certifi
import socketio
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()
sio_url = os.getenv("SERVER_SOCKET")

# Crear cliente socket.io
sio = socketio.Client(
    reconnection=True,           # reintentos automáticos
    reconnection_attempts=5,     # número de intentos
    reconnection_delay=2         # segundos entre intentos
)

# Crear contexto SSL seguro con certifi
ssl_context = ssl.create_default_context(cafile=certifi.where())

# Eventos básicos
@sio.event
def connect():
    print("✅ Conectado al servidor:", sio_url)
    sio.emit("test", "Hola desde Python 🚀")

@sio.event
def connect_error(data):
    print("❌ Error de conexión:", data)

@sio.event
def disconnect():
    print("⚠️ Desconectado del servidor")

# Ejemplo: escuchar un canal específico
@sio.on("canalFrontend")
def canal_frontend(data):
    print("📩 Mensaje en canalFrontend:", data)

def main():
    try:
        sio.connect(
            sio_url,
            transports=["websocket"],
            socketio_path="/socket.io"             # asegura validación SS          # usa el contexto con certifi
        )
        sio.wait()
    except Exception as e:
        print("❌ No se pudo conectar:", e)

if __name__ == "__main__":
    main()
