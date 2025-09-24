import os, ssl, certifi, socketio
from dotenv import load_dotenv

load_dotenv()
sio_url = os.getenv("SERVER_SOCKET", "https://cumbresanramon.cl")

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
        # Primer intento: como en el PC que funcionaba
        sio.connect(
            sio_url,
            transports=["websocket"],
            socketio_path="/socket.io"
        )
        sio.wait()
    except Exception as e:
        print("⚠️ Primer intento falló:", e)
        try:
            # Segundo intento: con validación explícita vía certifi
            sio.connect(
                sio_url,
                transports=["websocket"],
                socketio_path="/socket.io",
                sslopt={
                    "cert_reqs": ssl.CERT_REQUIRED,
                    "ca_certs": certifi.where()
                }
            )
            sio.wait()
        except Exception as e2:
            print("⚠️ Segundo intento falló:", e2)
            try:
                # Último recurso: sin validación
                sio.connect(
                    sio_url,
                    transports=["websocket"],
                    socketio_path="/socket.io",
                    sslopt={"cert_reqs": ssl.CERT_NONE}
                )
                sio.wait()
            except Exception as e3:
                print("❌ No se pudo conectar:", e3)

if __name__ == "__main__":
    main()
