import socketio

sio = socketio.Client()

@sio.event
def connect():
    print("✅ Conectado al servidor")

@sio.event
def connect_error(data):
    print("❌ Error de conexión:", data)

@sio.event
def disconnect():
    print("⚠️ Desconectado")

def main():
    try:
        sio.connect(
            "https://cumbresanramon.cl",
            transports=["polling", "websocket"],   # primero polling, luego websocket
            socketio_path="/socket.io"
        )
        sio.wait()
    except Exception as e:
        print("❌ No se pudo conectar:", e)

if __name__ == "__main__":
    main()
