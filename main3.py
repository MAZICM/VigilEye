

import paho.mqtt.client as mqtt
import time
import threading
from model_trainer import ModelTrainer
from f3 import FaceRecognition

from pymongo import MongoClient

def get_expected_cardID(detected_face):
    # Connect to MongoDB
    client = MongoClient('mongodb://localhost:27017/')
    db = client['2FA']  # Assuming your database is named '2FA'
    collection = db['users']  # Assuming your collection is named 'users'
    
    # Query the database to retrieve the expected CardID for the detected face
    user = collection.find_one({'name': detected_face})
    if user:
        expected_cardID = user['cardID']
        return expected_cardID
    else:
        print(f"No user found with the name: {detected_face}")
        return None

face_recognition = FaceRecognition()

print( type(face_recognition))

def f_rec(face_recognition):
    detected_face = face_recognition.run_recognition()
    if detected_face:
        #print(f"Detected Face: {detected_face}")
        return detected_face
    else:
        print("No face detected .")



def delayed_publish(client, message, delay):
    time.sleep(delay)
    print("5 secs Done .... Door Closed")
    client.publish("2FA/results", message)
    print("\n\nScan Card Please : ")

def on_message(client, userdata, message):
    print("\n\n")
    if message.topic == "rfid/cards":
        CardID = message.payload.decode('utf-8')
        print("Detected CardID: " + CardID)
        
        # Perform facial recognition
        print("Face Detection Process .... ")
        detected_face = f_rec(face_recognition)
        if detected_face:
            # Get the expected CardID for the detected face
            expected_cardID = get_expected_cardID(detected_face)
            print("expected")
            print(expected_cardID)
            if expected_cardID == CardID:
                print("ACCESS Granted for 5 secs")
                client.publish("2FA/results", "Access authorised")
                # Schedule publishing of "Access refused" after 5 seconds
                threading.Thread(target=delayed_publish, args=(client, "Access refused", 5)).start()
            else:
                print("ACCESS Refused")
                client.publish("2FA/results", "Access refused")
                print("\n\nScan Card Please : ")

# Initialize MQTT client
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
print("Scan Card Please : ")
client.on_message = on_message

# Connect to MQTT broker
client.connect("192.168.11.238", 1883)

# Subscribe to topics
client.subscribe("rfid/cards")

# Start the MQTT client loop
client.loop_forever()



