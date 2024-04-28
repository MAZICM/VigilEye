

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
    global latest_cardID
    logging.info("Received MQTT message: %s", str(message.payload.decode("utf-8")))

    if message.topic == "rfid/cards":
        cardID = message.payload.decode('utf-8')
        logging.info("Detected CardID: %s", cardID)
        latest_cardID = cardID
        
        # Get the owner's name based on card ID from MongoDB
        user = collection.find_one({'cardID': cardID})
        owner_name = user['name'] if user else 'Unknown'
        logging.info("Owner name: %s", owner_name)

        # Emit both cardID and owner's name
        socketio.emit("latest_cardID", {"cardID": cardID, "ownerName": owner_name})

        # Ensure synchronous operation with f_rec
        detected_face = f_rec(face_recognition)
        if detected_face is None:
            logging.warning("No face detected")
            socketio.emit("face_detection_error", {"error": "No face detected. Please try again."})
            return  # Early exit if no face is detected

        logging.info("Detected face: %s", detected_face)

        expected_cardID = get_expected_cardID(detected_face)
        if expected_cardID is None:
            logging.warning("No user found with the detected face: %s", detected_face)
            socketio.emit("access_refused", {"status": "refused", "message": "Access denied. No matching user found."})
            return  # Early exit if no expected cardID is found

        logging.info("Expected CardID: %s", expected_cardID)

        # Check if the expected card ID matches the detected card ID
        if expected_cardID == cardID:
            logging.info("ACCESS Granted for 5 secs")
            
            # Emit success event
            socketio.emit("access_granted", {"status": "granted"})
            
            # Start a thread to handle delayed actions without blocking
            threading.Thread(
                target=delayed_publish,
                args=(client, "Access refused", 5)  # Message is "Access refused" after 5 seconds
            ).start()

        else:
            logging.info("ACCESS Refused")
            socketio.emit("access_refused", {"status": "refused", "message": "Card ID does not match."})

        # Final message for the console log
        logging.info("End of on_message processing")

# Initialize MQTT client
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
print("Scan Card Please : ")
client.on_message = on_message

# Connect to MQTT broker
client.connect("192.168.1.103", 1883)

# Subscribe to topics
client.subscribe("rfid/cards")

# Start the MQTT client loop
client.loop_forever()



