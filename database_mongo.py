from pymongo import MongoClient

# Connection to MongoDB
client = MongoClient("mongodb://localhost:27017/")

# Create/use database
db = client["library_db"]

# Collections (like tables)
authors = db["authors"]
books = db["books"]
loans = db["loans"]

print("Connected to MongoDB successfully")