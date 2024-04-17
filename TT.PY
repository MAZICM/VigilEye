from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO
import paho.mqtt.client as mqtt
from model_trainer import ModelTrainer
from f3 import FaceRecognition
from pymongo import MongoClient
import threading
import time

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes
socketio = SocketIO(app, cors_allowed_origins="*")  # Initialize SocketIO with CORS enabled

face_recognition = FaceRecognition()
model_trainer = ModelTrainer()

# MQTT settings
mqtt_broker_address = "10.200.2.77"  # Update with your MQTT broker address
mqtt_topic = "rfid/cards"  # Update with your MQTT topic

latest_cardID = "0000"  # Initialize latest_cardID variable

def f_rec(face_recognition):
    detected_face = face_recognition.run_recognition()
    if detected_face:
        return detected_face
    else:
        print("No face detected.")

def delayed_publish(client, message, delay):
    time.sleep(delay)
    print("5 secs Done .... Door Closed")
    client.publish("2FA/results", message)
    print("\n\nScan Card Please : ")

def get_expected_cardID(detected_face):
    client = MongoClient('mongodb://localhost:27017/')
    db = client['2FA']
    collection = db['users']
    
    user = collection.find_one({'name': detected_face})
    if user:
        expected_cardID = user['cardID']
        return expected_cardID
    else:
        print(f"No user found with the name: {detected_face}")
        return None
def on_message(client, userdata, message):
    global latest_cardID  # Use the global variable to store the latest card ID
    print("Received MQTT message:", str(message.payload.decode("utf-8")))
    print("\n\n")
    if message.topic == "rfid/cards":
        CardID = message.payload.decode('utf-8')
        print("Detected CardID: " + CardID)
        
        # Update latest_cardID
        latest_cardID = CardID
        socketio.emit("latest_cardID", {"cardID": CardID})
        detected_face = f_rec(face_recognition)
        if detected_face:
            expected_cardID = get_expected_cardID(detected_face)
            print("expected")
            print(expected_cardID)
            if expected_cardID == CardID:
                print("ACCESS Granted for 5 secs")
                  # Emit event to the client
                threading.Thread(target=delayed_publish, args=(client, "Access refused", 5)).start()
            else:
                print("ACCESS Refused")
                #socketio.emit("latest_cardID", {"cardID": "Access refused"})  # Emit event to the client
                print("\n\nScan Card Please : ")


# Set up MQTT client
mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
mqtt_client.on_message = on_message
mqtt_client.connect(mqtt_broker_address)
mqtt_client.subscribe(mqtt_topic)
mqtt_client.loop_start()

# Endpoint to retrieve the latest card ID
@app.route('/latest_cardID', methods=['GET'])
def get_latest_cardID():
    global latest_cardID
    if latest_cardID:
        return jsonify({'latest_cardID': latest_cardID})
    else:
        return jsonify({'error': 'No card ID received'}), 404
    
@app.route('/api/getOwnerName', methods=['GET'])
def get_owner_name():
    card_id = request.args.get('cardID')
    client = MongoClient('mongodb://localhost:27017/')
    db = client['2FA']
    collection = db['users']

    if card_id:
        user = collection.find_one({'cardID': card_id})
        if user:
            print("NOM : ")
            print(user['name'])
            return jsonify({'ownerName': user['name']})
        else:
            return jsonify({'error': 'User not found'}), 404
    else:
        return jsonify({'error': 'Missing cardID parameter'}), 400


if __name__ == '__main__':
    socketio.run(app, host="127.0.0.1", port=5000)
