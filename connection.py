from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from bson import ObjectId
import os
from dotenv import load_dotenv

load_dotenv()  # Carga variables de entorno
    
MONGO_URI = os.getenv("MONGO_URI")

def get_collection(db_name: str, collection_name: str):
    try:
        print(f"🔄 Conectando a MongoDB con URI: {MONGO_URI}")
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        client.server_info()
        db = client[db_name]
        print(f"✅ Conectado a la base de datos: {db_name}, colección: {collection_name}")
        return db[collection_name]
    except ConnectionFailure as e:
        print("❌ Error de conexión a MongoDB:", e)
    except Exception as e:
        print("❌ Error general al obtener la colección:", e)
    return None
  

def get_apartment():
    collection = get_collection("huellas", "apartment")
    if collection is not None:
        return list(collection.find())
    return []


def update_apartment(apartamento_id, nuevos_datos):
    collection = get_collection("huellas", "apartment")
    if collection is None:
        return 0
    try:
        resultado = collection.update_one(
            {"id": apartamento_id},  # filtro por campo 'id', no por _id
            {"$set": nuevos_datos}
        )
        return resultado.modified_count
    except Exception as e:
        print("❌ Error al actualizar apartamento:", e)
        return 0


if __name__ == "__main__":
    apartamentos = get_apartment()
    print(f"Departamentos encontrados: {len(apartamentos)}")
    for apto in apartamentos:
        print(apto)