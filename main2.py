from model_trainer import ModelTrainer
from f3 import FaceRecognition

def main():
    # Train the model
    trainer = ModelTrainer()
    trainer.train_and_save_model()

    # Run face recognition
    face_recognition = FaceRecognition()
    face_recognition.run_recognition()

if __name__ == "__main__":
    main()
