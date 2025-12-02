from pymongo import MongoClient
import os

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
client = MongoClient(MONGO_URI)
db = client["mh"]
cats = db["categories"]

# Vacía colección (CUIDADO en prod)
cats.delete_many({})

# Asegúrate de tener imágenes de muestra en static/uploads
sample = [
    {"name": "BEBIDAS", "description": "Refresca tu paladar.", "order": 1, "image": "/static/uploads/bebidas.jpg"},
    {"name": "PIZZAS", "description": "Nuestras mejores pizzas.", "order": 2, "image": "/static/uploads/pizzas.jpg"},
    {"name": "COMPLEMENTOS", "description": "Papas, alitas y más.", "order": 3, "image": "/static/uploads/complementos.jpg"},
    {"name": "ESPECIALIDADES", "description": "Creaciones únicas del chef.", "order": 4, "image": "/static/uploads/especialidades.jpg"},
]

cats.insert_many(sample)
print("Datos iniciales insertados en mh.categories")
