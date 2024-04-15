import face_recognition
import os
import pickle
from datetime import datetime
from pymongo import MongoClient

class ModelTrainer:
    def __init__(self, known_faces_dir='known_faces'):
        self.known_faces_dir = known_faces_dir

    def train_and_save_model(self):
        known_face_encodings = []
        known_face_names = []

        for name in os.listdir(self.known_faces_dir):
            for filename in os.listdir(os.path.join(self.known_faces_dir, name)):
                image = face_recognition.load_image_file(os.path.join(self.known_faces_dir, name, filename))
                face_locations = face_recognition.face_locations(image)
                if len(face_locations) > 0:
                    print(f"Face found in {filename}")
                    encoding = face_recognition.face_encodings(image)[0]
                    known_face_encodings.append(encoding)
                    known_face_names.append(name)
                else:
                    print(f"No face found in {filename}")

        model_data = {
            'known_face_encodings': known_face_encodings,
            'known_face_names': known_face_names
        }

        # Generate filename with current date and time
        now = datetime.now()
        date_time = now.strftime("%Y-%m-%d_%H-%M-%S")
        model_pkl_file = f"model_{date_time}.pkl"

        # Save model to pickle file
        with open(model_pkl_file, 'wb') as f:
            pickle.dump(model_data, f)

        # Connect to MongoDB and insert the model data
        client = MongoClient('mongodb://localhost:27017/')  # Connect to MongoDB server
        db = client['2FA']  # Access 2FA database
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
