from pymongo import MongoClient
import urllib.parse

username = "iconichean"
password = "1Loye8PM3YwlV5h4"
encoded_password = urllib.parse.quote_plus(password)

uri = f"mongodb+srv://{username}:{encoded_password}@cluster0.meufk73.mongodb.net/?retryWrites=true&w=majority"

print(f"Testing connection to: {uri.replace(password, '*****')}")

try:
    client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    client.server_info()  # Will throw exception if cannot connect
    print("✅ Successfully connected to MongoDB Atlas!")
    
    # List databases
    print("\nAvailable databases:")
    for db in client.list_database_names():
        print(f"  - {db}")
    
    # Create mufra_fashions database if it doesn't exist
    db = client['mufra_fashions']
    print(f"\nUsing database: mufra_fashions")
    
    # Create collections
    collections = ['users', 'products', 'orders', 'reviews']
    for collection in collections:
        if collection not in db.list_collection_names():
            db.create_collection(collection)
            print(f"  Created collection: {collection}")
        else:
            print(f"  Collection exists: {collection}")
    
    print("\n✅ Database setup complete!")
    
except Exception as e:
    print(f"❌ Connection failed: {e}")
    print("\nTroubleshooting:")
    print("1. Check if your IP is whitelisted in MongoDB Atlas")
    print("2. Verify username and password")
    print("3. Check internet connection")