import face_recognition
import os
import pickle

class ModelTrainer:
    def __init__(self, known_faces_dir='known_faces', model_pkl_file="face_recognition_model3.pkl"):
        self.known_faces_dir = known_faces_dir
        self.model_pkl_file = model_pkl_file

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

        with open(self.model_pkl_file, 'wb') as f:
            pickle.dump(model_data, f)

def main():
    # Train the model
    trainer = ModelTrainer()
    trainer.train_and_save_model()



if __name__ == "__main__":
    main()
