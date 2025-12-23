from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()
client = MongoClient(os.getenv("MONGODB_URI"))
db = client[os.getenv("MONGODB_DB_NAME")]
collection = db[os.getenv("MONGODB_RAG_COLLECTION_NAME")]

print("Tổng số documents:", collection.count_documents({}))
doc = collection.find_one()
print("Một mẫu document:\n", doc)
# check mongodb