import face_recognition
import cv2
import numpy as np
import os
import pickle

class FaceRecognition:
    known_faces_dir = 'known_faces'
    tolerance = 0.000000001
    frame_thickness = 3
    font_thickness = 2
    model = 'cnn'
    model_pkl_file = "face_recognition_model.pkl"  # Path to save the trained model

    def __init__(self, known_faces_dir='known_faces', tolerance=0.45, frame_thickness=3, font_thickness=2, model='cnn'):
        self.known_faces_dir = known_faces_dir
        self.tolerance = tolerance
        self.frame_thickness = frame_thickness
        self.font_thickness = font_thickness
        self.model = model

        self.known_face_encodings = []
        self.known_face_names = []
        self.encode_faces()

        #self.video_capture = cv2.VideoCapture(0)
        #self.video_capture = cv2.VideoCapture("http://192.168.0.102:4747/video")

        self.frame_count = 0

    def encode_faces(self):
        for name in os.listdir(self.known_faces_dir):
            for filename in os.listdir(os.path.join(self.known_faces_dir, name)):
                image = face_recognition.load_image_file(os.path.join(self.known_faces_dir, name, filename))
                

                face_locations = face_recognition.face_locations(image)
                if len(face_locations) > 0:
                    print(f"Face found in {filename}")
                    encoding = face_recognition.face_encodings(image)[0]
                    self.known_face_encodings.append(encoding)
                    self.known_face_names.append(name)

                    self.known_face_encodings.append(encoding)
                    
                else:
                    print(f"No face found in {filename}")

        # Save the trained model
        self.save_model()

    def save_model(self):
        model_data = {
            'known_face_encodings': self.known_face_encodings,
            'known_face_names': self.known_face_names,
            'tolerance': self.tolerance,
            'frame_thickness': self.frame_thickness,
            'font_thickness': self.font_thickness,
            'model': self.model
        }

        with open(self.model_pkl_file, 'wb') as f:
            pickle.dump(model_data, f)

    def run_recognition(self):
        #video_capture = cv2.VideoCapture("http://192.168.0.102:4747/video")
        video_capture = cv2.VideoCapture(0)
        while True:

            ret, frame = video_capture.read()
            if not ret:
                print("Error reading frame.")
                break

            small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
            rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

            face_locations = face_recognition.face_locations(rgb_small_frame, model=self.model)
            face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)

            for face_encoding, face_location in zip(face_encodings, face_locations):
                top, right, bottom, left = [i * 4 for i in face_location]  # Scale back up face locations
                name = 'Unknown'
                accuracy = None

                # Perform face matching
                matches = face_recognition.compare_faces(self.known_face_encodings, face_encoding, tolerance=self.tolerance)
                if True in matches:
                    first_match_index = matches.index(True)
                    name = self.known_face_names[first_match_index]

                    # Calculate accuracy
                    face_distances = face_recognition.face_distance(self.known_face_encodings, face_encoding)
                    accuracy = 100 - (face_distances[first_match_index] * 100)
                    print(f"Detected Face: {name}")
                    print(f"Accuracy : {accuracy}")
                    cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), self.frame_thickness)
                    cv2.putText(frame, f"{name} ({accuracy:.2f}%)" if accuracy is not None else name, (left + 6, bottom - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), self.font_thickness)
                    cv2.imwrite("detected_face.jpg", frame)
                    return name
                color = (0, 255, 0) if name != 'Unknown' else (0, 0, 255)
                cv2.rectangle(frame, (left, top), (right, bottom), color, self.frame_thickness)
                cv2.putText(frame, f"{name} ({accuracy:.2f}%)" if accuracy is not None else name, (left + 6, bottom - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, self.font_thickness)

            #cv2.imshow('Face Recognition', frame)

            # Exit loop if 'q' is pressed
            #if cv2.waitKey(1) & 0xFF == ord('q'):
                #break

            self.frame_count += 1
        
        # Release video capture and close OpenCV windows
        self.video_capture.release()
        cv2.destroyAllWindows()
'''
# Main function to run face recognition
def main():
    face_recognition = FaceRecognition()
    face_recognition.run_recognition()

if __name__ == "__main__":
    main()
'''