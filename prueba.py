from pymongo import MongoClient

uri = "mongodb+srv://cumbre:319923@cumbre.ht5ejwk.mongodb.net/?retryWrites=true&w=majority"
cliente = MongoClient(uri, serverSelectionTimeoutMS=5000, tls=True)

try:
    cliente.server_info()  # Fuerza conexión
    print("✅ Conexión exitosa a MongoDB Atlas")
except Exception as e:
    print("❌ Error al conectar:", e)