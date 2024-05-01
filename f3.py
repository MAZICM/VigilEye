import face_recognition
import cv2
import pickle
from pymongo import MongoClient
import time
import base64
    # Convert the image to Base64
def image_to_base64(image_path):
    with open(image_path, "rb") as img_file:
        base64_str = base64.b64encode(img_file.read()).decode('utf-8')
    return base64_str

class FaceRecognition:
    

    def __init__(self, socketio=None,model_data=None, known_faces_dir='known_faces', tolerance=0.45, frame_thickness=3, font_thickness=2, model='cnn'):
        self.known_faces_dir = known_faces_dir
        self.socketio = socketio
        self.tolerance = tolerance
        self.frame_thickness = frame_thickness
        self.font_thickness = font_thickness
        self.model = model
        self.last_frame = None

        if model_data:
            self.known_face_encodings = model_data['known_face_encodings']
            self.known_face_names = model_data['known_face_names']
            self.tolerance = model_data.get('tolerance', 0.5)
            self.frame_thickness = model_data.get('frame_thickness', 3)
            self.font_thickness = model_data.get('font_thickness', 2)
            self.model = model_data.get('model', 'cnn')
            print("HEEERE")
        else:
            self.load_model_from_mongodb()


        #self.video_capture1 = cv2.VideoCapture("http://192.168.0.107:4747/video")
        #self.video_capture = cv2.VideoCapture(0)
        


            
    def load_model_from_mongodb(self):
        client = MongoClient('mongodb://localhost:27017/')
        db = client['2FA']
        collection = db['AI-Models']

        latest_model_doc = collection.find_one(sort=[('_id', -1)])  # Get the latest model document
        model_bytes = latest_model_doc['model_bytes']

        with open('temp_model.pkl', 'wb') as f:
            f.write(model_bytes)

        with open('temp_model.pkl', 'rb') as f:
            model_data = pickle.load(f)
            print(model_data['known_face_names'])
            self.known_face_encodings = model_data['known_face_encodings']
            self.known_face_names = model_data['known_face_names']
            self.tolerance = model_data.get('tolerance', 0.5)
            self.frame_thickness = model_data.get('frame_thickness', 3)
            self.font_thickness = model_data.get('font_thickness', 2)
            self.model = model_data.get('model', 'cnn')

    
    def run_recognition(self):
        start_time = time.time() 
        self.frame_count = 0
         # Record the start time
        #self.video_capture = cv2.VideoCapture("http://192.168.0.107:4747/video")
        #self.video_capture = cv2.VideoCapture(0)
        
        
        time.sleep(2)
        #video_capture3 = cv2.VideoCapture(0)
        while time.time() - start_time < 10:  # Extend the recognition loop to 10 seconds
            self.video_capture = cv2.VideoCapture("http://192.168.0.108:4747/video")
            #self.video_capture =  cv2.VideoCapture(0)
            ret, frame = self.video_capture.read()
            if not ret:
                print("Error reading frame.")
                self.socketio.emit("ai_frame", {"frame": ""})
                self.video_capture.release()
                cv2.destroyAllWindows()
                break
            #cv2.imshow("Video Feed", frame)
            #Check if 3 seconds have elapsed
            #if time.time() - start_time > 10:
                #return 'Unknown'  # Return 'Unknown' if no face is detected within 3 seconds

            small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
            rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

            face_locations = face_recognition.face_locations(rgb_small_frame, model=self.model)
            face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)
            
            face_detected = False  # Flag to indicate if any face is detected
            time.sleep(2)
            
            for face_encoding, face_location in zip(face_encodings, face_locations):
                top, right, bottom, left = [i * 4 for i in face_location]  # Scale back up face locations
                name = 'Unknown'
                accuracy = None

                # Perform face matching
                matches = face_recognition.compare_faces(self.known_face_encodings, face_encoding, tolerance=self.tolerance)
                time.sleep(2)
                if True in matches:
                    first_match_index = matches.index(True)
                    name = self.known_face_names[first_match_index]
                    # Calculate accuracy&
                    face_distances = face_recognition.face_distance(self.known_face_encodings, face_encoding)
                    accuracy = 100 - (face_distances[first_match_index] * 100)
                    print(f"Detected Face: {name}")
                    print(f"Accuracy : {accuracy}")
                    cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), self.frame_thickness)
                    cv2.putText(frame, f"{name} ({accuracy:.2f}%)" if accuracy is not None else name, (left + 6, bottom - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), self.font_thickness)
                    cv2.imwrite("detected_face.jpg", frame)
                   # Save the image and convert to Base64
                    cv2.imwrite("detected_face.jpg", frame)
                    base64_image = image_to_base64("detected_face.jpg")
                    self.video_capture.release()
                    # Emit the Base64 image to Socket.IO
                    self.socketio.emit("ai_frame", {"frame": base64_image})
                   
                    self.video_capture.release()
                    cv2.destroyAllWindows()
                    
                    return name
                color = (0, 255, 0) if name != 'Unknown' else (0, 0, 255)
                cv2.rectangle(frame, (left, top), (right, bottom), color, self.frame_thickness)
                cv2.putText(frame, f"{name} ({accuracy:.2f}%)" if accuracy is not None else name, (left + 6, bottom - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, self.font_thickness)
                
                face_detected = True  # Set the flag to True if any face is detected
            time.sleep(2)
            # If no face is detected, return "Unknown" and break the loop
            if not face_detected:
                cv2.imwrite("detected_face.jpg", frame)
                base64_image = image_to_base64("detected_face.jpg")
                self.socketio.emit("ai_frame", {"frame": base64_image})
                self.video_capture.release()
                cv2.destroyAllWindows()
                return 'Unknown'
            

            

        self.video_capture.release()
        #self.video_capture = cv2.VideoCapture("http://192.168.0.107:4747/video")
        cv2.destroyAllWindows()


'''


def main():
    client = MongoClient('mongodb://localhost:27017/')
    db = client['2FA']
    collection = db['AI-Models']

    latest_model_doc = collection.find_one(sort=[('_id', -1)])  # Get the latest model document
    model_bytes = latest_model_doc['model_bytes']

    with open('temp_model.pkl', 'wb') as f:
        f.write(model_bytes)

    with open('temp_model.pkl', 'rb') as f:
        model_data = pickle.load(f)
        print(model_data)

    # Run face recognition
    face_recognition = FaceRecognition(model_data)
    print(f"Using model: {face_recognition.model}")
    face_recognition.run_recognition()


if __name__ == "__main__":
    main()
'''