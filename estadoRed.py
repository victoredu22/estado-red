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

def obtener_apartamentos():
    try:
        url = f"{api_url}/apartment/all"
        response = requests.get(url)
        print("API URL:", url)
        print("Código de estado:", response.status_code)
        print("Texto crudo de la respuesta:", response.text)

        response.raise_for_status()
        data = response.json()
        print("JSON decodificado:", data)
        return data
    except requests.RequestException as e:
        print(f"Error al obtener apartamentos: {e}")
        return []


def actualizar_apartamento(apartamento_id, data):
    try:
        url = f"{api_url}/apartment/{apartamento_id}"
        print(f"Enviando Patch a {url} con data: {data}")
        response = requests.patch(url, json=data)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error al obtener apartamentos: {e}")
        return None
def main():
    sio.connect(sio_url)

    sio.disconnect()
if __name__ == "__main__":
    main()
