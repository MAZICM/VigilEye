import face_recognition
import pickle
from datetime import datetime
from pymongo import MongoClient
import numpy as np
import io
from PIL import Image
import base64

class ModelTrainer:
    def __init__(self):
        self.client = MongoClient('mongodb://localhost:27017/')
        self.db = self.client['2FA']  # Update with your actual database name
        self.collection = self.db['users']  # Update with your actual collection name

    def train_and_save_model(self):
        known_face_encodings = []
        known_face_names = []

        # Retrieve images and labels from MongoDB collection
        cursor = self.collection.find({})
        for document in cursor:
            name = document['name']
            image_data = document['data']
            
            # Decode Base64 image data to bytes
            image_bytes = base64.b64decode(image_data)
            
            try:
                # Convert bytes to PIL image object
                image = Image.open(io.BytesIO(image_bytes))
                image = np.array(image)

                # Detect face and encode it
                face_locations = face_recognition.face_locations(image)
                if len(face_locations) > 0:
                    print(f"Face found for {name}")
                    encoding = face_recognition.face_encodings(image)[0]
                    known_face_encodings.append(encoding)
                    known_face_names.append(name)
                else:
                    print(f"No face found for {name}")
            except Exception as e:
                print(f"Error processing image for {name}: {e}")

        # Add an "unknown" label with zeroed encoding
        #unknown_encoding = [0] * 128  # Assuming 128-dimensional encoding
        #known_face_encodings.append(unknown_encoding)
        #known_face_names.append('unknown')

        model_data = {
            'known_face_encodings': known_face_encodings,
            'known_face_names': known_face_names
        }
        
        print(model_data)
        # Generate filename with current date and time
        now = datetime.now()
        date_time = now.strftime("%Y-%m-%d_%H-%M-%S")
        model_pkl_file = f"model_{date_time}.pkl"

        # Save model to pickle file
        with open(model_pkl_file, 'wb') as f:
            pickle.dump(model_data, f)

        # Connect to MongoDB and insert the model data
        db = self.client['2FA']  # Access 2FA database
        collection = db['AI-Models']  # Access AI-Models collection
        with open(model_pkl_file, 'rb') as f:
            model_bytes = f.read()
        model_doc = {
            'datetime': date_time,
            'model_bytes': model_bytes
        }
        collection.insert_one(model_doc)


def main():
    # Train the model
    trainer = ModelTrainer()
    trainer.train_and_save_model()

if __name__ == "__main__":
    main()
