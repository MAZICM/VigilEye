# f_recognition.py
import face_recognition
import os
import cv2
import numpy as np
def f_rec(face_recognition):
        detected_face = face_recognition.run_recognition()
        if detected_face:
            print(f"Detected Face: {detected_face}")
            return detected_face
        else:
            print("No face detected.")

class FaceRecognition:
    def __init__(self):
        self.known_face_encodings = []
        self.known_face_names = []

        self.encode_faces()

    def encode_faces(self):
        for image in os.listdir('faces'):
            face_image = face_recognition.load_image_file(os.path.join('faces', image))

            face_locations = face_recognition.face_locations(face_image)
            if len(face_locations) > 0:
                print(f"Face found in {image}")
                face_encoding = face_recognition.face_encodings(face_image)[0]

                self.known_face_encodings.append(face_encoding)
                self.known_face_names.append(image)
            else:
                print(f"No face found in {image}")

        print(self.known_face_names)

    def run_recognition(self):
        video_capture = cv2.VideoCapture(0)
        #video_capture = cv2.VideoCapture("http://192.168.0.102:4747/video")

        if not video_capture.isOpened():
            print("Video source not found ....")
            return None

        try:
            while True:
                ret, frame = video_capture.read()
                if not ret:
                    print("Error reading frame.")
                    break

                small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
                rgb_small_frame = np.ascontiguousarray(small_frame[:, :, ::-1])

                face_locations = face_recognition.face_locations(rgb_small_frame)
                face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)

                detected_face = None

                for face_encoding in face_encodings:
                    matches = face_recognition.compare_faces(self.known_face_encodings, face_encoding)
                    name = 'Unknown'
                    confidence = 'Unknown'

                    face_distances = face_recognition.face_distance(self.known_face_encodings, face_encoding)
                    best_match_index = np.argmin(face_distances)

                    if matches[best_match_index]:
                        name = self.known_face_names[best_match_index]
                        name = name.split(".")[0]
                        confidence = self.face_confidence(face_distances[best_match_index])

                        detected_face = f'{name}'
                        break

                if detected_face:
                    break

                cv2.imshow('Face Reco', frame)
                if cv2.waitKey(1) == ord('q'):
                    break

        except Exception as e:
            print(f"An error occurred: {e}")
        finally:
            video_capture.release()
            cv2.destroyAllWindows()

        return detected_face

    def face_confidence(self, face_distance):
        if np.max(face_distance) == np.min(face_distance):
            return "Unknown"
    
        normalized_distance = (face_distance - np.min(face_distance)) / (np.max(face_distance) - np.min(face_distance))
        threshold_multiplier = 1.5
    
        dynamic_threshold = np.percentile(normalized_distance, 50) * threshold_multiplier
    
        if normalized_distance > dynamic_threshold:
            linear_val = (1.0 - normalized_distance) / (dynamic_threshold * 2.0)
            return f"{round(linear_val * 100, 2)}%"
        else:
            power_arg = max((normalized_distance / dynamic_threshold - 0.5) * 2, 0)
            value = (1.0 - np.power(power_arg, 0.2)) * 100
            return f"{round(value, 2)}%"
