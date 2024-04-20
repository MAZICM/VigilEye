from pymongo import MongoClient
import base64

# Connect to MongoDB
client = MongoClient('mongodb://localhost:27017/')  # Update the connection string accordingly
db = client['2FA']  # Update with your database name
collection = db['users']  # Update with your collection name

# Read image file as binary data
with open('C:\\Users\\mouhi\\Pictures\\Camera Roll\\JUDGE.jpg', 'rb') as file:
    image_data = file.read()

# Encode the binary data as base64
encoded_image = base64.b64encode(image_data).decode('utf-8')

# New element to insert
new_element = {
    "filename": "JJ.png",
    "data": encoded_image,
    "name": "JJ",
    "cardID": "6666"  # Update with the desired card ID
}

# Insert the new element into the collection
insert_result = collection.insert_one(new_element)

print("New element inserted with ID:", insert_result.inserted_id)
